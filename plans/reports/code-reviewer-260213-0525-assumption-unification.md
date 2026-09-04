# Code Review: Assumption-Based Solving Unification

**Date:** 2026-02-13
**Scope:** Unify assumption-based solving across Incremental, NonIncremental, SAT4J checkers
**Files reviewed:** 18 Python files, 5201 LOC across touched files
**Net change:** +433 / -596 lines (163 lines removed)

## Overall Assessment

Strong refactoring that successfully eliminates the dual-path (incremental vs non-incremental) branching across the entire codebase. The unification is architecturally sound: all checker modes now share the same assumption-based data representation (`List[int]` IDs everywhere), differing only in solver lifecycle. The 288/290 test pass rate confirms correctness; the 2 failures are pre-existing `FileNotFoundError` from moved data files.

## Critical Issues

None.

## High Priority

### H1. Performance: Linear scan in `is_consistent` delta computation

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/explanation/operations/algorithms/checker.py`, lines 219, 315, 402

```python
delta = [item for item in self.assumptions if item not in set_c]
```

`item not in set_c` is O(n) on a list. When `assumptions` and `set_c` are large, this becomes O(n*m). Converting `set_c` to a `set` first would make it O(n+m).

**Fix:**
```python
set_c_set = set(set_c)
delta = [item for item in self.assumptions if item not in set_c_set]
```

This applies to all three checker implementations (IncrementalPySATChecker, NonIncrementalPySATChecker, SAT4JChecker).

### H2. `add_clause`/`add_assumption` are no-ops on base class

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/explanation/operations/algorithms/checker.py`, lines 155-165

```python
def add_clause(self, clause: List[int]) -> None:
    pass  # <-- silently does nothing

def add_assumption(self, assumption_id: int) -> None:
    pass  # <-- silently does nothing
```

These are non-abstract methods with `pass` bodies on the base class. If a new checker subclass forgets to override them, calls will silently succeed but do nothing, leading to hard-to-debug correctness bugs. Either:
- Make them `@abstractmethod` (forces all subclasses to implement), or
- Raise `NotImplementedError` to fail loudly.

Since all three existing subclasses implement them, making them abstract is safe.

## Medium Priority

### M1. Root feature not assumption-embedded in CONGEN task preparation

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task_preparation.py`, lines 83-84 and 263-264

```python
if model.root_feature_id is not None:
    result.set_b.append(model.root_feature_id)
```

The root literal (e.g., `1`) is appended to `set_b` as a raw variable, not wrapped with an assumption ID. All other constraints use assumption-embedding (clause + [-assumption_id] in set_kb, assumption_id in assumptions list). The root bypasses this pattern.

**Why it still works:** PySAT accepts raw variable IDs as assumptions in `solve(assumptions=...)`, which forces the variable true. So `root_feature_id=1` in `set_c` causes the solver to assume var 1 = true, which is semantically correct.

**Concern:** The root is not in `self.assumptions`, so it's never in `delta` during `is_consistent`. This means it's always enabled (correct) but through an accidental mechanism. The plan document (`phase-02-task-unification.md`, lines 190-194) shows the _intended_ implementation was to embed root with an assumption. The current code deviates from the plan.

**Impact:** Low-medium. Works correctly but creates an inconsistency in the data model that could confuse future developers. The comment at line 262 says "Add root constraint as assumption-embedded clause" which is misleading since it's not embedded.

### M2. Dead code: `_to_hashable` in `interactive/task.py`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/interactive/task.py`, lines 12-16

```python
def _to_hashable(item: Any) -> Any:
    """Convert item to hashable form for set operations."""
    if isinstance(item, list):
        return tuple(_to_hashable(x) for x in item)
    return item
```

Defined but never called. No imports reference it. Should be removed.

### M3. Dead fields: `clauses_to_name` and `name_to_clauses` on `NonIncrementalCONGENTask`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task.py`, lines 65-69
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task_preparation.py`, lines 319-321

These fields are populated during `NonIncrementalCONGENTaskPreparation._prepare_bias_constraints` but never read anywhere in the codebase. They were used in the old non-incremental clause-based mode. Now that non-incremental uses assumption IDs, they serve no purpose.

### M4. Outdated docstring in `DescriptionProvider`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/task_preparation.py`, lines 174-176

```python
"""Automatically handles both key types:
- int keys (Incremental mode) -> used directly
- list keys (NonIncremental mode) -> hashed via get_hashcode()
```

Since non-incremental now also uses int keys, the list key path in `_to_key()` is effectively dead code. The docstring is misleading.

### M5. Assumption ID gap in Tseitin fallback path

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task_preparation.py`, lines 304-316

When `negate_cnf_tseitin` is used (no pre-computed negated map), there is a double increment pattern:
```python
negated_clauses, id_assumption = negate_cnf_tseitin(clauses, id_assumption)
negated_id = id_assumption
id_assumption += 1  # <-- first increment
# ... use negated_id ...
id_assumption += 1  # <-- second increment (skips one ID)
```

This skips one assumption ID per Tseitin-generated negation. Not a correctness issue (IDs just need to be unique), but wastes ID space. The same pattern exists in the incremental version (lines 140-151), so it's consistent.

### M6. TODO comments left in production code

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_congen_eval.py`, lines 990, 999

