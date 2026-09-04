# Code Review: DRY CV Functions Refactoring

**Date:** 2026-02-17
**Scope:** `conacq/eval/cross_validation.py` (394 lines, down from 470)
**Focus:** Extract shared CV loop from two near-identical functions

---

## Overall Assessment

Clean, well-executed DRY refactoring. Eliminated ~76 lines of duplication by extracting `_run_cv_loop()`. Public API preserved exactly. Duck typing is safe for the two known runner types.

---

## 1. Public Signature Preservation -- PASS

Both `n_fold_cross_validation()` and `n_fold_cross_validation_interactive()` retain identical parameter names, types, defaults, and return types compared to the original. Callers in `apps/run_congen_eval.py` (line 234) and `apps/run_interactive_eval.py` (line 228) use keyword arguments that match exactly. No breaking change.

## 2. Duck Typing Safety -- PASS (with note)

**Required interface on runner result objects:**

| Attribute | `ConGenRunResult` | `InteractiveRunResult` | Access in `_run_cv_loop` |
|---|---|---|---|
| `kb_constraints` | direct field | direct field | direct |
| `kb_clauses` | direct field | direct field | direct |
| `n_bias` | direct field | direct field | direct |
| `n_kb` | direct field | direct field | direct |
| `get_performance_metrics()` | method | method | direct |
| `redundant_constraints` | direct field | **missing** | `getattr(..., [])` |
| `n_mss` | direct field | **missing** | `getattr(..., 0)` |

The `getattr` fallbacks are correct:
- `InteractiveRunResult` lacks `redundant_constraints` and `n_mss` (QuAcq has no REDUCE/MSS steps)
- Original code hardcoded `redundant_constraints=[]` and `n_mss=0` for interactive -- `getattr` defaults match exactly

**Note (low priority):** If a third runner is added in the future, `getattr` silently masks missing required fields. A `typing.Protocol` would catch this at type-check time. Not needed now (YAGNI), but worth a comment in `_run_cv_loop` docstring.

## 3. Behavioral Differences

### 3a. Logging Changes -- MEDIUM

| Before (ConGen) | After |
|---|---|
| `Fold N: accuracy=X (TP=T, TN=T, FP=F, FN=F), KB=K` | `Fold N: accuracy=X, KB=K` |

The TP/TN/FP/FN detail was dropped from the per-fold log line for ConGen. This data is still available in `CrossValidationFoldResult.metrics`, so nothing is lost from results. But during debugging, the verbose log was useful for diagnosing accuracy anomalies without post-processing JSON.

**Similarly for interactive:** The original logged `queries=N` per fold; the unified version does not.

**Recommendation:** Consider a single unified log format that includes the most diagnostic fields:
```python
logging.info('Fold %d: accuracy=%.4f, KB=%d, TP=%d, FP=%d, FN=%d',
             fold_idx + 1, fold_accuracy, run_result.n_kb,
             accuracy_result.metrics.true_positives,
             accuracy_result.metrics.false_positives,
             accuracy_result.metrics.false_negatives)
```

### 3b. Import Path Change -- PASS

`from acqmss.runners import ConGenRunner` changed to `from conacq.runners import ConGenRunner`. This is consistent with the broader package rename visible in the commit history. The lazy import for `InteractiveRunner` also uses `conacq.runners`. Import test passes.

### 3c. Docstring Unicode Change -- COSMETIC

`+-` replaced `+-` (the original used the `+-` unicode character). Consistent throughout. No functional impact.

## 4. Code Quality of `_run_cv_loop`

**Strengths:**
- Clean separation: wrappers handle runner construction, shared function handles the loop
- `variables` parameter cleanly abstracts `runner.model.variables` vs `feature_ids`
- `label` parameter for log differentiation is simple and effective
- `solver_name` has no default in `_run_cv_loop` (good -- forces callers to be explicit)

**Issues:**

### 4a. File Length Still Over Threshold -- LOW

At 394 lines the file exceeds the project's 200-line Python guideline. The dataclasses (`CrossValidationFoldResult`, `CrossValidationResult`) could move to a `cv_types.py` module (~90 lines), bringing the main file under 300. Not urgent.

### 4b. Missing Return Type in Docstring -- LOW

`_run_cv_loop` docstring omits the `Returns:` section. Minor since it's private and the return type annotation is present.

---

## Summary Table

| Area | Verdict | Priority |
|---|---|---|
| Public API preserved | PASS | -- |
| Duck typing correctness | PASS | -- |
| getattr defaults match originals | PASS | -- |
| Import path consistency | PASS | -- |
| Per-fold log detail loss (TP/FP/FN, queries) | Regression | Medium |
| File length > 200 lines | Guideline | Low |
| No Protocol for runner interface | Future-proof | Low |
| Docstring Returns missing on private fn | Cosmetic | Low |

---

## Recommended Actions

1. **[Medium]** Restore TP/FP/FN to per-fold log line (aids debugging). Optionally log runner-specific fields via `getattr(run_result, 'n_queries', None)` and conditionally append.
2. **[Low]** Extract dataclasses to `cv_types.py` to bring file under threshold.
3. **[Low]** Add brief `Returns:` line to `_run_cv_loop` docstring.

---

## Positive Observations

- Significant DRY improvement (76 lines removed, zero logic duplication)
- `getattr` fallbacks precisely match the original hardcoded values
- Thin wrappers are easy to read and maintain
- Lazy import for InteractiveRunner preserved correctly
- Tests pass (22/23; 1 failure is pre-existing missing data file)

---

## Unresolved Questions

None.
