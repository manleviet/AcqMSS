# Code Review: GenerateNE Extraction from CONGEN

**Reviewer:** code-reviewer
**Date:** 2026-02-13
**Scope:** Refactoring to move GenerateNE out of CONGEN, eliminate checker mutation

## Scope

- **Files reviewed:** 11 source files + diffs across algorithms, eval, apps, explanation, tests
- **LOC:** ~3,607 across changed files
- **Focus:** Correctness of GenerateNE extraction, temp checker pattern, remaining references

## Overall Assessment

The refactoring is **well-executed and sound**. The core goal -- eliminating checker mutation (`add_clause`/`add_assumption`) by having callers run GenerateNE before CONGEN -- is cleanly achieved. The temp checker pattern (NonIncrementalPySATChecker for QXP calls, then final checker with merged data) is correct because NonIncrementalPySATChecker creates a fresh solver per call, so the stale snapshot of `set_kb`/`assumptions` at construction time does not matter for QXP's read-only consistency checks. All three call sites (tests, app, eval runner) follow the same pattern consistently.

The unification of non-incremental mode to use assumption-based representation (matching incremental) is a significant simplification that eliminates `_to_hashable`, `_unique_union`, clause-list polymorphism, and ~150 lines of conditional logic.

13/13 CONGEN tests pass; 2 pre-existing failures are unrelated.

## Critical Issues

None.

## High Priority

### H1. Reference sharing between temp_checker and final IncrementalPySATChecker

In `apps/run_congen.py:159-174`, `tests/test_congen.py:111-130`, and `acqmss/eval/congen_runner.py:178-197`, the pattern is:

```python
temp_checker = NonIncrementalPySATChecker(task.set_kb, task.assumptions, ...)
# ... merge_ne_into_task mutates task.set_kb and task.assumptions ...
checker = IncrementalPySATChecker(task.set_kb, task.assumptions, ...)
```

`NonIncrementalPySATChecker` stores references to the same `task.set_kb` and `task.assumptions` lists. After `merge_ne_into_task` extends these lists, the `temp_checker`'s `self.set_kb` and `self.assumptions` **also** include the NE data (since Python lists are mutable references). This is **not a correctness bug** because `temp_checker` is never used again after `merge_ne_into_task`. However, it is worth noting:

- **Risk:** If someone later reuses `temp_checker` after the merge, it would have a stale assumption set (assumptions exist in `self.assumptions` that were never in the solver it creates). Since NonIncrementalPySATChecker creates a fresh solver per call bootstrapped with `self.set_kb`, it would actually work correctly (the NE clauses would be in the solver, and the NE assumption IDs would be in the delta calculation). So even accidental reuse is safe.
- **Recommendation:** No action needed. The pattern is safe. If defensive coding is desired, `temp_checker` could be explicitly set to `None` after use, but this is optional.

### H2. `generate_from_examples` is orphaned dead code

`GenerateNE.generate_from_examples()` (line 126-132 in `generate_ne.py`) has **no callers** in the codebase. All three call sites use `generate()` directly. This method does not call `merge_ne_into_task`, so any caller using it would get assumption IDs but miss the critical merge step (clauses/assumptions not added to task).

**Impact:** Dead code that could mislead future developers into using an incomplete API path.

**Recommendation:** Remove `generate_from_examples` or clearly document that `merge_ne_into_task` must be called separately.

## Medium Priority

### M1. Root feature ID added to `set_b` without assumption embedding

In both `IncrementalCONGENTaskPreparation.prepare()` (line 83-84) and `NonIncrementalCONGENTaskPreparation.prepare()` (line 263-264):

```python
if model.root_feature_id is not None:
    result.set_b.append(model.root_feature_id)
```

The root feature ID (e.g., `1`) is added directly to `set_b` as a raw variable ID, not as an assumption ID with embedded clauses in `set_kb`. This is **intentionally different** from bias/example handling -- the root is a variable literal, not an assumption-controlled constraint. When the checker processes `set_b`, the root literal appears in `set_c` (the enabled assumptions list), and since it's not in `self.assumptions`, it won't be negated in the delta. It will appear in `final_assumptions` as-is, which PySAT treats as a unit assumption `[root_id]` meaning "root must be true."

**Verdict:** Correct. The root is treated as a permanent assumption (always enabled, never disabled). This is semantically right for background knowledge. Tests confirm correctness.

### M2. Duplicated caller pattern across 3 call sites

The GenerateNE + merge pattern is copy-pasted identically in:
- `apps/run_congen.py:158-168`
- `acqmss/eval/congen_runner.py:177-187`
- `tests/test_congen.py:110-120`

All three do:

```python
temp_checker = NonIncrementalPySATChecker(task.set_kb, task.assumptions, ...)
generate_ne = GenerateNE(temp_checker, profiler)
ne_result = generate_ne.generate(set_tv=..., set_bg=..., start_assumption_id=...)
merge_ne_into_task(task, ne_result)
```

