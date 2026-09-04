# Phase 04: Update Callers

## Context Links

- `apps/run_congen.py` lines 82-201 (`process_model()`)
- `acqmss/eval/congen_runner.py` lines 83-237 (`ConGenRunner.run()`)
- `tests/test_congen.py` lines 67-127 (`create_checker_and_task()`)
- `acqmss/algorithms/__init__.py` — exports
- `acqmss/eval/cross_validation.py` line 189 — uses ConGenRunner

## Overview

- **Priority**: P1
- **Status**: completed
- **Description**: Update all callers to use new ConGenModel.prepare() (no manual GenerateNE) and new ConGen.acquire() signature.

## Key Insights

- Three callers all have identical boilerplate: create model -> prepare(mode) -> GenerateNE -> merge -> create checker -> acquire(task)
- After refactoring: create model -> prepare() -> CheckerFactory -> acquire(set_b, set_bg, set_tc, set_ne, ...)
- run_congen.py can optionally use ConGenModelBuilder for simplest path
- congen_runner.py needs fold reuse: call model.prepare(pos, neg) per fold
- test_congen.py helper simplified: no manual GenerateNE calls

## Requirements

### Functional
- All callers produce identical results post-refactoring
- Remove all manual GenerateNE + merge_ne_into_task calls from callers
- Use CheckerFactory.create_from_model() where appropriate
- Update __init__.py exports

### Non-functional
- Reduce code duplication across callers
- Keep backward compatibility for cross_validation.py (uses ConGenRunner)

## Related Code Files

### Files to modify
- `apps/run_congen.py`
- `acqmss/eval/congen_runner.py`
- `tests/test_congen.py`
- `acqmss/algorithms/__init__.py`

### Files NOT modified
- `acqmss/eval/cross_validation.py` — uses ConGenRunner, which is updated

## Implementation Steps

### Step 1: Update `apps/run_congen.py` — `process_model()`

**Current** (lines 134-174): manual GenerateNE + checker creation + acquire(task)

**New**: use ConGenModelBuilder or simplified ConGenModel flow

```python
# Replace lines 134-174 of process_model()

# Create ConGen model
congen_model = ConGenModel.from_bias_and_examples(
    bias_constraints=bias_constraints,
    positive_examples=positive_examples,
    negative_examples=negative_examples,
    feature_ids=feature_ids,
    background_knowledge=[root_feature_id] if root_feature_id is not None else []
)
congen_model.use_incremental = is_incremental
congen_model.solver_name = solver_name

# Prepare (includes GenerateNE internally)
profiler = get_global_profiler()
congen_model.prepare(solver_name=solver_name, profiler=profiler)
task = congen_model.task

# Create checker via factory
from explanation.operations.algorithms.checker import CheckerFactory
checker = CheckerFactory.create_from_model(congen_model, solver_name, profiler)

# Run ConGen with direct params
congen = ConGen(checker, profiler)
result = congen.acquire(
    set_b=task.set_c,
    set_bg=task.set_b,
    set_tc=task.set_tc,
    set_ne=task.set_ne,
    neg_c_map=task.neg_c_map,
    assumption_to_constraint=task.assumption_to_constraint
)
```

**Removed imports**:
- `from acqmss.algorithms.generate_ne import GenerateNE, merge_ne_into_task`
- `from explanation.operations.algorithms.checker import IncrementalPySATChecker, NonIncrementalPySATChecker`

**Added imports**:
- `from explanation.operations.algorithms.checker import CheckerFactory`

### Step 2: Update `acqmss/eval/congen_runner.py` — `ConGenRunner.run()`

**Current** (lines 149-197): manual GenerateNE + checker creation + acquire(task)

**New**:

```python
def run(self, positive_examples, negative_examples,
        background_clauses=None, shuffle_seed=None) -> ConGenRunResult:
    # ... (profiler/memory setup unchanged through line 166)

    checker = None
    try:
        # Shuffle bias ordering if seed provided
        bias_clauses = self.bias_clauses
        if shuffle_seed is not None:
            keys = list(bias_clauses.keys())
            random.Random(shuffle_seed).shuffle(keys)
            bias_clauses = {k: bias_clauses[k] for k in keys}

        # Create model
        model = ConGenModel.from_bias_and_examples(
            bias_constraints=bias_clauses,
            positive_examples=positive_examples,
            negative_examples=negative_examples,
            feature_ids=self.feature_ids,
            background_knowledge=self.background_knowledge
        )
        model.use_incremental = self.use_incremental
        model.solver_name = self.solver_name

        # Prepare (includes GenerateNE)
        model.prepare(solver_name=self.solver_name, profiler=profiler)
        task = model.task

        # Create checker via factory
        from explanation.operations.algorithms.checker import CheckerFactory
        checker = CheckerFactory.create_from_model(
            model, self.solver_name, profiler
        )

        # Run ConGen
        congen = ConGen(checker, profiler)
        result = congen.acquire(
            set_b=task.set_c,
            set_bg=task.set_b,
            set_tc=task.set_tc,
            set_ne=task.set_ne,
            neg_c_map=task.neg_c_map,
            assumption_to_constraint=task.assumption_to_constraint
        )

    finally:
# ... (cleanup unchanged)
```

