# Phase 01: Extract `_run_cv_loop()` + Simplify Wrappers

## Context Links

- Source: `acqmss/eval/cross_validation.py` (470 LOC)
- Runners: `acqmss/runners/congen_runner.py`, `acqmss/runners/interactive_runner.py`
- Plan: [plan.md](plan.md)

## Overview

- **Priority**: P2
- **Status**: completed
- **Description**: Extract shared CV loop logic into `_run_cv_loop()`, reduce both public functions to thin wrappers.

## Key Insights

Both `n_fold_cross_validation()` and `n_fold_cross_validation_interactive()` share identical code for:
1. Fold generation/provision (lines 168-177 vs 344-353)
2. Per-fold loop: apply_folds, shuffle, shuffle_seed calc (lines 199-217 vs 380-398)
3. `runner.run(train_pos, train_neg, shuffle_seed=fold_shuffle_seed)` (lines 220-221 vs 401-402)
4. KB set collection, performance metrics collection (lines 224-228 vs 404-407)
5. AccuracyCalculator usage (lines 231-232 vs 410-411) — **differs only in `variables` arg**
6. CrossValidationFoldResult construction (lines 238-252 vs 416-430) — **differs in `redundant_constraints` and `n_mss` defaults**
7. Mean/std calculation (lines 263-268 vs 437-440)
8. KB intersection (lines 271-276 vs 445-449)
9. Aggregate metrics + total runtime (lines 283-288 vs 453-456)
10. Return CrossValidationResult (lines 292-301 vs 461-470)

Differences (5 total):
1. **Runner creation** — entirely different constructors/params
2. **Variables source** for `AccuracyCalculator.calculate()`: `runner.model.variables` vs `feature_ids` param
3. **`redundant_constraints`** field: `result.redundant_constraints` vs `[]`
4. **`n_mss`** field: `result.n_mss` vs `0`
5. **Log labels**: "Fold" vs "Interactive Fold", ConGen logs TP/TN/FP/FN, interactive logs queries

## Requirements

### Functional
- Extract `_run_cv_loop(runner, variables, positive_examples, negative_examples, n_folds, seed, ...)` private function
- Both public functions become ~15-line wrappers: create runner, determine variables, call `_run_cv_loop()`
- Identical behavior and return types

### Non-Functional
- File total drops to ~250 lines
- No new imports, no new Protocol/ABC
- Public API unchanged (same function signatures)

## Architecture

```
n_fold_cross_validation(...)          n_fold_cross_validation_interactive(...)
  │ create ConGenRunner                 │ create InteractiveRunner
  │ variables = runner.model.variables  │ variables = feature_ids
  └──────────┐                          └──────────┐
             ▼                                     ▼
        _run_cv_loop(runner, variables, pos, neg, n_folds, seed, ...)
             │
             ├─ generate_folds (if needed)
             ├─ for fold_idx in range(n_folds):
             │    ├─ apply_folds
             │    ├─ shuffle training examples
             │    ├─ runner.run(train_pos, train_neg, shuffle_seed)
             │    ├─ AccuracyCalculator(result.kb_clauses, solver_name)
             │    │   .calculate(test_pos, test_neg, variables)
             │    ├─ CrossValidationFoldResult(
             │    │     redundant_constraints=getattr(result, 'redundant_constraints', []),
             │    │     n_mss=getattr(result, 'n_mss', 0), ...)
             │    └─ collect accuracies, kbs, perf
             ├─ mean/std
             ├─ KB intersection
             ├─ aggregate_metrics
             └─ return CrossValidationResult
```

## Related Code Files

### Files to Modify
- `acqmss/eval/cross_validation.py` — main refactor target

### Files Unchanged
- `acqmss/runners/congen_runner.py` — no changes
- `acqmss/runners/interactive_runner.py` — no changes
- `apps/run_congen_eval.py` — caller, no signature change
- `apps/run_interactive_eval.py` — caller, no signature change

## Implementation Steps

### Step 1: Define `_run_cv_loop()` signature

