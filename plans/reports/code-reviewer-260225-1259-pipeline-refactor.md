# Code Review: Pipeline Refactoring

**Date**: 2026-02-25
**Reviewer**: code-reviewer
**Focus**: Correctness, backward compatibility, edge cases, security

---

## Scope

- **Files reviewed**: 12 changed + 2 deleted + dependent modules
- **LOC**: ~2,119 (changed files) + ~800 deleted
- **Focus**: Pipeline refactoring: shared config, separated concerns (learn/compare/describe)

## Overall Assessment

Solid refactoring that decomposes two monolithic eval scripts (`run_congen_eval.py`, `run_interactive_eval.py`) into single-responsibility scripts with a shared config module. Design principles (IDs-only in KB files, enrichment at presentation layer, shared config) are well applied. Several issues need attention around stale references, code duplication, missing cleanup, and file size.

---

## Critical Issues

### 1. Stale documentation references to deleted scripts

Multiple docs still reference `run_congen_eval.py` and `run_interactive_eval.py`:

- `/Users/manleviet/Development/GitHub/AcqMSS/README.md` (line 41): `PYTHONPATH=. python apps/run_congen_eval.py ...`
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` (lines 201-202, 208-209, 410, 421-432): file inventory, pipeline description, command examples
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` (lines 13-14): layer diagram
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/project-overview-pdr.md` (lines 212-213): file tree
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/project-roadmap.md` (lines 83-84, 101, 131): milestone references

**Impact**: Users running documented commands will get `No such file` errors. This effectively breaks the onboarding experience.

**Fix**: Update all docs to reference `run_cv.py`, `run_compare.py`, `run_interactive.py`, `describe_kb.py` with correct usage examples.

### 2. Orphaned config files from deleted scripts

`apps/conf/run_congen_eval_config.toml` and `apps/conf/run_interactive_eval_config.toml` still exist but their scripts are deleted. The header comments reference the deleted scripts.

**Impact**: Confusing for users. The configs are mostly compatible with the new scripts but the `[evaluation].strategy` field in `run_congen_eval_config.toml` is not used by `run_cv.py` (CV does not do comparison).

**Fix**: Either delete these configs or update them to reference the new scripts. Recommend deletion since `run_cv_config.toml` and `run_interactive_config.toml` now serve as canonical configs.

### 3. Test file references stale result path

`/Users/manleviet/Development/GitHub/AcqMSS/tests/test_evaluation.py` line 31 references:
```python
RESULT_PATH = DATA_DIR / "results" / "REAL-FM-7_rs_1n_non-incremental_fold1_kb.json"
```

Actual files are in `data/results/congen/`. Tests `test_evaluate_real_fm_7` and `test_accuracy_with_real_examples` fail with `FileNotFoundError`.

**Impact**: 2 test failures. Not a regression (likely broken before this refactor due to output dir change) but should be fixed.

**Fix**: Update `RESULT_PATH` to point to `data/results/congen/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json` or add a `skipUnless(RESULT_PATH.exists())` guard.

---

## High Priority

### 4. `run_interactive.py` -- `bg_clauses` always empty for interactive results

Lines 76-84:
```python
bg_clauses = getattr(result, 'bg_clauses', [])
save_kb_result(
    kb_constraints=result.kb_constraints,
    redundant_constraints=getattr(result, 'redundant_constraints', []),
    n_bias=getattr(result, 'n_bias', 0),
    ...
    bg_clauses=bg_clauses,
)
```

`InteractiveResult` (from `conacq/algorithms/interactive/result.py`) has no `bg_clauses`, `redundant_constraints`, or `n_bias` attributes. The `getattr` defaults ensure no crash, but the saved KB will always have `bg_clauses: []`, which means the root constraint is lost from the output. When later running `run_compare.py` with clause strategy on this KB, the comparison will be missing background knowledge, potentially producing wrong accuracy metrics.

**Fix**: The interactive learner has access to the oracle (FM). Extract `bg_clauses` from the oracle/FM path and pass it explicitly:
```python
from conacq.oracle import FeatureModelOracle
oracle = FeatureModelOracle(model_config.oracle, use_incremental=False)
bg_clauses = oracle.get_root_clauses()
oracle.cleanup()
```

