# Phase A5 — Logging + Error-Handling Hygiene Report

## Print() Count Before / After

| Package / File | Before | After (active) | Notes |
|---|---|---|---|
| `conacq/bias/bias_generator.py` | 5 | 0 | Converted to `logger.info` |
| `explanation/operations/algorithms/profiler.py` | 20 | 0 | Converted to `logger.info` |
| `explanation/operations/algorithms/fastdiag.py` | 0 | 0 | Already commented out pre-A5 |
| `explanation/operations/algorithms/quickxplain.py` | 0 | 0 | Already commented out pre-A5 |
| **conacq total** | **5** | **0** | |
| **explanation total** | **20** | **0** | |
| **user_prompt.py residual** | — | **10** | Kept: interactive membership-query UX |

Remaining grep hits in `conacq/example_generators/random_sampling.py` (3),
`conacq/examples/data_structures.py` (1), `conacq/eval/__init__.py` (1) are
docstring `>>> print(...)` lines — not active statements.
Hits in `fastdiag.py` (3) and `quickxplain.py` (3) are `# print(...)` debug
comments already present before this change.

## From-e Fixes (traceback-losing re-raises)

AST scan (`ast.ExceptHandler` → bare `raise` without `.cause`) found exactly
one site:

- `explanation/operations/algorithms/checker.py:226`
  ```python
  # Before
  raise RuntimeError(f"Failed to run SAT4J: {e}")
  # After
  raise RuntimeError(f"Failed to run SAT4J: {e}") from e
  ```
  Chaining preserves the original subprocess/OS exception in `__cause__`,
  so tracebacks show the full call chain when SAT4J invocation fails.

## executor.py:285 Swallow Decision — KEEP (log + continue)

**Decision:** keep the swallow; add `logger.debug(..., exc_info=True)`.

**Rationale:** `_store_from_future` is the done-callback on a speculative
(ahead-of-time) future submitted by `MemoizingExecutor.submit`. The method
writes the result into the cache if the check succeeded. Failure here means:

1. The speculative check encountered an error (e.g. future was cancelled,
   assumption set invalid for this lookahead round).
2. Nothing is written to the cache for this key.
3. When the synchronous call path later needs this value, it calls the inner
   executor directly and handles any real error at that boundary — the error
   is NOT suppressed from the caller's perspective.

Propagating the exception from a `Future.add_done_callback` would send it to
the thread pool's exception handler (not to any caller), so raising would be
incorrect anyway. The swallow is the only safe option; the comment now
documents why.

The flaky `test_consistency_check_count_parity` test (concurrency race) is in
the same file — the log-only change does not touch the parallel execution path
or counter logic, so no interaction.

## Files Modified

| File | Change |
|---|---|
| `conacq/bias/bias_generator.py` | Added `import logging` + `logger`; replaced 5 `print()` with `logger.info` |
| `explanation/operations/algorithms/profiler.py` | Added `import logging` + `logger`; replaced 20 `print()` in `print_summary` with `logger.info` |
| `explanation/operations/algorithms/checker.py` | Added `from e` to bare re-raise at line 226 |
| `explanation/operations/algorithms/executor.py` | Added `import logging` + `logger`; replaced bare `pass` swallow with `logger.debug(..., exc_info=True)` + explanatory comment |

## Test Results

```
437 passed, 1 warning in 51.92s
```

Baseline: 437 passed, 1 warning — **no regressions**.

## Deviations from Spec

None. `cached.py`, `ground_truth.py` had zero print() calls — no edits needed.
`user_prompt.py` intentionally untouched (interactive UX exception confirmed).

## Unresolved Questions

None.
