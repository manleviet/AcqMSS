# Phase 2: Update QuAcq Algorithm

## Context Links

- Phase 1: `phase-01-create-query-provider.md`
- Source: `conacq/algorithms/quacq/quacq.py` (340 LOC)

## Overview

- **Date**: 2026-02-28
- **Priority**: P2
- **Status**: completed
- **Description**: Replace `query_generator` + `example_provider` with single `query_provider` in QuAcq DI and simplify mode dispatch in learn()

## Key Insights

- Current learn() has complex mode dispatch: oracle -> query_generator.generate(), example_only/example_first -> example_provider.next_example() then fallback to query_generator
- With QueryProvider, mode maps directly to method: oracle -> generate_from_sat(), example_only -> generate_from_pool(), example_first -> generate()
- Factory methods simplify: for_oracle() needs QueryProvider (SAT only), for_examples() needs QueryProvider (pool required)
- FindC call currently passes `example_provider` -- Phase 3 removes this, but Phase 2 must stop passing it

## Requirements

### Functional
- Replace two constructor params (query_generator, example_provider) with single query_provider
- Simplify mode dispatch in learn() to call appropriate QueryProvider method
- Update factory methods (for_oracle, for_examples)
- Update _validate_mode to check query_provider
- Stop passing example_provider to find_c (prepare for Phase 3)

### Non-Functional
- Net code reduction: ~20 LOC removed from mode dispatch logic

## Architecture

Before:
```
QuAcq.__init__(oracle, query_generator, example_provider, discriminating_generator)
```

After:
```
QuAcq.__init__(oracle, query_provider, discriminating_generator)
```

Mode dispatch before (lines 167-184):
```python
if mode == 'oracle':
    query, tested_c_id = self.query_generator.generate(...)
else:
    query = self.example_provider.next_example()
    if query is None and mode == 'example_first':
        query, tested_c_id = self.query_generator.generate(...)
```

Mode dispatch after:
```python
kb_cls = get_kb_clauses(learned_kb, constraint_clauses)
if mode == 'oracle':
    query, tested_c_id = self.query_provider.generate_from_sat(...)
elif mode == 'example_only':
    query, tested_c_id = self.query_provider.generate_from_pool(...)
else:  # example_first
    query, tested_c_id = self.query_provider.generate(...)
```

## Related Code Files

### Files to modify
- `conacq/algorithms/quacq/quacq.py`

## Implementation Steps

### Step 1: Update imports (line 18)

Replace:
```python
from conacq.example_generators import QueryGenerator, ExampleProvider
```
With:
```python
from conacq.example_generators import QueryProvider
```

### Step 2: Update QuAcq.__init__ (lines 61-74)

Replace constructor:
```python
def __init__(self, checker: ConsistencyChecker,
             oracle: Oracle,
             query_provider: QueryProvider = None,
             discriminating_generator: DiscriminatingGenerator = None,
             profiler_instance: AbstractProfiler = None) -> None:
    self.checker = checker
    self.oracle = oracle
    self.profiler = profiler_instance if profiler_instance else get_global_profiler()
    self.result: Optional[QuAcqResult] = None

    self.query_provider = query_provider
    self.discriminating_generator = discriminating_generator
```

### Step 3: Update factory methods (lines 76-96)

Replace for_oracle:
```python
@classmethod
def for_oracle(cls, checker: ConsistencyChecker,
               oracle: Oracle,
               query_provider: QueryProvider,
               discrim_gen: DiscriminatingGenerator,
               profiler: AbstractProfiler = None) -> 'QuAcq':
    """Factory for oracle-based learning. discrim_gen required."""
    return cls(checker, oracle, query_provider=query_provider,
               discriminating_generator=discrim_gen,
               profiler_instance=profiler)
```

Replace for_examples:
```python
@classmethod
def for_examples(cls, checker: ConsistencyChecker,
                 oracle: Oracle,
                 query_provider: QueryProvider,
                 discrim_gen: DiscriminatingGenerator = None,
                 profiler: AbstractProfiler = None) -> 'QuAcq':
    """Factory for example-based learning."""
    return cls(checker, oracle, query_provider=query_provider,
               discriminating_generator=discrim_gen,
               profiler_instance=profiler)
```

### Step 4: Update class docstring (lines 46-59)

Update Args section:
```python
"""
QuAcq algorithm for interactive constraint acquisition.

Collaborators injected at construction (DI pattern).
Single learn() method with mode dispatch.

Args:
    oracle: Oracle for membership queries
    query_provider: Unified query provider (pool + SAT strategies)
    discriminating_generator: For FindC discriminating examples (required for oracle mode)
    profiler_instance: Optional profiler
"""
```

### Step 5: Simplify mode dispatch in learn() (lines 163-193)

Replace the entire Step 1 block (lines 163-193) with:

```python
            # Step 1: Get next query (mode-dependent)
            kb_cls = get_kb_clauses(learned_kb, constraint_clauses)

            if mode == 'oracle':
                query, tested_c_id = self.query_provider.generate_from_sat(
                    remaining_bias=remaining_bias, learned_kb=learned_kb,
                    kb_clauses=kb_cls, negated_clauses=negated_clauses,
                    bg_clauses=background_clauses, feature_ids=feature_ids,
                    id_to_feature=id_to_feature, n_bg=len(set_b))
            elif mode == 'example_only':
                query, tested_c_id = self.query_provider.generate_from_pool(
                    remaining_bias=remaining_bias, kb_clauses=kb_cls,
                    bg_clauses=background_clauses,
                    constraint_clauses=constraint_clauses,
                    feature_ids=feature_ids)
            else:  # example_first
                query, tested_c_id = self.query_provider.generate(
                    remaining_bias=remaining_bias, learned_kb=learned_kb,
                    kb_clauses=kb_cls, negated_clauses=negated_clauses,
                    bg_clauses=background_clauses, feature_ids=feature_ids,
                    id_to_feature=id_to_feature,
                    constraint_clauses=constraint_clauses,
                    n_bg=len(set_b))

            if query is None:
                if mode == 'oracle':
                    convergence_reason = 'no_query'
                elif mode == 'example_only':
                    convergence_reason = 'pool_exhausted'
                else:
                    convergence_reason = 'no_query'
                logging.info('No more queries: %s', convergence_reason)
                break
```

Note: `kb_cls` now computed once before the if/elif/else block (was computed inside each branch before).

### Step 6: Remove example_provider from find_c call (lines 230-241)

Replace:
```python
                    c_id = find_c(
                        e=query, scope=scope,
                        constraint_clauses=constraint_clauses,
                        feature_ids=feature_ids,
                        id_to_feature=id_to_feature,
                        remaining_bias=remaining_bias,
                        record_query=record_query, oracle=self.oracle,
                        learned_kb=learned_kb,
                        generator=self.discriminating_generator,
                        example_provider=self.example_provider if mode != 'oracle' else None,
                        query_mode=mode if mode != 'oracle' else 'example_only',
                        profiler=self.profiler
                    )
```

With:
```python
                    c_id = find_c(
                        e=query, scope=scope,
                        constraint_clauses=constraint_clauses,
                        feature_ids=feature_ids,
                        id_to_feature=id_to_feature,
                        remaining_bias=remaining_bias,
                        record_query=record_query, oracle=self.oracle,
                        learned_kb=learned_kb,
                        generator=self.discriminating_generator,
                        profiler=self.profiler
                    )
```

### Step 7: Update _validate_mode (lines 281-297)

Replace entire method:
```python
    def _validate_mode(self, mode: str) -> None:
        """Validate mode and required dependencies."""
        valid_modes = ('oracle', 'example_only', 'example_first')
        if mode not in valid_modes:
            raise ValueError(f"Unknown mode '{mode}'. Use one of: {valid_modes}")
        if self.query_provider is None:
            raise ValueError("query_provider is required (use for_oracle() or for_examples())")
        if mode == 'oracle' and self.discriminating_generator is None:
            raise ValueError("Oracle mode requires discriminating_generator (use for_oracle())")
        if mode == 'example_first' and self.discriminating_generator is None:
            raise ValueError("example_first mode requires discriminating_generator")
```

Note: all modes now require query_provider. The pool-related check is handled by QueryProvider itself (generate_from_pool returns None,None when pool empty/not provided).

### Step 8: Update module docstring (line 1-10)

Replace:
```python
"""
QuAcq algorithm for interactive constraint acquisition (IJCAI 2013).

Supports three modes via single learn() method:
- 'oracle': QueryProvider.generate_from_sat() + oracle.ask()
- 'example_only': QueryProvider.generate_from_pool() (paper-filtered)
- 'example_first': QueryProvider.generate() (pool first, SAT fallback)

All collaborators injected at construction (DI pattern).
Also contains QuAcqResult (co-located: algorithm produces its own result type).
"""
```

## Todo List

- [ ] Update imports (QueryGenerator, ExampleProvider -> QueryProvider)
- [ ] Update `__init__` params
- [ ] Update factory methods (for_oracle, for_examples)
- [ ] Update class and module docstrings
- [ ] Simplify mode dispatch in learn()
- [ ] Remove example_provider from find_c call
- [ ] Update _validate_mode

## Success Criteria

- QuAcq uses single `query_provider` instead of two separate objects
- Mode dispatch is cleaner: 3 branches calling 3 methods
- No reference to ExampleProvider or QueryGenerator
- find_c called without example_provider param

## Risk Assessment

- **Behavioral change**: Pool filtering now applies paper condition -- may find fewer pool matches in example_only mode. This is *intended* (correctness).
- **kb_clauses recomputed each iteration**: Was already the case in oracle mode; now also in example modes. Minimal overhead (list concatenation).

## Security Considerations

- No new external interfaces

## Next Steps

- Phase 3: Simplify FindC (remove _narrow_with_pool, remove example_provider param)