```python
result: str = None  # TODO: necessary?
result=m.get('result'),  # TODO: necessary?
```

These should be resolved or tracked separately.

## Low Priority

### L1. `NonIncrementalPySATChecker.is_consistent` creates solver per call

This is by design (non-incremental = fresh solver), but worth noting that with the new assumption-based data, each call now bootstraps the solver with the full `set_kb` (which grows as GenerateNE adds clauses). For large constraint sets, this creates significant overhead vs the incremental mode. This was always the performance trade-off, but now the set_kb is shared and can grow during execution.

### L2. `IncrementalTaskType` union naming

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/task_preparation.py`, lines 162-166

```python
IncrementalTaskType = Union[
    IncrementalDiagnosisTask, IncrementalTestCaseTask,
    NonIncrementalDiagnosisTask, NonIncrementalTestCaseTask
]
```

The name `IncrementalTaskType` is now misleading since it includes non-incremental types. A name like `AssumptionTaskType` would be more accurate.

## Edge Cases Found

1. **Root feature as raw literal in assumptions:** Works in PySAT because solve(assumptions=[1]) forces var 1 = true, but deviates from the assumption-embedding pattern. If the root feature ID ever collided with an assumption ID, it could cause incorrect behavior. In practice, root_feature_id is typically 1 and assumption IDs start at `next_tseitin_var` (much higher), so collision is unlikely.

2. **Empty negative examples:** `GenerateNE.generate()` correctly skips empty `e_neg` lists (line 77-78). The empty case returns `NEResult(assumption_ids=[], neg_map={}, original_literals=[])`.

3. **QuAcq `_reduce_kb` with constraints missing negated forms:** The method skips constraints where `c_id not in task.negated_constraint_map` (lines 398-399). This silently drops constraints from REDUCE consideration. If many constraints lack negated forms, the KB will not be properly reduced.

4. **`NonIncrementalPySATChecker.copy()` deep-copies lists:** Line 337 correctly does `list(self.set_kb), list(self.assumptions)` creating shallow copies. Since `set_kb` elements are `List[int]` (mutable), a parallel worker modifying clause contents (not expected currently) could cause issues. The current code never mutates individual clauses after creation, so this is safe.

5. **SAT4J assumption encoding as unit clauses:** Line 403: `assumption_clauses = [[a] for a in set_c] + [[-a] for a in delta]`. These are hard unit clauses, not solver assumptions. SAT4J has no assumption mechanism, so this encoding is correct but semantically different -- the solver cannot distinguish between "hard KB clause" and "soft assumption". This works for correctness but may affect UNSAT core extraction if ever needed.

## Positive Observations

1. **Excellent unification:** The dual-path branching (`_is_incremental`, `isinstance` checks) is completely eliminated. All `clause_lists`, `_to_hashable`, and `str()` key conversions are gone.
2. **Net code reduction:** 163 lines removed while maintaining identical functionality.
3. **Consistent API:** `add_clause()`/`add_assumption()` provide a clean extension point for runtime constraint addition (used by GenerateNE).
4. **Test coverage is comprehensive:** 288/290 tests pass, covering all modes (incremental, non-incremental) with and without profiling. The 2 failures are unrelated data file issues.
5. **No regressions in accuracy:** The test suite validates SAT solving correctness across all solver modes.
6. **Clean diff:** Changes are focused and systematic, making the refactoring easy to review.

## Recommended Actions

1. **[High]** Convert `set_c` to `set` before delta computation in all three checkers (H1)
2. **[High]** Make `add_clause`/`add_assumption` abstract or raise `NotImplementedError` (H2)
3. **[Medium]** Remove dead `_to_hashable` in `interactive/task.py` (M2)
4. **[Medium]** Remove dead `clauses_to_name`/`name_to_clauses` fields and population code (M3)
5. **[Medium]** Update `DescriptionProvider` docstring (M4)
6. **[Medium]** Resolve or remove TODO comments in `run_congen_eval.py` (M6)
7. **[Low]** Consider embedding root feature with assumption ID to match the plan (M1)
8. **[Low]** Rename `IncrementalTaskType` to `AssumptionTaskType` (L2)

## Metrics

- Test Coverage: 288/290 passed (99.3%), 2 failures unrelated to refactoring
- Linting Issues: 0 syntax errors, code compiles cleanly
- Type Coverage: Type hints present on all public method signatures in changed files

## Unresolved Questions

1. Was the deviation from the plan (M1, root not assumption-embedded) intentional or an oversight? The plan (`phase-02-task-unification.md` lines 190-194) specifies assumption-embedding.
2. Should the `clauses_to_name`/`name_to_clauses` fields be preserved for future evaluation/debugging purposes, or are they truly unnecessary now?
3. The 2 failing evaluation tests reference files moved to `old_results/`. Are the test data paths going to be updated to point to the new location?
