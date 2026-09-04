# Phase 01: DRY Refactor checker.py

## Context Links
- [Parent Plan](./plan.md)
- [Analysis Report](./reports/analysis-260213-1301-checker-redundancy.md)
- [Code Standards](../../docs/code-standards.md)

## Overview
- **Priority:** P2
- **Status:** Complete
- **Description:** Remove redundant code in `checker.py` by consolidating duplicated logic into the base class

## Key Insights
- 3 checker classes share identical assumption-delta calculation
- Pickle protocol duplicated 3x with minor variations
- 2 classes have no-op `cleanup()` that should be the default
- `self.result` is dead state — never read externally

## Requirements
- Preserve all existing public API behavior
- All tests must pass after refactoring
- No new dependencies

## Architecture
No architectural changes. Refactoring is internal to the class hierarchy:
```
ConsistencyChecker (ABC)    ← Add shared logic here
├── IncrementalPySATChecker  ← Override only what differs
├── NonIncrementalPySATChecker
└── SAT4JChecker
```

## Related Code Files
- **Modify:** `explanation/operations/algorithms/checker.py`
- **Verify:** `tests/test_diagnosis.py`, `tests/test_congen.py`, `tests/test_interactive.py`

## Implementation Steps

### Step 1: Extract assumption-delta to base class (R1)
Add to `ConsistencyChecker`:
```python
def _compute_delta(self, set_c: List) -> tuple:
    set_c_set = set(set_c)
    delta = [item for item in self.assumptions if item not in set_c_set]
    return set_c, delta
```
Update each subclass `is_consistent()` to call `_compute_delta()`.

Note: Base class needs `self.assumptions` — lift storage of `set_kb`/`assumptions` to base `__init__`.

### Step 2: Consolidate pickle protocol (R2)
Move to `ConsistencyChecker`:
```python
def __getstate__(self):
    state = self.__dict__.copy()
    state['profiler'] = None
    return state

def __setstate__(self, state):
    self.__dict__.update(state)
    if self.profiler is None:
        self.profiler = get_global_profiler()
```
`IncrementalPySATChecker` overrides to also exclude/recreate solver.
Remove `__getstate__`/`__setstate__` from NonIncremental and SAT4J.

### Step 3: Default no-op cleanup (R3)
Change base class `cleanup()` from `@abstractmethod` to:
```python
def cleanup(self) -> None:
    pass
```
Remove from NonIncremental and SAT4J. Keep override in Incremental.

### Step 4: Remove dead `self.result` (R4)
- Remove `self.result = False` from base `__init__`
- In each `is_consistent()`, use local variable and return directly
- Verify no external access (already confirmed via grep)

### Step 5: Trim docstrings (R6)
- Reduce module docstring from 87 lines to ~15 lines
- Remove subclass method docstrings that duplicate abstract definitions
- Keep only non-obvious documentation

### Step 6: Run tests
```bash
PYTHONPATH=. pytest tests/test_diagnosis.py tests/test_congen.py tests/test_interactive.py -v
```

## Todo List
- [x] Extract `_compute_delta()` to base class
- [x] Lift `set_kb`/`assumptions` storage to base `__init__`
- [x] Consolidate pickle protocol to base class
- [x] Change `cleanup()` to default no-op
- [x] Remove dead `self.result` field
- [x] Trim docstrings
- [x] Run full test suite

## Success Criteria
- All existing tests pass
- No public API changes
- File reduced by ~80-100 lines
- Each piece of logic exists in exactly one place

## Risk Assessment
- **Low risk:** Pure internal refactoring, no API changes
- **Mitigation:** Step 1 (delta extraction) requires lifting `assumptions` to base — verify all constructors pass it via `super().__init__`

## Security Considerations
- None — internal refactoring only

## Next Steps
- Run tests after each step to catch regressions early
- Consider whether R5 (constructor field consolidation) is worth the added abstraction
