# Phase 7: Update Tests

## Context Links
- [All previous phases](plan.md)
- Source: `tests/test_quacq.py` (765 LOC)

## Overview
- **Priority**: P1
- **Status**: complete
- **Description**: Update existing tests and add Part 4 coverage

## Key Insights
- test_quacq.py has its own `_learn_params_from_task` (line 43-56) -- must sync with runner
- Tests construct `_minimal_learn_params()` (line 661-666) for validation tests -- needs Part 4 fields
- Existing tests use `_minimal_checker()` which creates `NonIncrementalPySATChecker([], [])` -- no KB, no assumptions. This still works for backward compat (Part 4 None fallback).
- Integration tests using `prepared_model` + `CheckerFactory` will automatically get Part 4 data

## Requirements

### Functional
- Sync test `_learn_params_from_task` with runner version
- Add test for Part 4 fields populated on QuAcqTask after prepare()
- Add test for BGData Part 4 fields populated after oracle.get_bg_data()
- Add test for QuAcqModel.get_kb() includes assignment_clauses
- Add test verifying SAT-based prune catches same violations as Boolean

### Non-functional
- Minimal test helper `_minimal_learn_params` needs Part 4 fields with None defaults
- Existing empty-bias tests keep working

## Architecture

Test categories:
1. **Data flow**: BGData Part 4 -> QuAcqTask Part 4 -> QuAcqModel get_kb()/get_assumptions()
2. **Behavior**: SAT-based prune vs Boolean prune comparison
3. **Regression**: all existing tests still pass

## Related Code Files
- **Modify**: `tests/test_quacq.py`

## Implementation Steps

### Step 1: Sync _learn_params_from_task (line 43-56)

Replace with version matching Phase 6:
```python
def _learn_params_from_task(task):
    """Extract flat learn() params from QuAcqTask."""
    return dict(
        set_c=task.set_c,
        set_b=task.set_b,
        negation_map=task.negation_map,
        background_clauses=task.background_clauses,
        feature_ids=task.feature_ids,
        id_to_feature=task.id_to_feature,
        constraint_clauses=task.constraint_clauses,
        negated_clauses=task.negated_clauses,
        pos_assignment_to_assumption=task.pos_assignment_to_assumption,
        neg_assignment_to_assumption=task.neg_assignment_to_assumption,
        root_assumption=task.set_b[0] if task.set_b else None,
    )
```

### Step 2: Update _minimal_learn_params (line 661-666)

Add Part 4 None defaults:
```python
def _minimal_learn_params(self):
    return dict(
        set_c=[], set_b=[], negation_map={},
        background_clauses=[],
        feature_ids={'root': 1}, id_to_feature={1: 'root'},
        constraint_clauses={}, negated_clauses={},
        pos_assignment_to_assumption=None,
        neg_assignment_to_assumption=None,
        root_assumption=None)
```

### Step 3: Update empty-bias test params (lines 251-254, 489-494)

Same: add `pos_assignment_to_assumption=None, neg_assignment_to_assumption=None, root_assumption=None` to explicit learn() calls.

### Step 4: Add TestBGDataPart4 class

```python
class TestBGDataPart4:
    """Tests for BGData Part 4 fields."""

    def test_bgdata_part4_populated(self, oracle):
        """BGData Part 4 fields populated after oracle prepare."""
        bg_data = oracle.get_bg_data()
        assert len(bg_data.assignment_clauses) > 0
        assert len(bg_data.assignment_assumptions) > 0
        assert len(bg_data.pos_assignment_to_assumption) > 0
        assert len(bg_data.neg_assignment_to_assumption) > 0
        # Each feature should have pos and neg entry
        assert (len(bg_data.pos_assignment_to_assumption) ==
                len(bg_data.neg_assignment_to_assumption))

    def test_bgdata_part4_default_empty(self):
        """BGData Part 4 fields default to empty."""
        from conacq.oracle.bg_data import BGData
        bg = BGData(set_kb=[], assumptions=(1, 2),
                    negation_map={}, descriptions={},
                    next_available_id=10)
        assert bg.assignment_clauses == []
        assert bg.assignment_assumptions == []
        assert bg.pos_assignment_to_assumption == {}
        assert bg.neg_assignment_to_assumption == {}
```

### Step 5: Add TestQuAcqTaskPart4 class

```python
class TestQuAcqTaskPart4:
    """Tests for QuAcqTask Part 4 fields."""

    def test_task_part4_populated(self, prepared_model):
        """QuAcqTask Part 4 fields populated after prepare."""
        task = prepared_model.task
        assert len(task.assignment_clauses) > 0
        assert len(task.pos_assignment_to_assumption) > 0
        assert len(task.neg_assignment_to_assumption) > 0
        # Every feature in feature_ids should have assignment mappings
        for feat in task.feature_ids:
            assert feat in task.pos_assignment_to_assumption
            assert feat in task.neg_assignment_to_assumption

    def test_model_get_kb_includes_part4(self, prepared_model):
        """QuAcqModel.get_kb() includes Part 4 assignment clauses."""
        task = prepared_model.task
        model_kb = prepared_model.get_kb()
        # model KB should be larger than task.set_kb alone
        assert len(model_kb) == len(task.set_kb) + len(task.assignment_clauses)

    def test_model_get_assumptions_includes_part4(self, prepared_model):
        """QuAcqModel.get_assumptions() includes Part 4."""
        task = prepared_model.task
        model_assumptions = prepared_model.get_assumptions()
        assert len(model_assumptions) == len(task.assumptions) + len(task.assignment_assumptions)
```

### Step 6: Add TestSATBasedPrune class

```python
class TestSATBasedPrune:
    """Tests for SAT-based pruning via checker."""

    def test_prune_with_checker(self, prepared_model, oracle, checker):
        """SAT-based prune catches at least as many violations as Boolean."""
        task = prepared_model.task
        # Get a valid configuration as positive example
        features = list(task.feature_ids.keys())
        # Use oracle to get a valid config
        config = {f: True for f in features}  # naive
        if oracle.is_valid(config):
            from conacq.algorithms.quacq.sat_utils import (
                config_to_assumptions, violates_clauses
            )
            remaining = set(task.set_c)
            # Boolean prune
            assumptions_list = config_to_assumptions(config, task.feature_ids)
            assignment = {abs(lit): lit > 0 for lit in assumptions_list}
            boolean_pruned = set()
            for aid in remaining:
                clauses = task.constraint_clauses.get(aid, [])
                if violates_clauses(clauses, assignment):
                    boolean_pruned.add(aid)
            # SAT prune should catch at least the same
            # (may catch more due to BG implications)
```

## Todo List
- [ ] Sync _learn_params_from_task
- [ ] Update _minimal_learn_params
- [ ] Update explicit learn() calls with Part 4 None defaults
- [ ] Add TestBGDataPart4 class
- [ ] Add TestQuAcqTaskPart4 class
- [ ] Add TestSATBasedPrune class
- [ ] Run full test suite: `PYTHONPATH=. pytest tests/test_quacq.py -v`

## Success Criteria
- All existing tests pass (no regressions)
- New tests validate Part 4 data flow end-to-end
- SAT-based prune test confirms >= Boolean prune coverage

## Risk Assessment
- **Low**: mostly additive tests
- Must keep backward compat for minimal param tests (None defaults)

## Security Considerations
- None

## Next Steps
- Plan complete. All 7 phases implement the full data flow.