### 5. No resource cleanup in `run_interactive.py` process_model

`InteractiveLearner.from_files()` creates an oracle internally, but there is no `cleanup()` or `close()` call in the `finally` block. Compare with `run_congen.py` lines 115-117 which properly calls `runner.cleanup()`.

**Impact**: Potential solver resource leak (file descriptors, native solver state) when processing multiple models.

**Fix**: Add cleanup logic:
```python
finally:
    if learner is not None:
        learner.cleanup()  # or learner.task.cleanup() if applicable
```

Verify `InteractiveLearner` exposes a cleanup method, or add one.

### 6. `find_kb_files()` duplicated between `run_compare.py` and `describe_kb.py`

Both files define identical `find_kb_files(kb_path: Path) -> List[Path]` with nearly the same logic (glob `*_kb.json` and `*_intersected_kb.json`). This violates DRY.

**Fix**: Move `find_kb_files()` to `conacq/eval/config.py` or a new `conacq/eval/utils.py` and import from both scripts.

---

## Medium Priority

### 7. `extract_results.py` at 739 lines -- exceeds 200-line Python threshold

This file is well-organized with clear sections but at 739 lines it is 3.7x the recommended maximum. The table generation functions are logically separable.

**Suggestion**: Extract table generators into `apps/extract_results_tables.py` or split by concern:
- `extract_results.py` -- data loading + main
- `table_generators.py` -- all `generate_*` functions + helpers

### 8. `parse_models()` silently defaults oracle to empty string

In `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/config.py` line 65:
```python
oracle = m.get('oracle', m.get('path', ''))
```

If both `oracle` and `path` keys are missing, `oracle` silently becomes `''`. This will cause a confusing `FileNotFoundError` later rather than a clear config validation error.

**Fix**: Add validation:
```python
oracle = m.get('oracle', m.get('path'))
if not oracle:
    raise ValueError(f"Model entry missing 'oracle' or 'path' field: {m}")
```

Similarly for `bias`:
```python
bias=m['bias']  # KeyError is ok but unclear
```
Consider catching with a better message.

### 9. `parse_models()` silently accepts missing `bias` (KeyError)

Line 70: `bias=m['bias']` will raise `KeyError` if `bias` is missing from a model entry. This produces an unhelpful traceback.

**Fix**: Use `.get()` with validation or wrap with a descriptive error.

### 10. `save_kb_result` mutable default argument

`/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/report.py` line 182:
```python
def save_kb_result(..., bg_clauses: list = None, metadata: dict = None) -> None:
```

While `None` is used (not a mutable default), the type hints should use `Optional[list]` and `Optional[dict]` for clarity:
```python
bg_clauses: Optional[List[List[int]]] = None
metadata: Optional[Dict] = None
```

### 11. `run_cv.py` does not save bg_clauses in fold KB files

`save_cv_kb_files()` saves fold KBs via `fold_result.to_kb_dict()` which may not include `bg_clauses`. The intersected KB file also omits `bg_clauses`. When these are later loaded by `run_compare.py`, the clause-based comparison will miss root constraint.

**Verify**: Check if `CrossValidationFoldResult.to_kb_dict()` includes `bg_clauses`. If not, this is the same bg_clauses-lost issue as item #4.

### 12. `run_congen_config.toml` only has 1 model entry

The config file only contains REAL-FM-7_rs_1n as an example. Previously the old eval config had all models across all KBs/strategies. While this is a config file (not code), having a single model as the only non-commented example could mislead users.

**Suggestion**: Add a comment indicating users should add their own model entries, or provide a more complete example config.

---

## Low Priority

### 13. Inconsistent error message patterns

- `run_congen.py` line 110: `print(f"Error processing {model_config.oracle}: {e}")`
- `run_interactive.py` line 96: `print(f"Error processing {model_config.oracle}: {e}")`
- `run_cv.py` line 201: `print(f"Error evaluating {model_config.name}: {e}")`

Some use `oracle` path, others use `name`. Recommend consistent use of `model_config.name` since oracle paths can be long and less readable.

### 14. `extract_results.py` -- `_find_matching_eval` naming pattern mismatch potential

