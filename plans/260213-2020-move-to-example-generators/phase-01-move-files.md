# Phase 01: Move Files and Update Internal Imports

## Context Links

- [Plan overview](plan.md)
- [Phase 02: Update references](phase-02-update-references.md)
- Source: `acqmss/algorithms/interactive/query_generator.py`
- Source: `acqmss/oracle/example_provider.py`
- Target: `acqmss/example_generators/`

## Overview

- **Priority**: P2
- **Status**: pending
- **Description**: Physically move `query_generator.py` and `example_provider.py` into `acqmss/example_generators/`, then fix their internal imports and update the target package's `__init__.py`.

## Key Insights

- `QueryGenerator` imports `from .task import InteractiveTask` (relative) -- must become absolute: `from acqmss.algorithms.interactive.task import InteractiveTask`
- `QueryGenerator` imports `from explanation.operations.algorithms.profiler import ...` -- already absolute, no change
- `ExampleProvider` has zero local imports (only stdlib `random` + `typing`) -- no internal import changes needed
- `example_generators/__init__.py` currently exports 7 classes; add 2 more + `clause_count_priority`, `literal_count_priority` functions from `query_generator.py`

## Requirements

### Functional
- `query_generator.py` accessible at `acqmss.example_generators.query_generator`
- `example_provider.py` accessible at `acqmss.example_generators.example_provider`
- All classes importable from `acqmss.example_generators`

### Non-functional
- No circular imports introduced
- Existing tests still pass after Phase 02 completes

## Architecture

No architectural change. Pure file relocation within `acqmss/` package.

```
acqmss/example_generators/
├── __init__.py              # Updated: add QueryGenerator, ExampleProvider exports
├── base.py                  # ExampleGenerator (unchanged)
├── query_generator.py       # MOVED from algorithms/interactive/
├── example_provider.py      # MOVED from oracle/
├── random_sampling.py       # unchanged
├── feature_frequency.py     # unchanged
└── nwise_coverage.py        # unchanged
```

## Related Code Files

| File | Action |
|------|--------|
| `acqmss/algorithms/interactive/query_generator.py` | **Move** to `acqmss/example_generators/` |
| `acqmss/oracle/example_provider.py` | **Move** to `acqmss/example_generators/` |
| `acqmss/example_generators/__init__.py` | **Update**: add new exports |

## Implementation Steps

### 1. Move `query_generator.py`

```bash
git mv acqmss/algorithms/interactive/query_generator.py acqmss/example_generators/query_generator.py
```

### 2. Fix `query_generator.py` internal imports

Change line 12:

```python
# OLD
from .task import InteractiveTask

# NEW
from conacq.algorithms.interactive.task import InteractiveTask
```

Line 13-15 (`from explanation.operations.algorithms.profiler import ...`) -- no change needed (already absolute).

### 3. Move `example_provider.py`

```bash
git mv acqmss/oracle/example_provider.py acqmss/example_generators/example_provider.py
```

### 4. No internal import fix needed for `example_provider.py`

It only imports `random` and `typing` from stdlib.

### 5. Update `acqmss/example_generators/__init__.py`

Add imports and exports:

```python
"""Example generators for different sampling strategies."""

from .base import ExampleGenerator
from .random_sampling import RandomSamplingGenerator, BalancedRandomSamplingGenerator, ControlledRandomSamplingGenerator
from .feature_frequency import FeatureFrequencyGenerator
from .nwise_coverage import NWiseCoverageGenerator, TwoCoverageGenerator
from .query_generator import QueryGenerator, clause_count_priority, literal_count_priority
from .example_provider import ExampleProvider

__all__ = [
    'ExampleGenerator',
    'RandomSamplingGenerator',
    'BalancedRandomSamplingGenerator',
    'ControlledRandomSamplingGenerator',
    'FeatureFrequencyGenerator',
    'NWiseCoverageGenerator',
    'TwoCoverageGenerator',
    'QueryGenerator',
    'clause_count_priority',
    'literal_count_priority',
    'ExampleProvider',
]
```

## Todo List

- [ ] `git mv` query_generator.py to example_generators/
- [ ] Fix relative import `.task` to absolute `acqmss.algorithms.interactive.task`
- [ ] `git mv` example_provider.py to example_generators/
- [ ] Update `example_generators/__init__.py` with new exports
- [ ] Verify no circular imports: `PYTHONPATH=. python -c "from acqmss.example_generators import QueryGenerator, ExampleProvider"`

## Success Criteria

- Both files exist in `acqmss/example_generators/`
- Old files removed from original locations
- `from acqmss.example_generators import QueryGenerator, ExampleProvider` works
- No circular import errors

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Circular import (QueryGenerator → InteractiveTask → ...) | Low | Medium | InteractiveTask has no dependency on QueryGenerator |
| Missed internal import | Low | Low | Only one relative import to fix in query_generator.py |

## Security Considerations

N/A -- pure file relocation, no logic changes.

## Next Steps

Proceed to [Phase 02](phase-02-update-references.md) to update all external references.
