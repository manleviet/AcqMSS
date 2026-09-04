# Phase 01: Modify ConGenModel

## Context Links

- Current: `acqmss/algorithms/congen_model.py` (93 LOC)
- Task prep: `acqmss/algorithms/task_preparation.py` (214 LOC)
- GenerateNE: `acqmss/algorithms/generate_ne.py` (146 LOC)
- CheckerModel protocol: `explanation/operations/algorithms/checker.py` L22-32
- DiagnosisModel reference: `explanation/models/pysat_diagnosis_model.py`

## Overview

- **Priority**: P1 (blocking all other phases)
- **Status**: completed
- **Description**: Make ConGenModel implement CheckerModel protocol, add `use_incremental` flag, restructure `prepare()` to include GenerateNE execution internally.

## Key Insights

- CheckerModel protocol requires: `use_incremental: bool`, `get_kb()`, `get_assumptions()`
- Protocol uses structural subtyping (`@runtime_checkable`), so no inheritance needed
- DiagnosisModel pattern: `build()` calls `prepare()`, which populates `_task`; then model exposes `get_kb()`/`get_assumptions()` from task
- GenerateNE currently called by every caller (run_congen.py, congen_runner.py, test_congen.py) with identical boilerplate: create temp checker -> generate -> merge. Moving into `prepare()` eliminates this duplication
- `prepare()` must accept optional `pos_examples`/`neg_examples` for fold reuse in cross-validation

## Requirements

### Functional
- ConGenModel satisfies CheckerModel protocol (structural subtyping)
- `prepare()` runs GenerateNE internally, stores results in task
- `prepare()` accepts optional examples for fold reuse
- Remove `mode_name` parameter from `prepare()`
- Expose `get_kb()` and `get_assumptions()` that delegate to task

### Non-functional
- No `if is_incremental` branching in model code
- Backward compat: `from_bias_and_examples()` still works

## Architecture

```
ConGenModel
  +-- use_incremental: bool = True          # NEW: for CheckerModel
  +-- solver_name: str = 'glucose4'         # NEW: for checker creation
  +-- get_kb() -> List[List[int]]           # NEW: delegates to task.set_kb
  +-- get_assumptions() -> List[int]        # NEW: delegates to task.assumptions
  +-- prepare(pos_examples?, neg_examples?, solver_name?, profiler?) -> ConGenTask
        1. Update task_input if examples provided
        2. ConGenTaskPreparation.prepare(self) -> task
        3. Create temp NonIncrementalPySATChecker from task data
        4. GenerateNE(temp_checker, profiler).generate(...)
        5. merge_ne_into_task(task, ne_result)
        6. Store task, return task
```

## Related Code Files

### Files to modify
- `acqmss/algorithms/congen_model.py` — main changes

### Files NOT modified (this phase)
- `acqmss/algorithms/task_preparation.py` — no changes needed
- `acqmss/algorithms/generate_ne.py` — no changes needed (merge_ne_into_task stays)

## Implementation Steps

### Step 1: Add `use_incremental` and `solver_name` attributes

In `ConGenModel.__init__()` (line 30-36), add:

```python
self.use_incremental: bool = True
self.solver_name: str = 'glucose4'
```

### Step 2: Add `get_kb()` and `get_assumptions()` methods

Add after the `description_provider` property (after line 54):

```python
def get_kb(self) -> List[List[int]]:
    """Get full KB with assumptions (CheckerModel protocol)."""
    if self._task is None:
        raise RuntimeError("Call prepare() first")
    return self._task.set_kb

def get_assumptions(self) -> List[int]:
    """Get assumption literals (CheckerModel protocol)."""
    if self._task is None:
        raise RuntimeError("Call prepare() first")
    return self._task.assumptions
```

### Step 3: Restructure `prepare()` method

Replace current `prepare()` (lines 56-82) with new signature and logic:

