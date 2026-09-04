# Phase 2: Unify Task Classes and Task Preparation

## Context Links
- [Phase 1: Checker Interface](phase-01-checker-interface.md)
- Source: `acqmss/algorithms/task.py`, `acqmss/algorithms/task_preparation.py`
- Source: `explanation/models/task_preparation.py`

## Overview
- **Priority**: High (must precede phase 3)
- **Status**: COMPLETE
- **Description**: Non-incremental task preparation produces assumption-based
  output (same as incremental). Eliminates separate non-incremental task classes
  and preparation classes for CONGEN.

## Key Insights
- `IncrementalCONGENTaskPreparation` already produces the right format:
  `set_kb` with embedded assumptions, `assumptions` list, `set_c` as
  assumption IDs, `neg_c_map` as `Dict[int, int]`.
- `NonIncrementalCONGENTaskPreparation` currently produces clause lists.
  We rewrite it to produce the SAME assumption-based format.
- The ONLY difference at task level: a flag indicating which checker to create.
- `IncrementalCONGENTask` has `assumptions` field (from `IncrementalTestCaseTask`).
  `NonIncrementalCONGENTask` lacks it. After unification, both use assumptions.
- Explanation package tasks (`NonIncrementalDiagnosisTask`,
  `NonIncrementalTestCaseTask`) are used by diagnosis operations (Phase 5).
  Keep them for now but add `set_kb`/`assumptions` fields.

## Requirements
1. `NonIncrementalCONGENTaskPreparation` produces assumption-based output
   identical in structure to `IncrementalCONGENTaskPreparation`
2. `NonIncrementalCONGENTask` gets `assumptions` field (or merges into
   `IncrementalCONGENTask`)
3. `neg_c_map` is `Dict[int, int]` for both modes
4. CONGEN instantiation code passes `set_kb`/`assumptions` to checker

## Architecture
```
Before:
  Incremental:     set_c = [101, 102, ...]        (assumption IDs)
  Non-incremental: set_c = [[[1,2]], [[-3]], ...]  (clause lists)

After:
  Both modes:      set_c = [101, 102, ...]        (assumption IDs)
  Both modes:      set_kb = [clauses with -assumption_id embedded]
  Both modes:      neg_c_map = {101: 102, 103: 104, ...}
```

## Related Code Files
- **Modify**: `acqmss/algorithms/task.py`
  - `NonIncrementalCONGENTask`: add `assumptions` or merge with incremental
- **Modify**: `acqmss/algorithms/task_preparation.py`
  - `NonIncrementalCONGENTaskPreparation`: rewrite to produce assumptions
- **Modify**: `explanation/models/task_preparation.py`
  - `NonIncrementalTestCaseTask`: add `set_kb`, `assumptions` fields
  - `NonIncrementalDiagnosisTask`: add `set_kb`, `assumptions` fields
- **Modify**: CONGEN runner code that creates checker from task

## Implementation Steps

### Step 1: Add fields to `NonIncrementalTestCaseTask`
File: `explanation/models/task_preparation.py`, line 152

```python
@dataclass
class NonIncrementalTestCaseTask(TestCaseTask):
    """Test case task for non-incremental mode.
    Now also stores set_kb + assumptions for assumption-based solving."""
    set_kb: List[List[int]] = field(default_factory=list)
    assumptions: List[int] = field(default_factory=list)
```

### Step 2: Simplify `NonIncrementalCONGENTask`
File: `acqmss/algorithms/task.py`, line 77

Since `NonIncrementalTestCaseTask` now has `assumptions`, and `CONGENTask`
already has `assumption_to_constraint`, `constraint_to_assumption`,
`next_assumption_id`, `neg_c_map` -- `NonIncrementalCONGENTask` just
needs to keep `clauses_to_name` for result formatting:

```python
@dataclass
class NonIncrementalCONGENTask(CONGENTask, NonIncrementalTestCaseTask):
    """ConGen task for non-incremental mode.
    Uses assumption IDs (same as incremental). Checker creates fresh solver.
    """
    clauses_to_name: Dict[Tuple, str] = field(default_factory=dict)
    name_to_clauses: Dict[str, List[List[int]]] = field(default_factory=dict)
```

Remove `clauses_to_name`-based `get_constraint_name()` override if assumption-based
lookup now handles it. Or keep it as fallback.

### Step 3: Rewrite `NonIncrementalCONGENTaskPreparation`
File: `acqmss/algorithms/task_preparation.py`, line 214

The core change: use the SAME assumption embedding logic as
`IncrementalCONGENTaskPreparation`. For each bias constraint:
1. Embed clauses with `[-assumption_id]` into `set_kb`
2. Store assumption ID in `set_c`, `assumptions`
3. Create negated form with its own assumption ID
4. Store `neg_c_map[original_id] = negated_id`

