# Brainstorm: FindScope & FindC → Class Refactor

**Date:** 2026-02-28
**Status:** Agreed
**Context:** `conacq/algorithms/quacq/findscope.py` (110 LOC), `conacq/algorithms/quacq/findc.py` (137 LOC)

## Problem

`find_scope()` and `find_c()` are standalone functions with 11-12 parameters each. Most params are "plumbing" data passed through from `QuAcq.learn()`. This creates:
- Long, error-prone call sites (10+ keyword args)
- Collaborators (oracle, profiler, generator) re-passed every call
- Inconsistency with QuAcq class-based pattern

## Agreed Design

### FindScope Class

```python
class FindScope:
    """Algorithm 2 from IJCAI13 — binary search for violated constraint scope."""

    def __init__(self, oracle, checker, profiler=None):
        self.oracle = oracle
        self.checker = checker  # reserved for future use
        self.profiler = profiler

    def run(self, e, R, Y, ask_query,
            constraint_clauses, feature_ids, id_to_feature,
            remaining_bias, record_query) -> List[str]:
        """Find scope of violated constraint."""
        ...

    def _prune_rejecting_partial(self, constraint_clauses, feature_ids,
                                  id_to_feature, remaining_bias, e, R):
        """Prune bias constraints that reject partial assignment e[R]."""
        ...
```

**File:** `findscope.py` — rename export, keep file name

### FindC Class

```python
class FindC:
    """Algorithm 3 from IJCAI13 — identify specific violated constraint within scope."""

    def __init__(self, oracle, checker, generator=None, profiler=None):
        self.oracle = oracle
        self.checker = checker  # reserved for future use
        self.generator = generator  # DiscriminatingGenerator
        self.profiler = profiler

    def run(self, e, scope, constraint_clauses, feature_ids,
            id_to_feature, remaining_bias, record_query,
            learned_kb) -> Optional[int]:
        """Find the specific constraint violated by example e within scope."""
        ...

    def _narrow_with_generator(self, candidates, remaining_bias,
                                record_query, learned_kb, scope):
        """Use discriminating generator to narrow candidates."""
        ...
```

**File:** `findc.py` — rename export, keep file name

### QuAcq Integration

```python
class QuAcq:
    def __init__(self, checker, oracle, model=None,
                 query_provider=None, discriminating_generator=None,
                 profiler_instance=None):
        ...
        # Internal algorithm components — NOT exposed to callers
        self._find_scope = FindScope(oracle, checker, profiler_instance)
        self._find_c = FindC(oracle, checker, discriminating_generator, profiler_instance)
```

Call sites in `learn()`:
```python
scope_vars = self._find_scope.run(
    e=query, R=set(), Y=all_variables,
    ask_query=False,
    constraint_clauses=constraint_clauses,
    feature_ids=feature_ids, id_to_feature=id_to_feature,
    remaining_bias=remaining_bias,
    record_query=record_query
)

c_id = self._find_c.run(
    e=query, scope=scope,
    constraint_clauses=constraint_clauses,
    feature_ids=feature_ids, id_to_feature=id_to_feature,
    remaining_bias=remaining_bias,
    record_query=record_query,
    learned_kb=learned_kb
)
```

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Constructor params | Collaborators (oracle, checker, profiler) | Injected once, reused across calls |
| Method params | Algorithm-specific data (e, R, Y, constraint_clauses...) | Changes per call, flexible |
| Private helpers | Instance methods | Access `self.oracle`/`self.profiler` naturally |
| State sharing | Independent classes (no shared base) | KISS, no coupling |
| remaining_bias | Keep mutable (status quo) | Consistent with QuAcq.learn() pattern |
| QuAcq ownership | QuAcq creates internally (private attrs) | Encapsulation, no API surface change |
| Method name | `run()` | Generic, clear intent |
| checker param | Included in constructor | Future extensibility, minimal cost |

## Impact Analysis

### Files to Modify
- `conacq/algorithms/quacq/findscope.py` — function → class
- `conacq/algorithms/quacq/findc.py` — function → class
- `conacq/algorithms/quacq/quacq.py` — create instances in `__init__`, update call sites
- `conacq/algorithms/quacq/__init__.py` — update exports (FindScope, FindC classes)

### Files NOT Changed
- `quacq_model.py` — no dependency on find_scope/find_c
- `quacq_model_builder.py` — no dependency
- `quacq_runner.py` — doesn't call find_scope/find_c directly
- `sat_utils.py` — pure utility, no change
- `task_preparation.py` — no dependency

### Param Count Reduction

| Component | Before | After |
|---|---|---|
| find_scope call | 11 args | 9 args (oracle, profiler → constructor) |
| find_c call | 12 args | 8 args (oracle, generator, profiler → constructor) |

### Backward Compatibility
- **External API unchanged**: QuAcq constructor signature stays same
- **Runner unchanged**: QuAcqRunner doesn't interact with FindScope/FindC
- **__init__.py exports**: Update from `find_scope`/`find_c` functions to `FindScope`/`FindC` classes

## Risks
- **checker param unused now**: Minimal risk — stored but not called. YAGNI concern noted but cost is 1 line.
- **Recursive self-call in FindScope.run()**: Must change recursive `find_scope()` call to `self.run()` — easy but must not miss.

## Success Criteria
- All existing tests pass unchanged
- Call sites in QuAcq.learn() cleaner (fewer args)
- FindScope and FindC independently testable via class instantiation
- No external API changes (QuAcq constructor, runner, etc.)
