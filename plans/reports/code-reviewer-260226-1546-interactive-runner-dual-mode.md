# Code Review: InteractiveRunner Dual-Mode Refactoring

**Date:** 2026-02-26
**Reviewer:** code-reviewer
**Scope:** InteractiveRunner rewrite + callers (run_interactive, cross_validation, run_cv)
**LOC:** ~280 (runner) + ~190 (app) + ~410 (CV) + ~210 (run_cv)

---

## Overall Assessment

Clean, well-structured refactoring. The runner correctly mirrors ConGenRunner's pattern: file-path constructor, dual-mode `run()`, profiler_session scoping. Duck-typing contract with `_run_cv_loop` is satisfied. Two medium-priority issues found; no critical bugs.

---

## Critical Issues

None.

---

## High Priority

### H1. `to_dict()` omits `kb_clauses` field

`InteractiveRunResult.to_dict()` (line 51-66) includes `kb_constraints` and `bg_clauses` but omits `kb_clauses`. Compare with `ConGenRunResult.to_dict()` which also omits `kb_clauses` from its serialized dict -- so this is **consistent with the existing pattern**. However, if any downstream consumer expects `kb_clauses` in the JSON (e.g., `extract_results.py` or KB comparison tools), this would silently lose data.

**Verdict:** Consistent with ConGenRunner. No action needed unless a downstream consumer expects it.

### H2. `profiler_session` sets global profiler (concurrency hazard)

`profiler_session()` calls `use_global_profiler()` which mutates the module-level `gprofiler`. In `_run_cv_loop`, `runner.run()` is called N times sequentially, so each fold's profiler session replaces the previous global. This is safe for sequential execution but would break if folds were ever parallelized. ConGenRunner has the same pattern, so this is a **known project-wide design constraint**, not a regression.

**Verdict:** Acceptable. Same pattern as ConGenRunner.

---

## Medium Priority

### M1. `tracemalloc.start()` nesting across CV folds

`InteractiveRunner.run()` calls `tracemalloc.start()` / `tracemalloc.stop()` on every invocation (lines 165, 194-195). In the CV loop, this means `tracemalloc.start()` is called N times, each after a `stop()`. CPython handles this correctly -- `start()` after `stop()` restarts tracing. However, if a caller has already started `tracemalloc` before calling `run()`, the `stop()` in `finally` will stop the caller's tracing unexpectedly.

ConGenRunner has the identical pattern (lines 180, 216-217), so this is **consistent**, but worth noting as a latent edge case.

**Verdict:** Consistent with ConGenRunner. Document that callers must not have active tracemalloc.

### M2. Double bias shuffle in example mode

In `_run_example_mode()` (lines 249-267):
1. `from_examples()` receives `seed=shuffle_seed` and uses it to shuffle the ExampleProvider's internal pool (line 258)
2. Then lines 263-266 also shuffle `learner.task.bias` with the same `shuffle_seed`

The ExampleProvider shuffle and the bias shuffle serve different purposes (example ordering vs. constraint ordering), so using the same seed for both is semantically correct -- they operate on different data. However, `from_examples()` also passes the seed to `ExampleProvider.__init__()`, which shuffles examples internally. The `_run_example_mode` caller passes `mixed_examples = list(pos) + list(neg)` (line 252) -- concatenating all examples before the learner shuffles them. This is correct behavior.

The subtle issue: when `shuffle_seed is None` (no bias shuffling requested), `from_examples(seed=None)` means ExampleProvider gets `seed=None`, which may or may not shuffle examples depending on ExampleProvider's implementation. In the CV loop, `fold_shuffle_seed` is None when `shuffle_bias=False`, so examples passed to `from_examples` won't be shuffled by the provider -- the training examples were already shuffled by the CV loop's `fold_rng` (cross_validation.py line 196-198). This is correct.

**Verdict:** No bug. The data flow is correct.

### M3. Oracle mode ignores `positive_examples`/`negative_examples` silently