```python
def _run_cv_loop(
        runner,  # ConGenRunner or InteractiveRunner (duck-typed)
        variables: Dict[str, int],  # for AccuracyCalculator
        positive_examples: List[Dict[str, bool]],
        negative_examples: List[Dict[str, bool]],
        n_folds: int,
        seed: int,
        solver_name: str,
        label: str,  # "ConGen" or "Interactive" for logging
        shuffle_each_fold: bool = True,
        fold_data: Optional[FoldData] = None,
        shuffle_bias: bool = False
) -> CrossValidationResult:
```

### Step 2: Move shared body into `_run_cv_loop()`

Copy the body of `n_fold_cross_validation()` into `_run_cv_loop()`, making these changes:
- Replace `runner.model.variables` with `variables` parameter
- Replace `congen_result` variable name with `run_result` (generic)
- Use `getattr(run_result, 'redundant_constraints', [])` for redundant_constraints
- Use `getattr(run_result, 'n_mss', 0)` for n_mss
- Use `label` param in logging: `f'=== {label} Fold {fold_idx+1}/{n_folds} ==='`
- Log format: use generic log line (accuracy + KB size), drop TP/TN/FP/FN and queries from loop log (keep in fold_result data)

### Step 3: Simplify `n_fold_cross_validation()`

```python
def n_fold_cross_validation(
        positive_examples, negative_examples, n_folds,
        bias_path, fm_path, seed,
        solver_name='glucose4', is_incremental=True,
        shuffle_each_fold=True, fold_data=None, shuffle_bias=False
) -> CrossValidationResult:
    """...(keep existing docstring)..."""
    runner = ConGenRunner(
        bias_path=bias_path, fm_path=fm_path,
        solver_name=solver_name, is_incremental=is_incremental
    )
    return _run_cv_loop(
        runner=runner, variables=runner.model.variables,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
        n_folds=n_folds, seed=seed,
        solver_name=solver_name, label='ConGen',
        shuffle_each_fold=shuffle_each_fold,
        fold_data=fold_data, shuffle_bias=shuffle_bias
    )
```

### Step 4: Simplify `n_fold_cross_validation_interactive()`

```python
def n_fold_cross_validation_interactive(
        positive_examples, negative_examples, n_folds,
        bias_clauses, feature_ids, fm_path, bias_path, seed,
        solver_name='glucose4', max_queries=1000,
        query_mode='example_only',
        shuffle_each_fold=True, fold_data=None, shuffle_bias=False
) -> CrossValidationResult:
    """...(keep existing docstring)..."""
    from conacq.runners import InteractiveRunner  # lazy import
    runner = InteractiveRunner(
        bias_clauses=bias_clauses, feature_ids=feature_ids,
        fm_path=fm_path, bias_path=bias_path,
        solver_name=solver_name, max_queries=max_queries,
        query_mode=query_mode
    )
    return _run_cv_loop(
        runner=runner, variables=feature_ids,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
        n_folds=n_folds, seed=seed,
        solver_name=solver_name, label='Interactive',
        shuffle_each_fold=shuffle_each_fold,
        fold_data=fold_data, shuffle_bias=shuffle_bias
    )
```

### Step 5: Remove duplicate import

The `ConGenRunner` import at top stays. The `InteractiveRunner` lazy import moves into the wrapper. Remove the existing top-level `from acqmss.runners import ConGenRunner` if only used in the wrapper (check).

## Todo List

- [ ] Write `_run_cv_loop()` with full body
- [ ] Replace `n_fold_cross_validation()` body with runner creation + `_run_cv_loop()` call
- [ ] Replace `n_fold_cross_validation_interactive()` body with runner creation + `_run_cv_loop()` call
- [ ] Keep lazy import of InteractiveRunner in wrapper only
- [ ] Verify file is ~250 lines
- [ ] Preserve all existing docstrings on public functions

## Success Criteria

- File under 270 lines
- Both public functions produce identical output as before (same `CrossValidationResult`)
- No new classes, protocols, or ABCs introduced
- `getattr` handles optional fields cleanly

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| `getattr` returns wrong default silently | Low | ConGenRunResult has both fields; InteractiveRunResult lacks them — defaults correct |
| Log format change | None | Logs are for debugging only, not API |
| Runner duck-typing breaks | Low | Both runners have identical `.run()` signature confirmed |

## Next Steps

- Phase 02: Verify `__init__.py` exports + caller compatibility
- Phase 03: Run tests + lint