```python
def prepare(
        self,
        positive_examples: Optional[List[Dict[str, bool]]] = None,
        negative_examples: Optional[List[Dict[str, bool]]] = None,
        solver_name: Optional[str] = None,
        profiler: Optional[AbstractProfiler] = None
) -> ConGenTask:
  """Prepare ConGen task including GenerateNE.

  If examples provided, updates task_input before preparing.
  Runs GenerateNE internally (callers no longer need to).

  Args:
      positive_examples: Optional new E+ (for fold reuse)
      negative_examples: Optional new E- (for fold reuse)
      solver_name: Override solver name for temp checker
      profiler: Optional profiler instance

  Returns:
      ConGenTask with set_ne already populated.
  """
  # Update task_input if new examples provided
  if positive_examples is not None or negative_examples is not None:
    pos_tc = self._examples_to_testsuite(positive_examples or [])
    neg_tc = self._examples_to_testsuite(negative_examples or [])
    self.task_input = TaskInput(
      positive_test_cases=pos_tc,
      negative_test_cases=neg_tc
    )

  # Step 1: Run ConGenTaskPreparation
  from .task_preparation import ConGenTaskPreparation
  preparation = ConGenTaskPreparation()
  output = preparation.prepare(self)

  assert isinstance(output.task, ConGenTask)
  self._task = output.task
  self._description_provider = output.description_provider

  # Step 2: Run GenerateNE with temp non-incremental checker
  _solver = solver_name or self.solver_name
  _profiler = profiler or get_global_profiler()

  from .generate_ne import GenerateNE, merge_ne_into_task
  from explanation.operations.algorithms.checker import NonIncrementalPySATChecker

  temp_checker = NonIncrementalPySATChecker(
    self._task.set_kb, self._task.assumptions, _solver, _profiler
  )
  generate_ne = GenerateNE(temp_checker, _profiler)
  ne_result = generate_ne.generate(
    set_tv=self._task.e_neg_literals,
    set_bg=self._task.set_b,
    start_assumption_id=self._task.next_assumption_id
  )
  merge_ne_into_task(self._task, ne_result)

  return self._task
```

### Step 4: Update `from_bias_and_examples()` factory

No signature change. But the returned model now has `use_incremental` and `solver_name` defaults that callers can override before calling `prepare()`.

### Step 5: Add imports

Add to top of file:

```python
from explanation.operations.algorithms.profiler import get_global_profiler, AbstractProfiler
```

### Step 6: Remove `mode_name` param usage

The old `prepare(mode_name)` call from callers will break. Callers updated in Phase 04.

## Todo List

- [ ] Add `use_incremental: bool` and `solver_name: str` to `__init__()`
- [ ] Add `get_kb()` method
- [ ] Add `get_assumptions()` method
- [ ] Restructure `prepare()` to include GenerateNE
- [ ] Add new imports (profiler, checker)
- [ ] Verify CheckerModel protocol satisfaction with isinstance check
- [ ] Keep `from_bias_and_examples()` working

## Success Criteria

- `isinstance(model, CheckerModel)` returns True after prepare()
- `model.get_kb()` returns task.set_kb
- `model.get_assumptions()` returns task.assumptions
- `prepare()` populates task.set_ne (GenerateNE ran internally)
- No caller needs to manually run GenerateNE + merge_ne_into_task
- `CheckerFactory.create_from_model(model)` works

## Risk Assessment

- **Risk**: Changing `prepare()` signature breaks all callers
  - **Mitigation**: Callers updated in Phase 04; run all tests in Phase 05
- **Risk**: temp_checker inside prepare() not cleaned up
  - **Mitigation**: NonIncrementalPySATChecker has no persistent state to clean up
- **Risk**: Protocol mismatch (missing attribute)
  - **Mitigation**: Add `isinstance(self, CheckerModel)` assert in prepare()

## Security Considerations

- No security impact (internal refactoring only)

## Next Steps

- Phase 02 depends on this (ConGenModelBuilder calls prepare())
- Phase 03 depends on task structure being stable
- Phase 04 updates callers to remove manual GenerateNE calls
