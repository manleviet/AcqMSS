# Phase 3: QuAcqTask Stores Part 4, Preparation Copies from BGData

## Context Links
- [Phase 2](phase-02-oracle-extract-part4.md) (prerequisite)
- Source: `conacq/algorithms/quacq/task_preparation.py` (full file, 127 LOC)

## Overview
- **Priority**: P1
- **Status**: complete
- **Description**: QuAcqTask gains 4 Part 4 fields; QuAcqTaskPreparation copies them from BGData

## Key Insights
- QuAcqTask already stores `background_clauses`, `feature_ids`, etc. as raw data
- Part 4 fields follow same pattern: store raw data, let algorithm use it
- QuAcqTaskPreparation.prepare() already calls `oracle.get_bg_data()` at line 87
- Just need to copy 4 additional fields from bg_data

## Requirements

### Functional
- QuAcqTask gains: `assignment_clauses`, `assignment_assumptions`, `pos_assignment_to_assumption`, `neg_assignment_to_assumption`
- QuAcqTaskPreparation.prepare() copies these from BGData

### Non-functional
- Default empty values (backward compat for test construction)

## Architecture

```
QuAcqTask (dataclass)
  inherited: set_c, set_b, set_kb, negation_map, assumptions
  existing:  background_clauses, feature_ids, id_to_feature,
             constraint_clauses, negated_clauses
  new:       assignment_clauses, assignment_assumptions,
             pos_assignment_to_assumption, neg_assignment_to_assumption
```

## Related Code Files
- **Modify**: `conacq/algorithms/quacq/task_preparation.py`

## Implementation Steps

### Step 1: Add fields to QuAcqTask (after line 60)

```python
# Part 4: Feature assignment assumptions (for SAT-based pruning)
assignment_clauses: List[List[int]] = field(default_factory=list)
assignment_assumptions: List[int] = field(default_factory=list)
pos_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
neg_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
```

### Step 2: Update QuAcqTask docstring

Add to the docstring (after line 43, "negated_clauses" entry):
```
    QuAcq-specific Part 4 data (from BGData):
        assignment_clauses:          Assumption-guarded unit clauses for feature assignments
        assignment_assumptions:      Part 4 assumption IDs
        pos_assignment_to_assumption: Feature name -> positive assignment assumption ID
        neg_assignment_to_assumption: Feature name -> negative assignment assumption ID
```

### Step 3: Copy Part 4 in QuAcqTaskPreparation.prepare()

After line 95 (`result.background_clauses = oracle.get_root_clauses()`), add:

```python
# Copy Part 4 data from BGData (feature assignment assumptions)
result.assignment_clauses = list(bg_data.assignment_clauses)
result.assignment_assumptions = list(bg_data.assignment_assumptions)
result.pos_assignment_to_assumption = dict(bg_data.pos_assignment_to_assumption)
result.neg_assignment_to_assumption = dict(bg_data.neg_assignment_to_assumption)
```

Defensive copies (`list()`, `dict()`) since bg_data is frozen but contains mutable collections.

## Todo List
- [ ] Add 4 Part 4 fields to QuAcqTask dataclass
- [ ] Update QuAcqTask docstring
- [ ] Copy Part 4 from BGData in QuAcqTaskPreparation.prepare()
- [ ] Verify existing test_quacq.py still passes (new fields default to empty)

## Success Criteria
- `task.pos_assignment_to_assumption` populated after prepare()
- `task.assignment_clauses` matches oracle Part 4 clauses
- Existing tests pass with no changes (empty defaults)

## Risk Assessment
- **Low**: additive fields with backward-compatible defaults
- Defensive copies prevent mutation of BGData internals

## Security Considerations
- None

## Next Steps
- Phase 4: QuAcqModel.get_kb()/get_assumptions() include Part 4
