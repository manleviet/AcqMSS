# Code Review: checker.py DRY Refactoring

**Reviewer**: code-reviewer (a79f276)
**Date**: 2026-02-13
**File**: `explanation/operations/algorithms/checker.py`
**LOC**: 494 -> 231 (53% reduction)

## Overall Assessment

Clean, well-executed DRY refactoring. All 246 core tests pass. Pickle roundtrip verified manually. No behavioral regressions detected. One **critical behavioral change** in `NonIncrementalPySATChecker` was intentional and correct -- it now uses the same assumption-based protocol as `IncrementalPySATChecker`, which aligns with all current call sites.

## Focus Area 1: Behavioral Changes That Could Break Existing Functionality

### NonIncrementalPySATChecker -- MAJOR semantic change (intentional, correct)

**Old behavior**: Constructor took `(solver_name, profiler)`. `is_consistent(set_c)` expected `set_c` to be a list-of-lists (CNF clauses), flattened them, created a fresh solver with that CNF, and called `solver.solve()` with no assumptions.

**New behavior**: Constructor takes `(set_kb, assumptions, solver_name, profiler)`. `is_consistent(set_c)` now uses `_compute_delta()` to compute enabled/disabled assumptions, creates a fresh solver bootstrapped with `self.set_kb`, and solves with assumption literals.

**Risk assessment**: LOW. All current call sites already pass `(set_kb, assumptions, solver_name, profiler)`:
- `tests/test_congen.py` lines 106-108, 123-125
- `apps/run_congen.py` lines 151-153, 168-170
- `acqmss/eval/congen_runner.py` lines 174-176, 191-193
- `acqmss/algorithms/interactive/quacq.py` line 432-433
- `CheckerFactory.create_from_model()` now passes `model.get_kb(), model.get_assumptions()`

The old constructor signature `NonIncrementalPySATChecker(solver_name, profiler)` appears nowhere in the current codebase. This confirms the callers were already updated before this refactoring.

### SAT4JChecker -- MAJOR semantic change (intentional, correct)

**Old behavior**: Constructor took `(jar_path, profiler, timeout)`. `is_consistent(set_c)` expected a list-of-lists, flattened them into a single CNF, wrote to file.

**New behavior**: Constructor takes `(set_kb, assumptions, jar_path, profiler, timeout)`. `is_consistent(set_c)` uses `_compute_delta()` to partition assumptions, converts them to unit clauses `[[a]]` / `[[-a]]`, and extends `self.set_kb` with those.

**Risk assessment**: LOW. `CheckerFactory.create_sat4jchecker()` was already updated to accept and forward `set_kb` and `assumptions`. Both SAT4J callers (`pysat_conflict_sat4j.py:55`, `pysat_diagnosis_sat4j.py:54`) pass `set_kb=model.get_kb(), assumptions=model.get_assumptions()`.

### Removed `self.result` field (R4)

**Old**: Base class set `self.result = False`; subclass `is_consistent()` assigned to `self.result` then returned it.

**New**: Local `result` variable, returned directly.

**Risk assessment**: NONE. Grep for `checker.result` across the entire codebase returns zero matches. No external code ever read this field.

## Focus Area 2: Pickle Protocol Chain

### IncrementalPySATChecker.__getstate__ / __setstate__

```python
def __getstate__(self):
    state = super().__getstate__()   # sets profiler=None
    if 'solver' in state:
        state['solver'] = None       # strips unpicklable C extension
    return state

def __setstate__(self, state):
    super().__setstate__(state)      # restores profiler
    if hasattr(self, 'solver_name') and hasattr(self, 'set_kb'):
        self.solver = Solver(...)    # recreates solver
```

**Verdict**: CORRECT. The chain works properly:
1. `super().__getstate__()` creates `dict.copy()`, nulls profiler -- child then nulls solver
2. `super().__setstate__()` calls `__dict__.update(state)`, restores profiler -- child then recreates solver

