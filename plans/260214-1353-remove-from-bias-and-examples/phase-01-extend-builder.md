# Phase 1: Refactor Builder's `build()` — Inline Model Construction

## Context Links
- [ConGenModelBuilder](../../conacq/algorithms/congen_model_builder.py)
- [ConGenModel](../../conacq/algorithms/congen_model.py)
- [Plan overview](plan.md)

## Overview
- **Priority**: P2
- **Status**: complete
- **Description**: Refactor `build()` to inline model construction instead of calling `from_bias_and_examples()`. Make examples optional so CV can build model once and use `prepare()` per fold.

## Key Insights

1. `from_bias_and_examples()` does 3 things: compute max_var, convert examples to TestSuite, set model attributes
2. Builder's `build()` loads files then calls `from_bias_and_examples()` — should inline that logic
3. Examples must become optional: CV builds model without examples, provides them per fold via `prepare()`
4. Dead `_create_model()` method (lines 180-198) references non-existent attributes — remove now

## Requirements

### Functional
- `build()` inlines model construction (no `from_bias_and_examples()` call)
- Examples optional: if not provided, `build()` skips `prepare()` and returns unprepared model
- If examples provided, behavior identical to current (build + prepare)
- Existing `from_bias_and_fm_uvl()` / `from_bias_and_fm_fide()` still work

### Non-functional
- No behavior change for callers that provide examples

## Architecture

```
ConGenModelBuilder
  ├── from_bias_and_fm_uvl(bias_path, fm_path)  # existing
  ├── from_bias_and_fm_fide(bias_path, fm_path)  # existing
  ├── with_examples(path)                         # existing, now optional
  ├── with_examples_data(pos, neg)                # existing, now optional
  ├── use_incremental() / with_solver() / with_profiler()
  └── build()  # inlines model construction; calls prepare() only if examples set
```

## Related Code Files

- **Modify**: `acqmss/algorithms/congen_model_builder.py`

## Implementation Steps

### Step 1: Refactor `build()` to inline model construction

```python
# BEFORE (build calls from_bias_and_examples):
model = ConGenModel.from_bias_and_examples(
    bias_constraints=bias_constraints,
    positive_examples=pos, negative_examples=neg,
    feature_ids=feature_ids, background_knowledge=bg
)
model.use_incremental = self._use_incremental
model.solver_name = self._solver_name
model.prepare(solver_name=self._solver_name, profiler=self._profiler)


# AFTER (build inlines logic):
def build(self) -> ConGenModel:
    self._validate()

    from conacq.bias import BiasIO
    from conacq.oracle import FeatureModelOracle

    oracle = FeatureModelOracle(self._fm_path)
    bias = BiasIO.load_from_json(self._bias_path)
    feature_ids = oracle.get_feature_ids()

    root_name = oracle.get_root_feature()
    root_id = feature_ids.get(root_name)
    bg = [root_id] if root_id is not None else []

    bias_constraints = {c.id: c.clauses for c in bias.constraints}

    # Inline from_bias_and_examples logic
    max_var = max(feature_ids.values()) if feature_ids else 0
    for clauses in bias_constraints.values():
        for clause in clauses:
            for lit in clause:
                max_var = max(max_var, abs(lit))

    model = ConGenModel()
    model.constraint_map = bias_constraints
    model.variables = feature_ids
    model.next_tseitin_var = max_var + 1
    model.background_knowledge = bg
    model.use_incremental = self._use_incremental
    model.solver_name = self._solver_name

    # Set examples + prepare only if examples provided
    if self._has_examples():
        pos, neg = self._resolve_examples()
        model.task_input = TaskInput(
            positive_test_cases=ConGenModel._examples_to_testsuite(pos),
            negative_test_cases=ConGenModel._examples_to_testsuite(neg)
        )
        model.prepare(solver_name=self._solver_name, profiler=self._profiler)

    return model
```

### Step 2: Add `_has_examples()` helper + make validation allow no examples

```python
def _has_examples(self) -> bool:
    return (self._examples_path is not None
            or self._positive_examples is not None)

def _validate(self) -> None:
    if self._bias_path is None or self._fm_path is None:
        raise ValueError("Source must be specified")
    # Examples now optional (CV builds without, uses prepare() per fold)
```

### Step 3: Add `TaskInput` import

```python
from explanation.models.task_preparation import TaskInput
```

## Todo List

- [x] Add `TaskInput` import
- [x] Refactor `build()` to inline model construction
- [x] Add `_has_examples()` helper
- [x] Update `_validate()` — examples now optional

## Success Criteria

- `build()` no longer calls `from_bias_and_examples()`
- Build without examples returns unprepared model (for CV reuse)
- Build with examples returns fully prepared model (same as before)
- All existing tests pass

## Risk Assessment

- **Low**: straightforward inlining of data-flow logic
- `_examples_to_testsuite` is static on ConGenModel — accessible from builder

## Security Considerations

None — internal refactor only.

## Next Steps

Phase 2: Migrate callers.
