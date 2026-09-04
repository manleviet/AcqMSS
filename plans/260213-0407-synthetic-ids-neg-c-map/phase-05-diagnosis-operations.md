# Phase 5: Update Diagnosis Operations

## Context Links
- [Phase 1: Checker Interface](phase-01-checker-interface.md)
- Source: `explanation/operations/algorithms/wipeoutr_fm.py`
- Source: `explanation/operations/algorithms/wipeoutr_t.py`
- Source: `explanation/operations/pysat_redundancy_constraints.py`
- Source: `explanation/models/task_preparation.py`

## Overview
- **Priority**: Medium
- **Status**: COMPLETE
- **Description**: Update WipeOutR_FM, WipeOutR_T, and diagnosis task
  preparation to work with assumption-based checkers. Diagnosis operations
  use `NonIncrementalDiagnosisTask` which now has `set_kb`/`assumptions`.

## Key Insights
- WipeOutR_FM currently uses `str(c_alpha)` for non-incremental neg_c_map
  keys (line 76). This is buggy -- str representation of lists is fragile.
- Diagnosis task preparation (`NonIncrementalDiagnosisTaskPreparation`)
  must also produce assumption-based output for consistency.
- `PySATRedundancyConstraints` creates checker via `CheckerFactory.create_from_model()`.
  After Phase 1, this already passes `set_kb`/`assumptions` to non-incremental.
- `neg_c_map` for diagnosis becomes `Dict[int, int]` naturally.

## Requirements
1. `NonIncrementalDiagnosisTaskPreparation` produces assumption-based output
2. `WipeOutR_FM` simplified: no `isinstance(c, list)` branching, no `str()` keys
3. `WipeOutR_T` simplified: same pattern as WipeOutR_FM but for `neg_t_map`
4. `PySATRedundancyConstraints` works with updated checker factory
4. SAT4J diagnosis operations work with updated `SAT4JChecker`

## Related Code Files
- **Modify**: `explanation/models/task_preparation.py`
  - `NonIncrementalDiagnosisTaskPreparation.prepare()` (line 508)
  - `NonIncrementalTestCaseTaskPreparation._prepare_testsuite_with_negation()`
- **Modify**: `explanation/operations/algorithms/wipeoutr_fm.py`
  - `WipeOutR_FM.find_redundancies()` (line 45)
- **Modify**: `explanation/operations/algorithms/wipeoutr_t.py`
  - `WipeOutR_T.find_redundancies()` -- uses `neg_t_map: Dict[int, int]`
- **Modify**: `explanation/operations/pysat_redundancy_constraints.py`
  - `PySATRedundancyConstraints.execute()` caller (line 63)
- **Check**: `explanation/operations/pysat_conflict_sat4j.py`
- **Check**: `explanation/operations/pysat_diagnosis_sat4j.py`

## Implementation Steps

### Step 1: Update `NonIncrementalDiagnosisTaskPreparation.prepare()`
Produce assumption-based output: embed clauses with `[-assumption_id]`,
populate `set_kb`, `assumptions`, and `neg_c_map` as `Dict[int, int]`.

Same pattern as Phase 2 Step 3 for CONGEN. The constraint loop becomes:
```python
id_assumption = next_tseitin_var  # or similar start value

for key, clauses in model.constraint_map.items():
    original_id = id_assumption
    for clause in clauses:
        result.set_kb.append(clause + [-original_id])
    result.assumptions.append(original_id)
    result.set_c.append(original_id)
    # ... description provider ...
    id_assumption += 1

    # Negated form
    if negated_constraint_map and f"NOT({key})" in negated_constraint_map:
        neg_clauses = negated_constraint_map[f"NOT({key})"]
        neg_id = id_assumption
        for neg_clause in neg_clauses:
            result.set_kb.append(neg_clause + [-neg_id])
        result.assumptions.append(neg_id)
        result.neg_c_map[original_id] = neg_id
        id_assumption += 1
```

### Step 2: Update `NonIncrementalTestCaseTaskPreparation`
Same pattern for test case preparation: embed examples with assumptions.
`neg_tc_map` becomes `Dict[int, int]`.

### Step 3: Simplify `WipeOutR_FM.find_redundancies()`
Remove `str()` key conversion and `isinstance` branching:

```python
def find_redundancies(self, set_c, neg_c_map: Dict[int, int]):
    # set_c is now List[int] (assumption IDs)
    redundant = []
    non_redundant = list(set_c)

    for c_alpha in set_c:
        if c_alpha not in neg_c_map:
            continue
        neg_alpha = neg_c_map[c_alpha]

        c_without = [c for c in non_redundant if c != c_alpha]
        test_set = c_without + [neg_alpha]
        is_consistent = self.checker.is_consistent(test_set)

        if not is_consistent:
            non_redundant.remove(c_alpha)
            redundant.append(c_alpha)

    return redundant, non_redundant
```

### Step 3b: Simplify `WipeOutR_T.find_redundancies()`
Same pattern as WipeOutR_FM but for test case redundancy.
`neg_t_map` is `Dict[int, int]` (assumption ID -> negated assumption ID).
Remove any `str()` or `isinstance` branching.

### Step 4: Update `PySATRedundancyConstraints.execute()`
Verify it passes correct data. After Phase 1, `CheckerFactory.create_from_model()`
already creates assumption-based checker. `model.get_neg_c_map()` returns
`Dict[int, int]`. Should work as-is, but verify.

### Step 5: Check SAT4J diagnosis operations
`PySATConflictSAT4J` and `PySATDiagnosisSAT4J` create `SAT4JChecker` via
`CheckerFactory.create_sat4jchecker()`. After Phase 1 update, factory passes
`set_kb`/`assumptions`. Verify these operations still work with
assumption-based SAT4JChecker.

The diagnosis models (`DiagnosisModel`) need `get_kb()` and
`get_assumptions()` methods for non-incremental too. If they don't exist,
add them.

### Step 6: Remove `get_hashcode` usage
If `get_hashcode` is no longer used anywhere in `task_preparation.py`,
remove the import and function.

## Todo List
- [x] Update `NonIncrementalDiagnosisTaskPreparation.prepare()`
- [x] Update `NonIncrementalTestCaseTaskPreparation` example preparation
- [x] Simplify `WipeOutR_FM.find_redundancies()`
- [x] Simplify `WipeOutR_T.find_redundancies()` (neg_t_map)
- [x] Verify `PySATRedundancyConstraints.execute()` works
- [x] Verify SAT4J diagnosis operations work
- [x] Add `get_kb()`/`get_assumptions()` to non-incremental diagnosis model
- [x] Remove unused `get_hashcode` import

## Success Criteria
- WipeOutR_FM has no `str()` or `isinstance` branching
- WipeOutR_T has no `str()` or `isinstance` branching (`neg_t_map` unified)
- `neg_c_map` and `neg_t_map` are `Dict[int, int]` in all diagnosis tasks
- SAT4J operations pass with assumption-based checker
- All diagnosis tests pass

## Risk Assessment
- **Diagnosis model API**: `DiagnosisModel.get_kb()` and
  `get_assumptions()` may only be defined for incremental. Need to add
  for non-incremental. Check `use_incremental` flag handling.
- **SAT4J jar availability**: tests may skip if jar not found.
  Existing test infrastructure handles this.
