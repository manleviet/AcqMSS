# Phase 3: Simplify Builder

## Context Links
- [plan.md](./plan.md)
- [phase-02-refactor-congen-model.md](./phase-02-refactor-congen-model.md)
- [congen_model_builder.py](../../conacq/algorithms/congen_model_builder.py)

## Overview
- **Date**: 2026-02-16
- **Description**: Remove FM loading from `ConGenModelBuilder`. Builder handles only bias loading and solver config. Oracle creation moves to callers (runner, tests, apps).
- **Priority**: P2
- **Implementation Status**: Pending
- **Review Status**: Pending

## Key Insights
- Builder currently: loads bias JSON + loads FM (via `_load_model()` -> `DiagnosisModel`) + creates `FeatureModelOracle` + sets all FM fields on model + optionally calls `prepare()`
- After refactor: builder loads bias JSON + sets solver config. No FM, no oracle.
- `_load_model()` creates `DiagnosisModel` just to get `next_tseitin_var` and `constraint_map` length -- both now come from oracle at `prepare()` time
- Builder still needs to accept FM path for the `prepare()` convenience path, OR callers handle oracle creation entirely
- **Decision**: Builder does NOT handle oracle/FM at all. Simplest API: `from_bias(path)` or `from_bias_data(constraint_map, variables)`. Callers create oracle separately.
- The `build()` method no longer calls `prepare()` -- returns unprepared model. Callers call `model.prepare(oracle, pos, neg)`.

## Requirements

### Functional
- Replace `from_bias_and_fm_uvl()` / `from_bias_and_fm_fide()` with `from_bias(bias_path)`
- Remove `_fm_path`, `_fm_source_type`, `_load_model()` from builder
- Remove `FeatureModelOracle` import from builder
- Remove `DiagnosisModel` / flamapy imports from builder
- `build()` returns unprepared model (no `prepare()` call)
- Keep `with_examples()` / `with_examples_data()` for storing examples on builder (used when caller wants to pass examples through builder)

### Non-Functional
- Builder has zero FM dependencies
- Simpler, more focused responsibility

## Architecture

### Before
```
ConGenModelBuilder
  ├── from_bias_and_fm_uvl(bias, fm)
  ├── from_bias_and_fm_fide(bias, fm)
  ├── with_examples(path)
  ├── with_examples_data(pos, neg)
  ├── use_incremental(bool)
  └── build()
      ├── _validate()
      ├── BiasIO.load(bias)
      ├── _load_model() → DiagnosisModel      # FM concern
      ├── FeatureModelOracle(fm)               # FM concern
      ├── set model.{_fm_path, _oracle, ...}   # FM concern
      └── model.prepare() if has_examples
```

### After
```
ConGenModelBuilder
  ├── from_bias(bias_path)
  ├── with_examples(path)
  ├── with_examples_data(pos, neg)
  ├── use_incremental(bool)
  └── build() → ConGenModel (unprepared)
      ├── _validate()
      ├── BiasIO.load(bias)
      └── set model.{constraint_map, variables, _use_incremental}
```

## Related Code Files

### Files to Modify
| File | Change |
|------|--------|
| `acqmss/algorithms/congen_model_builder.py` | Complete simplification |

### Files Unchanged (modified in Phase 4)
| File | Phase |
|------|-------|
| `acqmss/eval/congen_runner.py` | Phase 4 |
| `apps/run_congen.py` | Phase 4 |
| `tests/test_congen.py` | Phase 4 |

## Implementation Steps

1. **Remove FM-related imports** (lines 9-12):
   ```python
   # Remove:
   from flamapy.metamodels.pysat_metamodel.models import PySATModel
   from explanation.models import DiagnosisModel
   from ..oracle import FeatureModelOracle
   ```

2. **Replace factory methods**:
   - Remove `from_bias_and_fm_fide()` and `from_bias_and_fm_uvl()`
   - Add `from_bias()`:
     ```python
     @classmethod
     def from_bias(cls, bias_path: str) -> 'ConGenModelBuilder':
         """Create builder from bias JSON file."""
         builder = cls()
         builder._bias_path = bias_path
         return builder
     ```

3. **Remove FM fields from `__init__`**:
   ```python
   # Remove:
   self._fm_source_type: Optional[str] = None
   self._fm_path: Optional[str] = None
   ```

4. **Simplify `build()`**:
   ```python
   def build(self) -> ConGenModel:
       """Build and return configured ConGenModel (unprepared).

       Returns model with bias loaded. Caller must call
       model.prepare(oracle, pos_examples, neg_examples) before use.
       """
       self._validate()

       from conacq.bias import BiasIO
       bias = BiasIO.load_from_json(self._bias_path)

       model = ConGenModel()
       model.constraint_map = bias.to_constraint_map()
       model.variables = bias.feature_ids
       model._use_incremental = self._use_incremental

       return model
   ```

5. **Simplify `_validate()`**:
   ```python
   def _validate(self) -> None:
       if self._bias_path is None:
           raise ValueError("Bias path required (use from_bias())")
   ```

6. **Remove `_load_model()`** method entirely

7. **Keep example methods** (`with_examples()`, `with_examples_data()`, `_resolve_examples()`, `_has_examples()`):
   - These are useful for callers that want builder to hold examples
   - Add `get_examples()` method so callers can extract them:
     ```python
     def get_examples(self) -> Optional[Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]]:
         """Get resolved examples if any were provided."""
         if not self._has_examples():
             return None
         return self._resolve_examples()
     ```

8. **Update docstring/examples** in class docstring:
   ```python
   """Fluent builder for ConGenModel.

   Examples:
       # Build model, prepare separately
       model = ConGenModelBuilder.from_bias('data/bias/model.json').build()
       oracle = FeatureModelOracle('data/fms/model.uvl')
       model.prepare(oracle, positive_examples=pos, negative_examples=neg)

       # For CV: build once, prepare per fold
       model = ConGenModelBuilder.from_bias('data/bias/model.json').build()
       oracle = FeatureModelOracle('data/fms/model.uvl')
       for fold_pos, fold_neg in folds:
           model.prepare(oracle, positive_examples=fold_pos, negative_examples=fold_neg)
   """
   ```

## Todo List
- [ ] Remove FM imports (`PySATModel`, `DiagnosisModel`, `FeatureModelOracle`)
- [ ] Replace `from_bias_and_fm_uvl()` / `from_bias_and_fm_fide()` with `from_bias()`
- [ ] Remove `_fm_path`, `_fm_source_type` from `__init__`
- [ ] Simplify `build()` -- no oracle, no FM, no `prepare()`
- [ ] Remove `_load_model()` method
- [ ] Update `_validate()` -- only check bias_path
- [ ] Add `get_examples()` method for caller convenience
- [ ] Update class docstring with new usage pattern

## Success Criteria
- Builder has zero FM/oracle imports
- `build()` returns unprepared model
- No flamapy dependency in builder
- API: `ConGenModelBuilder.from_bias(path).build()`

## Risk Assessment
- **Medium**: All callers using `from_bias_and_fm_uvl()` break -- must update in Phase 4 atomically
- **Low**: `_load_model()` removal is clean since no other code calls it

## Security Considerations
- None -- internal refactoring

## Next Steps
- Phase 4: Update all callers (runner, tests, apps) to new API
