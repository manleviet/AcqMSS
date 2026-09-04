# Code Review: Unified Shuffle-After-Prepare Refactoring

**Date:** 2026-02-28
**Reviewer:** code-reviewer
**Scope:** ConGenRunner, QuAcqRunner, example_generators/__init__.py

---

## Scope

- Files reviewed: 3
  - `conacq/runners/congen_runner.py` (-12 / +5 lines)
  - `conacq/runners/quacq_runner.py` (-18 / +12 lines)
  - `conacq/example_generators/__init__.py` (+1 line)
- Focus: Behavioral equivalence, stale references, pattern consistency
- Scout findings: 1 bug in unrelated file included in diff

---

## Overall Assessment

The runner refactoring is **correct and clean**. Both runners now follow an identical lifecycle: build model once in `__init__()`, call `prepare()` per run, shuffle `task.set_c` after prepare. The transformation is mathematically equivalent because both `ConGenTaskPreparation` and `QuAcqTaskPreparation` create a fresh task object on every `prepare()` call, so `set_c` is always a new list derived from `model.constraint_map` in its original order.

---

## Critical Issues

None.

---

## High Priority

### 1. Eager import defeats lazy-load guard in `__init__.py`

**File:** `conacq/example_generators/__init__.py` (line 4)

The diff adds an eager import:
```python
from .query_generator import QueryGenerator, clause_count_priority, literal_count_priority
```

But lines 10-21 contain a lazy `__getattr__` specifically designed to avoid a circular dependency:
```python
# QueryGenerator is lazily imported to avoid circular dependency:
# example_generators/__init__ -> query_generator -> algorithms.interactive.task
# -> algorithms/__init__ -> interactive/__init__ -> example_generators (partial)
```

The eager import on line 4 makes the `__getattr__` dead code and **re-introduces the circular dependency risk**. This likely works today because Python's import machinery resolved the cycle at test time, but it can break on import order changes.

**Fix:** Remove line 4. The lazy `__getattr__` handles it correctly.

---

## Medium Priority

None.

---

## Low Priority

None.

---

## Edge Cases Verified

| Edge Case | Status |
|-----------|--------|
| `_original_bias_constraint_order` fully removed from codebase | PASS -- only in plan/report .md files |
| `_feature_ids` / `_use_incremental` removed from QuAcqRunner | PASS -- remaining uses are in unrelated classes |
| No stale `model` (without `self.`) refs in quacq_runner.py | PASS -- all 8 references use `self.model` |
| `prepare()` creates fresh task each call (ConGenTask/QuAcqTask) | PASS -- verified fresh instantiation at line 83 and 164 respectively |
| `model.next_available_id` stays fixed across prepare() calls | PASS -- explicit code comment at line 116-118 in congen task_preparation.py |
| No callers mutate model between `run()` calls | PASS -- CV loops just call `runner.run(...)` |
| Shuffle determinism preserved | PASS -- `random.Random(seed).shuffle(task.set_c)` produces identical order per seed |
| `constraint_map` order no longer matters for shuffle correctness | PASS -- `set_c` is derived from `assumptions` list built by `prepare_kb()` |

---

## Positive Observations

1. Both runners now share identical lifecycle pattern -- easy to reason about
2. QuAcqRunner no longer re-reads bias file per run (was `BiasIO.load_from_json` in old `_feature_ids`)
3. QuAcqRunner negation computed once (was `negate_cnf_tseitin` per run) -- significant perf win
4. ConGenRunner lost 3 lines of snapshot state + 7 lines of shuffle logic, replaced by 3 clean lines
5. Docstrings updated accurately in both files

---

## Recommended Actions

1. **[High]** Remove eager `QueryGenerator` import from `conacq/example_generators/__init__.py` line 4 to preserve the lazy-load circular-dependency guard
2. **[Optional]** Update plan phase statuses to completed

---

## Metrics

- Type Coverage: N/A (no type-check tool configured)
- Test Coverage: 340/340 passed per tester report
- Linting Issues: 1 (eager import conflict described above)

---

## Unresolved Questions

1. Was the eager `QueryGenerator` import in `__init__.py` intentional or accidental? If intentional, the `__getattr__` lazy-load block and its comment should be removed instead.
