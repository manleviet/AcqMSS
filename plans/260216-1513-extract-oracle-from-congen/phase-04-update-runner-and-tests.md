# Phase 4: Update Runner and Tests

## Context Links
- [plan.md](./plan.md)
- [phase-03-simplify-builder.md](./phase-03-simplify-builder.md)
- [congen_runner.py](../../conacq/eval/congen_runner.py)
- [test_congen.py](../../tests/test_congen.py)
- [run_congen.py](../../apps/run_congen.py)

## Overview
- **Date**: 2026-02-16
- **Description**: Update all callers to create oracle externally and pass to `model.prepare(oracle)`. Includes `ConGenRunner`, `run_congen.py` app, and `test_congen.py`.
- **Priority**: P2
- **Implementation Status**: Pending
- **Review Status**: Pending

## Key Insights
- `ConGenRunner.__init__` already has `fm_path` -- create oracle there, reuse across folds
- `ConGenRunner.run()` calls `model.prepare(pos, neg)` -- add oracle param
- `run_congen.py` uses `ConGenModelBuilder.from_bias_and_fm_uvl()` -- change to `from_bias()` + oracle creation
- `test_congen.py` helper `create_checker_and_task()` uses same builder pattern -- update similarly
- Cross-validation (`cross_validation.py`) delegates to `ConGenRunner` -- no direct changes needed

## Requirements

### Functional
- `ConGenRunner` creates `FeatureModelOracle` in `__init__`, reuses across folds
- `run_congen.py` creates oracle per model, passes to `model.prepare()`
- Test helper creates oracle, passes to `model.prepare()`
- All tests pass with new API

### Non-Functional
- Oracle created once, reused (performance benefit for CV)
- No behavioral change in results

## Architecture

### ConGenRunner Flow (After)
```
ConGenRunner.__init__(bias_path, fm_path, ...)
  ├── model = ConGenModelBuilder.from_bias(bias_path).build()
  └── oracle = FeatureModelOracle(fm_path, use_incremental=False)

ConGenRunner.run(pos, neg)
  ├── model.prepare(oracle, pos, neg)
  ├── checker = CheckerFactory.create_from_model(model)
  └── congen.acquire(...)
```

## Related Code Files

### Files to Modify
| File | Change |
|------|--------|
| `acqmss/eval/congen_runner.py` | Create oracle in `__init__`, pass to `prepare()` |
| `apps/run_congen.py` | Use `from_bias()`, create oracle separately |
| `tests/test_congen.py` | Update `create_checker_and_task()` helper |

### Files Unchanged
| File | Reason |
|------|--------|
| `acqmss/eval/cross_validation.py` | Delegates to `ConGenRunner` -- no direct model access |

## Implementation Steps

### Step 1: Update `ConGenRunner` (`congen_runner.py`)

1. **Add oracle import**:
   ```python
   from conacq.oracle import FeatureModelOracle
   ```

2. **Update `__init__`** -- create oracle, use simplified builder:
   ```python
   def __init__(self, bias_path, fm_path, solver_name='glucose4', is_incremental=True):
       self.solver_name = solver_name
       self.use_incremental = is_incremental

       # Build model (bias only)
       self.model = (ConGenModelBuilder
                     .from_bias(bias_path)
                     .use_incremental(is_incremental)
                     .build())

       # Create oracle (reused across folds)
       self.oracle = FeatureModelOracle(fm_path, use_incremental=False)

       self._original_bias_constraint_order = list(self.model.constraint_map.keys())
   ```

3. **Update `run()`** -- pass oracle to `prepare()`:
   ```python
   self.model.prepare(
       oracle=self.oracle,
       positive_examples=positive_examples,
       negative_examples=negative_examples
   )
   ```

4. **Add cleanup for oracle** (optional, good practice):
   ```python
   def cleanup(self):
       """Release oracle resources."""
       if hasattr(self, 'oracle') and self.oracle is not None:
           self.oracle.cleanup()
   ```