Manually verified with `pickle.dumps/loads` roundtrip: solver and profiler both restored correctly.

### NonIncrementalPySATChecker and SAT4JChecker

These inherit `__getstate__`/`__setstate__` from base class unchanged. No solver to strip, no solver to recreate. Pickle roundtrip verified.

## Focus Area 3: _compute_delta() and SAT4J Unit Clause Wrapping

### Base class _compute_delta() (line 29-33)

```python
def _compute_delta(self, set_c: List) -> tuple:
    set_c_set = set(set_c)
    delta = [item for item in self.assumptions if item not in set_c_set]
    return set_c, delta
```

This method returns raw assumption IDs (integers). It does NOT do unit-clause wrapping.

### SAT4JChecker.is_consistent() (line 173-175)

```python
enabled, disabled = self._compute_delta(set_c)
assumption_clauses = [[a] for a in enabled] + [[-a] for a in disabled]
```

**Verdict**: CORRECT. The unit-clause wrapping `[[a]]` happens in `SAT4JChecker.is_consistent()`, NOT in `_compute_delta()`. The base method returns plain ints; SAT4J wraps them into unit clauses; PySAT checkers use them as solver assumptions. Clean separation of concerns.

### Performance improvement

The old `IncrementalPySATChecker.is_consistent()` used `item not in set_c` (O(n*m) for list). The new `_compute_delta()` uses `set(set_c)` (O(n+m)). This is a minor but real improvement for large assumption sets.

## Focus Area 4: Missing self.assumptions References

All three concrete classes set `self.assumptions` in their constructors:
- `IncrementalPySATChecker.__init__` line 85
- `NonIncrementalPySATChecker.__init__` line 131
- `SAT4JChecker.__init__` line 164 (`self.assumptions = assumptions or []`)

The base class `_compute_delta()` references `self.assumptions` (line 32). Since `_compute_delta()` is only called from `is_consistent()` on concrete instances, `self.assumptions` will always be present.

**Verdict**: NO RISK. Cannot hit `AttributeError` unless someone instantiates a custom subclass without setting `self.assumptions`.

**Minor suggestion**: Could add `self.assumptions: List[int]` as a class-level annotation on the ABC to make the contract explicit, but this is cosmetic.

## Additional Observations

### Positive

- `cleanup()` changed from `@abstractmethod` to default no-op: eliminates empty `pass` implementations in NonIncremental and SAT4J. Good -- these classes have no persistent state to release.
- `IncrementalPySATChecker.cleanup()` uses defensive `hasattr(self, 'solver')` check, safe against partial init failures.
- `copy()` in NonIncremental and SAT4J now deep-copies `set_kb` and `assumptions` with `list(...)`, preventing shared-state bugs in multiprocessing. The old `NonIncrementalPySATChecker.copy()` did not copy these because it did not have them.
- Docstrings trimmed appropriately. Module docstring from 87 lines to 8 lines. Class/method docstrings are concise but sufficient.

### The One Test Failure

`test_evaluate_real_fm_7` fails with `FileNotFoundError` for a missing result JSON file. This is unrelated to the checker refactoring -- it is a missing test fixture.

## Severity Summary

| Severity | Count | Details |
|----------|-------|---------|
| Critical | 0 | -- |
| High | 0 | -- |
| Medium | 0 | -- |
| Low | 1 | Consider adding `assumptions` type annotation to ABC |

## Metrics

- **Tests**: 246/246 passed (excluding unrelated fixture issue)
- **Pickle**: Roundtrip verified for IncrementalPySATChecker, NonIncrementalPySATChecker
- **LOC reduction**: 53% (494 -> 231)
- **Behavioral correctness**: Confirmed via tests + manual verification

## Recommended Actions

1. **(Optional, Low)** Add `assumptions: List[int]` as a class-level field annotation on `ConsistencyChecker` to document the contract that all subclasses must set it.

## Unresolved Questions

None.
