# Code Review: QueryProvider ConsistencyChecker Refactor

**Date**: 2026-02-28
**Scope**: Replace ad-hoc PySAT solver usage in QueryProvider with ConsistencyChecker DI; add `get_model()` to ConsistencyChecker ABC
**Status**: All 62 QuAcq tests pass. Contains one bug and several cleanup items.

## Scope

- **Files**: 8 modified (`checker.py`, `query_provider.py`, `quacq.py`, `quacq_runner.py`, `quacq_model.py`, `quacq_model_builder.py`, `task_preparation.py`, `test_quacq.py`)
- **LOC**: ~791 across diffs (381 added, 410 removed)
- **Focus**: Recent changes (last 2 commits + unstaged)
- **Scout findings**: `field()` sentinel bug, `set_b[0]` crash, stale docs, empty test class, commented-out dead code

## Overall Assessment

Good DRY refactoring. Eliminates duplicate PySAT solver lifecycle management in QueryProvider by delegating to the shared ConsistencyChecker. The `get_model()` abstraction is clean and correctly handles all three checker implementations (persistent solver, cached model, parsed SAT4J output). Method signatures simplified from 8-9 params to 3-5 params. All 62 tests pass.

However, there is a **critical bug** (`field()` sentinel in non-dataclass), a **crash risk** (`set_b[0]` with no guard), commented-out dead code in 6 locations, and stale documentation examples.

## Critical Issues

### 1. Bug: `field()` used in non-dataclass `__init__` (`/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py:53-54`)

`QuAcqModel` is a regular class, not a `@dataclass`. Using `field(default_factory=dict)` assigns a `dataclasses.Field` sentinel object instead of a `dict`:

```python
# BUG -- returns Field object, not dict
self.pos_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
self.neg_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
```

Confirmed via test: `type(m.pos_assignment_to_assumption)` returns `<class 'dataclasses.Field'>`. Calling `config_to_assumptions()` without the builder crashes: `TypeError: argument of type 'Field' is not iterable`.

**Why it passes tests**: The builder (`quacq_model_builder.py:73-74`) overwrites these with actual dicts before any code reads them. But any code path constructing `QuAcqModel()` directly and calling `config_to_assumptions()` will crash.

**Fix**:
```python
self.pos_assignment_to_assumption: Dict[str, int] = {}
self.neg_assignment_to_assumption: Dict[str, int] = {}
```

Also remove unused `from dataclasses import field` at line 10.

### 2. `set_b[0]` IndexError risk (`/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py:197`)

```python
pruned = self._prune_rejecting_constraints(
    remaining_bias, query, set_b[0])
```

If `set_b` is empty, this crashes with `IndexError`. The old code guarded this with `if self.model and root_assumption is not None`, and the runner passed `root_assumption=task.set_b[0] if task.set_b else None`. The guard was removed and the legacy fallback is now commented out.

In practice, `set_b` always has the root BG assumption from oracle, but the defensive check was dropped. The test `test_quacq_empty_bias` passes only because `remaining_bias` is empty so the `while remaining_bias` loop never enters.

**Fix** -- add assertion at `learn()` start:
```python
assert set_b, "set_b must not be empty (root BG assumption required)"
```

## High Priority

### 3. Condition 2 semantics changed from boolean eval to SAT (plan deviation)

Plan phase-02 states: "Condition 2 (`violates_clauses`) stays as boolean eval (faster than SAT)". The implementation replaces it with `checker.is_consistent([c_id] + config_assumptions)` (`query_provider.py:95`).

Semantic difference:
- **Boolean eval** (old): Checks raw clause literals violated by assignment
- **SAT check** (new): Checks if constraint assumption + config assumptions are inconsistent within full KB+BG

The SAT approach is more correct (catches implied violations via BG constraints) but slower (full solver call per constraint per pool example). If intentional, acknowledge in plan. If not, revert to boolean eval and restore `constraint_clauses`/`feature_ids` params on `generate_from_pool`.

### 4. Commented-out dead code in 6 locations

| File | Lines | Content |
|------|-------|---------|
| `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` | 195-200 | Legacy pruning fallback |
| `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py` | 87-93 | `get_cf()` method |
| `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py` | 98 | Old `get_kb()` return |
| `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq_model.py` | 113 | Old `get_assumptions()` return |
| `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py` | 63-66 | Part 4 dataclass fields |
| `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/task_preparation.py` | 106-107 | Assignment dict copy to model |

Keeping commented code violates KISS/DRY. Git history preserves old code.

### 5. Stale docs reference old QueryProvider API

Two documentation files still show the old API:

