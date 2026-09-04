# Phase 2: Integrate into QuAcq & Update Exports

## Context Links

- [Parent plan](plan.md)
- [Phase 1](phase-01-convert-to-classes.md) — prerequisite
- Source: `conacq/algorithms/quacq/quacq.py` (326 LOC)
- Source: `conacq/algorithms/quacq/__init__.py` (82 LOC)

## Overview

- **Priority:** P2
- **Status:** complete
- **Description:** Wire FindScope/FindC classes into QuAcq constructor; update call sites in `learn()`; update package exports

## Key Insights

- QuAcq creates FindScope/FindC internally — NOT exposed to callers
- No external API change to QuAcq constructor signature
- `__init__.py` exports change from function names to class names
- Call sites in `learn()` shrink by removing oracle/profiler/generator args

## Requirements

### Functional
- QuAcq creates `self._find_scope` and `self._find_c` in `__init__`
- Call sites in `learn()` use `self._find_scope.run(...)` and `self._find_c.run(...)`
- `__init__.py` exports `FindScope`, `FindC` classes

### Non-functional
- QuAcq constructor signature unchanged (no new params)
- Runner code unchanged (no dependency on FindScope/FindC)

## Related Code Files

### Modify
- `conacq/algorithms/quacq/quacq.py` — import classes, create instances, update call sites
- `conacq/algorithms/quacq/__init__.py` — update exports

### Read-only
- `conacq/runners/quacq_runner.py` — verify no direct find_scope/find_c usage

## Implementation Steps

### Step 1: Update `quacq.py` imports

```python
# Change:
from .findscope import find_scope
from .findc import find_c
# To:
from .findscope import FindScope
from .findc import FindC
```

### Step 2: Create instances in `QuAcq.__init__`

After existing assignments (line ~73), add:
```python
self._find_scope = FindScope(oracle, checker, profiler_instance)
self._find_c = FindC(oracle, checker, discriminating_generator, profiler_instance)
```

### Step 3: Update call site — find_scope (line 216-224)

```python
# Before (10 keyword args):
scope_vars = find_scope(
    e=query, R=set(), Y=all_variables,
    ask_query=False, oracle=self.oracle,
    constraint_clauses=constraint_clauses,
    feature_ids=feature_ids, id_to_feature=id_to_feature,
    remaining_bias=remaining_bias,
    record_query=record_query, profiler=self.profiler)

# After (8 keyword args — oracle, profiler removed):
scope_vars = self._find_scope.run(
    e=query, R=set(), Y=all_variables,
    ask_query=False,
    constraint_clauses=constraint_clauses,
    feature_ids=feature_ids, id_to_feature=id_to_feature,
    remaining_bias=remaining_bias,
    record_query=record_query)
```

### Step 4: Update call site — find_c (line 228-238)

```python
# Before (11 keyword args):
c_id = find_c(
    e=query, scope=scope,
    constraint_clauses=constraint_clauses,
    feature_ids=feature_ids, id_to_feature=id_to_feature,
    remaining_bias=remaining_bias,
    record_query=record_query, oracle=self.oracle,
    learned_kb=learned_kb,
    generator=self.discriminating_generator,
    profiler=self.profiler)

# After (8 keyword args — oracle, generator, profiler removed):
c_id = self._find_c.run(
    e=query, scope=scope,
    constraint_clauses=constraint_clauses,
    feature_ids=feature_ids, id_to_feature=id_to_feature,
    remaining_bias=remaining_bias,
    record_query=record_query,
    learned_kb=learned_kb)
```

### Step 5: Update `__init__.py` exports

```python
# Change:
from .findscope import find_scope
from .findc import find_c
# To:
from .findscope import FindScope
from .findc import FindC

# In __all__, change:
'find_scope',  →  'FindScope',
'find_c',      →  'FindC',
```

## Todo List

- [x] Update imports in quacq.py (FindScope, FindC classes)
- [x] Create `self._find_scope` and `self._find_c` in `QuAcq.__init__`
- [x] Update find_scope call site in learn() (remove oracle, profiler args)
- [x] Update find_c call site in learn() (remove oracle, generator, profiler args)
- [x] Update __init__.py imports and __all__ exports
- [x] Run tests: `PYTHONPATH=. pytest tests/ -v` — All 359 tests passed

## Success Criteria

- All existing tests pass
- QuAcq constructor signature unchanged
- Call sites use `self._find_scope.run()` and `self._find_c.run()`
- `__init__.py` exports FindScope/FindC classes
- No import errors

## Risk Assessment

- **Low**: No external API changes, all internal wiring
- **Import check**: Verify `from conacq.algorithms.quacq import FindScope, FindC` works

## Next Steps

- Run full test suite
- Code review