Line 222: The new-format pattern `{model}_{strategy}_{mode}_intersected_kb_eval.json` must exactly match what `run_compare.py` produces. `run_compare.py` line 82 uses `{kb_path.stem}_eval.json`. If the intersected KB stem is `{model}_{strategy}_{mode}_intersected_kb`, the pattern matches. But if `save_cv_kb_files` uses `{model_name}_{mode_name}_intersected_kb` (which it does at report.py line 251), the strategy component is missing.

For example, `save_cv_kb_files` produces: `REAL-FM-7_rs_1n_non-incremental_intersected_kb.json`
But `_find_matching_eval` looks for: `REAL-FM-7_rs_1n_non-incremental_intersected_kb_eval.json`

This pattern should match correctly since `model_name` already contains the strategy (e.g., `REAL-FM-7_rs_1n`). Verified: the naming is consistent.

### 15. `run_interactive.py` profiler starts before model loop

Lines 151-152 start the global profiler before the loop. If processing multiple models, all profiler metrics blend together. Consider per-model profiler sessions or a clear note that the profiler summary is aggregate.

---

## Edge Cases Found by Scout

1. **Empty models list**: All scripts handle `if not models` with error + sys.exit(1). Good.
2. **Missing examples path in run_cv.py**: Handled with `WARNING` + continue (line 117). Good.
3. **Missing folds_path**: Handled gracefully (line 133-139). Good.
4. **Unknown algorithm in run_cv.py**: `else` branch prints error and `continue` (line 176-177). Good.
5. **KeyboardInterrupt**: Not handled -- long-running CV could leave solver resources un-cleaned. Low risk for research tooling.

---

## Positive Observations

1. **Clean separation of concerns**: learn (run_congen, run_interactive) / evaluate (run_compare) / describe (describe_kb) / cross-validate (run_cv) is a good decomposition
2. **Shared config module**: `conacq/eval/config.py` eliminates ModelConfig and config-loading duplication across 4+ scripts -- good DRY improvement
3. **Backward compatibility in parse_models**: supports both `oracle` and legacy `path` field, with name derivation from path stem
4. **Backward compatibility in extract_results.py**: `_find_matching_eval` checks both new and old eval file patterns
5. **bg_clauses in KB format**: Adding background knowledge to the saved JSON is the right design -- enables correct clause-based comparison
6. **Consistent output format**: `save_kb_result` and `ConGenResultData.from_json` are symmetric (roundtrip verified)
7. **save_cv_kb_files**: Clean fold/intersected KB persistence

---

## Recommended Actions (Priority Order)

1. **[Critical]** Update all docs (README, codebase-summary, system-architecture, project-overview-pdr, project-roadmap) to reference new scripts
2. **[Critical]** Delete or update orphaned config files (`run_congen_eval_config.toml`, `run_interactive_eval_config.toml`)
3. **[Critical]** Fix test_evaluation.py `RESULT_PATH` or add skip guard
4. **[High]** Fix `run_interactive.py` to extract `bg_clauses` from oracle FM instead of relying on `getattr` default
5. **[High]** Add resource cleanup in `run_interactive.py` `process_model()`
6. **[High]** Extract `find_kb_files()` to shared module (DRY)
7. **[Medium]** Add validation in `parse_models()` for missing `oracle`/`path` and `bias` fields
8. **[Medium]** Add proper type hints (`Optional[List[List[int]]]`) to `save_kb_result` params
9. **[Medium]** Consider splitting `extract_results.py` (739 lines)
10. **[Low]** Standardize error message format across scripts

---

## Metrics

- **Type Coverage**: ~70% (type hints on function signatures, missing some inner variables)
- **Test Coverage**: 24/26 passing (2 failures from stale path reference, not from this refactor)
- **Linting Issues**: 0 syntax errors, imports resolve cleanly

---

## Unresolved Questions

1. Should `run_cv.py` fold KB files also include `bg_clauses`? Currently `save_cv_kb_files` calls `fold_result.to_kb_dict()` -- need to verify if bg_clauses is included.
2. Does `InteractiveLearner` have a `cleanup()` method? If not, one should be added.
3. Should the old eval configs be deleted now or kept for one more release cycle for users who may have automated pipelines referencing them?
