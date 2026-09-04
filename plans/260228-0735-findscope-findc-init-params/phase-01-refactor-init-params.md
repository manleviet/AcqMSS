# Phase 01: Refactor FindScope & FindC Init Params

## Context
- Parent: [plan.md](plan.md)
- Docs: [quacq.md](../../docs/quacq.md)

## Overview
- **Priority:** P3
- **Status:** Complete
- **Description:** Move `record_query` and `root_assumption` from method params to `__init__` in FindScope and FindC

## Key Insights
- `record_query` — closure defined once in `QuAcq.run()`, never reassigned
- `root_assumption` — from `set_b[0]`, computed per-iteration but instances also created per-iteration
- Both threaded through recursive calls without mutation — pure noise in signatures

## Requirements
- Remove `record_query` and `root_assumption` from `run()`, `_prune_rejecting_partial()`, `_narrow_with_generator()` signatures
- Store as `self.record_query` and `self.root_assumption` via `__init__`
- Update QuAcq caller to pass at construction time

## Related Code Files

### Modify
- `conacq/algorithms/quacq/findscope.py` — FindScope class (lines 17-94)
- `conacq/algorithms/quacq/findc.py` — FindC class (lines 20-140)
- `conacq/algorithms/quacq/quacq.py` — QuAcq caller (lines 197-220)

## Implementation Steps

### Step 1: FindScope (`findscope.py`)

1. `__init__`: Add `record_query` and `root_assumption` params, store as `self.`
   ```python
   def __init__(self, oracle, checker, model, record_query, root_assumption: int):
       self.oracle = oracle
       self.checker = checker
       self.model = model
       self.record_query = record_query
       self.root_assumption = root_assumption
   ```

2. `run()`: Remove `record_query` and `root_assumption` from signature. Replace usages:
   - `record_query(partial, ...)` → `self.record_query(partial, ...)`
   - `self._prune_rejecting_partial(remaining_bias, e, R, root_assumption)` → `self._prune_rejecting_partial(remaining_bias, e, R)`
   - Recursive `self.run(e, R|Y1, Y2, True, remaining_bias, record_query, root_assumption)` → `self.run(e, R|Y1, Y2, True, remaining_bias)`
   - Same for second recursive call

3. `_prune_rejecting_partial()`: Remove `root_assumption` param, use `self.root_assumption`

### Step 2: FindC (`findc.py`)

1. `__init__`: Add `record_query` and `root_assumption` params
   ```python
   def __init__(self, oracle, checker, model, generator, record_query, root_assumption: int):
       ...
       self.record_query = record_query
       self.root_assumption = root_assumption
   ```

2. `run()`: Remove `record_query` and `root_assumption` from signature. Replace:
   - `base = [root_assumption] + e_assumptions` → `base = [self.root_assumption] + e_assumptions`
   - `self._narrow_with_generator(remaining, remaining_bias, record_query, ...)` → `self._narrow_with_generator(remaining, remaining_bias, ...)`

3. `_narrow_with_generator()`: Remove `record_query` param, use `self.record_query`

### Step 3: QuAcq caller (`quacq.py`)

1. Update FindScope construction (around line 197):
   ```python
   find_scope = FindScope(self.oracle, self.checker, self.model,
                          record_query, set_b[0])
   ```

2. Update FindScope.run() call — remove `record_query` and `root_assumption` kwargs

3. Update FindC construction (around line 210):
   ```python
   find_c = FindC(self.oracle, self.checker, self.model,
                  self.discriminating_generator, record_query, set_b[0])
   ```

4. Update FindC.run() call — remove `record_query` and `root_assumption` kwargs

## Todo List
- [x] Update FindScope.__init__ with new params
- [x] Simplify FindScope.run() signature
- [x] Simplify FindScope._prune_rejecting_partial() signature
- [x] Update FindC.__init__ with new params
- [x] Simplify FindC.run() signature
- [x] Simplify FindC._narrow_with_generator() signature
- [x] Update QuAcq caller to pass params at construction
- [x] Run tests: `PYTHONPATH=. pytest tests/ -v` — All 356 tests pass

## Success Criteria
- All existing tests pass
- No `record_query` or `root_assumption` in any `run()` / helper method signatures
- Only appear in `__init__` signatures and `self.` references

## Risk Assessment
- **Low risk** — pure mechanical refactoring, no logic changes
- Tests cover FindScope/FindC behavior already

## Next Steps
- Run tests to verify
- Code review
