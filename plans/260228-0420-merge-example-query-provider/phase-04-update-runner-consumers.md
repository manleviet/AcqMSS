# Phase 4: Update Runner and Consumers

## Context Links

- Phase 3: `phase-03-simplify-findc.md`
- Source: `conacq/runners/quacq_runner.py` (285 LOC)
- Source: `conacq/example_generators/__init__.py` (39 LOC)

## Overview

- **Date**: 2026-02-28
- **Priority**: P2
- **Status**: completed
- **Description**: Update QuAcqRunner to construct QueryProvider instead of separate QueryGenerator/ExampleProvider. Update `__init__.py` exports.

## Key Insights

- QuAcqRunner._run_oracle_mode (line 233) creates QueryGenerator -> becomes QueryProvider (SAT only, no pool)
- QuAcqRunner._run_example_mode (line 255) creates ExampleProvider + optional QueryGenerator -> becomes QueryProvider (with pool, SAT fallback for example_first)
- `__init__.py` exports both QueryGenerator and ExampleProvider -> replace with QueryProvider
- Lazy import pattern in `__init__.py` for QueryGenerator -> adapt for QueryProvider

## Requirements

### Functional
- QuAcqRunner constructs QueryProvider instead of QueryGenerator + ExampleProvider
- _run_oracle_mode: QueryProvider(solver_name, profiler_instance=profiler) -- no pool
- _run_example_mode: QueryProvider(solver_name, pool=mixed_examples, seed=shuffle_seed, profiler_instance=profiler)
- __init__.py: export QueryProvider, remove ExampleProvider export
- Keep backward compat: export `clause_count_priority`, `literal_count_priority`

### Non-Functional
- Net code reduction in runner: ~10 LOC

## Related Code Files

### Files to modify
- `conacq/runners/quacq_runner.py`
- `conacq/example_generators/__init__.py`

## Implementation Steps

### Step 1: Update quacq_runner.py imports (line 17)

Replace:
```python
from conacq.example_generators import QueryGenerator, ExampleProvider
```
With:
```python
from conacq.example_generators import QueryProvider
```

### Step 2: Update _run_oracle_mode (lines 233-253)

Replace:
```python
    def _run_oracle_mode(self, checker, task, task_data, profiler, mode):
        """Run oracle-based learning via QuAcq.learn(mode='oracle')."""
        if mode == 'interactive':
            from conacq.oracle import UserPromptOracle
            learn_oracle = UserPromptOracle(list(task.feature_ids.keys()))
        else:
            learn_oracle = self.oracle

        query_provider = QueryProvider(self.solver_name, profiler_instance=profiler)
        discrim_gen = DiscriminatingGenerator(
            background_clauses=task.background_clauses,
            constraint_clauses=task.constraint_clauses,
            negated_clauses=task.negated_clauses,
            id_to_feature=task.id_to_feature,
            solver_name=self.solver_name)

        quacq = QuAcq.for_oracle(checker, learn_oracle, query_provider, discrim_gen, profiler=profiler)

        return quacq.learn(
            **task_data, mode='oracle',
            max_queries=self.max_queries)
```

### Step 3: Update _run_example_mode (lines 255-284)

Replace:
```python
    def _run_example_mode(self, checker, task, task_data, profiler,
                          positive_examples, negative_examples,
                          mode, shuffle_seed):
        """Run example-based learning via QuAcq.learn(mode=...)."""
        mixed_examples = list(positive_examples) + list(negative_examples)
        query_provider = QueryProvider(
            self.solver_name,
            pool=mixed_examples,
            seed=shuffle_seed,
            profiler_instance=profiler)

        # For example_first, also need discrim_gen
        discrim_gen = None
        if mode == 'example_first':
            discrim_gen = DiscriminatingGenerator(
                background_clauses=task.background_clauses,
                constraint_clauses=task.constraint_clauses,
                negated_clauses=task.negated_clauses,
                id_to_feature=task.id_to_feature,
                solver_name=self.solver_name)

        quacq = QuAcq(
            checker=checker,
            oracle=self.oracle,
            query_provider=query_provider,
            discriminating_generator=discrim_gen,
            profiler_instance=profiler)

        return quacq.learn(
            **task_data, mode=mode,
            max_queries=self.max_queries)
```

### Step 4: Update `conacq/example_generators/__init__.py`

Replace the entire file:

```python
"""Example generators for different sampling strategies."""

from .base import ExampleGenerator
from .random_sampling import RandomSamplingGenerator, BalancedRandomSamplingGenerator, ControlledRandomSamplingGenerator
from .feature_frequency import FeatureFrequencyGenerator
from .nwise_coverage import NWiseCoverageGenerator, TwoCoverageGenerator


# QueryProvider is lazily imported to avoid circular dependency:
# example_generators/__init__ -> query_provider -> algorithms.quacq.sat_utils
def __getattr__(name):
    if name in ('QueryProvider', 'clause_count_priority', 'literal_count_priority'):
        from .query_provider import QueryProvider, clause_count_priority, literal_count_priority
        globals()['QueryProvider'] = QueryProvider
        globals()['clause_count_priority'] = clause_count_priority
        globals()['literal_count_priority'] = literal_count_priority
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'ExampleGenerator',
    'RandomSamplingGenerator',
    'BalancedRandomSamplingGenerator',
    'ControlledRandomSamplingGenerator',
    'FeatureFrequencyGenerator',
    'NWiseCoverageGenerator',
    'TwoCoverageGenerator',
    'QueryProvider',
    'clause_count_priority',
    'literal_count_priority',
]
```

Note: ExampleProvider and QueryGenerator removed from exports. Lazy import adapted for QueryProvider.

## Todo List

- [ ] Update quacq_runner.py imports
- [ ] Update _run_oracle_mode to use QueryProvider
- [ ] Update _run_example_mode to use QueryProvider
- [ ] Update example_generators/__init__.py exports

## Success Criteria

- QuAcqRunner uses QueryProvider exclusively
- No references to QueryGenerator or ExampleProvider in runner
- __init__.py exports QueryProvider (not QueryGenerator/ExampleProvider)
- Lazy import pattern preserved for circular dependency avoidance

## Risk Assessment

- **Backward compat**: Any external code importing QueryGenerator or ExampleProvider from __init__.py will break. Internal refactoring only -- acceptable.
- **Lazy import**: QueryProvider import path changed from query_generator to query_provider -- verify no circular dependency

## Security Considerations

- No new external interfaces

## Next Steps

- Phase 5: Delete ExampleProvider and old files, update tests
