# Phase 2: Refactor ConGenTaskPreparation

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-bgdata-oracle-extraction.md)

## Overview
- **Priority**: High
- **Status**: complete
- **Description**: Replace `_prepare_bg` + skip arithmetic with `BGData` copy from Oracle

## Key Insights
- `_prepare_bg` (15 lines) is a degenerate case of `prepare_kb` for a single root constraint
- Skip arithmetic `(num_fm_constraints - 1) * 2 + len(variables) * 2` is replaced by `bg_data.next_available_id`
- `FMData` parameter removed from `prepare()` — ConGen no longer needs `root_feature` or `num_constraints`
- `congen_model.py:187-188` (`fm_data = oracle.get_fm_data()` / `self.next_tseitin_var = fm_data.next_tseitin_var`) becomes dead code

## Related Code Files
- **Modify**: `conacq/algorithms/acqmss/task_preparation.py` (primary)
- **Modify**: `conacq/algorithms/acqmss/congen_model.py` (caller update)

## Implementation Steps

### 1. Modify `ConGenTaskPreparation.prepare()` in `task_preparation.py`

**Remove**:
- `FMData` import (TYPE_CHECKING block, line 28)
- `_prepare_bg` function (lines 52-84)
- `fm_data` parameter from `prepare()` signature
- Lines 113-115: `root_feature = fm_data.root_feature` / `num_fm_constraints = fm_data.num_constraints`
- Line 118: `id_assumption = model.next_tseitin_var`
- Line 121: `id_assumption = _prepare_bg(result, provider, model.variables, root_feature, id_assumption)`
- Lines 124-125: skip arithmetic

**Replace with**:
```python
def prepare(self, model: ConGenModel, oracle: FeatureModelOracle) -> PreparationOutput:
    """Prepare ConGen task from model. BG from Oracle, oracle for GenerateNE."""
    result = ConGenTask()
    provider = DescriptionProvider()
    task_input = model.task_input

    # Step 0: Copy BG data from Oracle (root constraint pair from Part 3)
    bg_data = oracle.get_bg_data()
    result.set_kb.extend(bg_data.set_kb)
    result.assumptions.extend(list(bg_data.assumptions))
    result.negation_map.update(bg_data.negation_map)
    for aid, desc in bg_data.descriptions.items():
        provider.add_constraint_description(aid, desc)
    id_assumption = bg_data.next_available_id

    # Step 1: Prepare bias constraints as set_c (with negated forms for REDUCE)
    # ... rest unchanged from line 127 onward ...
```

### 2. Modify `ConGenModel.prepare()` in `congen_model.py`

**Remove**:
- Lines 187-188: `fm_data = oracle.get_fm_data()` / `self.next_tseitin_var = fm_data.next_tseitin_var`
- `fm_data` argument from `preparation.prepare()` call at line 203

**Change line 203**:
```python
# Before:
output = preparation.prepare(self, fm_data, oracle)
# After:
output = preparation.prepare(self, oracle)
```

### 3. Verify `model.next_tseitin_var` usage
After removing lines 187-188, `model.next_tseitin_var` keeps its initial value from `ConGenModel.__init__` (or from `ConGenModelBuilder`). Check that `task_preparation.py:129` (`next_tseitin_var = id_assumption`) still works because it's now assigned from `bg_data.next_available_id`, not from `model.next_tseitin_var`.

## Todo
- [ ] Delete `_prepare_bg` function
- [ ] Remove `FMData` import from task_preparation.py
- [ ] Update `prepare()` signature: remove `fm_data` param
- [ ] Replace BG creation + skip arithmetic with `bg_data` copy
- [ ] Update `ConGenModel.prepare()`: remove `fm_data` usage, update `preparation.prepare()` call
- [ ] Verify no other code references `_prepare_bg`

## Success Criteria
- `_prepare_bg` function deleted
- `FMData` no longer imported in `task_preparation.py`
- `prepare()` signature is `(self, model, oracle)`
- Skip arithmetic eliminated
- All ConGen tests pass with identical results

## Risk Assessment
- **`model.next_tseitin_var` dead code**: Lines 187-188 in congen_model.py must be removed to avoid confusion
- **Caller mismatch**: Only one caller (`congen_model.py:203`) — straightforward update
