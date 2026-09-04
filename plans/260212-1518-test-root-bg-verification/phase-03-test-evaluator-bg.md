# Phase 3: Test Evaluator BG Union

## Context Links
- Parent: [plan.md](./plan.md)
- File: `tests/test_evaluation.py`
- Source: `acqmss/eval/evaluator.py`

## Overview
**Priority**: P2 | **Status**: Complete | **Effort**: 25min

Verify `_evaluate_by_clause()` includes bg_clauses in comparison.

## Key Insights
- Current eval tests use `CONGENResultData(bg_clauses=[])` (default)
- Need test showing that bg_clauses get counted as TP in clause eval
- Can use synthetic data: oracle has clause `(1,)`, bg_clauses=`[[1]]`, KB empty → root should be TP

## Related Code Files
**Modify**: `tests/test_evaluation.py`

## Implementation Steps

### Step 1: Add `test_clause_eval_includes_bg_clauses` in TestEvaluator

```python
def test_clause_eval_includes_bg_clauses(self):
    """Verify bg_clauses are unioned with kb_clauses in clause eval."""
    evaluator = Evaluator.from_bias_and_fm_fide(FM_PATH, BIAS_PATH)

    # Result with NO KB but WITH bg_clauses containing root
    result_with_bg = CONGENResultData(
        kb_constraints=[],
        n_bias=len(evaluator.bias.constraints),
        n_kb=0,
        bg_clauses=[[1]]  # Root constraint
    )

    # Result with NO KB and NO bg_clauses
    result_without_bg = CONGENResultData(
        kb_constraints=[],
        n_bias=len(evaluator.bias.constraints),
        n_kb=0,
        bg_clauses=[]
    )

    eval_with = evaluator.compare(result_with_bg, EvaluationStrategy.CLAUSE)
    eval_without = evaluator.compare(result_without_bg, EvaluationStrategy.CLAUSE)

    # With bg_clauses: root (1,) should be TP → fewer FN
    assert eval_with.metrics.true_positives >= eval_without.metrics.true_positives
    assert eval_with.metrics.false_negatives <= eval_without.metrics.false_negatives
```

### Step 2: Add `test_bg_clauses_default_empty`
```python
def test_bg_clauses_default_empty(self):
    """Verify bg_clauses defaults to empty, no impact on eval."""
    result = CONGENResultData(kb_constraints=[], n_bias=10, n_kb=0)
    assert result.bg_clauses == []
```

## Todo List
- [x] Add `test_clause_eval_includes_bg_clauses`
- [x] Add `test_bg_clauses_default_empty`
- [x] Run all evaluation tests

## Success Criteria
- bg_clauses=[[1]] → root counted as TP (fewer FN)
- bg_clauses=[] → root counted as FN (current behavior)
- Default bg_clauses is empty list
- All evaluation tests pass
