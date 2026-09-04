---
phase: 1
title: Timeout Rail
status: completed
effort: S
priority: P1
dependencies: []
---

# Phase 1: Timeout Rail

## Overview

Add a **cooperative wall-clock timeout** to QuAcq oracle learning so a large KB (busybox:
854 features, |B| 6635) always terminates. This is net-new: `QuAcq.learn` currently only
guards on `max_queries` (`quacq.py:159-163`), and `QuAcqRunner.__init__` has no timeout
param. On timeout the partial theory learned so far is returned with
`convergence_reason='timeout'`.

> **[Red-team C-4/H-4] Rail hierarchy — reproducibility first.** `max_queries` is the
> **primary, deterministic** rail; the wall-clock timeout is a **safety net of last resort**,
> because a wall-clock `break` truncates learning at a machine-load-dependent point → a
> non-reproducible partial theory. Therefore: **size `max_queries` per KB so it fires *before*
> the timeout** (busybox `|B|=6635` needs a budget scaled to the model, not the current 5000 —
> the counter is shared with FindScope/FindC, so effective constraints learned ≪ budget; see
> Phase 3 per-KB override). A KB that can only terminate via the timeout must be reported as
> non-converged (Phase 2 H-3), never as a clean number. Record `max_queries`+`timeout_s` as
> provenance (Phase 2/3) so a timed row is traceable to the budget that produced it.

## Requirements

- Functional: `QuAcq.learn(mode='oracle')` halts when a caller-supplied deadline passes and
  reports `convergence_reason='timeout'`; the already-learned constraints and query count
  are preserved and returned.
- Functional: `QuAcqRunner` accepts `timeout_s` and threads it into the oracle path only.
- Non-functional: **zero behaviour change when `timeout_s is None`** (the current default) —
  the example-only / existing callers must be byte-identical. No new dependencies; use
  `time.monotonic()` (import `time` in `quacq.py`).

## Architecture

- **Deadline, not duration.** `QuAcqRunner._run_oracle_mode` computes
  `deadline = time.monotonic() + self.timeout_s` right before calling `learn`, and passes it
  as `deadline=`. Computing the deadline at the call boundary keeps model-build / checker
  setup out of the budget (those already happened in `__init__` / `run`).
- **Check site = top of the outer loop**, mirroring the existing `max_queries` guard at
  `quacq.py:160`. The timeout is therefore checked *between outer iterations*: an in-flight
  `FindScope`/`FindC` runs to completion before the next check. **[Red-team M-1] The overrun
  is NOT "one binary search."** FindScope double-recurses (`findscope.py:84-85`, two recursive
  calls) issuing an oracle SAT solve per node → `O(|scope|·log|X|)` solves, and the same outer
  iteration then runs FindC (`findc.py:83-86,117-142`, candidate loop + `DiscriminatingGenerator`
  `find_model` per pair ≈ `O(k²)` solves). On busybox (854 vars) one overrunning iteration can
  be **tens of seconds to minutes** of large-model SAT work. So the wall-clock cap is a **floor,
  not a ceiling** — honest wording required, and Phase 4 must measure a worst-case single
  iteration on a mid-size KB before quoting any per-learn wall-clock. Threading the deadline
  into FindScope/FindC for a tighter bound is out of scope (YAGNI); the deterministic
  `max_queries` rail (C-4) is the real reproducibility guarantee, not the timeout.
- The final `Reduce` (`quacq.py:249-255`) runs after the loop regardless — timeout stops
  *acquisition*, not the cleanup that produces a valid KB.
- `convergence_reason='timeout'` is a **new enum value**; no existing string is reused, so
  downstream code that switch/compares on it is unaffected.

## Related Code Files

- Modify: `conacq/algorithms/quacq/quacq.py`
  - add `import time` (top of file)
  - `learn(...)` signature: add `deadline: Optional[float] = None` (already imports
    `Optional`? verify — add if missing)
  - inside `while remaining_bias:` (after the `max_queries` guard at ~line 160):
    ```python
    if deadline is not None and time.monotonic() >= deadline:
        convergence_reason = 'timeout'
        logging.info('QuAcq wall-clock timeout hit (deadline reached)')
        break
    ```
  - Do **not** touch the `example_only` / `example_first` branches' semantics; `deadline`
    stays `None` for them (callers never pass it).
- Modify: `conacq/runners/quacq_runner.py`
  - `QuAcqRunner.__init__`: add `timeout_s: Optional[float] = None`; store `self.timeout_s`.
  - `_run_oracle_mode(...)`: compute `deadline` iff `self.timeout_s is not None`, pass
    `deadline=deadline` into `quacq.learn(**task_data, mode='oracle', max_queries=…, deadline=…)`.
  - `_run_example_mode`: **unchanged** (no `deadline`).

## Implementation Steps

1. `quacq.py`: add `import time`; extend `learn` signature with `deadline`; add the
   top-of-loop guard. Keep `max_queries` guard first (query budget is the primary rail).
2. `quacq_runner.py`: add `timeout_s` param + attribute; in `_run_oracle_mode` derive the
   deadline and pass it through. Leave `run()`/`_run_example_mode` signatures intact so
   `_eval_quacq_fold`'s existing `QuAcqRunner(bias, fm, solver, use_incremental=…)` +
   `runner.run(tr_pos, tr_neg)` call is unaffected.
3. Confirm `QuAcqResult`/`QuAcqRunResult` already carry `convergence_reason` (they do —
   `quacq.py:36`, `quacq_runner.py:36`) so no result-schema change is needed.

## Success Criteria

- [ ] With `timeout_s=None`, `QuAcq.learn` and `QuAcqRunner.run(...)` are behaviourally
      unchanged (existing `test_quacq.py` still green, no diffs in oracle/example outputs).
- [ ] A unit test drives oracle mode with a tiny `timeout_s` (e.g. `0.0` or a monkeypatched
      clock) on REAL-FM-7 and asserts `res.convergence_reason == 'timeout'` and
      `res.n_kb >= 0` (partial KB returned, no exception).
- [ ] A unit test with a generous `timeout_s` + small `max_queries` still converges via
      `max_queries`/`empty_bias` (timeout does not fire early).
- [ ] `deadline` never leaks into example modes (grep: `_run_example_mode` has no `deadline`).

## Risk Assessment

- **[M-1] Soft-ceiling overrun is a full FindScope+FindC, not one solve**: on busybox a single
  overrunning iteration can exceed the deadline by tens of seconds to minutes (evidence above).
  Mitigation: state the true bound in the runner docstring; do NOT claim 400 s is a cap. The
  reproducible bound is `max_queries`, not wall-clock.
- **[C-4/H-4] Wall-clock truncation is non-deterministic**: the learned KB at a timeout depends
  on machine load → not reproducible. Mitigation: for any KB that would rely on the timeout to
  stop, raise its `max_queries` so the deterministic rail fires first (Phase 3 per-KB budget),
  or report it non-converged (Phase 2 H-3). Provenance columns record which budget/timeout
  produced each row.
- **Testing time-based logic**: prefer injecting a fake `deadline` in the past (e.g.
  `time.monotonic()` captured then `timeout_s` effectively 0) over sleeping, to keep the test
  fast and deterministic. If a monkeypatch of `time.monotonic` is used, patch it in the
  `quacq` module namespace.
- **`Optional` import**: verify `from typing import Optional` (or equivalent) is present in
  `quacq.py`; add if missing (the file already uses `Literal`, `Sequence`, `Mapping`).