When `run(mode='automated')` is called with example arguments, they are silently ignored (line 176-179 dispatches to `_run_oracle_mode` which doesn't use them). The validation at lines 157-160 only checks the reverse (example mode without examples). Consider adding a warning:

```python
if is_oracle_mode and (positive_examples is not None or negative_examples is not None):
    logging.warning("Oracle mode ignores positive/negative examples")
```

**Verdict:** Nice-to-have. Not a bug -- callers currently use the right dispatch.

---

## Low Priority

### L1. Unused `current` variable from `tracemalloc.get_traced_memory()`

Line 194: `current, peak = tracemalloc.get_traced_memory()` -- `current` is never used. Same as ConGenRunner. Harmless but could use `_` for clarity.

### L2. Type annotation on `_run_oracle_mode` / `_run_example_mode`

Both private methods lack return type hints. Adding `-> Tuple[InteractiveResult, InteractiveLearner]` would improve IDE support.

---

## Edge Cases Verified

| Edge Case | Status |
|---|---|
| Empty bias file | Handled -- `self.bias_clauses` = empty dict, `self.feature_ids` = empty dict |
| `shuffle_seed=None` (no shuffle) | Both `_run_oracle_mode` and `_run_example_mode` skip shuffle block correctly |
| All constraints learned (empty remaining bias) | `convergence_reason='empty_bias'` from QuAcq propagates correctly |
| `max_queries=0` | Immediately returns with `convergence_reason='max_queries'` from QuAcq |
| Missing constraint in `self.bias_clauses` during KB clause resolution | Line 209 `if cid in self.bias_clauses` -- silently skips unknown IDs. Correct. |
| `task.background` is empty (no root feature) | Line 201-204: produces `bg_clauses = []`. Correct. |

---

## Backward Compatibility

| Aspect | Status |
|---|---|
| `n_fold_cross_validation_interactive()` signature | Removed `bias_clauses` and `feature_ids` params. Runner loads bias internally. **Breaking** if any external caller used these params. |
| `_run_cv_loop` duck-typing contract | `InteractiveRunResult` satisfies: `.kb_constraints`, `.kb_clauses`, `.bg_clauses`, `.n_bias`, `.n_kb`, `.get_performance_metrics()`, `.profiler_data`. All present. |
| `run_interactive.py` public interface | CLI args unchanged. Internal switch from InteractiveLearner to InteractiveRunner is transparent. |
| `run_cv.py` call site | Removed `bias_clauses=...` and `feature_ids=...` kwargs. Matches new signature. |
| `cleanup()` is no-op | ConGenRunner.cleanup() releases oracle. InteractiveRunner.cleanup() is no-op because oracle is created per-learner inside `_run_oracle_mode`/`_run_example_mode`. Correct -- no resource leak. |

---

## Duck-Typing Compliance (`_run_cv_loop`)

The CV loop accesses these attributes on `run_result` (lines 208-242 of cross_validation.py):

| Attribute | ConGenRunResult | InteractiveRunResult | Match |
|---|---|---|---|
| `kb_constraints` | List[str] | List[str] | Yes |
| `kb_clauses` | List[List[int]] | List[List[int]] | Yes |
| `bg_clauses` | List[List[int]] | List[List[int]] | Yes (also via getattr fallback) |
| `n_bias` | int | int | Yes |
| `n_kb` | int | int | Yes |
| `n_mss` | int | N/A | Uses `getattr(run_result, 'n_mss', 0)` -- safe |
| `redundant_constraints` | List[str] | N/A | Uses `getattr(run_result, 'redundant_constraints', [])` -- safe |
| `n_queries` | N/A | int | Uses `getattr(run_result, 'n_queries', None)` -- safe |
| `profiler_data` | Dict | Dict | Uses `getattr(run_result, 'profiler_data', {})` -- safe |
| `get_performance_metrics()` | method | method | Yes |

All accesses are safe. The getattr fallbacks correctly handle the structural differences between the two result types.

---

## Positive Observations

- Runner pattern is consistent with ConGenRunner (file-path constructor, dual-mode run, profiler_session)
- `enable_profiling=False` on learner correctly prevents double-profiling
- Lazy imports avoid circular dependencies
- Mode validation with clear error messages
- `cleanup()` correctly documented as no-op with rationale
- CV integration is clean -- `feature_ids` exposed as property for AccuracyCalculator

---

## Recommended Actions

1. **(Optional, M3)** Add warning log when oracle mode receives unused examples
2. **(Optional, L2)** Add return type hints to `_run_oracle_mode` / `_run_example_mode`

No blocking issues. Code is ready for use.

---

## Unresolved Questions

1. Are there any external callers of `n_fold_cross_validation_interactive()` that passed the old `bias_clauses`/`feature_ids` params? If so, those callers need updating. Within the repository, `run_cv.py` is the only caller and it has been updated.
