# Phase 3: Refactor ExampleGenerators

## Context Links
- [ExampleGenerator base](../../conacq/example_generators/base.py) -- `_generate_valid_config()` lines 61-109
- [FeatureFrequency](../../conacq/example_generators/feature_frequency.py) -- `_generate_valid_config_for_coverage()` lines 172-229
- [RandomSampling](../../conacq/example_generators/random_sampling.py) -- callers of `_generate_valid_config()`
- [NWiseCoverage](../../conacq/example_generators/nwise_coverage.py) -- does NOT call `_generate_valid_config()`

## Overview
- **Priority**: P2
- **Status**: Complete
- **Description**: Replace direct SAT solver usage in generators with `oracle.complete_configuration()`

## Key Insights

### Current `_generate_valid_config()` flow (base.py):
1. Shuffle features, pick random subset to fix (n_fixed = 0..len/2)
2. Build assumptions from random values
3. Create solver + add CNF + solve + extract config
4. Fallback: solve without assumptions

### Mapping to `complete_configuration()`:
- Steps 1-2 = sampling policy (stays in generator)
- Steps 3-4 = SAT solving (moves to oracle)
- Generator builds `partial: Dict[str, bool]` from sampling, then calls `oracle.complete_configuration(partial)`

### Current `_generate_valid_config_for_coverage()` flow (feature_frequency.py):
1. Pick uncovered (feature, value) pair as target
2. Add random extra assumptions for diversity
3. Create solver + add CNF + solve + extract config
4. Fallback: solve with just target assumption

### Mapping:
- Steps 1-2 = coverage policy (stays in generator)
- Steps 3-4 = SAT solving (two-stage: full partial -> target-only partial)
- Need two calls to `complete_configuration()`: first with full partial, then fallback with target-only

## Requirements

### Functional
- `_generate_valid_config()` builds partial dict, calls `oracle.complete_configuration(partial)`
- `_generate_valid_config_for_coverage()` builds partial dict, calls oracle twice (full -> target-only fallback)
- Remove `from pysat.solvers import Solver` from both files
- Remove `from pysat.solvers import Solver` from base.py

### Non-Functional
- Generator files should get shorter (removing SAT boilerplate)
- No behavioral change in generated examples (same randomness, same fallback logic)

## Architecture

### New `_generate_valid_config()` (base.py):
```python
def _generate_valid_config(self, features_list: list) -> Optional[Dict[str, bool]]:
    shuffled = list(features_list)
    random.shuffle(shuffled)
    n_fixed = random.randint(0, len(shuffled) // 2)

    partial = {}
    for f in shuffled[:n_fixed]:
        partial[f] = random.choice([True, False])

    return self.oracle.complete_configuration(partial)
```

### New `_generate_valid_config_for_coverage()` (feature_frequency.py):
```python
def _generate_valid_config_for_coverage(self, features_list, uncovered):
    random.shuffle(uncovered)
    target_feature, target_value = uncovered[0]

    # Build partial with target + random extras
    partial = {target_feature: target_value}
    other_features = [f for f in features_list if f != target_feature]
    random.shuffle(other_features)
    n_extra = min(len(other_features) // 3, 5)
    for f in other_features[:n_extra]:
        partial[f] = random.choice([True, False])

    # Try full partial, then target-only fallback
    config = self.oracle.complete_configuration(partial)
    if config is None:
        config = self.oracle.complete_configuration({target_feature: target_value})
    return config
```

## Related Code Files

### Files to Modify
- `acqmss/example_generators/base.py` -- rewrite `_generate_valid_config()`, remove Solver import
- `acqmss/example_generators/feature_frequency.py` -- rewrite `_generate_valid_config_for_coverage()`, remove Solver import

### Files NOT Modified
- `acqmss/example_generators/random_sampling.py` -- calls `_generate_valid_config()` from base (inherited), no changes needed
- `acqmss/example_generators/nwise_coverage.py` -- does not use SAT solving at all
- `acqmss/example_generators/query_generator.py` -- has own Solver usage for different purpose (query gen, not config completion)

## Implementation Steps

1. **Edit `acqmss/example_generators/base.py`**:
   - Remove `from pysat.solvers import Solver` import
   - Rewrite `_generate_valid_config()`: build partial dict, call `self.oracle.complete_configuration(partial)`
   - Method goes from 48 lines to ~15 lines

2. **Edit `acqmss/example_generators/feature_frequency.py`**:
   - Remove `from pysat.solvers import Solver` import
   - Rewrite `_generate_valid_config_for_coverage()`: build partial, call oracle twice (full -> target-only)
   - Method goes from 57 lines to ~20 lines

3. **Verify imports**: `PYTHONPATH=. python -c "from acqmss.example_generators.base import ExampleGenerator"`

4. **Verify no remaining Solver references in generators**:
   `grep -r "from pysat" acqmss/example_generators/` should only show query_generator.py

## Todo List

- [x] Rewrite `_generate_valid_config()` in base.py
- [x] Remove Solver import from base.py
- [x] Rewrite `_generate_valid_config_for_coverage()` in feature_frequency.py
- [x] Remove Solver import from feature_frequency.py
- [x] Verify no remaining pysat imports in generators (except query_generator.py)

## Success Criteria
- `_generate_valid_config()` calls `oracle.complete_configuration()` instead of creating Solver
- `_generate_valid_config_for_coverage()` calls `oracle.complete_configuration()` with fallback
- No `pysat.solvers` import in base.py or feature_frequency.py
- Existing tests pass (test_congen.py uses generators indirectly)
- Generated examples are functionally equivalent (same randomness strategy)

## Risk Assessment
- **Low**: Behavioral equivalence -- same SAT solver, same CNF, same fallback logic
- **Subtle difference in `_generate_valid_config`**: current code has explicit fallback `solver.solve()` without assumptions. New `complete_configuration()` includes this fallback internally. Verify behavior matches.
- **`_generate_valid_config_for_coverage` fallback**: current code falls back to single target assumption. New code calls `complete_configuration({target: value})` -- same semantics.

## Security Considerations
- None

## Next Steps
- Phase 4: Run full test suite, verify backward compatibility