### Step 2: Update `run_congen.py` (`apps/run_congen.py`)

1. **Add oracle import**:
   ```python
   from conacq.oracle import FeatureModelOracle
   ```

2. **Update `process_model()`**:
   ```python
   # Build model (bias only)
   congen_model = (ConGenModelBuilder
                   .from_bias(model_config.bias)
                   .use_incremental(is_incremental)
                   .build())

   # Create oracle
   oracle = FeatureModelOracle(model_config.path, use_incremental=False)

   # Load examples
   from conacq.examples import ExampleIO
   examples = ExampleIO.load_json(model_config.examples)
   pos = [e.assignments for e in examples.positive]
   neg = [e.assignments for e in examples.negative]

   # Prepare with oracle + examples
   congen_model.prepare(oracle=oracle, positive_examples=pos, negative_examples=neg)
   ```

   Note: `run_congen.py` currently uses `.with_solver()` and `.with_profiler()` which don't exist on builder. These calls will need to be removed/fixed as part of this update. Solver name used directly in `CheckerFactory.create_from_model()` call.

3. **Add oracle cleanup in finally block**

### Step 3: Update `test_congen.py` (`tests/test_congen.py`)

1. **Update `create_checker_and_task()` helper**:
   ```python
   def create_checker_and_task(bias_path, fm_path, examples_path, is_incremental=True):
       profiler = get_global_profiler()

       # Create oracle
       oracle = FeatureModelOracle(fm_path, use_incremental=False)

       # Build model (bias only)
       model = (ConGenModelBuilder
                .from_bias(bias_path)
                .use_incremental(is_incremental)
                .build())

       # Load examples and prepare
       from conacq.examples import ExampleIO
       examples = ExampleIO.load_json(examples_path)
       pos = [e.assignments for e in examples.positive]
       neg = [e.assignments for e in examples.negative]
       model.prepare(oracle=oracle, positive_examples=pos, negative_examples=neg)

       root_name = oracle.get_root_feature()
       root_id = model.variables[root_name]

       task = model.task
       checker = CheckerFactory.create_from_model(model, 'glucose4', profiler)

       return checker, task, model, profiler, root_id
   ```

2. **Oracle in test already created separately** (line 59) for root_name -- now use same oracle instance.

### Step 4: Update `__init__.py` exports if needed

Check `acqmss/algorithms/__init__.py` for `ConGenModelBuilder` exports -- ensure API change is reflected.

### Step 5: Run all tests
```bash
PYTHONPATH=. pytest tests/test_congen.py -v
PYTHONPATH=. pytest tests/ -v  # full suite for regressions
```

## Todo List
- [ ] Update `ConGenRunner.__init__` -- `from_bias()` + oracle creation
- [ ] Update `ConGenRunner.run()` -- pass oracle to `model.prepare()`
- [ ] Add oracle cleanup to runner
- [ ] Update `run_congen.py` -- `from_bias()` + oracle + manual example loading
- [ ] Fix `run_congen.py` stale `.with_solver()` / `.with_profiler()` calls
- [ ] Update `test_congen.py` `create_checker_and_task()` helper
- [ ] Update `acqmss/algorithms/__init__.py` if needed
- [ ] Run full test suite

## Success Criteria
- All tests pass with new oracle injection pattern
- `ConGenRunner` creates oracle once, reuses across folds
- No caller accesses `model.oracle` or `model._fm_path`
- `from_bias_and_fm_uvl` / `from_bias_and_fm_fide` no longer referenced

## Risk Assessment
- **Medium**: `run_congen.py` has stale method calls (`.with_solver()`, `.with_profiler()`) that may indicate the file is out of sync -- verify actual runtime behavior
- **Low**: Example loading pattern is well-established (`ExampleIO.load_json`)

## Security Considerations
- None -- internal refactoring

## Next Steps
- Phase 5: Cleanup dead code (bias.root_feature, docs)
