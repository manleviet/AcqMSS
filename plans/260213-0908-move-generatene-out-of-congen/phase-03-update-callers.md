# Phase 3: Update Callers

## Context Links

- run_congen: `apps/run_congen.py`
- congen_runner: `acqmss/eval/congen_runner.py`
- Phase 1: `phase-01-modify-generate-ne.md`
- Phase 2: `phase-02-update-task-and-congen.md`

## Overview

- **Priority**: P1 (blocks phase 4)
- **Status**: completed
- **Description**: Move GenerateNE invocation to callers. Both `run_congen.py` and `congen_runner.py` follow the same pattern: prep task, run GenerateNE, merge NE into task, create final checker, run CONGEN.

## Key Insights

- Both callers currently do: prepare task -> create checker -> CONGEN(checker).acquire(task)
- New flow: prepare task -> temp checker for QXP -> GenerateNE -> merge NE into task -> final checker -> CONGEN
- `NonIncrementalPySATChecker` is best for temp checker (no persistent solver to clean up, cheap)
- After NE generation, merge `ne_result.new_clauses` into `task.set_kb` and `ne_result.new_assumptions` into `task.assumptions`
- Final checker (incremental or non-incremental) gets the complete data

## Requirements

### Functional
- GenerateNE runs before CONGEN in both callers
- NE result merged into task: `set_ne`, `set_kb`, `assumptions`, `neg_c_map`, `assumption_to_constraint`
- Final checker created with complete data (including NE clauses)

### Non-functional
- Algorithm results identical to before
- No performance regression (temp checker is lightweight)

## Architecture

```
Before:
  prep task -> checker(task.set_kb, task.assumptions) -> CONGEN(checker).acquire(task)
                                                         [internally: GenerateNE -> ACQMSS -> REDUCE]

After:
  prep task -> temp_checker(task.set_kb, task.assumptions) -> GenerateNE(temp_checker)
            -> merge NE into task
            -> final_checker(task.set_kb, task.assumptions)  [now includes NE data]
            -> CONGEN(final_checker).acquire(task)
               [internally: ACQMSS -> REDUCE]
```

## Related Code Files

- **Modify**: `apps/run_congen.py` (function `process_model`, lines 85-203)
- **Modify**: `acqmss/eval/congen_runner.py` (method `CONGENRunner.run`, lines 119-231)

## Implementation Steps

### Step 1: Create shared helper function `run_generate_ne_and_merge`

Add a helper in `acqmss/algorithms/generate_ne.py` (or as a static method on `GenerateNE`) to avoid duplicating the merge logic:

```python
def merge_ne_into_task(task: 'ConGenTask', ne_result: NEResult) -> None:
  """Merge GenerateNE results into task.

  Updates task in-place:
  - set_ne: NE assumption IDs
  - set_kb: appends new clauses
  - assumptions: appends new assumption IDs
  - neg_c_map: merges NE negation map
  - assumption_to_constraint: adds ne_X entries

  Args:
      task: ConGenTask to update
      ne_result: Result from GenerateNE.generate()
  """
  task.set_ne = ne_result.assumption_ids
  task.set_kb.extend(ne_result.new_clauses)
  task.assumptions.extend(ne_result.set_neg_tv)
  task.neg_c_map.update(ne_result.neg_map)
  for ne_id in ne_result.assumption_ids:
    task.assumption_to_constraint[ne_id] = f"ne_{ne_id}"
```

Add this as a module-level function in `generate_ne.py` and export it from `__init__.py`.

### Step 2: Update `apps/run_congen.py` - `process_model()`

After task preparation (lines ~148-169), insert GenerateNE step before creating final checker.

**Current code** (simplified):
```python
if is_incremental:
    preparation = IncrementalCONGENTaskPreparation()
    output = preparation.prepare(congen_model)
    task = output.task
    checker = IncrementalPySATChecker(task.set_kb, task.assumptions, solver_name, profiler)
else:
    preparation = NonIncrementalCONGENTaskPreparation()
    output = preparation.prepare(congen_model)
    task = output.task
    checker = NonIncrementalPySATChecker(task.set_kb, task.assumptions, solver_name, profiler)

congen = CONGEN(checker, profiler)
result = congen.acquire(task)
```

