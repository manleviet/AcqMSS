# Code Review: Strategy Class Merge Refactoring

**Date:** 2026-02-13
**Scope:** Merge of redundant Incremental/NonIncremental preparation strategy and task classes
**Tests:** 219/219 passing

---

## Code Review Summary

### Scope
- Files: 19 Python files changed
- LOC: -757 net (490 added, 1247 removed)
- Focus: Strategy class merge across explanation and acqmss modules

### Overall Assessment

**Rating: 8/10**

Clean, well-executed refactoring that eliminates the Incremental/NonIncremental class split. The key insight -- that the preparation logic is identical and only the checker differs -- is correct. The merge preserves all behavior, verified by 219/219 tests passing.

---

### Critical Issues

None.

---

### High Priority

**H1. Stale documentation references to old class names**

`CLAUDE.md` (line 168-172) and `docs/system-architecture.md` (line 268) still reference `IncrementalCONGENTaskPreparation`. These are developer-facing docs that will confuse anyone reading them.

Files:
- `/Users/manleviet/Development/GitHub/AcqMSS/CLAUDE.md` lines 168, 172
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` line 268

Fix: Update to `CONGENTaskPreparation` and add the `GenerateNE` + `merge_ne_into_task` flow.

**H2. `TaskPreparationFactory` singleton caching has no reset mechanism**

`/Users/manleviet/Development/GitHub/AcqMSS/explanation/models/task_preparation.py` lines 549-572

Class-level `_diagnosis` and `_testcase` singletons persist across test runs. Currently safe because the cached instances are stateless, but fragile if anyone adds state to `DiagnosisTaskPreparation` or `TestCaseTaskPreparation` in the future. Consider adding a `@classmethod reset()` or switching to instance creation (no cache).

---

### Medium Priority

**M1. `mode_name` parameter on CONGENTaskPreparation serves no functional purpose**

`/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task_preparation.py` line 34

The `mode_name` constructor parameter (e.g., `"incremental-congen"` vs `"non-incremental-congen"`) is only used in a `logging.debug` call (line 57). The preparation logic is identical regardless of mode. This is a vestigial remnant of the old split. Not harmful, but could be simplified to just `"congen"` everywhere, or removed entirely.

**M2. `root_feature_id` appended directly as literal (not as an assumption-encoded variable)**

`/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/task_preparation.py` line 77

```python
result.set_b.append(model.root_feature_id)
```

`root_feature_id` is a SAT variable ID (e.g., `1`), while all other entries in `set_b`, `set_c`, `set_tc` are assumption IDs from `id_assumption` counter. This works because PySAT treats both as assumption literals -- passing `1` forces variable 1 to true. However, it creates an inconsistency in the data model: `set_b` contains a mix of assumption IDs (from the counter) and raw feature variable IDs. If there is ever a collision (unlikely given the ID range gap), this could cause subtle bugs. Consider encoding root via its own assumption, consistent with other entries.

**M3. Duplicated GenerateNE + merge pattern across 3 call sites**

The exact same 10-line pattern appears in:
- `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/eval/congen_runner.py` lines 172-182
- `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_congen.py` lines 153-166
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py` lines 108-120

```python
temp_checker = NonIncrementalPySATChecker(
    task.set_kb, task.assumptions, solver_name, profiler
)
generate_ne = GenerateNE(temp_checker, profiler)
ne_result = generate_ne.generate(
    set_tv=task.e_neg_literals,
    set_bg=task.set_b,
    start_assumption_id=task.next_assumption_id
)
merge_ne_into_task(task, ne_result)
```

This violates DRY. Consider extracting a helper function like `run_generate_ne(task, solver_name, profiler) -> None` in the generate_ne module.

---

### Low Priority

**L1. Missing blank line before `merge_ne_into_task` function**

`/Users/manleviet/Development/GitHub/AcqMSS/acqmss/algorithms/generate_ne.py` line 126

PEP 8 requires two blank lines before top-level function definitions. There is only one blank line before `merge_ne_into_task`.

---

### Positive Observations

1. **Massive complexity reduction**: 952 -> 572 lines in `explanation/models/task_preparation.py`. 6 task classes collapsed to 2, 4 strategy classes collapsed to 2. Very clean.

2. **Unified data model**: All modes now use `List[int]` assumption IDs consistently. No more `List[List[int]]` (clause lists) for non-incremental. This eliminates the polymorphic dispatch and simplifies all downstream code (Reduce, WipeOutR_FM, WipeOutR_T).

3. **`NonIncrementalPySATChecker` now symmetric with `IncrementalPySATChecker`**: Both take `set_kb` + `assumptions`. The only difference is solver lifecycle. This is much cleaner than the old design where NonIncremental operated on raw clause lists.

4. **`DiagnosisTask` is no longer abstract**: Removing `ABC` from `DiagnosisTask` is correct since there are no abstract methods -- `get_cf()` was always concrete. The old `ABC` marker was misleading.

5. **GenerateNE extracted to return NEResult**: Clean separation. Callers merge results explicitly via `merge_ne_into_task()`. Clear data flow.

6. **QuAcq `_reduce_kb` properly updated**: The most complex migration -- building assumption-based data from the interactive task's clause-based constraint maps -- is correctly implemented.

7. **Tests updated correctly**: Assertion changes (e.g., `root_id in task.set_b` instead of `[[root_id]] in task.set_b`) correctly reflect the unified data model.

---

### Recommended Actions

1. **[High]** Update `CLAUDE.md` and `docs/system-architecture.md` to reference the new class names
2. **[Medium]** Extract the GenerateNE + merge pattern into a helper to eliminate 3x duplication
3. **[Low]** Add PEP 8 blank line before `merge_ne_into_task`
4. **[Optional]** Consider encoding `root_feature_id` via a proper assumption for data model consistency

### Metrics
- Type Coverage: No type annotations regressions; typing is consistent with existing codebase style
- Test Coverage: 219/219 passing; all incremental and non-incremental paths exercised
- Linting Issues: 1 minor (PEP 8 blank line)

### Unresolved Questions

1. Should the `mode_name` parameter be removed from `CONGENTaskPreparation` since it has no behavioral effect? It adds a minor maintenance burden for zero functional value.
2. Should the root feature be encoded via a dedicated assumption ID for consistency with the rest of `set_b`? Currently works fine but is a data model inconsistency.
