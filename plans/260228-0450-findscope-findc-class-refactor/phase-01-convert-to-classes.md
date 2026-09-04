# Phase 1: Convert FindScope & FindC to Classes

## Context Links

- [Parent plan](plan.md)
- [Brainstorm report](../reports/brainstorm-260228-0450-findscope-findc-class-refactor.md)
- Source: `conacq/algorithms/quacq/findscope.py` (110 LOC)
- Source: `conacq/algorithms/quacq/findc.py` (137 LOC)

## Overview

- **Priority:** P2
- **Status:** complete
- **Description:** Convert standalone `find_scope()` and `find_c()` functions into `FindScope` and `FindC` classes with constructor-injected collaborators

## Key Insights

- Both functions have 11-12 params; ~6-7 are "plumbing" data, 2-3 are collaborators
- `find_scope()` calls itself recursively — must change to `self.run()`
- `_prune_rejecting_partial()` and `_narrow_with_generator()` are module-level private helpers that become instance methods
- No external callers outside quacq package — safe to refactor

## Requirements

### Functional
- FindScope class wraps find_scope function logic
- FindC class wraps find_c function logic
- Private helpers become instance methods
- Method signature `run()` for main algorithm entry

### Non-functional
- Keep existing algorithm behavior unchanged
- Maintain same return types and side effects (mutable remaining_bias)

## Related Code Files

### Modify
- `conacq/algorithms/quacq/findscope.py` — function → class
- `conacq/algorithms/quacq/findc.py` — function → class

### Read-only (reference)
- `conacq/algorithms/quacq/sat_utils.py` — utility imports unchanged
- `explanation/operations/algorithms/profiler.py` — AbstractProfiler type

## Implementation Steps

### Step 1: FindScope class (`findscope.py`)

1. Create `FindScope` class with constructor:
   ```python
   class FindScope:
       def __init__(self, oracle, checker, profiler=None):
           self.oracle = oracle
           self.checker = checker
           self.profiler = profiler
   ```

2. Convert `find_scope()` → `FindScope.run()`:
   - Remove `oracle` and `profiler` from method params (use `self.oracle`, `self.profiler`)
   - Keep algorithm-specific params: `e, R, Y, ask_query, constraint_clauses, feature_ids, id_to_feature, remaining_bias, record_query`
   - **CRITICAL**: Change recursive calls `find_scope(e, R|Y1, ...)` → `self.run(e, R|Y1, ...)`
   - Remove `oracle=` and `profiler=` from recursive call args

3. Convert `_prune_rejecting_partial()` → `FindScope._prune_rejecting_partial()`:
   - Add `self` as first param
   - Keep all other params (they're per-call data)

### Step 2: FindC class (`findc.py`)

1. Create `FindC` class with constructor:
   ```python
   class FindC:
       def __init__(self, oracle, checker, generator=None, profiler=None):
           self.oracle = oracle
           self.checker = checker
           self.generator = generator
           self.profiler = profiler
   ```

2. Convert `find_c()` → `FindC.run()`:
   - Remove `oracle`, `generator`, `profiler` from method params (use `self.*`)
   - Keep algorithm-specific params: `e, scope, constraint_clauses, feature_ids, id_to_feature, remaining_bias, record_query, learned_kb`
   - Update call to `_narrow_with_generator()` → `self._narrow_with_generator()`
   - Remove `oracle=` and `generator=` from that call's args

3. Convert `_narrow_with_generator()` → `FindC._narrow_with_generator()`:
   - Add `self` as first param
   - Remove `oracle` and `generator` from params (use `self.oracle`, `self.generator`)
   - Keep: `candidates, remaining_bias, record_query, learned_kb, scope`

## Todo List

- [x] Convert `find_scope()` to `FindScope` class
- [x] Convert `_prune_rejecting_partial()` to instance method
- [x] Change recursive `find_scope()` calls to `self.run()`
- [x] Convert `find_c()` to `FindC` class
- [x] Convert `_narrow_with_generator()` to instance method
- [x] Verify module docstrings updated

## Success Criteria

- Both classes instantiable with collaborators
- `run()` method has correct signature (no oracle/profiler/generator in params)
- Recursive call in FindScope uses `self.run()`
- Private helpers use `self.oracle` etc. instead of passed params

## Risk Assessment

- **Recursive self-call**: Must not miss changing `find_scope()` → `self.run()` in 2 places (lines 72, 75)
- **Low risk**: No external callers, all within package

## Next Steps

→ Phase 2: Update QuAcq integration and __init__.py exports
