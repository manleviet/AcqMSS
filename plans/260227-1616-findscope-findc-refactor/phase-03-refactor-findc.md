# Phase 3: Refactor FindC — oracle + DiscriminatingGenerator

## Context

- Brainstorm: `plans/reports/brainstorm-260227-1614-findscope-findc-oracle-refactor.md`
- Paper: IJCAI 2013 Algorithm 3 — FindC uses C_L[Y] for discriminating examples, oracle for queries
- Depends on: Phase 1 (DiscriminatingGenerator)

## Overview

- **Priority**: P1
- **Status**: completed
- **Effort**: 45min

Replace FM-clauses-based SAT narrowing with DiscriminatingGenerator (C_L[Y]). Replace `_check_fm_consistency()` with `oracle.is_valid()`. Remove `fm_clauses`, `solver_name` params. Keep `example_provider` and `query_mode` (pool-first hybrid per validation).

## Key Changes

| Before | After |
|--------|-------|
| `_narrow_with_sat()` uses `fm_clauses + c_i + neg_j` | `generator.generate(c_i, c_j, learned_kb, scope)` |
| `_narrow_with_pool()` uses `_check_fm_consistency()` | `oracle.is_valid(disc_e)` |
| `_check_fm_consistency()` via OneShotModel | `oracle.is_valid()` |
| Params: `fm_clauses`, `solver_name` | Params: `oracle`, `generator`, `learned_kb` (keep `example_provider`, `query_mode`) |
| Imports: `OneShotModel`, `CheckerFactory`, `Solver` | Imports: none new (keep `ExampleProvider`) |

## Requirements

### Functional
- Pool-based narrowing: validate via `oracle.is_valid(disc_e)` instead of SAT
- SAT-based narrowing: use `generator.generate(c_i, c_j, learned_kb, scope)`
- All queries recorded via `record_query(config, answer, 'findc')`

### Non-functional
- No direct SAT solver usage in findc.py (SAT encapsulated in DiscriminatingGenerator)
- File ~140 LOC (down from 205)

## Related Code Files

### Modify
- `conacq/algorithms/quacq/findc.py` (205 LOC -> ~140 LOC)

### Dependencies
- `conacq/algorithms/quacq/discriminating_generator.py` (Phase 1)
- `conacq/algorithms/quacq/task_preparation.py` — QuAcqTask

## New Signatures

### find_c (main entry)
```python
def find_c(
        e: dict,
        scope: set,
        task,
        remaining_bias: set,
        record_query,
        oracle,                    # NEW: replaces fm_clauses
        learned_kb: list,          # NEW: for DiscriminatingGenerator
        generator,                 # NEW: DiscriminatingGenerator instance
        example_provider=None,     # KEPT: pool-first hybrid
        query_mode='example_only', # KEPT: controls pool-first vs generator-only
        profiler: AbstractProfiler = None
):
```

**Removed params**: `fm_clauses`, `solver_name`
**Kept params**: `example_provider`, `query_mode` (pool-first hybrid per validation)

### _narrow_with_pool — KEPT (modified)
<!-- Updated: Validation Session 1 - Keep pool narrowing with oracle.is_valid -->
Pool-based narrowing is kept but `_check_fm_consistency()` replaced with `oracle.is_valid()`. Hybrid: try pool first, then DiscriminatingGenerator. Keeps `example_provider` param in find_c().

### _narrow_with_sat — REPLACED by inline generator loop
The pairwise `c_i`/`c_j` loop stays but uses `generator.generate()` instead of raw SAT.

## Implementation Steps

1. **Update `find_c()` signature**: Remove `fm_clauses`, `solver_name`. Add `oracle`, `learned_kb`, `generator`. Keep `example_provider`, `query_mode`.

2. **Update `_narrow_with_pool()`** (lines 106-148): Replace `_check_fm_consistency(fm_clauses, disc_assumptions, solver_name, profiler)` with `oracle.is_valid(disc_e)`. Remove `fm_clauses`, `solver_name` params from `_narrow_with_pool`. Add `oracle` param.

