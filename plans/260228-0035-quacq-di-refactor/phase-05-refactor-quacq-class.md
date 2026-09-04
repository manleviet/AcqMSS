# Phase 5: Refactor QuAcq Class

## Context Links
- [Plan overview](plan.md)
- [Brainstorm](../reports/brainstorm-260228-0035-quacq-di-refactor.md)
- Source: `conacq/algorithms/quacq/quacq.py` (471 LOC, includes QuAcqResult)
- Depends on: Phase 1 (DiscriminatingGenerator), Phase 2 (QueryGenerator), Phase 3 (FindScope), Phase 4 (FindC)
<!-- Updated: Validation Session 1 - No internal QuAcqTask; discrim_gen required in for_oracle() -->

## Overview
- **Priority:** Critical (core of refactor)
- **Status:** complete
- **Description:** New `__init__` with DI objects, factory class methods, single `learn()` with flat params and `mode` param. NO internal QuAcqTask — pass raw data directly to FindScope/FindC/sat_utils.

## Key Insights
- `QuAcqResult` dataclass (~105 LOC) stays unchanged
- Current `__init__` creates `QueryGenerator` internally — move to DI
- `DiscriminatingGenerator` created inside `learn()` — move to DI, **required** in `for_oracle()`
- `learn()` and `learn_from_examples()` share ~80% logic — merge with mode dispatch
- FindScope/FindC now accept raw params (Phases 3-4) — no need for QuAcqTask reconstruction
- `_apply_reduce` already decoupled (receives explicit field values)

## Requirements

### Functional
1. `__init__` receives: `oracle`, `query_generator` (optional), `example_provider` (optional), `discriminating_generator` (optional), `profiler` (optional)
2. Factory: `for_oracle(oracle, query_gen, discrim_gen, profiler)` — `discrim_gen` **required** (not optional)
3. Factory: `for_examples(oracle, example_provider, discrim_gen=None, profiler=None)`
4. Single `learn()` with `mode='oracle'|'example_only'|'example_first'` and flat raw data
5. learn() passes raw data directly to FindScope/FindC (no QuAcqTask)
6. Mode validation at runtime: oracle needs query_generator + discriminating_generator; example modes need example_provider

### Non-Functional
- QuAcq class portion under 200 LOC (QuAcqResult stays ~105 LOC)
- Type hints on all public methods

## Architecture

### After
```python
class QuAcq:
    def __init__(self, oracle: Oracle,
                 query_generator: QueryGenerator = None,
                 example_provider: ExampleProvider = None,
                 discriminating_generator: DiscriminatingGenerator = None,
                 profiler_instance: AbstractProfiler = None):
        self.oracle = oracle
        self.query_generator = query_generator
        self.example_provider = example_provider
        self.discriminating_generator = discriminating_generator
        self.profiler = profiler_instance or get_global_profiler()

    @classmethod
    def for_oracle(cls, oracle: Oracle,
                   query_gen: QueryGenerator,
                   discrim_gen: DiscriminatingGenerator,  # REQUIRED
                   profiler: AbstractProfiler = None) -> 'QuAcq':
        return cls(oracle, query_generator=query_gen,
                   discriminating_generator=discrim_gen,
                   profiler_instance=profiler)

    @classmethod
    def for_examples(cls, oracle: Oracle,
                     example_provider: ExampleProvider,
                     discrim_gen: DiscriminatingGenerator = None,
                     profiler: AbstractProfiler = None) -> 'QuAcq':
        return cls(oracle, example_provider=example_provider,
                   discriminating_generator=discrim_gen,
                   profiler_instance=profiler)

    def learn(self,
              set_c: List[int],
              set_b: List[int],
              set_kb: List[int],
              negation_map: Dict[int, int],
              assumptions: List[int],
              background_clauses: List[List[int]],
              feature_ids: Dict[str, int],
              id_to_feature: Dict[int, str],
              constraint_clauses: Dict[int, List[List[int]]],
              negated_clauses: Dict[int, List[List[int]]],
              mode: Literal['oracle', 'example_only', 'example_first'] = 'oracle',
              max_queries: int = 1000,
              description_provider: DescriptionProvider = None,
              ) -> QuAcqResult:
```

### Key change from original plan
- **No internal QuAcqTask construction** — raw data flows directly to FindScope/FindC/sat_utils
- `discrim_gen` required in `for_oracle()` (was optional)
- `_apply_reduce` receives raw params (already decoupled)

## Related Code Files
- **Modify:** `conacq/algorithms/quacq/quacq.py`
- **Import:** `sat_utils` functions for internal computation (config_to_assumptions, violates_clauses, etc.)
- **No change:** `QuAcqResult` dataclass

