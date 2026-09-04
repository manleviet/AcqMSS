# Phase 5: Update Eval Pipeline

## Context Links
- [Parent Plan](plan.md) | [Phase 4](phase-04-update-result-and-runner.md)
- Source: `conacq/eval/cross_validation.py` (412 LOC)
- Source: `conacq/eval/result_loader.py` (112 LOC)
- Source: `conacq/eval/interactive_metrics.py` (391 LOC)
- Source: `conacq/eval/accuracy.py` (171 LOC)

## Overview
- **Priority**: P2
- **Status**: completed
- **Depends on**: Phase 4
- **Description**: Update eval pipeline files that consume InteractiveResult or InteractiveRunResult to handle the new dual-representation format (int IDs + str names).

## Key Insights
1. **Minimal impact**: InteractiveRunResult.kb_constraints remains `List[str]` (resolved by runner in Phase 4). The CV loop (`_run_cv_loop`) and AccuracyCalculator operate on string names and clauses — they don't touch assumption IDs directly.
2. **cross_validation.py**: `n_fold_cross_validation_interactive()` creates InteractiveRunner and passes to `_run_cv_loop()`. Runner already returns kb_constraints as `List[str]`. `CrossValidationFoldResult.kb_constraints` stays `List[str]`. No change needed here IF runner resolves correctly.
3. **result_loader.py**: `ConGenResultData.from_dict()` reads `kb_constraints`. InteractiveResult JSON now includes `kb_assumption_ids` field too. ConGenResultData doesn't need it. But InteractiveLearner.evaluate() wraps result in ConGenResultData — must pass string names.
4. **accuracy.py**: AccuracyCalculator takes `kb_clauses` and `variables` — no constraint IDs involved. No change needed.
5. **interactive_metrics.py**: Consumes kb_constraints as strings. No change needed.
6. **report.py**: `generate_unified_cv_dict()` and `_enrich_constraints()` work with string KB names. No change needed.

## Requirements

### Functional
- CV pipeline continues to work with InteractiveRunner producing resolved string names
- Result JSON files include both `kb_constraints` (str) and `kb_assumption_ids` (int)
- InteractiveLearner.evaluate() continues to work (it wraps result in ConGenResultData)

### Non-functional
- No breaking changes to existing eval JSON format
- Existing result files remain loadable

## Related Code Files

### Files to Inspect (likely NO changes needed)
| File | Why | Change? |
|------|-----|---------|
| `conacq/eval/cross_validation.py` | CV loop uses runner.run() -> InteractiveRunResult | **No** — runner resolves to str |
| `conacq/eval/accuracy.py` | AccuracyCalculator uses kb_clauses, not IDs | **No** |
| `conacq/eval/interactive_metrics.py` | Uses kb_constraints as str | **No** |
| `conacq/eval/report.py` | Uses kb_constraints as str for enrichment | **No** |
| `conacq/eval/result_loader.py` | ConGenResultData.from_dict() reads kb_constraints | **No** |

### Files that MAY need minor updates
| File | Changes |
|------|---------|
| `conacq/algorithms/interactive/learner.py` | evaluate() method wraps InteractiveResult — uses kb_constraints (str). Keep working with new dual-field result. |

## Implementation Steps

### Step 1: Verify cross_validation.py compatibility

Check `_run_cv_loop()` (line 137):
- `run_result = runner.run(train_pos, train_neg, ...)` — returns InteractiveRunResult
- `fold_kbs.append(set(run_result.kb_constraints))` — uses `List[str]`
- `run_result.kb_clauses` — resolved clauses
- `getattr(run_result, 'bg_clauses', [])` — bg clauses

All of these use the resolved string/clause forms from InteractiveRunResult. Phase 4 ensures runner populates these correctly. **No change needed.**

### Step 2: Verify result_loader.py compatibility

`ConGenResultData.from_dict()` reads:
```python
kb_raw = data.get('kb_constraints', [])
```

InteractiveResult.to_dict() outputs `kb_constraints: List[str]` (backward compat). When InteractiveResult JSON is loaded by ConGenResultData, it reads string names. **No change needed.**

### Step 3: Verify InteractiveLearner.evaluate() compatibility

`learner.evaluate(result)` at line 273 of learner.py:
```python
congen_result = ConGenResultData(
    kb_constraints=result.kb_constraints,  # List[str] — still populated
    ...
)
```

Since InteractiveResult now has both `kb_assumption_ids` and `kb_constraints`, and evaluate() uses `result.kb_constraints`, **no change needed.**

### Step 4: Verify accuracy.py compatibility

AccuracyCalculator takes `kb_clauses: List[List[int]]` and `variables: Dict[str, int]`. These come from InteractiveRunResult, not InteractiveResult directly. **No change needed.**

### Step 5: Update apps/run_interactive.py (if it reads InteractiveResult)

Check if `apps/run_interactive.py` or `apps/run_cv.py` directly access `result.kb_constraints`. If so, they continue to work since the field is still populated.

### Step 6: Verify JSON output format

New InteractiveResult.to_dict() includes:
```json
{
  "kb_constraints": ["c1_name", "c2_name"],
  "kb_assumption_ids": [101, 103],
  ...
}
```

Old format had only `kb_constraints`. New format adds `kb_assumption_ids`. This is additive — existing consumers ignore unknown fields. **Backward compatible.**

## Todo List
- [ ] Verify cross_validation.py works with updated InteractiveRunner (integration test)
- [ ] Verify result_loader.py handles new JSON format (kb_assumption_ids ignored gracefully)
- [ ] Verify InteractiveLearner.evaluate() works with dual-field InteractiveResult
- [ ] Verify apps/run_interactive.py and apps/run_cv.py work with updated pipeline
- [ ] Run full eval pipeline end-to-end test

## Success Criteria
- CV pipeline produces identical results (same accuracy, same KB names)
- Result JSON files include both fields
- Existing result files remain loadable
- No eval pipeline code changes required (verification only)

## Risk Assessment
1. **Low risk**: This phase is primarily verification. The design ensures backward compatibility by keeping `kb_constraints: List[str]` alongside `kb_assumption_ids: List[int]`.
2. **Edge case**: If any eval code does `isinstance(kb_constraints[0], str)` checks, it continues to work since kb_constraints remains List[str].

## Security Considerations
- No changes to external input handling

## Next Steps
- Phase 6: Update tests
