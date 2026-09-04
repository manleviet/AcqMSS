# Phase 2: Migrate Callers to ConGenModelBuilder

## Context Links
- [ConGenRunner](../../conacq/eval/congen_runner.py)
- [cross_validation](../../conacq/eval/cross_validation.py)
- [run_congen.py](../../apps/run_congen.py)
- [run_congen_eval.py](../../apps/run_congen_eval.py)
- [test_congen.py](../../tests/test_congen.py)
- [Phase 1](phase-01-extend-builder.md) | [Plan](plan.md)

## Overview
- **Priority**: P2
- **Status**: complete
- **Description**: Replace all `ConGenModel.from_bias_and_examples()` calls with builder. ConGenRunner changes to accept file paths. CV and eval scripts update signatures accordingly.

## Key Insights

1. **ConGenRunner.run()** creates new model per fold — wasteful. Build once in `__init__`, use `prepare(pos, neg)` per fold.
2. **Bias shuffle**: ConGenRunner reorders `constraint_map` keys per fold. Must reorder `model.constraint_map` before calling `prepare()`.
3. **`n_fold_cross_validation`** receives raw dicts from `run_congen_eval.py` — change to accept paths.
4. **`apps/run_congen.py`** loads files manually — replace with builder's `from_bias_and_fm_uvl()`.
5. **Tests** load from fixture paths — use builder directly.

## Requirements

### Functional
- All callers produce identical results as before
- ConGenRunner uses `prepare()` for per-fold examples (no new model per fold)
- Bias shuffle still works (reorder `model.constraint_map` before `prepare()`)

### Non-functional
- Fewer lines of boilerplate per caller
- Consistent builder-based model construction

## Related Code Files

- **Modify**: `acqmss/eval/congen_runner.py` — accept paths, build model once
- **Modify**: `acqmss/eval/cross_validation.py` — pass paths to ConGenRunner
- **Modify**: `apps/run_congen.py` — use builder directly
- **Modify**: `apps/run_congen_eval.py` — pass paths to `n_fold_cross_validation`
- **Modify**: `tests/test_congen.py` — use builder with file paths

## Implementation Steps

### Step 1: Refactor `ConGenRunner` — accept paths, build model once

```python
# BEFORE __init__:
def __init__(self, bias_clauses, feature_ids, solver_name, is_incremental, background_knowledge):
    self.bias_clauses = bias_clauses
    self.feature_ids = feature_ids
    ...


# AFTER __init__:
def __init__(self, bias_path: str, fm_path: str, solver_name='glucose4',
             is_incremental=True):
    self.solver_name = solver_name
    self.use_incremental = is_incremental

    # Build model once (without examples — will use prepare() per fold)
    self.model = (ConGenModelBuilder
                  .from_bias_and_fm_uvl(bias_path, fm_path)
                  .use_incremental(is_incremental)
                  .with_solver(solver_name)
                  .build())

    # Keep original bias order for shuffle restore
    self._original_bias_constraint_order = list(self.model.constraint_map.keys())
```

```python
# BEFORE run():
model = ConGenModel.from_bias_and_examples(
    bias_constraints=bias_clauses, ...)
model.prepare(solver_name=..., profiler=profiler)
task = model.task


# AFTER run():
def run(self, positive_examples, negative_examples, shuffle_seed=None):
    profiler = Profiler()
    profiler.start()
    tracemalloc.start()
    start_time = time.perf_counter()

    checker = None
    try:
        # Shuffle bias ordering if needed
        if shuffle_seed is not None:
            keys = list(self._original_bias_constraint_order)
            random.Random(shuffle_seed).shuffle(keys)
            self.model.constraint_map = {k: self.model.constraint_map[k] for k in keys}

        # Prepare for this fold's examples (runs GenerateNE)
        self.model.prepare(
            positive_examples=positive_examples,
            negative_examples=negative_examples,
            solver_name=self.solver_name,
            profiler=profiler
        )
        task = self.model.task

        # Create checker and run ConGen (same as before)
        checker = CheckerFactory.create_from_model(self.model, self.solver_name, profiler)
        congen = ConGen(checker, profiler)
        result = congen.acquire(...)

    finally:
        ...  # timing/cleanup same as before

    # Build kb_clauses from model.constraint_map (was self.bias_clauses)
    kb_clauses = []
    for cid in result.kb_constraints:
        if cid in self.model.constraint_map:
            kb_clauses.extend(self.model.constraint_map[cid])

    return ConGenRunResult(...)
```

Remove `background_clauses` param from `run()` (was unused).

### Step 2: Update `n_fold_cross_validation` signature

