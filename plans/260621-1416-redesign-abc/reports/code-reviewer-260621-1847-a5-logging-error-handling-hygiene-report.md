# Code Review — Stage A5: Logging + Error-Handling Hygiene

**Verdict: PASS**
**Status: DONE**

Date: 2026-06-21
Branch: feat/redesign-abc
Scope: uncommitted working-tree changes only (`git diff`), conacq/ + explanation/

## Scope

4 files, +49 / -37:
- `conacq/bias/bias_generator.py` (+8 -5)
- `explanation/operations/algorithms/checker.py` (+1 -1)
- `explanation/operations/algorithms/executor.py` (+11 -3)
- `explanation/operations/algorithms/profiler.py` (+29 -28)

Tests: `uv run --no-sync pytest tests/ -q` → 437 passed, 1 warning (known `TestSuiteReader` PytestCollectionWarning). No flaky failure this run.

## Overall Assessment

Clean, behavior-preserving logging-hygiene stage. Every print→logger.info conversion preserves exact message content; all `%`-style format strings have matching arg counts and types; no eager/side-effecting args. The `from e` chain and the executor swallow comment are correct. No assertion weakening, no plan-stage labels, scope correct. Ship it.

## Verification of Required Concerns

### 1. No behavior change (print→logger.info) — PASS
- bias_generator.py: 5 conversions, 0 active print() remain. Args are `len(...)` / `.value` — pure, no side effects. `%d`/`%s` specifiers match args (L242,244,247,249,261).
- profiler.py: all print() in `print_summary` + the "No profiling data available." early-return converted; 0 active print() remain. Every format string checked for spec/arg parity:
  - L810 `"  %s: %s"` ← pre-formatted `f"{key:45s}"`, `f"{value:>10,}"` (2/2) — alignment preserved by pre-formatting into %s.
  - L819-820 `"…Calls:  %8s  Total: %10.4fs  Mean: %10.6fs"` (3/3). `count` pre-formatted `f"{count:,}"` then `%8s` — identical to original `{count:>8,}`.
  - L822-823 (3/3), L825-826 (2/2), L831 (2/2), L833 (2/2), L841/843 (2/2).
  - Separator lines (`"=" * 70`, `"-" * 70`, `"\n" + …`) pass pre-built str, no placeholders/args — safe.
  - Emoji headers contain no `%` — safe.
- executor.py/checker.py: 0 print().
- **capsys/capfd: NONE in tests/** — no test captures stdout. Three tests reference `print_summary` (test_profiler.py:335,379) but invoke it as a smoke call and assert on `get_metric(...)` values, never on captured text. print→logger is invisible to assertions.

### 2. Untested-oracle constraint (red-team) — PASS
- `conacq/oracle/{cached.py, user_prompt.py, ground_truth.py}` NOT in working-tree diff → zero changes, no control-flow modification.
- user_prompt.py retains exactly 10 interactive print() (intentional, confirmed by count).

### 3. executor.py speculative-check swallow — PASS
- L286-299 `_store_from_future`: try/except Exception/finally structure IDENTICAL to before. Only change: body `pass` → `logger.debug("Speculative consistency check did not cache (key=%s)", key, exc_info=True)`.
- No new propagation, no new suppression. The future's own exception still reaches the synchronous caller via `is_consistent` (L247-249 `pending.set_exception(exc); raise`), unchanged and out of scope.
- Comment describes the invariant ("we never suppress a result the caller is waiting for"), NOT a plan stage. Good.
- Logging-only → cannot perturb parallel path or the known flaky `test_consistency_check_count_parity` (did not fail this run).

### 4. `from e` chaining (checker.py:226) — PASS
- `raise RuntimeError(f"Failed to run SAT4J: {e}") from e` — correct explicit chaining.
- Grep across conacq/ + explanation/ for other `except … as VAR:` blocks that raise a new exception without `from`: the only match is executor.py:247-249, which uses bare `raise` (re-raises original, preserves traceback/cause) — correct, not a defect, and out of scope. No missed bare re-raise.

### 5. Hygiene / scope — PASS
- No weakened/changed assertions in diff.
- No plan-stage labels (phase/A5/stage/red-team/finding codes/§) in any added line.
- All changes confined to conacq/ + explanation/.

## Findings

### Critical
None.

### High
None.

### Medium
None.

### Low / Informational (non-blocking, no action required for A5)
1. **executor.py:41** — `logger = logging.getLogger(__name__)` is placed BETWEEN the stdlib imports (L35-39) and the local package imports (L43-51). PEP8 prefers all imports grouped before module-level code. Cosmetic; does not affect behavior. Optional cleanup in a later stage.
2. **bias_generator.py:235-240** — `generate_bias` docstring header `Example output:` still shows the literal lines. Content still matches the new logger.info messages exactly (INFO output is identical text), so it remains accurate; only the framing is slightly less literal now that emission goes through logging. No change needed.
3. **profiler.py logger.info count = 22** vs spec's "20 in print_summary." Reconciled: spec counted only the 20 inside the print_summary body block; the total includes the separate `"No profiling data available."` early-return conversion (L775) plus the summary block. All prints converted; no missed/extra conversion — the delta is a counting boundary, not a defect.

## Positive Observations
- Format-arg conversions preserve column alignment by pre-formatting width/comma specs into `%s` args rather than dropping them — careful, correct.
- Lazy %-logging used throughout (no premature f-string evaluation); all interpolated args are side-effect-free.
- executor swallow comment is a model of "explain the invariant, not the origin."
- `from e` adds proper exception chaining without altering the error message or type.

## Metrics
- Tests: 437 passed / 0 failed / 1 known warning.
- Active print() remaining in A5-touched files: 0 (user_prompt.py's 10 intentionally kept, untouched).
- Assertion changes: 0. Plan-stage labels in code: 0. Out-of-scope file changes: 0.

## Unresolved Questions
None.