**Removed imports**:
- `from acqmss.algorithms.generate_ne import GenerateNE, merge_ne_into_task`
- `from explanation.operations.algorithms.checker import IncrementalPySATChecker, NonIncrementalPySATChecker`

**Added imports**:
- `from explanation.operations.algorithms.checker import CheckerFactory`

### Step 3: Update `tests/test_congen.py` — `create_checker_and_task()`

**Current** (lines 67-127): manual GenerateNE + checker creation

**New**:

```python
def create_checker_and_task(oracle, bias, examples, is_incremental=True):
    """Helper to create checker and task for tests."""
    from explanation.operations.algorithms.checker import CheckerFactory

    bias_constraints = {c.id: c.clauses for c in bias.constraints}
    positive_examples = [e.assignments for e in examples.positive]
    negative_examples = [e.assignments for e in examples.negative]

    root_name = oracle.get_root_feature()
    root_id = oracle.get_feature_ids()[root_name]

    model = ConGenModel.from_bias_and_examples(
        bias_constraints=bias_constraints,
        positive_examples=positive_examples,
        negative_examples=negative_examples,
        feature_ids=oracle.get_feature_ids(),
        background_knowledge=[root_id]
    )
    model.use_incremental = is_incremental

    profiler = get_global_profiler()
    model.prepare(profiler=profiler)
    task = model.task

    checker = CheckerFactory.create_from_model(model, 'glucose4', profiler)

    return checker, task, profiler, root_id
```

**Update test methods**: Change `congen.acquire(task)` calls to:

```python
result = congen.acquire(
    set_b=task.set_c,
    set_bg=task.set_b,
    set_tc=task.set_tc,
    set_ne=task.set_ne,
    neg_c_map=task.neg_c_map,
    assumption_to_constraint=task.assumption_to_constraint
)
```

This affects:
- `test_congen_incremental_with_rs_examples` (line 144)
- `test_congen_non_incremental_with_rs_examples` (line 179)
- `test_congen_incremental_with_ff_examples` (line 215)

**Removed imports** from test file:
- `from acqmss.algorithms.generate_ne import merge_ne_into_task`
- `from explanation.operations.algorithms.checker import IncrementalPySATChecker, NonIncrementalPySATChecker`

**Note**: Keep `GenerateNE` import for `TestGenerateNE` class (tests GenerateNE in isolation).

### Step 4: Update `acqmss/algorithms/__init__.py`

Add ConGenModelBuilder:

```python
from .congen_model_builder import ConGenModelBuilder
```

Add to `__all__`:

```python
'ConGenModelBuilder',
```

Keep existing exports — `GenerateNE`, `merge_ne_into_task` remain exported for direct use/testing.

### Step 5: Verify cross_validation.py

`cross_validation.py` line 189 creates `ConGenRunner(...)` and calls `runner.run(pos, neg)`. Since ConGenRunner.run() is updated internally, no changes needed in cross_validation.py. Verify import chain works.

## Todo List

- [ ] Update `apps/run_congen.py` — remove GenerateNE boilerplate, use CheckerFactory
- [ ] Update `acqmss/eval/congen_runner.py` — same simplification
- [ ] Update `tests/test_congen.py` — simplify helper, update acquire() calls
- [ ] Update `acqmss/algorithms/__init__.py` — add ConGenModelBuilder export
- [ ] Verify `cross_validation.py` works unchanged
- [ ] Remove unused imports from all modified files

## Success Criteria

- All three callers produce identical results to before
- No manual GenerateNE + merge_ne_into_task in any caller
- All callers use CheckerFactory.create_from_model()
- All callers use new acquire() keyword signature
- cross_validation.py works unchanged (ConGenRunner API preserved)

## Risk Assessment

- **Risk**: ConGenRunner.run() signature change breaks cross_validation.py
  - **Mitigation**: ConGenRunner.run() external API unchanged; only internals change
- **Risk**: Test assertions on task structure break
  - **Mitigation**: task.set_ne now populated by prepare(); same data, different call site
- **Risk**: Import ordering issues with CheckerFactory in runners
  - **Mitigation**: Use lazy imports where needed

## Security Considerations

- No security impact

## Next Steps

- Phase 05: Run all tests to verify