```python
# BEFORE:
def n_fold_cross_validation(
    positive_examples, negative_examples, n_folds,
    bias_clauses, feature_ids, seed,
    solver_name, is_incremental, shuffle_each_fold,
    fold_data, shuffle_bias, background_knowledge
):
    runner = ConGenRunner(bias_clauses=bias_clauses, feature_ids=feature_ids, ...)

# AFTER:
def n_fold_cross_validation(
    positive_examples, negative_examples, n_folds,
    bias_path: str, fm_path: str, seed: int,
    solver_name='glucose4', is_incremental=True,
    shuffle_each_fold=True, fold_data=None,
    shuffle_bias=False
):
    runner = ConGenRunner(bias_path=bias_path, fm_path=fm_path,
                          solver_name=solver_name, is_incremental=is_incremental)
```

Remove `bias_clauses`, `feature_ids`, `background_knowledge` params.
Add `bias_path`, `fm_path` params.

Also update `AccuracyCalculator` call — it uses `feature_ids`. Get from `runner.model.variables`:
```python
# BEFORE:
accuracy_result = calculator.calculate(test_pos, test_neg, feature_ids)

# AFTER:
accuracy_result = calculator.calculate(test_pos, test_neg, runner.model.variables)
```

### Step 3: Update `apps/run_congen_eval.py`

```python
# BEFORE (lines 241-253):
cv_result = n_fold_cross_validation(
    positive_examples=pos_assignments,
    negative_examples=neg_assignments,
    n_folds=n_folds,
    bias_clauses=bias_clauses,
    feature_ids=bias.features,
    seed=seed, ...)

# AFTER:
cv_result = n_fold_cross_validation(
    positive_examples=pos_assignments,
    negative_examples=neg_assignments,
    n_folds=n_folds,
    bias_path=model_config.bias,
    fm_path=model_config.path,
    seed=seed, ...)
```

Remove `bias_clauses`/`feature_ids` extraction code that's no longer needed.

### Step 4: Migrate `apps/run_congen.py`

```python
# BEFORE (lines 109-143): manual file loading + from_bias_and_examples
bias = BiasIO.load_from_json(model_config.bias)
examples = ExampleIO.load_json(model_config.examples)
...
congen_model = ConGenModel.from_bias_and_examples(...)

# AFTER:
from conacq.algorithms import ConGenModelBuilder

congen_model = (ConGenModelBuilder
                .from_bias_and_fm_uvl(model_config.bias, model_config.path)
                .with_examples(model_config.examples)
                .use_incremental(is_incremental)
                .with_solver(solver_name)
                .build())
profiler = get_global_profiler()
```

Remove `BiasIO`, `ExampleIO` imports; add `ConGenModelBuilder`.
Move verbose logging to after build using `model.constraint_map` and `model.task_input`.

### Step 5: Migrate `tests/test_congen.py`

```python
# BEFORE (lines 78-100):
def create_checker_and_task(oracle, bias, examples, is_incremental=True):
    bias_constraints = {c.id: c.clauses for c in bias.constraints}
    positive_examples = [e.assignments for e in examples.positive]
    ...
    model = ConGenModel.from_bias_and_examples(...)


# AFTER:
def create_checker_and_task(bias_path, fm_path, examples_path, is_incremental=True):
    profiler = get_global_profiler()
    model = (ConGenModelBuilder
             .from_bias_and_fm_uvl(bias_path, fm_path)
             .with_examples(examples_path)
             .use_incremental(is_incremental)
             .with_profiler(profiler)
             .build())

    # Get root_id from model.variables (for test assertions)
    # Need oracle for root feature name
    from conacq.oracle import FeatureModelOracle
    oracle = FeatureModelOracle(fm_path)
    root_name = oracle.get_root_feature()
    root_id = model.variables[root_name]

    task = model.task
    checker = CheckerFactory.create_from_model(model, 'glucose4', profiler)
    return checker, task, profiler, root_id
```

Update test fixtures/callers to pass paths instead of loaded objects.

## Todo List

- [x] Refactor `ConGenRunner.__init__` — accept `bias_path`, `fm_path`
- [x] Refactor `ConGenRunner.run()` — use `prepare()`, handle bias shuffle
- [x] Update `n_fold_cross_validation` signature — paths instead of raw dicts
- [x] Update `AccuracyCalculator` call to use `runner.model.variables`
- [x] Update `apps/run_congen_eval.py` — pass paths
- [x] Migrate `apps/run_congen.py` — use builder directly
- [x] Migrate `tests/test_congen.py` — use builder with file paths
- [x] Run all tests

## Success Criteria

- Zero calls to `ConGenModel.from_bias_and_examples()` outside `congen_model.py`
- ConGenRunner builds model once, reuses via `prepare()` per fold
- All existing tests pass
- CV results identical (bias shuffle still works)

## Risk Assessment

- **Medium**: ConGenRunner API change ripples to cross_validation → run_congen_eval
- **Bias shuffle**: reordering `model.constraint_map` before `prepare()` should work since `ConGenTaskPreparation` reads constraint_map — verify in tests
- `run_congen.py` verbose logging: needs adjustment to log after build

## Security Considerations

None — internal refactor only.

## Next Steps

Phase 3: Remove `from_bias_and_examples()` from ConGenModel, cleanup docs.
