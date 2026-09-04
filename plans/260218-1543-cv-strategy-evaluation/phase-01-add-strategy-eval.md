# Phase 1: Add Strategy Evaluation to run_congen_eval.py

**Parent**: [plan.md](plan.md)
**Priority**: High | **Status**: pending | **Effort**: 45m

## Overview

After CV completes for each solver mode, evaluate every fold KB + intersected KB against oracle FM groundtruth using `Evaluator` with user-selected strategies. Append results to CV JSON and save intersected eval separately.

## Key Insights

- `Evaluator.from_files(oracle_path, bias_path)` loads FM + bias once — reuse across folds
- `ConGenResultData` wrapper needed: `kb_constraints` from fold, `n_bias`/`n_kb` from fold stats, `bg_clauses=[]`
- `EvaluationResult.to_dict()` provides serializable metrics
- `CrossValidationFoldResult.kb_constraints` gives per-fold constraint IDs
- `CrossValidationResult.intersected_kb` gives shared constraint IDs
- `generate_cv_report()` calls `cv_result.to_dict()` — need to inject eval data BEFORE this call, or serialize separately

## Related Code Files

- `apps/run_congen_eval.py` — main target (currently ~260 lines)
- `conacq/eval/evaluator.py` — `Evaluator`, `EvaluationStrategy`, `EvaluationResult` (read-only)
- `conacq/eval/result_loader.py` — `ConGenResultData` (read-only)
- `conacq/eval/cross_validation.py` — `CrossValidationResult`, `CrossValidationFoldResult` (read-only)
- `conacq/eval/report.py` — `generate_cv_report()` (may extend or work around)
- `apps/conf/run_congen_eval_config.toml` — strategy field already exists in [evaluation]

## Implementation Steps

1. **Restore strategy imports and config:**
   - Re-add `EvaluationStrategy` to imports from `conacq.eval`
   - Add `Evaluator, ConGenResultData` to imports
   - Re-add `get_strategies()` function
   - Re-add strategy parsing in `main()` header print

2. **Add `evaluate_cv_with_strategy()` helper function:**
   ```python
   def evaluate_cv_with_strategy(
       cv_result: CrossValidationResult,
       strategies: List[EvaluationStrategy],
       oracle_path: str,
       bias_path: str,
   ) -> Tuple[List[Dict], Dict]:
       """Evaluate fold KBs + intersected KB with strategies.
       Returns: (fold_evaluations, intersected_evaluation)
       """
   ```
   - Create `Evaluator.from_files(Path(oracle_path), Path(bias_path))`
   - For each fold in `cv_result.fold_results`:
     - Build `ConGenResultData(kb_constraints=fold.kb_constraints, redundant_constraints=fold.redundant_constraints, n_bias=fold.n_bias, n_mss=fold.n_mss, n_kb=fold.n_kb, bg_clauses=[])`
     - Evaluate with each strategy → collect results as dict
   - For intersected KB:
     - Build `ConGenResultData(kb_constraints=cv_result.intersected_kb, redundant_constraints=[], n_bias=first_fold.n_bias, n_mss=0, n_kb=len(cv_result.intersected_kb), bg_clauses=[])`
     - Evaluate with each strategy
   - Return fold eval dicts + intersected eval dict

3. **Integrate into `evaluate_model()` flow:**
   - After `cv_result = n_fold_cross_validation(...)` and before `generate_cv_report()`
   - Call `evaluate_cv_with_strategy()` with configured strategies
   - Inject fold evaluations into CV result dict (post-serialization approach):
     - Call `cv_result_dict = cv_result.to_dict()` manually
     - Append `strategy_evaluation` to each fold dict
     - Add `intersected_evaluation` to top level
     - Save modified dict to JSON directly (instead of using `generate_cv_report()`)
   - Print strategy evaluation summary

4. **Save intersected KB evaluation separately:**
   - File: `{output_dir}/{model_name}_intersected_eval_{mode}.json`
   - Content: intersected_evaluation dict + metadata (model, mode, strategies)

5. **Update config print in `main()`:**
   - Re-add strategies display line

## Todo

- [ ] Restore strategy imports + get_strategies()
- [ ] Add evaluate_cv_with_strategy() helper
- [ ] Integrate into evaluate_model() after CV
- [ ] Save intersected eval to separate file
- [ ] Update main() header print
- [ ] Run tests: `PYTHONPATH=. pytest tests/ -v`

## Success Criteria

- Strategy evaluation runs for each fold + intersected KB
- CV JSON contains `strategy_evaluation` per fold + `intersected_evaluation` top-level
- Separate intersected eval file saved
- Backward compatible: existing fields unchanged
- All tests pass (excluding pre-existing 4 failures)

## Risk

- **bg_clauses gap**: `CrossValidationFoldResult` doesn't store `bg_clauses`. CLAUSE strategy may give incomplete results if it uses bg_clauses for comparison. Mitigation: check if `Evaluator.evaluate()` uses `ConGenResultData.bg_clauses` — if not, `[]` is fine.
- **Serialization approach**: Modifying dict post-serialization is slightly fragile. Alternative: extend `CrossValidationFoldResult.to_dict()` — but that's invasive to core library. Post-serialization dict patching is simpler and contained in the app layer.