**New code:**

```python
if is_incremental:
    preparation = IncrementalCONGENTaskPreparation()
else:
    preparation = NonIncrementalCONGENTaskPreparation()

output = preparation.prepare(congen_model)
task = output.task

# Run GenerateNE with temp non-incremental checker (read-only QXP calls)
temp_checker = NonIncrementalPySATChecker(
    task.set_kb, task.assumptions, solver_name, profiler
)
generate_ne = GenerateNE(temp_checker, profiler)
ne_result = generate_ne.generate(
    set_tv=task.e_neg_literals,
    set_bg=task.set_b,
    start_assumption_id=task.next_assumption_id
)
merge_ne_into_task(task, ne_result)

# Create final checker with complete data (including NE)
if is_incremental:
    checker = IncrementalPySATChecker(
        task.set_kb, task.assumptions, solver_name, profiler
    )
else:
    checker = NonIncrementalPySATChecker(
        task.set_kb, task.assumptions, solver_name, profiler
    )

congen = CONGEN(checker, profiler)
result = congen.acquire(task)
```

Add imports at top:

```python
from conacq.algorithms.generate_ne import GenerateNE, merge_ne_into_task
```

### Step 3: Update `acqmss/eval/congen_runner.py` - `CONGENRunner.run()`

Same pattern as Step 2. Current code (lines ~168-191):

**New code:**

```python
if self.use_incremental:
    preparation = IncrementalCONGENTaskPreparation()
else:
    preparation = NonIncrementalCONGENTaskPreparation()

output = preparation.prepare(model)
task = output.task

# Run GenerateNE with temp non-incremental checker
temp_checker = NonIncrementalPySATChecker(
    task.set_kb, task.assumptions, self.solver_name, profiler
)
generate_ne = GenerateNE(temp_checker, profiler)
ne_result = generate_ne.generate(
    set_tv=task.e_neg_literals,
    set_bg=task.set_b,
    start_assumption_id=task.next_assumption_id
)
merge_ne_into_task(task, ne_result)

# Create final checker with complete data
if self.use_incremental:
    checker = IncrementalPySATChecker(
        task.set_kb, task.assumptions, self.solver_name, profiler
    )
else:
    checker = NonIncrementalPySATChecker(
        task.set_kb, task.assumptions, self.solver_name, profiler
    )

congen = CONGEN(checker, profiler)
result = congen.acquire(task)
```

Add imports at top:

```python
from conacq.algorithms.generate_ne import GenerateNE, merge_ne_into_task
```

### Step 4: Update `__init__.py` exports

Add `merge_ne_into_task` to `acqmss/algorithms/__init__.py` exports:

```python
from .generate_ne import GenerateNE, NEResult, merge_ne_into_task
```

And add `'merge_ne_into_task'` to `__all__`.

## Todo List

- [ ] Create `merge_ne_into_task()` function in `generate_ne.py`
- [ ] Export `merge_ne_into_task` from `acqmss/algorithms/__init__.py`
- [ ] Update `apps/run_congen.py` `process_model()` with GenerateNE step
- [ ] Update `acqmss/eval/congen_runner.py` `CONGENRunner.run()` with GenerateNE step
- [ ] Add new imports to both callers
- [ ] Verify both callers create temp checker, run GenerateNE, merge, create final checker

## Success Criteria

- `run_congen.py` runs GenerateNE before CONGEN
- `congen_runner.py` runs GenerateNE before CONGEN
- CONGEN receives task with populated `set_ne`
- Results identical to before refactoring
- No calls to `checker.add_clause()` or `checker.add_assumption()` anywhere in the call chain

## Risk Assessment

- **Medium risk**: Temp NonIncrementalPySATChecker shares `task.set_kb` list by reference with final checker
  - **Mitigation**: This is intentional -- `merge_ne_into_task` appends to `task.set_kb` before creating final checker, so final checker gets complete data. The temp checker is unused after GenerateNE completes.
- **Low risk**: Performance -- temp checker overhead is negligible (NonIncremental creates fresh solver per call anyway)

## Security Considerations

None -- internal refactoring only.

## Next Steps

Phase 4: Remove `add_clause` and `add_assumption` from `ConsistencyChecker` and all subclasses.
