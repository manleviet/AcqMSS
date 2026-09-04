# Phase 01: Extract _generate_valid_config to Base Class

## Context Links

- [random_sampling.py](../../conacq/example_generators/random_sampling.py)
- [base.py](../../conacq/example_generators/base.py)
- [generators __init__.py](../../conacq/example_generators/__init__.py)

## Overview

- **Priority**: P2
- **Status**: completed
- **Effort**: 30m

Both `BalancedRandomSamplingGenerator._generate_valid_config()` (lines 164-212) and `ControlledRandomSamplingGenerator._generate_valid_config()` (lines 341-389) are **byte-for-byte identical** (49 lines). Move to `ExampleGenerator` base class.

## Key Insights

- Method uses `self.feature_ids` and `self.oracle` -- both already on base class
- `RandomSamplingGenerator` does NOT use this method (pure random, no SAT solver)
- Method creates temporary SAT solver, uses random assumptions for diversity, falls back to no-assumptions

## Requirements

- Move `_generate_valid_config()` to `ExampleGenerator` in `base.py`
- Remove from both `BalancedRandomSamplingGenerator` and `ControlledRandomSamplingGenerator`
- Add `pysat.solvers.Solver` import to `base.py`
- Add `random` and `Optional, Dict` imports to `base.py`

## Architecture

```
ExampleGenerator (base.py)
  + _generate_valid_config(features_list) -> Optional[Dict[str, bool]]
  |
  +-- RandomSamplingGenerator      (does NOT use _generate_valid_config)
  +-- BalancedRandomSamplingGenerator   (inherits from base)
  +-- ControlledRandomSamplingGenerator (inherits from base)
```

## Related Code Files

- **Modify**: `acqmss/testcases/generators/base.py` (add method + imports)
- **Modify**: `acqmss/testcases/generators/random_sampling.py` (remove 2 copies of method)

## Implementation Steps

1. Add imports to `base.py`: `import random`, `from typing import Optional, Dict`, `from pysat.solvers import Solver`
2. Add `_generate_valid_config()` method to `ExampleGenerator` class in `base.py` (copy from either subclass, identical)
3. Remove `_generate_valid_config()` from `BalancedRandomSamplingGenerator` (lines 164-212)
4. Remove `_generate_valid_config()` from `ControlledRandomSamplingGenerator` (lines 341-389)
5. Remove now-unnecessary `Solver` import from `random_sampling.py` (only if no other usage)
6. Verify: `PYTHONPATH=. python apps/generate_examples.py apps/conf/generate_examples_config.toml -v`

## Todo List

- [x] Add imports to `base.py`
- [x] Move `_generate_valid_config()` to `ExampleGenerator`
- [x] Remove from `BalancedRandomSamplingGenerator`
- [x] Remove from `ControlledRandomSamplingGenerator`
- [x] Clean up `random_sampling.py` imports
- [x] Run verification command

## Success Criteria

- `base.py` contains `_generate_valid_config()`
- `random_sampling.py` has zero copies of the method
- Example generation produces identical output
- No import errors

## Risk Assessment

- **Low risk**: Pure method relocation, no logic change
- `Solver` import might still be needed in `random_sampling.py` if used elsewhere -- check before removing

## Next Steps

Proceed to Phase 02 (independent of this phase)