- `/Users/manleviet/Development/GitHub/AcqMSS/docs/quacq.md:349` -- `QueryProvider(solver_name='glucose4')` (removed param)
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/code-standards.md:202` -- `QueryProvider()` with no checker/model, old `QuAcq.for_oracle()` signature missing checker param

The `__init__.py` docstring (`/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/__init__.py:28-43`) also shows the old `learn()` signature with removed params `background_clauses`, `negated_clauses`.

## Medium Priority

### 6. `quacq.py` at 318 lines exceeds 200-line Python threshold

Per code standards, Python files should be ~200 lines. `QuAcq.learn()` alone is ~120 lines. Consider extracting `_prune_rejecting_constraints` and `_prune_rejecting_constraints_legacy` to a separate module, or moving `QuAcqResult` to its own file.

### 7. FindScope/FindC re-instantiated per loop iteration (`/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py:211,225`)

```python
find_scope = FindScope(self.oracle)
...
find_c = FindC(self.oracle, self.discriminating_generator)
```

These were previously created once in `__init__` (removed in unstaged diff). Now they're created fresh on every negative answer. While functional, this is wasteful for stateless classes. Move creation before the loop or back to `__init__`.

### 8. Empty test class `TestQuAcqTaskPart4` (`/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py:805-807`)

All 3 tests were removed but the class shell remains:
```python
class TestQuAcqTaskPart4:
    """Tests for QuAcqTask Part 4 fields."""
```

Either delete the class or add replacement tests for the new Part 4 data flow.

### 9. `get_model()` null guard is good but defensive coding pattern should be consistent

The `generate_from_sat` method correctly guards `get_model()` returning None (`query_provider.py:128-130`). This is good defensive practice. However, `generate_from_pool` does not call `get_model()` at all -- it only uses `is_consistent()` for violation checks. This is correct but worth noting the asymmetry is intentional (pool generates configs from the pool, not from SAT models).

### 10. `NonIncrementalPySATChecker._cached_model` not reset in `copy()`

```python
def copy(self):
    return NonIncrementalPySATChecker(
        list(self.set_kb), list(self.assumptions),
        self.solver_name, self.profiler
    )
```

The copy creates a new instance via `__init__`, which initializes `_cached_model = None`. This is correct, but the original instance's cached model is not copied. If `copy()` is called mid-computation and the copy is expected to have the same model state, this could be an issue. Currently no code path does this.

## Low Priority

### 11. `example_generators/__init__.py` lazy import comment is stale

```python
# QueryProvider is lazily imported to avoid circular dependency:
# example_generators/__init__ -> query_provider -> algorithms.quacq.sat_utils
```

The `query_provider.py` no longer imports `algorithms.quacq.sat_utils`. The lazy import may no longer be needed. Verify and simplify if safe.

## Positive Observations

- **Clean abstraction**: `get_model()` on ConsistencyChecker well-designed with clear semantics per implementation
- **NonIncremental caching**: Correctly caches model before `solver.delete()` -- handles lifecycle elegantly
- **SAT4J parser**: `_parse_model()` correctly handles multi-line "v" output and filters trailing 0
- **Signature simplification**: QueryProvider went from 8-9 params per method to 3-5, much cleaner
- **DRY achieved**: No more ad-hoc `Solver()` creation in QueryProvider; all SAT through checker
- **Tests comprehensive**: 62 QuAcq tests pass; pool filtering test updated to use real FM data
- **TYPE_CHECKING guard**: Correctly avoids circular imports for ConsistencyChecker/QuAcqModel
- **Defensive get_model()**: Null guard in `generate_from_sat` prevents crash when solver returns no model

## Recommended Actions (priority order)

1. **Fix bug**: Replace `field(default_factory=dict)` with `= {}` in `quacq_model.py:53-54`, remove `field` import
2. **Guard `set_b[0]`**: Add assertion or conditional check before accessing `set_b[0]` in `quacq.py:197`
3. **Decide Condition 2 semantics**: If SAT-based is intentional, update plan; if not, revert to boolean eval
4. **Remove commented-out code**: Clean up all 6 locations listed above
5. **Update stale docs**: Fix `quacq.md`, `code-standards.md`, and `__init__.py` docstring for new API signatures
6. **Delete empty test class**: Remove `TestQuAcqTaskPart4` or add replacement tests
7. **Move FindScope/FindC creation**: Before the loop or back to `__init__`
8. **Check lazy import necessity**: `example_generators/__init__.py` may no longer need lazy import

## Metrics

- **Type Coverage**: Good -- TYPE_CHECKING imports, Optional annotations, typed params
- **Test Coverage**: 62 QuAcq-specific tests pass; Part 4 tests reduced (3 removed, 0 added)
- **Linting Issues**: 1 confirmed (unused `field` import after bug fix)

## Unresolved Questions

1. Was the Condition 2 change from boolean eval to SAT intentional? Plan explicitly says "stays as boolean eval" but implementation uses SAT. Performance impact for large pools could be significant.
2. Should `_prune_rejecting_constraints_legacy` be deleted entirely, or is there a case where `self.model` is `None`?
3. Part 4 data moved from `QuAcqTask` dataclass fields to inline in `set_kb`/`assumptions`. Should commented-out Part 4 fields be fully removed or kept for documentation?
