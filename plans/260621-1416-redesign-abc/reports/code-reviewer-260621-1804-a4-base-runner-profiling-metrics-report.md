# Code Review — A4 BaseRunner Profiling + Metric Maps

Date: 2026-06-21
Reviewer: code-reviewer
Scope: uncommitted working-tree changes on `feat/redesign-abc`
Verdict: **PASS** (one MEDIUM consistency note, no blockers)

## Scope
- `conacq/runners/base_runner.py` (+106/-? ; new `_run_with_profiling`)
- `conacq/runners/congen_runner.py` (+85/-103)
- `conacq/runners/quacq_runner.py` (refactor to base)
- `tests/test_runners_characterization.py` (NEW, 44 tests) — verified count = 44
- Full suite: `uv run --no-sync pytest tests/ -q` → **420 passed, 1 warning, 61s** (known flaky `test_consistency_check_count_parity` passed)

## Verdicts on the two judgment calls

### 1. `is_consistent_calls` reclassification (ConGen) — verdict: SAFE, but mislabeled (NOT genuine nondeterminism on this path)

Brief framing ("genuine nondeterminism — incremental SAT cache state; subagent pinned 1656, it varied to 1647") is **not reproduced**. Empirical:
- ConGen `is_consistent_calls` = **1647**, stable across 4 in-process runs AND 3 fresh processes.
- QuAcq `is_consistent_calls` = **1996**, stable across fresh processes.
- All other counts stable: n_kb=19, n_mss=152, consistency_checks=452, acqmss_calls=519, is_consistent_test_cases_calls=452, redundancy_consistency_checks=153 (ConGen); n_queries=17, findscope=15, findc=1, reduce=1, dis_gen=0 (QuAcq).

**Drift ruled out** (3 independent lines of evidence):
1. Structural: the refactor does not touch the algorithm's solver-call sequence. `_run_with_profiling` preserves exact order shuffle→`CheckerFactory.create_from_task`→`algorithm_fn`. The only relocation is `prepare_task()` moving OUTSIDE the profiler timer.
2. `prepare_task` / `ConGenTaskPreparation` / `GenerateNE` receive NO run-profiler (`task_preparation.py` has zero profiler refs; the profiler-instrumented checker is created AFTER prepare in both old and new code). So `is_consistent_calls` could never have included prepare-phase calls in either version. Moving prepare outside the timer cannot change any profiler COUNTER — only the `runtime_ms` wall-clock.
3. Empirical stability at 1647 + identical algorithm path ⇒ the pre-refactor value was also 1647. **1656 was the subagent's bad initial pin, not a real baseline.**

Conclusion: the relaxation to presence/lower-bound (`> 0` + isinstance, `test_runners_characterization.py:105-110`) is **not a forbidden weakening masking drift** — it is *overly cautious*. The genuine nondeterminism documented by the repo's known-flaky `test_consistency_check_count_parity` is specific to the **parallel `ProcessExecutor`** speculative-submit path (`tests/test_executor.py:127-163`), which the characterization tests do NOT exercise (they run default serial `use_incremental=True`). So on this path the metric is deterministic and *could* have been exact-pinned at 1647.

Confirmed required invariants hold (brief item 1a/1b):
- (a) ALL algorithm counts EXACT-pinned and verified stable: n_kb, n_mss, acqmss_calls, consistency_checks, is_consistent_test_cases_calls(=452), redundancy_consistency_checks, n_queries, convergence_reason, quacq/findscope/findc/dis_gen/reduce_calls, KB shape (constraints, clause counts, bg, redundant=134).
- (b) Only ConGen `is_consistent_calls` (+ all timing/memory) is presence-only. QuAcq `is_consistent_calls` is EXACT-pinned at 1996 — confirmed deterministic.

### 2. Circular-import fix (method-local `PerformanceMetrics`) — verdict: LEGIT and behavior-preserving

Genuine pre-existing latent bug, correctly fixed. Confirmed by stashing the working tree to HEAD:
- HEAD's `congen_runner.py`/`quacq_runner.py` import `PerformanceMetrics` at module level → cycle `conacq.runners.congen_runner → conacq.eval(.__init__/result_loader) → conacq.runners` (partially-initialized package). Direct `import conacq.runners.congen_runner` raises `ImportError: cannot import name 'ConGenRunner' ... circular import`. All 44 characterization tests ERROR against HEAD with this trace.
- The fix moves the import inside `get_performance_metrics()` (deferred), breaking the cycle. Same `PerformanceMetrics` symbol, same call, just lazy. No runtime semantic change — `get_performance_metrics` constructs an identical object. Full suite green confirms.
- Note: `base_runner.get_performance_metrics` already used this deferred pattern at HEAD; only the two runner overrides were newly converted. Consistent, not a smell.

