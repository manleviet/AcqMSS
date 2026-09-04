# Phase 2: Refactor ExampleGenerator

## Context Links
- [Plan overview](plan.md)
- [Phase 1: Slim Oracle](phase-01-slim-oracle-and-fm-data.md)
- ExampleGenerator base: `acqmss/example_generators/base.py`
- RandomSampling: `acqmss/example_generators/random_sampling.py`
- FeatureFrequency: `acqmss/example_generators/feature_frequency.py`

## Overview
- **Priority**: P1
- **Status**: complete
- **Effort**: 1h

ExampleGenerator currently pulls `features`, `feature_ids`, and `complete_configuration()` from Oracle. After Phase 1, Oracle no longer has these. Refactor to receive `FMData` + `FeatureModelOracle` explicitly.

## Key Insights
- `ExampleGenerator.__init__` stores `oracle.get_features()` and `oracle.get_feature_ids()` as instance attrs
- `_generate_valid_config()` calls `oracle.complete_configuration()` — this needs FeatureModelOracle specifically
- `_classify_and_add()` calls `oracle.is_valid()` — this is the only true Oracle ABC usage
- All concrete generators (RS, BalancedRS, ControlledRS, FF) use `self.features` for iteration
- Callers always pass FeatureModelOracle anyway (never UserPromptOracle or CachedOracle for example generation)

## Requirements

### Functional
1. ExampleGenerator constructor: `__init__(self, oracle: FeatureModelOracle)` — gets FMData internally
2. `self.features` and `self.feature_ids` populated from `oracle.get_fm_data()`
3. `_generate_valid_config()` calls `self.oracle.complete_configuration()` directly (same as before, but now oracle is typed as FeatureModelOracle)
4. `_classify_and_add()` calls `self.oracle.is_valid()` (unchanged)

### Non-functional
- Minimal API change for callers (still pass oracle, just typed differently)

## Architecture

```
ExampleGenerator(ABC)
├── __init__(oracle: FeatureModelOracle)
│   ├── self.oracle = oracle
│   ├── fm_data = oracle.get_fm_data()
│   ├── self.features = fm_data.features
│   └── self.feature_ids = fm_data.feature_ids
├── _classify_and_add()  → oracle.is_valid()
└── _generate_valid_config()  → oracle.complete_configuration()
```

## Related Code Files

### Modify
| File | Changes |
|------|---------|
| `acqmss/example_generators/base.py` | Change `oracle: Oracle` → `oracle: FeatureModelOracle`. Get features from `oracle.get_fm_data()`. Update import. |
| `acqmss/example_generators/random_sampling.py` | No changes (uses `self.features`, `self.oracle.is_valid()` — both unchanged) |
| `acqmss/example_generators/feature_frequency.py` | No changes (uses `self.features`, `self.oracle.complete_configuration()`, `self.oracle.is_valid()`) |
| `apps/generate_examples.py` | No changes (already passes FeatureModelOracle) |

## Implementation Steps

1. **Update `acqmss/example_generators/base.py`**
   ```python
   from conacq.oracle.fm_oracle import FeatureModelOracle

   class ExampleGenerator(ABC):
       def __init__(self, oracle: FeatureModelOracle):
           self.oracle = oracle
           fm_data = oracle.get_fm_data()
           self.features = fm_data.features
           self.feature_ids = fm_data.feature_ids
   ```
   - Remove `from acqmss.oracle import Oracle`
   - Everything else stays the same

2. **Verify subclasses** — RS, BalancedRS, ControlledRS, FF all inherit and don't override `__init__` or use Oracle ABC type. No changes needed.

3. **Verify callers** — `apps/generate_examples.py` line 142 creates `FeatureModelOracle` and passes to generators. Already correct type.

## Todo List
- [x] Update ExampleGenerator base import and constructor type
- [x] Populate features/feature_ids from `oracle.get_fm_data()`
- [x] Verify no subclass overrides `__init__` with Oracle type

## Success Criteria
- ExampleGenerator accepts `FeatureModelOracle` (not generic Oracle)
- `self.features` and `self.feature_ids` populated from FMData
- `complete_configuration()` called on oracle directly
- No changes needed in subclasses or callers

## Risk Assessment
- **Risk**: Future oracle types (e.g., database oracle) can't be used for example generation
- **Mitigation**: YAGNI. Only FeatureModelOracle is used. If needed later, introduce protocol/ABC.

## Next Steps
- Phase 3: Refactor InteractiveLearner
