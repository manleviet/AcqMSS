# Code Review: resolve_result() Refactoring (Final)

**Date:** 2026-02-25
**Reviewer:** code-reviewer
**Follows:** code-reviewer-260225-1625-resolve-result-refactor.md

## Scope

- Files: 5 modified
  - `conacq/algorithms/acqmss/congen_model.py` (+34 lines: `_root_constraint` field, `_resolve_ids()`, `resolve_result()`)
  - `conacq/algorithms/acqmss/congen.py` (-5 lines: removed `bg_clauses` from `ConGenResult`)
  - `conacq/runners/congen_runner.py` (-13, +3 lines: 15-line block replaced by `model.resolve_result(result)`)
  - `conacq/algorithms/acqmss/task_preparation.py` (+1 line: `model._root_constraint = oracle.get_root_clauses()`)
  - `tests/test_congen.py` (-9 lines: 3 removed `result.bg_clauses` assertions)
- LOC delta: net ~-20
- Tests: 18/18 congen pass, 24/26 eval (2 pre-existing failures)

## Overall Assessment

Clean refactoring. The previous review's **critical bug** (empty bg_clauses from `_resolve_ids(self.get_b())`) is **fixed** -- implemented via Option B (cache during `prepare()`). `get_root_clauses()` is active in `fm_oracle.py`. Behavioral equivalence confirmed.

---

## Critical Issues

None.

## High Priority

### 1. Private field access from external class

**Location:** `task_preparation.py:89` -- `model._root_constraint = oracle.get_root_clauses()`

`ConGenTaskPreparation.prepare()` directly writes to `model._root_constraint` (a private `_`-prefixed field). This breaks the naming convention that `_` means internal-only.

**Impact:** Low risk in practice -- `ConGenTaskPreparation` is tightly coupled to `ConGenModel` by design (preparation strategy pattern). But it sets a pattern where external code mutates private model state.

**Fix options:**
- (A) Make `_root_constraint` a settable property or add a setter method
- (B) Move the assignment into `ConGenModel.prepare()` itself (since `prepare()` calls `ConGenTaskPreparation.prepare()` and has access to `oracle`)
- (C) Accept it -- task_preparation is a trusted collaborator in the same package

**Recommendation:** Option B is cleanest -- move `self._root_constraint = oracle.get_root_clauses()` to `ConGenModel.prepare()` before/after calling `preparation.prepare()`. Keeps private state mutation in the owning class.

## Medium Priority

### 2. Return type is unnamed 4-tuple

**Location:** `congen_model.py:192`

`resolve_result()` returns `Tuple[List[List[int]], List[List[int]], List[str], List[str]]` -- 4 positional items. Only one caller exists currently (`congen_runner.py:242`). Not urgent, but a `NamedTuple` would prevent position-swap bugs if more callers appear.

### 3. No test for `resolve_result()` directly

No unit test validates `model.resolve_result(result)` returns correct bg_clauses/kb_clauses. The runner integration tests pass, which provides indirect coverage, but a focused test would catch regressions faster.

## Low Priority

### 4. `_root_constraint` not reset on re-prepare

`ConGenModel.prepare()` can be called multiple times (CV folds). The `_root_constraint` is set in `task_preparation.py`, so it does get refreshed. But if `prepare()` were called with a different oracle, the old `_root_constraint` from a previous `prepare()` call would persist until the new `prepare()` reaches Step 0. Not a practical issue since the same oracle is reused across folds in `ConGenRunner`.

---

## BG Clauses Equivalence Verification

| Aspect | Old (congen_runner.py) | New (congen_model.py) |
|--------|----------------------|---------------------|
| Source | `self.oracle.get_root_clauses()` | `model._root_constraint` (cached from same call) |
| Value | `list(oracle_model.constraint_map[root])` | Same -- set at `task_preparation.py:89` |
| Type | `List[List[int]]` (e.g., `[[1]]`) | Same |
| Timing | Called after `acquire()` | Cached during `prepare()`, read after `acquire()` |

**Verdict:** Equivalent. The only timing difference is caching at prepare-time vs fetching at resolve-time. Since `constraint_map` is immutable during a run, result is identical.

## Missed References Check

Verified all `bg_clauses` references in `.py` files:
- `ConGenRunResult.bg_clauses` (congen_runner.py:45) -- still exists, correctly populated
- `apps/run_congen.py:104` -- reads `ConGenRunResult.bg_clauses`, unaffected
- `conacq/eval/kb_comparator.py:186` -- reads `ConGenRunResult.bg_clauses`, unaffected
- `tests/test_evaluation.py:225` -- tests `ConGenResultData.bg_clauses`, unaffected
- `apps/run_interactive.py:77` -- constructs `bg_clauses` from learner.task.background, unaffected

No missed references to the removed `ConGenResult.bg_clauses` field.

---

## Positive Observations

1. **Previous critical bug fixed** -- Option B (caching) correctly resolves the empty bg_clauses regression
2. **`get_root_clauses()` kept active** -- method in `fm_oracle.py` is NOT commented out (previous review's concern resolved)
3. **Clean separation** -- `ConGenResult` no longer carries materialized clauses; stays a pure algorithm output (IDs + counts)
4. **Good encapsulation for KB/redundant** -- `_resolve_ids()` correctly moves the assumption-to-name-to-clause chain from runner into model
5. **Removed TODO** -- Cleaned up `# TODO: check lai` tech debt

## Recommended Actions

1. **[High]** Move `_root_constraint` assignment from `task_preparation.py:89` to `ConGenModel.prepare()` to keep private field mutation in the owning class
2. **[Medium]** Consider `NamedTuple` return type for `resolve_result()` if more callers appear
3. **[Low]** Add focused unit test for `resolve_result()` output

## Unresolved Questions

1. Should `_root_constraint` assignment stay in `task_preparation.py` (trusted collaborator pattern) or move to `ConGenModel.prepare()` (strict encapsulation)?