```python
def _prepare_bias_constraints(self, result, provider,
                               constraint_map, negated_constraint_map):
    id_assumption = result.next_assumption_id

    for name, clauses in constraint_map.items():
        original_id = id_assumption
        # Embed with assumption: clause ∨ ¬assumption
        for clause in clauses:
            result.set_kb.append(clause + [-original_id])
        result.assumptions.append(original_id)
        result.set_c.append(original_id)
        result.constraint_to_assumption[name] = original_id
        result.assumption_to_constraint[original_id] = name
        provider.add_constraint_description(clauses, name)
        id_assumption += 1

        # Negated form
        negated_key = f"NOT({name})"
        if negated_constraint_map and negated_key in negated_constraint_map:
            negated_clauses = negated_constraint_map[negated_key]
        else:
            negated_clauses, _ = negate_cnf_tseitin(clauses, id_assumption)
        negated_id = id_assumption
        for neg_clause in negated_clauses:
            result.set_kb.append(neg_clause + [-negated_id])
        result.assumptions.append(negated_id)
        result.neg_c_map[original_id] = negated_id
        provider.add_constraint_description(negated_clauses, negated_key)
        id_assumption += 1

        # Keep name mappings for result formatting
        clauses_key = tuple(tuple(c) for c in clauses)
        result.clauses_to_name[clauses_key] = name
        result.name_to_clauses[name] = clauses

    result.next_assumption_id = id_assumption
```

### Step 4: Rewrite `_prepare_examples` for non-incremental
Same assumption embedding logic as incremental:

```python
def _prepare_examples(self, result, provider, variables,
                      examples, is_negative):
    id_assumption = result.next_assumption_id
    for testcase in examples.testcases:
        literals = []
        desc_parts = []
        for assignment in testcase.assignments:
            var = variables[assignment.feature]
            if not assignment.value:
                var = -var
            literals.append(var)
            desc_parts.append(f'{assignment.feature}='
                              f'{"true" if assignment.value else "false"}')

        original_id = id_assumption
        for lit in literals:
            result.set_kb.append([lit, -original_id])
        result.assumptions.append(original_id)

        desc = ' & '.join(desc_parts)
        example_clauses = [[lit] for lit in literals]
        provider.add_test_case_description(example_clauses, desc)

        if is_negative:
            result.set_tv.append(original_id)
            result.e_neg_literals.append(literals)
        else:
            result.set_tc.append(original_id)

        id_assumption += 1

    result.next_assumption_id = id_assumption
```

### Step 5: Update `prepare()` method
Add root constraint as assumption-embedded clause:

```python
def prepare(self, model):
    result = NonIncrementalCONGENTask()
    # Start assumption IDs from next_tseitin_var to avoid conflicts
    result.next_assumption_id = model.next_tseitin_var
    # ... prepare bias, examples ...
    if model.root_feature_id is not None:
        root_id = result.next_assumption_id
        result.set_kb.append([model.root_feature_id, -root_id])
        result.assumptions.append(root_id)
        result.set_b.append(root_id)
        result.next_assumption_id += 1
    return PreparationOutput(result, provider)
```

### Step 6: Update CONGEN runner to pass set_kb/assumptions to checker
File: wherever `NonIncrementalPySATChecker` is instantiated for CONGEN

```python
checker = NonIncrementalPySATChecker(
    task.set_kb, task.assumptions, solver_name, profiler)
```

## Todo List
- [x] Add `set_kb`, `assumptions` to `NonIncrementalTestCaseTask`
- [x] Update `NonIncrementalCONGENTask` (keep name mappings for formatting)
- [x] Rewrite `NonIncrementalCONGENTaskPreparation._prepare_bias_constraints()`
- [x] Rewrite `NonIncrementalCONGENTaskPreparation._prepare_examples()`
- [x] Update `NonIncrementalCONGENTaskPreparation.prepare()` root handling
- [x] Update CONGEN runner to pass `set_kb`/`assumptions` to checker
- [x] Verify: `python -c "from acqmss.algorithms.task_preparation import *"`

## Success Criteria
- Non-incremental task has same fields as incremental: `set_kb`, `assumptions`,
  `set_c` as `List[int]`, `neg_c_map` as `Dict[int, int]`
- `NonIncrementalPySATChecker` receives `set_kb`/`assumptions` from task
- All data types unified between modes

## Risk Assessment
- **`next_tseitin_var` must be correct** for non-incremental too: if
  `CONGENModel` doesn't compute it for non-incremental, assumption IDs
  could collide with variable IDs. Verify `model.next_tseitin_var` is set.
- **`set_b` changes from clause lists to assumption IDs**: callers that
  iterate `set_b` and expect clauses will break. Update in Phase 3.