**Recommendation:** Consider extracting a helper function (e.g., `run_generate_ne(task, solver_name, profiler)`) that encapsulates this pattern. This would reduce the 3 copies to a single function, following DRY. The helper could live in `generate_ne.py` alongside `merge_ne_into_task`.

### M3. `NonIncrementalCONGENTaskPreparation` duplicates incremental logic

`NonIncrementalCONGENTaskPreparation._prepare_bias_constraints()` (lines 274-323) and `_prepare_examples()` (lines 325-361) are nearly identical to the incremental versions. Since both now produce assumption-based output, these could share the same implementation.

**Recommendation:** Consider making `NonIncrementalCONGENTaskPreparation` delegate to or inherit the methods from `IncrementalCONGENTaskPreparation`, similar to how `NonIncrementalDiagnosisTaskPreparation` now reuses `IncrementalKBPreparator.prepare_kb()`.

### M4. `task_preparation.py` exceeds 200-line threshold at 361 lines

Per project coding standards, Python files should be ~200 lines. The non-incremental preparation class could be extracted to a separate module if the duplication from M3 is not resolved.

## Low Priority

### L1. Stale comment in IncrementalCONGENTaskPreparation

Line 76 comment says "NE generation is done by GenerateNE in CONGEN.acquire()" but NE generation is now done by callers before CONGEN. The docstring at line 33-34 also references `set_neg_tv` which is no longer relevant for CONGEN tasks.

### L2. `clause_lists` field removed from `NEResult` but `NEResult` still in `__all__`

The export is fine, but the docstring could note the new fields (`new_clauses`, `new_assumptions`) for API consumers.

### L3. SAT4J assumption encoding uses unit clauses instead of solver assumptions

In `SAT4JChecker.is_consistent()` (line 377), assumptions are encoded as unit clauses (`[[a]]` and `[[-a]]`) rather than using the SAT4J assumption mechanism. This is correct for the subprocess-based approach (DIMACS format doesn't support assumptions directly), but adds clauses that permanently constrain the formula. Since a fresh CNF is built per call, this is fine.

## Edge Cases Found by Scouting

1. **No remaining references to removed `add_clause`/`add_assumption` on checker** -- confirmed via grep. All `add_clause` references are on PySAT Solver objects or in `.venv`, not on `ConsistencyChecker`.
2. **`generate_from_examples` is orphaned** -- see H2.
3. **QuAcq `_reduce_kb` correctly adapted** -- builds its own assumption-based data locally for `NonIncrementalPySATChecker`, passes `Dict[int, int]` neg_map to Reduce. Pattern is correct.
4. **WipeOutR_FM/WipeOutR_T updated** -- removed `str()` key conversion for neg_map lookup, now uses direct int keys. Correct.
5. **`DiagnosisModel.get_assumptions()` now uses `hasattr`** -- works for both incremental and non-incremental tasks since `NonIncrementalDiagnosisTask` and `NonIncrementalTestCaseTask` now have `assumptions` fields.
6. **`IncrementalTaskType` union updated** -- now includes non-incremental task types, matching the unified assumption-based approach.

## Positive Observations

1. **Clean separation of concerns** -- GenerateNE is now a pure function that returns data; callers decide when/how to merge it.
2. **Elimination of `isinstance` checks** -- `_is_incremental` flag removed from CONGEN and GenerateNE; mode-agnostic code is simpler.
3. **~150 lines of conditional logic removed** -- `_to_hashable`, `_unique_union`, clause-list polymorphism all gone from `reduce.py` and `task.py`.
4. **Consistent caller pattern** -- All 3 call sites follow identical flow.
5. **Tests comprehensively cover both modes** -- 13/13 CONGEN tests pass including incremental, non-incremental, with/without profiling.
6. **NonIncrementalPySATChecker now has same API as IncrementalPySATChecker** -- `(set_kb, assumptions, solver_name, profiler)` constructor, simplifying the overall design.

## Recommended Actions

1. **(H2)** Remove `generate_from_examples` or mark deprecated -- dead code with incomplete API path
2. **(M2)** Extract shared helper for the temp-checker + GenerateNE + merge pattern -- DRY
3. **(M3)** Deduplicate non-incremental task preparation by reusing incremental methods
4. **(L1)** Fix stale comment on line 76 of `task_preparation.py`

## Metrics

- **Type Coverage:** Moderate -- function signatures have type hints, dataclass fields typed
- **Test Coverage:** 13/13 CONGEN tests pass (100%), both modes covered
- **Linting Issues:** Not explicitly run (no mypy/ruff in scope); no syntax errors observed

## Unresolved Questions

1. Should `generate_from_examples` be kept for backward compatibility or removed entirely?
2. Is there a plan to consolidate `IncrementalCONGENTaskPreparation` and `NonIncrementalCONGENTaskPreparation` into a single class given they now produce identical output?
