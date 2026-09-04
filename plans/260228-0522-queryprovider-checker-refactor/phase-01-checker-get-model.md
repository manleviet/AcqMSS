---
title: "Phase 1: Add get_model() to ConsistencyChecker"
status: complete
priority: P1
effort: 20m
created: 2026-02-28
completed: 2026-02-28
---

# Phase 1: Add get_model() to ConsistencyChecker

## Context Links

- [Brainstorm](../reports/brainstorm-260228-0522-queryprovider-checker-refactor.md)
- Source: `explanation/operations/algorithms/checker.py`

## Overview

- **Priority**: P1 (blocks Phase 2)
- **Status**: complete
- Add abstract `get_model()` to `ConsistencyChecker` ABC
- Implement in all 3 checker implementations

## Key Insights

- IncrementalPySATChecker: solver persists, `solver.get_model()` available after solve
- NonIncrementalPySATChecker: solver deleted after each `is_consistent()`, must cache model
- SAT4JChecker: parse model from subprocess stdout, cache it
- Model only valid after `is_consistent()` returns True

## Requirements

- `get_model() -> Optional[List[int]]` returns SAT assignment or None
- Must return None if last `is_consistent()` returned False or never called
- Thread-safe not required (single-threaded usage)

## Architecture

```
ConsistencyChecker (ABC)
  + get_model() -> Optional[List[int]]   # NEW abstract
  |
  ├─ IncrementalPySATChecker
  │    get_model(): self.solver.get_model()
  │
  ├─ NonIncrementalPySATChecker
  │    is_consistent(): cache model before solver.delete()
  │    get_model(): return self._cached_model
  │
  └─ SAT4JChecker
       is_consistent(): parse "v ..." lines, cache model
       get_model(): return self._cached_model
```

## Related Code Files

- **Modify**: `explanation/operations/algorithms/checker.py`

## Implementation Steps

### 1. Add abstract method to ConsistencyChecker (line ~52)

**After:**
```python
@abstractmethod
def get_model(self) -> Optional[List[int]]:
    """Return SAT model from last successful is_consistent() call.

    Only valid after is_consistent() returned True.
    Returns None if last check was UNSAT or no check performed.
    """
    pass
```

Add `Optional` to typing imports (already has `List`).

### 2. IncrementalPySATChecker.get_model()

**Add after `is_consistent()` (line ~113):**
```python
def get_model(self) -> Optional[List[int]]:
    """Return model from persistent solver."""
    if self.solver is None:
        return None
    return self.solver.get_model()
```

No caching needed — solver persists and tracks last solve result.

### 3. NonIncrementalPySATChecker — cache + get_model()

**Modify `is_consistent()` to cache model before `solver.delete()`:**

Before:
```python
result = solver.solve(assumptions=final_assumptions)
self.profiler.record_time("solver_time", solver.time())
solver.delete()
return result
```

After:
```python
result = solver.solve(assumptions=final_assumptions)
self.profiler.record_time("solver_time", solver.time())
self._cached_model = solver.get_model() if result else None
solver.delete()
return result
```

**Add `__init__` initialization:**
```python
self._cached_model: Optional[List[int]] = None
```

**Add get_model():**
```python
def get_model(self) -> Optional[List[int]]:
    """Return cached model from last is_consistent() call."""
    return self._cached_model
```

### 4. SAT4JChecker — parse model + get_model()

**Add `__init__` initialization:**
```python
self._cached_model: Optional[List[int]] = None
```

**Modify `is_consistent()` to parse model from stdout:**

After `output = result.stdout`, add:
```python
self._cached_model = self._parse_model(output)
```

**Add parser:**
```python
def _parse_model(self, output: str) -> Optional[List[int]]:
    """Parse SAT model from SAT4J output (v lines)."""
    if "UNSATISFIABLE" in output or "SATISFIABLE" not in output:
        return None
    model = []
    for line in output.splitlines():
        if line.startswith('v '):
            model.extend(int(x) for x in line[2:].split() if x != '0')
    return model if model else None

def get_model(self) -> Optional[List[int]]:
    """Return cached model from last is_consistent() call."""
    return self._cached_model
```

## Todo List

- [ ] Add abstract `get_model()` to ConsistencyChecker
- [ ] Implement in IncrementalPySATChecker (delegate to solver)
- [ ] Implement in NonIncrementalPySATChecker (cache before delete)
- [ ] Implement in SAT4JChecker (parse stdout, cache)
- [ ] Add `Optional` to imports if missing
- [ ] Run: `PYTHONPATH=. pytest tests/test_diagnosis.py -v`

## Success Criteria

- All existing tests pass unchanged
- `get_model()` returns List[int] after SAT, None after UNSAT
- NonIncremental caches model before solver deletion

## Risk Assessment

- **Low**: PySAT `solver.get_model()` well-documented
- **Medium**: SAT4J output format may vary — parser must handle edge cases

## Security Considerations

N/A — internal solver interface.

## Next Steps

Phase 2: Use `checker.get_model()` in QueryProvider's `generate_from_sat()`.
