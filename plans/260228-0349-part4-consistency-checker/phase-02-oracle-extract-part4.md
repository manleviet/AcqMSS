# Phase 2: Oracle Extract Part 4 into BGData

## Context Links
- [Phase 1](phase-01-bgdata-part4-fields.md) (prerequisite)
- Source: `conacq/oracle/fm_oracle_model.py` lines 188-254 (FMOracleTaskPreparation.prepare)

## Overview
- **Priority**: P1
- **Status**: complete
- **Description**: FMOracleTaskPreparation.prepare() populates Part 4 fields in BGData

## Key Insights
- Part 4 data already computed in `FMOracleTaskPreparation.prepare()` (lines 204-230)
- Currently stored only on `model._pos_assignment_to_assumption` and `model._neg_assignment_to_assumption`
- Assignment clauses already in `result.set_kb` (appended at lines 212, 222)
- Assignment assumption IDs already in `result.assumptions` (appended at lines 214, 224)
- Need to extract these into BGData at construction time (line 242-249)

## Requirements

### Functional
- BGData must include Part 4 assignment_clauses, assignment_assumptions, pos/neg maps
- No change to FMOracleModel's internal `_pos_assignment_to_assumption`/`_neg_assignment_to_assumption` (oracle still needs them for `_config_to_assumptions`)

### Non-functional
- No extra computation -- reuse data already computed in prepare()

## Architecture

Current BGData construction (line 242-249):
```python
model._bg_data = BGData(
    set_kb=result.set_kb[:2],
    assumptions=(result.assumptions[0], result.assumptions[1]),
    negation_map={...},
    descriptions={...},
    next_available_id=id_assumption,
)
```

New: add Part 4 fields. Assignment clauses are the unit clauses added to `result.set_kb` after Part 3 constraints. Need to capture them.

## Related Code Files
- **Modify**: `conacq/oracle/fm_oracle_model.py` (FMOracleTaskPreparation.prepare method)

## Implementation Steps

1. In `FMOracleTaskPreparation.prepare()`, after Step 2 loop (line 228), capture Part 4 data:

   The assignment clauses start at index `assignments_start_index * 2` in set_kb (each Part 3 constraint adds 2 clauses via prepare_kb). Wait -- this is wrong. `prepare_kb` adds variable-length clauses per constraint. We can't index by constraint count.

   Better approach: track the set_kb length before and after Part 4 loop.

2. Add a marker before the Part 4 loop (before line 208):
```python
assignment_kb_start = len(result.set_kb)
assignment_assumptions_start = len(result.assumptions)
```

3. After the Part 4 loop (after line 228), extract Part 4 data:
```python
assignment_clauses = result.set_kb[assignment_kb_start:]
assignment_assumptions = result.assumptions[assignment_assumptions_start:]
```

4. Update BGData construction (lines 242-249) to include Part 4:
```python
model._bg_data = BGData(
    set_kb=result.set_kb[:2],
    assumptions=(result.assumptions[0], result.assumptions[1]),
    negation_map={result.assumptions[0]: result.assumptions[1]},
    descriptions=provider.get_descriptions_for(
        [result.assumptions[0], result.assumptions[1]]),
    next_available_id=id_assumption,
    # Part 4
    assignment_clauses=assignment_clauses,
    assignment_assumptions=assignment_assumptions,
    pos_assignment_to_assumption=dict(pos_assignment_to_assumption),
    neg_assignment_to_assumption=dict(neg_assumption_to_assumption),
)
```

Note: Use `dict(...)` copies since BGData is frozen. The local dicts (`pos_assignment_to_assumption`, `neg_assumption_to_assumption`) are created fresh each call, so copy is technically optional but safe.

## Todo List
- [ ] Add `assignment_kb_start` / `assignment_assumptions_start` markers before Part 4 loop
- [ ] Extract `assignment_clauses` / `assignment_assumptions` after loop
- [ ] Pass all 4 Part 4 fields to BGData constructor
- [ ] Verify existing Oracle functionality unchanged

## Success Criteria
- `oracle.get_bg_data().assignment_clauses` returns Part 4 clauses
- `oracle.get_bg_data().pos_assignment_to_assumption` maps feature names to pos IDs
- Existing `oracle.get_bg_data().set_kb` still returns only Part 3 root pair
- FMOracleModel's own `_config_to_assumptions` still works

## Risk Assessment
- **Low**: additive data extraction, no behavioral changes
- FMOracleModel still stores its own copies of pos/neg maps

## Security Considerations
- None

## Next Steps
- Phase 3: QuAcqTask stores Part 4, QuAcqTaskPreparation copies from BGData