## Implementation Steps

1. **Update `__init__` signature** with DI params (oracle, query_gen, example_provider, discrim_gen, profiler).

2. **Add factory class methods**: `for_oracle()` with `discrim_gen` required, `for_examples()` with optional.

3. **Create single `learn()` method** with flat params + mode.

4. **Add mode validation** at top of `learn()`:
   ```python
   if mode == 'oracle':
       if self.query_generator is None:
           raise ValueError("Oracle mode requires query_generator (use for_oracle())")
       if self.discriminating_generator is None:
           raise ValueError("Oracle mode requires discriminating_generator (use for_oracle())")
   if mode in ('example_only', 'example_first') and self.example_provider is None:
       raise ValueError("Example mode requires example_provider (use for_examples())")
   if mode == 'example_first' and self.query_generator is None:
       raise ValueError("example_first mode requires query_generator")
   ```

5. **Merge learn logic** with mode dispatch:
   - **Query acquisition**: oracle → `query_generator.generate(...)`, example_only → `example_provider.next_example()`, example_first → pool first then SAT fallback
   - **Oracle check**: oracle → `self.oracle.ask(query)`, example modes → `self.oracle.is_valid(query)`
   - **Positive/negative processing**: identical across modes

6. **Wire FindScope with raw params**:
   ```python
   find_scope(e, R, Y, ask_query, self.oracle,
              constraint_clauses=constraint_clauses,
              feature_ids=feature_ids,
              id_to_feature=id_to_feature,
              remaining_bias=remaining_bias, ...)
   ```

7. **Wire FindC with raw params**:
   ```python
   find_c(e, scope,
          constraint_clauses=constraint_clauses,
          feature_ids=feature_ids,
          id_to_feature=id_to_feature,
          remaining_bias=remaining_bias,
          oracle=self.oracle,
          learned_kb=learned_kb,
          generator=self.discriminating_generator, ...)
   ```

8. **Wire QueryGenerator with raw params**:
   ```python
   kb_clauses = get_kb_clauses(learned_kb, constraint_clauses)  # sat_utils
   self.query_generator.generate(
       remaining_bias=remaining_bias, learned_kb=learned_kb,
       kb_clauses=kb_clauses, negated_clauses=negated_clauses,
       bg_clauses=background_clauses, feature_ids=feature_ids,
       id_to_feature=id_to_feature, n_bg=len(set_b))
   ```

9. **Update `_apply_reduce`**: Accept raw params (set_kb, assumptions, set_b, negation_map).

10. **Update `_prune_rejecting_constraints`**: Use sat_utils functions instead of task methods.

11. **Update `_build_result`**: Use `len(constraint_clauses)` for initial_bias_size.

12. **Delete `learn_from_examples()` method** entirely.

13. **Clean up imports**: Remove QuAcqTask import if no longer needed, add sat_utils imports.

## Todo List
- [ ] Rewrite `__init__` with DI params
- [ ] Add `for_oracle()` factory (discrim_gen required)
- [ ] Add `for_examples()` factory
- [ ] Create single `learn()` with flat params and mode
- [ ] Add mode validation (4 checks)
- [ ] Merge oracle/example loop logic with mode dispatch
- [ ] Wire FindScope with raw params
- [ ] Wire FindC with raw params
- [ ] Wire QueryGenerator with raw params
- [ ] Update `_apply_reduce` to raw params
- [ ] Update `_prune_rejecting_constraints` to use sat_utils
- [ ] Update `_build_result`
- [ ] Delete `learn_from_examples()`
- [ ] Clean up imports
- [ ] Verify QuAcq class under 200 LOC

## Success Criteria
- Single `learn()` with mode — no `learn_from_examples()`
- `__init__` accepts DI objects, no internal QueryGenerator/DiscriminatingGenerator creation
- No QuAcqTask import/usage in algorithm flow
- Factory methods work correctly, `for_oracle` requires discrim_gen
- Mode validation raises ValueError for missing deps
- FindScope/FindC called with raw params

## Risk Assessment
- **High risk — largest change**: Merging two methods + removing task dependency. Mitigated by: phases 1-4 already done, shared logic ~80%.
- **`get_kb_clauses` extraction**: Currently a QuAcqTask method. Need standalone version in sat_utils or inline.
- **`_apply_reduce` signature change**: Only called internally, low risk.
- **Profiler metrics**: Single decorator set. Old `quacq_example_runtime` disappears — acceptable.

## Next Steps
- Phase 6 updates QuAcqRunner and tests to use new API
