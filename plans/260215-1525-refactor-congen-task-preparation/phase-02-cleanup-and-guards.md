# Phase 2: Cleanup Dead Code & Add Guards

## Context

- Parent plan: [plan.md](plan.md)
- Depends on: Phase 1 complete

## Overview

- **Priority**: Medium
- **Status**: pending
- **Description**: Remove commented-out code from both files, add guard clauses, clean unused imports

## Related Code Files

- `acqmss/algorithms/task_preparation.py` — ~20 lines commented-out code in Step 3
- `acqmss/algorithms/congen_model.py` — ~80 lines commented-out code (lines 218-280)

## Implementation Steps

1. **Remove commented-out code in `task_preparation.py`**
   - All `# result.set_kb.append(...)`, `# result.assumptions.append(...)` blocks in extracted methods
   - Stale `# id_assumption = prepare_testsuite_with_negation(...)` block

2. **Remove commented-out code in `congen_model.py`**
   - Lines 218-280: entire commented Step 2 (GenerateNE) block in `ConGenModel.prepare()`

3. **Clean unused imports in `task_preparation.py`**
   - Remove `from .generate_ne import GenerateNE, merge_ne_into_task` if unused after extraction
   - Keep `NonIncrementalPySATChecker` and `QuickXPlain` imports (still used)

4. **Add guard clause**
   - In `_prepare_negative_examples()`: validate `model.oracle is not None`
   - `raise ValueError("Oracle required for NE generation from negative examples")`

5. **Remove stale commented fields in `ConGenTask`**
   - `# e_neg_literals` and `# next_assumption_id` commented lines (lines ~49, 52)

## Todo

- [ ] Remove commented code in task_preparation.py
- [ ] Remove commented code in congen_model.py
- [ ] Clean unused imports
- [ ] Add oracle guard clause
- [ ] Remove stale commented fields in ConGenTask

## Success Criteria

- Zero commented-out code blocks in both files
- No unused imports
- Guard clause raises clear error for None oracle
- All tests pass unchanged