Caveat on the safety-net claim: the test header says "written BEFORE the refactor so they run green against current code." Literally, against HEAD they ERROR (the cycle). They are valid safety-net tests **for the refactored code** — the circular-import fix is correctly bundled into the same change so the tests can run at all. Not a blocker; worth noting the header is slightly inaccurate.

## Other verifications (all pass)

3. **BaseRunner extraction behavior-preserving** — 44 tests pin exact deterministic counts + KB shape, all pass. `_run_with_profiling` reproduces the original tracemalloc/profiler/checker lifecycle exactly. Note: `runtime_ms` (the `*_total_time` timer) no longer includes `prepare_task()` time since prepare moved outside the timer. This is a timing metric (presence-only), so no count impact, but it IS a small semantic change to what `runtime_ms` measures. Acceptable; flag for awareness.
4. **shuffle dedup correct** — single definition at `base_runner.py:168-170`: `random.Random(shuffle_seed).shuffle(task.set_c)` only when `shuffle_seed is not None`. Seed semantics identical to both originals. `_learn_params_from_task` captures `task.set_c` by reference, so the in-place shuffle still propagates (QuAcq). QuAcq's dual seed use (set_c shuffle in base + `QueryProvider(seed=shuffle_seed)` in `_run_example_mode`) is independent and matches the original exactly.
5. **metric-map generic** (C2 handoff) — `{key: callable(profiler)->value}`, keys opaque, plumbed via `{key: fn(profiler)}` + `**extracted`. No `PerformanceMetrics`/`RunMetrics` field names baked into `base_runner._run_with_profiling`. The only `PerformanceMetrics` ref in base is the deferred import in `get_performance_metrics` (unrelated to the map). Sink is freely swappable.
6. **No collateral changes** — only 3 source files + 1 new test touched (conacq-only). `_base_to_dict`, both `to_dict` overrides, and both result-dataclass field sets are **byte-identical to HEAD** (verified via diff). No on-disk JSON format change, no field add/remove/reorder, no backwards-compat break. `last_task` comment/semantics unchanged. No plan-stage labels in code comments (the word "stage" at base_runner.py:90 is generic English, not a plan ref).

## Findings by severity

### MEDIUM
- **M1 — Inconsistent `is_consistent_calls` assertion policy.** ConGen relaxes it to presence-only (`test:105-110`) while QuAcq pins it exact at 1996 (`test:220-221`). Both are deterministic on the serial path (verified). The ConGen relaxation is unnecessary; either pin ConGen at 1647 too (preferred — stronger safety net, drift verified absent) or document why the two runners differ. Not blocking: the relaxation only loses sensitivity, it does not hide current drift.

### LOW
- **L1 — Test docstring inaccuracy.** `test_runners_characterization.py:5-7` claims the tests "run green against the current [pre-refactor] code." They ERROR against HEAD due to the circular import. Reword to note the import fix is a prerequisite. Cosmetic.
- **L2 — `runtime_ms` semantic drift.** Now excludes `prepare_task()` time (prepare moved outside the `*_total_time` timer). Timing metric, presence-only asserted, so harmless — but if any downstream report compares `runtime_ms` across the refactor boundary it will see slightly smaller values. Worth a one-line note in the commit/PR.
- **L3 — `current` unused.** `base_runner.py:181` `current, peak = tracemalloc.get_traced_memory()` — `current` unused (carried over verbatim from both originals). Trivial.

## Positive observations
- Clean DRY collapse; ~150 cloned lines → one path. Lambdas in metric maps are readable and self-documenting.
- Drift guard (exact-pinned counts + KB shape) is well-constructed and genuinely catches algorithm-path regressions.
- Bundling the circular-import fix with the tests that expose it is the correct sequencing.
- Reference-semantics of the deduped shuffle correctly preserved — a subtle point handled right.

## Recommended actions (none blocking)
1. (M1) Pin ConGen `is_consistent_calls` at 1647 OR add a comment explaining the ConGen/QuAcq asymmetry.
2. (L1) Fix the test docstring re: pre-refactor green claim.
3. (L2) Note the `runtime_ms`-excludes-prepare change in the PR description.

## Metrics
- Tests: 420 passed / 1 warning (full suite); 44/44 characterization pass.
- Files changed: 3 source + 1 new test (conacq-only).
- Serialization & dataclass fields: byte-identical to HEAD (verified).

## PASS/FAIL: **PASS** for A4.
Behavior-preserving, scoped, format-stable, no forbidden count weakening, circular-import fix legit. M1 is a polish item, not a gate.

## Unresolved questions
1. Should ConGen `is_consistent_calls` be re-pinned to 1647 (drift verified absent) for parity with QuAcq's exact pin? (My recommendation: yes.) — needs owner decision, not a blocker.
