# Code Review: QueryProvider ConsistencyChecker Refactor

**Date**: 2026-02-28
**Scope**: Replace ad-hoc PySAT solver usage in QueryProvider with ConsistencyChecker DI
**Status**: All 356 tests pass. Contains one bug and several cleanup items.

## Scope

- **Files**: 8 modified (`checker.py`, `query_provider.py`, `quacq.py`, `quacq_runner.py`, `quacq_model.py`, `quacq_model_builder.py`, `task_preparation.py`, `test_quacq.py`)
- **LOC**: ~2161 total in changed files; net diff -18 lines (160 added, 178 removed per last commit; additional unstaged changes)
- **Focus**: Recent changes (committed + unstaged)

## Overall Assessment

Good DRY refactoring -- eliminates duplicate PySAT solver lifecycle management in QueryProvider by delegating to the shared ConsistencyChecker. The `get_model()` abstraction is clean and correctly handles all three checker implementations. Signatures simplified significantly. However, there is a **critical bug** in `QuAcqModel.__init__`, commented-out dead code in several files, and a plan deviation on Condition 2 semantics that needs acknowledgment.

## Critical Issues

### 1. Bug: `field()` used in non-dataclass `__init__` (quacq_model.py:53-54)

`QuAcqModel` is a regular class, not a `@dataclass`. Using `field(default_factory=dict)` in `__init__` assigns a `dataclasses.Field` object instead of a `dict`:

```python
# quacq_model.py:53-54 -- BUG
self.pos_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
self.neg_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
```

Confirmed: `type(m.pos_assignment_to_assumption)` returns `<class 'dataclasses.Field'>` and dict operations (`m.pos_assignment_to_assumption['x'] = 1`) raise `TypeError`.

**Why it passes tests**: The builder (`quacq_model_builder.py:72-73`) overwrites these fields with actual dicts before any code reads them. But any code path that constructs `QuAcqModel()` directly and calls `config_to_assumptions()` without going through the builder will crash.

**Fix**:
```python
self.pos_assignment_to_assumption: Dict[str, int] = {}
self.neg_assignment_to_assumption: Dict[str, int] = {}
```

Also remove the unused `from dataclasses import field` import at line 9.

### 2. `set_b[0]` IndexError risk (quacq.py:197)

```python
pruned = self._prune_rejecting_constraints(
    remaining_bias, query, set_b[0])
```

If `set_b` is empty, this crashes with `IndexError`. The old code guarded this with `if self.model and root_assumption is not None`, and the runner passed `root_assumption=task.set_b[0] if task.set_b else None`. The guard is now commented out.

In practice, `set_b` always has the root BG assumption from oracle, but the defense was removed. The commented-out legacy fallback (lines 199-204) should either be fully removed or the guard restored.

**Fix**: Either restore guard or add assertion:
```python
assert set_b, "set_b must not be empty (root BG assumption required)"
```

## High Priority

### 3. Condition 2 changed from boolean eval to SAT (plan deviation)

Plan phase-02 explicitly states: "Condition 2 (`violates_clauses`) stays as boolean eval (faster than SAT)". The unstaged changes replace it with `checker.is_consistent([c_id] + config_assumptions)` (query_provider.py:97). This is semantically different:

- **Boolean eval**: Checks if the raw clause literals are violated by the assignment
- **SAT check**: Checks if the constraint assumption + config assumptions are inconsistent within the full KB+BG solver

The SAT approach is more correct (catches implied violations via BG constraints) but slower (full solver call per constraint per pool example). If intentional, update the plan. If unintentional, revert to boolean eval.

### 4. `generate_from_pool` missing `constraint_clauses`/`feature_ids` params