3. **Replace `_narrow_with_sat()`** (lines 151-191) with DiscriminatingGenerator loop:
   ```python
   def _narrow_with_generator(candidates, task, remaining_bias, record_query,
                               oracle, learned_kb, generator, scope):
       for i, c_i in enumerate(candidates):
           if len(candidates) == 1:
               break
           for c_j in list(candidates[i + 1:]):
               disc_e = generator.generate(c_i, c_j, learned_kb, scope)
               if disc_e is None:
                   continue
               is_valid = oracle.is_valid(disc_e)
               record_query(disc_e, is_valid, 'findc')
               if is_valid:
                   candidates = [c for c in candidates if c != c_j]
                   remaining_bias.discard(c_j)
               if len(candidates) == 1:
                   return candidates[0]
       return candidates[0] if candidates else None
   ```

4. **Update `find_c()` body**: Pool-first hybrid flow:
   ```python
   remaining = list(rejecting)
   if example_provider is not None and not example_provider.is_exhausted():
       result = _narrow_with_pool(remaining, task, remaining_bias, record_query, oracle)
       if result is not None:
           return result
   if query_mode == 'example_first':
       result = _narrow_with_generator(remaining, task, remaining_bias, record_query,
                                        oracle, learned_kb, generator, scope)
       if result is not None:
           return result
   return remaining[0] if remaining else None
   ```

5. **Delete `_check_fm_consistency()`** (lines 194-205) — replaced by `oracle.is_valid()`.

6. **Remove dead imports**: `Solver`, `OneShotModel`, `CheckerFactory`, `get_negated_clauses`. Keep `ExampleProvider`.

7. **Update module docstring and function docstring**.

## Implementation Code (Final State — Key Sections)

Signature + pool-first hybrid flow:
```python
def find_c(e, scope, task, remaining_bias, record_query, oracle,
           learned_kb, generator, example_provider=None,
           query_mode='example_only', profiler=None):
    # ... candidate filtering (unchanged) ...
    remaining = list(rejecting)

    # Pool-first hybrid (validated: keep pool narrowing)
    if example_provider is not None and not example_provider.is_exhausted():
        result = _narrow_with_pool(remaining, task, remaining_bias,
                                    record_query, oracle, example_provider)
        if result is not None:
            return result

    if query_mode == 'example_first':
        result = _narrow_with_generator(remaining, task, remaining_bias,
                                         record_query, oracle, learned_kb,
                                         generator, scope)
        if result is not None:
            return result

    return remaining[0] if remaining else None
```

`_narrow_with_pool` updated (oracle.is_valid replaces SAT):
```python
def _narrow_with_pool(candidates, task, remaining_bias, record_query,
                       oracle, example_provider):
    # Same loop, but oracle.is_valid(disc_e) instead of _check_fm_consistency
```

`_narrow_with_generator` replaces `_narrow_with_sat`:
```python
def _narrow_with_generator(candidates, task, remaining_bias, record_query,
                            oracle, learned_kb, generator, scope):
    # Pairwise c_i/c_j loop using generator.generate() + oracle.is_valid()
```

## Todo

- [x] Update `find_c()` signature: remove `fm_clauses`, `solver_name`; add `oracle`, `learned_kb`, `generator`
- [x] Update `_narrow_with_pool()`: replace `_check_fm_consistency` with `oracle.is_valid()`; remove `fm_clauses`/`solver_name` params
- [x] Replace `_narrow_with_sat()` with `_narrow_with_generator()` using DiscriminatingGenerator
- [x] Delete `_check_fm_consistency()`
- [x] Remove dead imports (`Solver`, `OneShotModel`, `CheckerFactory`, `get_negated_clauses`)
- [x] Update docstrings
- [x] DO NOT update callers yet (Phase 4)

## Success Criteria

- `findc.py` has no `OneShotModel`, `CheckerFactory`, `Solver` imports
- `_check_fm_consistency` deleted, `_narrow_with_sat` replaced by `_narrow_with_generator`
- `_narrow_with_pool` kept (oracle.is_valid replaces SAT)
- SAT-based narrowing uses `generator.generate()` (C_L[Y]), not FM clauses
- All queries via `oracle.is_valid()` + `record_query`

## Risk Assessment

- **Low risk**: `_narrow_with_pool` kept with mechanical oracle.is_valid replacement.
- **Medium risk**: `_narrow_with_sat` → `_narrow_with_generator` changes discriminating example source from FM to C_L[Y]. More paper-faithful but less powerful early in learning (C_L small → fewer SAT solutions).
