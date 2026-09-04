# Brainstorm: QuAcq Dependency Injection Refactor

## Problem Statement
QuAcq's current design creates dependencies internally (QueryGenerator in `__init__`, DiscriminatingGenerator in `learn()`), has 2 separate learning methods (`learn()` + `learn_from_examples()`), and accepts a `QuAcqTask` object rather than raw data. This diverges from ConGen's cleaner DI pattern where `__init__` accepts a checker and `acquire()` accepts flat data params.

## Requirements
1. QuAcq `__init__` receives DI objects: Oracle, QueryGenerator, ExampleProvider, DiscriminatingGenerator
2. Factory class methods: `for_oracle()`, `for_examples()`
3. Single `learn()` method with `mode` param ('oracle'/'example_only'/'example_first')
4. `learn()` accepts flat raw data params (set_c, set_b, ...) like ConGen.acquire()
5. Cascading refactor: DiscriminatingGenerator + QueryGenerator accept raw data instead of QuAcqTask

## Agreed Design

### QuAcq Class
```python
class QuAcq:
    def __init__(self, oracle: Oracle,
                 query_generator: QueryGenerator = None,
                 example_provider: ExampleProvider = None,
                 discriminating_generator: DiscriminatingGenerator = None,
                 profiler_instance: AbstractProfiler = None):
        ...

    @classmethod
    def for_oracle(cls, oracle, query_gen, discrim_gen, profiler=None): ...

    @classmethod
    def for_examples(cls, oracle, example_provider, discrim_gen=None, profiler=None): ...

    def learn(self,
              set_c: List[int],                              # bias B
              set_b: List[int],                              # background knowledge BG
              set_kb: List[int],                             # initial learned KB
              negation_map: Dict[int, int],
              assumptions: Dict[int, Any],
              background_clauses: List[List[int]],           # raw CNF for FindScope
              feature_ids: Dict[str, int],                   # name -> SAT var
              id_to_feature: Dict[int, str],                 # SAT var -> name
              constraint_clauses: Dict[int, List[List[int]]],
              negated_clauses: Dict[int, List[List[int]]],
              mode: Literal['oracle', 'example_only', 'example_first'] = 'oracle',
              max_queries: int = 1000,
              description_provider: DescriptionProvider = None,
              ) -> QuAcqResult:
        ...
```

### DiscriminatingGenerator — refactored
Accept raw data instead of QuAcqTask. Either via `__init__` or per-`generate()` call.

### QueryGenerator — refactored
`generate()` accepts raw data instead of task object.

## Files Affected
1. `conacq/algorithms/quacq/quacq.py` — major: merge 2 methods, add factories, flat params
2. `conacq/algorithms/quacq/discriminating_generator.py` — refactor away from QuAcqTask
3. `conacq/example_generators/query_generator.py` — refactor generate() signature
4. `apps/quacq_runner.py` — caller update (extract raw data from task)
5. `tests/test_quacq.py` — update test calls
6. Possibly `conacq/algorithms/quacq/quacq_model_builder.py` if builder creates QuAcq instances

## Risks
- **Large param list**: 10+ params in learn() — accepted trade-off for explicitness
- **Cascading changes**: DiscrimGen + QueryGen refactor touches foundational SAT code
- **Breaking all callers**: QuAcqRunner + all tests need updating
- **Mode validation**: Must validate deps exist for chosen mode at runtime

## Decision Log
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Learning modes | Single learn() + mode param | Consistent API, single entry point |
| learn() params | Flat raw data | Matches ConGen pattern, explicit, type-safe |
| DI strategy | Factory class methods | Clean construction validation per mode |
| DiscrimGen | Refactor to raw data | Consistent with overall direction |
| Param count | Accept 10+ flat | IDE autocomplete helps, explicit > implicit |