The plan specifies `generate_from_pool(remaining_bias, learned_kb, set_b, constraint_clauses, feature_ids)` but the actual signature is just `generate_from_pool(remaining_bias, learned_kb, set_b)`. This is consistent with the Condition 2 change (SAT doesn't need raw clauses), but means `generate()` and the `example_only` mode in `quacq.py` also lost these params. If Condition 2 reverts to boolean eval, these params must be restored.

### 5. Commented-out dead code in multiple files

Several files have commented-out code that should be fully removed or restored:

| File | Lines | Content |
|------|-------|---------|
| `quacq.py` | 199-204 | Legacy pruning fallback |
| `quacq_model.py` | 87-93 | `get_cf()` method |
| `quacq_model.py` | 98 | Old `get_kb()` return |
| `quacq_model.py` | 113 | Old `get_assumptions()` return |
| `task_preparation.py` | 63-66 | Part 4 dataclass fields |
| `task_preparation.py` | 106-107 | Assignment dict copy to model |

Keeping commented code violates KISS/DRY. Git history preserves the old code.

## Medium Priority

### 6. `quacq.py` at 317 lines exceeds 200-line Python threshold

Per code standards, Python files should be ~200 lines. `QuAcq.learn()` alone is ~120 lines. Consider extracting `_prune_rejecting_constraints` and `_prune_rejecting_constraints_legacy` to a separate module, or moving `QuAcqResult` to its own file.

### 7. FindScope/FindC re-instantiated per loop iteration (quacq.py:211,225)

```python
find_scope = FindScope(self.oracle)
...
find_c = FindC(self.oracle, self.discriminating_generator)
```

Previously these were created once in `__init__`. Now they're created fresh on every negative answer. While functional, this is wasteful for stateless classes. Move back to `__init__` or create once before the loop.

### 8. Empty test class `TestQuAcqTaskPart4` (test_quacq.py:806-807)

All 3 tests were removed but the class shell remains:
```python
class TestQuAcqTaskPart4:
    """Tests for QuAcqTask Part 4 fields."""
```

Either delete the class or add replacement tests for the new Part 4 data flow (Part 4 fields moved from QuAcqTask to being inlined in `set_kb`/`assumptions`).

### 9. `get_model()` could return `None` after successful `is_consistent()` (query_provider.py:129)

If `is_consistent()` returns `True` but `get_model()` returns `None` (race condition with cleanup, or solver invalidation), `_model_to_config(None, id_to_feature)` crashes. Add a guard:

```python
model_lits = self.checker.get_model()
if model_lits is None:
    logging.warning('No model available after SAT for constraint %s', c_id)
    continue
```

### 10. `NonIncrementalPySATChecker` type annotation mismatch

`_cached_model` is typed `Optional[List[int]]` but `solver.get_model()` returns `list | None`. Technically compatible but explicit cast would be cleaner.

## Low Priority

### 11. `solver_name` still stored on QueryProvider but no longer used

QueryProvider no longer creates solvers directly, so `self.solver_name` (line 45) is unused. Remove it.

### 12. `import field` in quacq_model.py no longer needed after bug fix

`from dataclasses import field` at line 9 was added for the buggy `field()` usage. After fixing to `= {}`, this import becomes dead.

## Positive Observations

- **Clean abstraction**: `get_model()` on ConsistencyChecker is well-designed with clear semantics per implementation (persistent solver vs. cached model vs. parsed output)
- **NonIncremental caching**: Correctly caches model before `solver.delete()` -- handles the lifecycle issue elegantly
- **SAT4J parser**: `_parse_model()` correctly handles multi-line "v" output and filters trailing 0
- **Signature simplification**: QueryProvider went from 8-9 params per method to 3-5, much cleaner
- **DRY achieved**: No more ad-hoc `Solver()` creation in QueryProvider; all SAT goes through checker
- **Tests comprehensive**: 62 QuAcq tests pass, 356 total; pool filtering test updated to use real FM data
- **TYPE_CHECKING guard**: Correctly avoids circular imports for ConsistencyChecker/QuAcqModel

## Recommended Actions (priority order)

1. **Fix bug**: Replace `field(default_factory=dict)` with `= {}` in `quacq_model.py:53-54`, remove `field` import
2. **Decide Condition 2 semantics**: If SAT-based is intentional, update plan; if not, revert to boolean eval and restore `constraint_clauses`/`feature_ids` params
3. **Guard `set_b[0]`**: Add assertion or conditional check before accessing `set_b[0]`
4. **Remove commented-out code**: Clean up all 6 locations listed above
5. **Delete empty test class**: Remove `TestQuAcqTaskPart4` or add replacement tests
6. **Guard `get_model()` return**: Add None check before passing to `_model_to_config`
7. **Move FindScope/FindC creation**: Back to `__init__` or before the loop
8. **Remove unused `solver_name`** from QueryProvider

## Metrics

- **Type Coverage**: Good -- TYPE_CHECKING imports, Optional annotations, typed params
- **Test Coverage**: 62 QuAcq-specific tests pass; Part 4 tests reduced (3 removed, 0 added)
- **Linting Issues**: 1 (unused `field` import)

## Unresolved Questions

1. Was the Condition 2 change from boolean eval to SAT intentional? The plan explicitly says "stays as boolean eval" but implementation uses SAT. Performance impact for large pools could be significant.
2. Should `_prune_rejecting_constraints_legacy` be deleted entirely, or is there a case where `self.model` is `None`?
3. The Part 4 data was moved from `QuAcqTask` dataclass fields to being inlined into `set_kb`/`assumptions` during preparation. Should `QuAcqTask` Part 4 fields be fully removed (currently commented out) or kept for documentation?
