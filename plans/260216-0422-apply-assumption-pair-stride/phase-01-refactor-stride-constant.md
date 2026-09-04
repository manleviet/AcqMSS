# Phase 1: Refactor Stride Constant

## Context Links

- [plan.md](plan.md)
- [explanation/models/task_preparation.py](../../explanation/models/task_preparation.py) - base module, new constant home
- [acqmss/algorithms/task_preparation.py](../../conacq/algorithms/task_preparation.py) - ConGen task prep
- [acqmss/oracle/fm_oracle_model.py](../../conacq/oracle/fm_oracle_model.py) - current constant location

## Overview

- **Priority**: P3
- **Status**: Complete
- **Description**: Move `_ASSUMPTION_PAIR_STRIDE` to `explanation/models/task_preparation.py` and update all consumers

## Key Insights

- All 3 files use the same semantic: "each constraint/test case produces a pair of assumptions (original + negated), stride by 2 to get originals"
- `explanation/models/task_preparation.py` is the lowest-level module; both acqmss files already import from it
- `DiagnosisTaskPreparation._assign_sets` conditionally uses `step = 2 if has_negated_forms else 1` -- the constant only applies when `has_negated_forms=True`

## Requirements

**Functional:**
- Define `_ASSUMPTION_PAIR_STRIDE = 2` in `explanation/models/task_preparation.py` (module-level)
- Remove definition from `acqmss/oracle/fm_oracle_model.py`
- Replace all hardcoded `2` stride values with the constant

**Non-functional:**
- No new package dependencies
- All existing tests pass unchanged

## Architecture

No structural changes. Single constant moves from `acqmss/oracle/fm_oracle_model.py` to `explanation/models/task_preparation.py`. Import direction unchanged.

## Related Code Files

**Modify:**
1. `explanation/models/task_preparation.py` - Add constant definition; use in `DiagnosisTaskPreparation._assign_sets` and `TestCaseTaskPreparation._assign_sets`
2. `acqmss/oracle/fm_oracle_model.py` - Remove constant definition; import from `explanation.models.task_preparation`
3. `acqmss/algorithms/task_preparation.py` - Import constant; replace `step = 2`

**No new files.**

## Implementation Steps

### Step 1: Add constant to `explanation/models/task_preparation.py`

Add near top of file (after imports, before class definitions):

```python
# Each constraint produces a pair of assumptions (original + negated),
# so we stride by 2 to select only original assumptions.
_ASSUMPTION_PAIR_STRIDE = 2
```

### Step 2: Update `DiagnosisTaskPreparation._assign_sets` (line 387)

Change:
```python
step = 2 if has_negated_forms else 1
```
To:
```python
step = _ASSUMPTION_PAIR_STRIDE if has_negated_forms else 1
```

### Step 3: Update `TestCaseTaskPreparation._assign_sets` (lines 528, 530)

Change:
```python
original_tc_tv = [tc_tv_assumptions[i] for i in range(0, len(tc_tv_assumptions), 2)]
num_tc_original = (start_id_tv - start_id_tc) // 2
```
To:
```python
original_tc_tv = [tc_tv_assumptions[i] for i in range(0, len(tc_tv_assumptions), _ASSUMPTION_PAIR_STRIDE)]
num_tc_original = (start_id_tv - start_id_tc) // _ASSUMPTION_PAIR_STRIDE
```

### Step 4: Update `acqmss/oracle/fm_oracle_model.py`

- Remove lines 17-19 (constant definition + comment)
- Add to existing import from `explanation.models.task_preparation`:
  ```python
  from explanation.models.task_preparation import PreparationOutput, prepare_kb, _ASSUMPTION_PAIR_STRIDE
  ```
- Usages on lines 116 and 242 already reference `_ASSUMPTION_PAIR_STRIDE` -- no change needed

### Step 5: Update `acqmss/algorithms/task_preparation.py`

- Add `_ASSUMPTION_PAIR_STRIDE` to existing import block (line 13-19):
  ```python
  from explanation.models.task_preparation import (
      TestCaseTask,
      TestCaseTaskPreparationStrategy,
      DescriptionProvider,
      PreparationOutput, prepare_testsuite_with_negation,
      prepare_kb,
      _ASSUMPTION_PAIR_STRIDE,
  )
  ```
- Change line 255: `step = 2` to `step = _ASSUMPTION_PAIR_STRIDE`
- Usages on lines 258, 261, 263 reference `step` variable -- no change needed

### Step 6: Run tests

```bash
PYTHONPATH=. pytest tests/ -v
```

### Step 7: Run linting

```bash
ruff check acqmss/algorithms/task_preparation.py acqmss/oracle/fm_oracle_model.py explanation/models/task_preparation.py
```

## Todo List

- [ ] Add `_ASSUMPTION_PAIR_STRIDE = 2` to `explanation/models/task_preparation.py`
- [ ] Update `DiagnosisTaskPreparation._assign_sets` to use constant
- [ ] Update `TestCaseTaskPreparation._assign_sets` to use constant (2 occurrences)
- [ ] Remove constant from `acqmss/oracle/fm_oracle_model.py`, update import
- [ ] Add constant to import in `acqmss/algorithms/task_preparation.py`, use in `_assign_sets`
- [ ] Run tests
- [ ] Run linting

## Success Criteria

- `grep -rn "step = 2" acqmss/algorithms/task_preparation.py explanation/models/task_preparation.py` returns 0 matches
- `grep -rn "_ASSUMPTION_PAIR_STRIDE" acqmss/oracle/fm_oracle_model.py` shows import only, no local definition
- `PYTHONPATH=. pytest tests/ -v` all pass
- `ruff check` clean on all 3 files

## Risk Assessment

- **Low risk**: Pure rename/move refactor, no logic changes
- **Mitigation**: Tests cover all code paths through both incremental and non-incremental modes

## Security Considerations

None -- internal constant refactor only.

## Next Steps

- Commit with message: `refactor(task-prep): replace magic number 2 with _ASSUMPTION_PAIR_STRIDE constant`
- Optionally export via `explanation/models/__init__.py` if other modules need it in future (YAGNI for now)
