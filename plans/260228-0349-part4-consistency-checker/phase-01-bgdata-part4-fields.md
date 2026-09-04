# Phase 1: BGData Part 4 Fields

## Context Links
- [Brainstorm](../reports/brainstorm-260228-0349-part4-consistency-checker.md)
- Source: `conacq/oracle/bg_data.py` (27 LOC)
- FMOracleTaskPreparation: `conacq/oracle/fm_oracle_model.py` lines 173-254

## Overview
- **Priority**: P1 (blocker for all subsequent phases)
- **Status**: complete
- **Description**: Add 4 Part 4 fields to BGData frozen dataclass

## Key Insights
- BGData currently captures only Part 3 (root BG constraint pair)
- Part 4 data (feature assignment assumptions) already exists in FMOracleTaskPreparation.prepare() but stays on FMOracleModel private fields
- Need to expose: clauses, assumption IDs, and both direction maps (pos/neg)

## Requirements

### Functional
- BGData gains `assignment_clauses`: `List[List[int]]` -- assumption-guarded unit clauses from Part 4
- BGData gains `assignment_assumptions`: `List[int]` -- Part 4 assumption IDs
- BGData gains `pos_assignment_to_assumption`: `Dict[str, int]` -- feature_name -> pos assumption ID
- BGData gains `neg_assignment_to_assumption`: `Dict[str, int]` -- feature_name -> neg assumption ID

### Non-functional
- Dataclass remains frozen (immutable)
- No behavioral changes to existing consumers (ConGen uses only existing fields)

## Architecture

```
BGData (frozen dataclass)
  existing:  set_kb, assumptions, negation_map, descriptions, next_available_id
  new:       assignment_clauses, assignment_assumptions,
             pos_assignment_to_assumption, neg_assignment_to_assumption
```

## Related Code Files
- **Modify**: `conacq/oracle/bg_data.py`
- **No other files modified** in this phase

## Implementation Steps

1. Open `conacq/oracle/bg_data.py`
2. Add 4 new fields after `next_available_id` (line 27):

```python
# Part 4: Feature assignment assumptions (for QuAcq pruning)
assignment_clauses: List[List[int]] = field(default_factory=list)
assignment_assumptions: List[int] = field(default_factory=list)
pos_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
neg_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
```

3. **IMPORTANT**: frozen dataclass with mutable defaults requires `field(default_factory=...)`. This makes BGData backward-compatible -- existing callers that don't pass Part 4 fields get empty defaults.

4. Update docstring to document Part 4 fields:
```python
"""Root BG constraint data extracted post-preparation from Oracle.

Fields (Part 3 -- root constraint):
    set_kb: Assumption-guarded clauses for root constraint + negated form
    assumptions: (root_assumption_id, negated_root_assumption_id)
    negation_map: {root_id: negated_root_id}
    descriptions: {root_id: "desc", neg_id: "NOT(desc)"}
    next_available_id: First free ID after Oracle Parts 3+4

Fields (Part 4 -- feature assignments):
    assignment_clauses: Assumption-guarded unit clauses ([-a_pos, fid], [-a_neg, -fid])
    assignment_assumptions: All Part 4 assumption IDs
    pos_assignment_to_assumption: {feature_name: pos_assumption_id}
    neg_assignment_to_assumption: {feature_name: neg_assumption_id}
"""
```

5. Update import to include `field`:
```python
from dataclasses import dataclass, field
```

## Todo List
- [ ] Add `field` import
- [ ] Add 4 new fields with default_factory
- [ ] Update docstring
- [ ] Verify frozen dataclass still works with mutable defaults

## Success Criteria
- BGData can be constructed with or without Part 4 fields (backward compat)
- Existing ConGen code continues to work (only reads existing fields)
- `frozen=True` preserved

## Risk Assessment
- **Low risk**: additive change only, defaults preserve backward compat
- `frozen=True` + `field(default_factory=...)` is standard Python pattern

## Security Considerations
- None (internal data structure)

## Next Steps
- Phase 2: FMOracleTaskPreparation populates these fields
