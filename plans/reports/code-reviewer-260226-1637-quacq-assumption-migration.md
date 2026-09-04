# Code Review: QuAcq Assumption ID Migration

**Date:** 2026-02-26
**Reviewer:** code-reviewer
**Scope:** QuAcq/ConGen symmetry — assumption-ID-based classes for interactive learning

---

## Scope

- **New files (3):** `quacq_task.py` (180 LOC), `interactive_task_preparation.py` (94 LOC), `interactive_model.py` (92 LOC)
- **Modified files (9):** `quacq.py`, `result.py`, `findscope.py`, `findc.py`, `query_generator.py`, `interactive_runner.py`, `__init__.py`, `task.py`, `learner.py`
- **Test file:** `test_interactive.py` (904 LOC, 54 tests)
- **Total LOC reviewed:** ~3,347
- **Focus:** Correctness of assumption ID handling, backward compatibility, duck typing, REDUCE integration, test coverage

---

## Overall Assessment

Well-structured migration that achieves strong symmetry between QuAcq and ConGen. The new `QuAcqTask` / `InteractiveModel` / `InteractiveTaskPreparation` trinity mirrors `ConGenTask` / `ConGenModel` / `ConGenTaskPreparation` exactly. Backward compatibility via `TaskType = Union[QuAcqTask, InteractiveTask]` and duck-typed helper functions is clean. REDUCE integration is correct. One critical semantic bug found in `_find_conflict` and `QueryGenerator` BG handling for the oracle-mode path.

All 54 tests pass. Full suite: 333 passed, 2 pre-existing failures (missing data files, unrelated).

---

## Critical Issues

### 1. BG assumption IDs treated as SAT variable literals in oracle-mode path

**Files:** `quacq.py` (`_find_conflict`), `query_generator.py` (`_try_generate_for_constraint`)

**Problem:** `QuAcqTask.background` contains assumption IDs (e.g., `[5, 6]` for root constraint pair from `BGData.assumptions`). Both `_find_conflict` and `QueryGenerator._try_generate_for_constraint` check `isinstance(task.background[0], int)` and wrap each int as a unit clause `[[aid]]`. This was correct for legacy `InteractiveTask` where `background = [root_feature_id]` (a feature variable literal). For `QuAcqTask`, these assumption IDs are meaningless in a raw SAT context -- they don't encode the root constraint semantics.

**Impact:** In oracle-mode (`QuAcq.learn()`), the root BG constraint is effectively **ignored** in:
- Query generation (all queries, primary path) -- may generate queries that violate root constraint
- Conflict detection (negative examples, fallback path)

Example-based mode (`learn_from_examples`) is less affected: FindScope/FindC use FM clauses directly, and `_find_conflict` is only a last-resort fallback.

**Fix:** For `QuAcqTask`, `background` should provide raw BG clauses (not assumption IDs). Either:
- (a) Store raw root constraint clauses in `QuAcqTask.background_clauses` alongside the assumption IDs, or
- (b) In `InteractiveTaskPreparation`, populate `result.background` with the raw root constraint clauses from `bg_data.set_kb` (stripping assumption guards), rather than the assumption IDs

Option (b) is simpler:
```python
# In InteractiveTaskPreparation.prepare(), replace:
result.background = list(bg_data.assumptions)

# With raw clauses (strip assumption guards from bg_data.set_kb):
result.background = [clause[:-1] for clause in bg_data.set_kb]  # Remove [-assumption_id] guard
```

Then `_find_conflict` and `QueryGenerator` would receive raw clauses (lists of ints) and take the `else: bg_clauses.extend(task.background)` branch correctly.

**Note:** This also means `_apply_reduce` would need to get BG assumption IDs separately (currently from `task.background`). Consider adding a `bg_assumption_ids` field to QuAcqTask, keeping `background` for raw clauses.

---

## High Priority

### 2. `quacq.py` exceeds 200 LOC threshold (498 lines)

The file now contains the core QuAcq algorithm, legacy `_reduce_kb_legacy`, and QuickXPlain. Consider extracting `_quickxplain_constraints` + helpers into a separate utility or moving legacy code to `learner.py`.

### 3. `_apply_reduce` exception handling silently returns unfiltered KB

**File:** `quacq.py`, line ~296

```python
except Exception as e:
    logging.warning('REDUCE failed: %s, returning learned KB as-is', e)
    return list(task.learned_kb)
```

This is overly broad. A `KeyError` in `negation_map` or an invalid assumption ID would be silently swallowed. Consider catching only expected exceptions (e.g., `RuntimeError` from checker) or at minimum logging the traceback.

### 4. `_find_conflict` BG handling assumes homogeneous list type

```python
if task.background:
    if isinstance(task.background[0], int):
```

If `background` is empty, this is fine. But if it's a mix of ints and lists (pathological edge case), behavior is undefined. A type annotation or assertion would help. Same pattern in `QueryGenerator._try_generate_for_constraint`.

---

## Medium Priority

### 5. Duplicated `_get_clause_map` helper across 3 files

`quacq.py`, `findscope.py`, and `findc.py` each define their own `_get_clause_map(task)` with the same logic:
```python
def _get_clause_map(task):
    if hasattr(task, 'constraint_clauses'):
        return task.constraint_clauses
    return task.constraint_map
```

DRY violation. Extract to a shared module (e.g., `conacq/algorithms/interactive/_task_compat.py`).

### 6. Duplicated `_get_negated_clauses` in `findc.py` and `query_generator.py`

Same duck-typing pattern duplicated. Should live in one place.

### 7. `QuAcqTask.bias` is `Set[int]` but iteration order is nondeterministic

In `get_constraints_with_scope`, `_find_conflict`, and `_prune_rejecting_constraints`, the bias set is iterated directly. While functionally correct, nondeterministic ordering makes debugging harder. The test `test_remove_from_bias` validates correctness but not determinism. Not a bug per se, but noted for reproducibility.

### 8. `InteractiveRunner.run()` -- `shuffle_seed` on set has no ordering effect

```python
keys = sorted(task.bias)
random.Random(shuffle_seed).shuffle(keys)
task.bias = set(keys)  # Shuffled list → set loses ordering
```

The shuffle is immediately discarded by converting back to `set`. This seed parameter is misleading for the QuAcqTask path. For `InteractiveTask`, `bias` is also a `set`, same problem. This appears to be a pre-existing issue but worth flagging.

### 9. `InteractiveModel.prepare()` type annotation uses bare `oracle` parameter

```python
def prepare(self, oracle) -> QuAcqTask:
```

Should be `oracle: 'FeatureModelOracle'` (with TYPE_CHECKING import) for type safety, matching the docstring.

---

## Low Priority

### 10. `_ASSUMPTION_PAIR_STRIDE` imported from `explanation.models.task_preparation`

`interactive_task_preparation.py` imports a private constant `_ASSUMPTION_PAIR_STRIDE`. The underscore prefix signals it's internal to the explanation package. Consider making it public or using the value directly with a comment.

### 11. `test_interactive.py` at 904 LOC

Large test file. The new QuAcqTask/InteractiveModel test classes are well-organized, but file could be split into `test_interactive_legacy.py` and `test_interactive_assumption.py` in the future.

### 12. Missing `__repr__` on QuAcqTask

`InteractiveResult` has `__repr__` but `QuAcqTask` does not. Would help with debugging.

---

## Edge Cases Found

1. **`_find_conflict` with QuAcqTask + empty `learned_kb`:** `get_kb_clauses()` correctly returns `[]`. BG clauses are the only background -- and they're incorrect per Issue #1.

2. **`_apply_reduce` with empty `learned_kb`:** Short-circuits to `return []`. Correct.

3. **`violates_clauses` with partial assignments:** If a variable in a clause is not in the assignment dict, the literal is treated as "unknown" (doesn't satisfy the clause). This means unassigned variables can cause false violations. This is pre-existing behavior shared between `QuAcqTask` and `InteractiveTask`, but worth noting for partial config scenarios in FindScope.

4. **`PreparationOutput.task` typed as `DiagnosisTask` but receives `QuAcqTask`:** Duck typing works because `prepare_kb()` only accesses `set_kb`, `assumptions`, and `negation_map` -- all present on `QuAcqTask`. But this is a type-safety gap. If `DiagnosisTask` adds new required fields, `QuAcqTask` would silently break.

5. **`_narrow_with_sat` in `findc.py`:** When narrowing candidates fails, returns `candidates[0]` (first remaining). For QuAcqTask this is an int, for InteractiveTask a str. Return type is `Optional` (untyped), which is correct but opaque.

6. **Serialization backward compatibility:** `InteractiveResult.load()` handles missing `kb_assumption_ids` with `data.get('kb_assumption_ids', [])`. Old results load correctly with empty assumption IDs. Forward compatibility tested.

---

## Positive Observations

- **Clean symmetry:** `InteractiveModel` / `QuAcqTask` / `InteractiveTaskPreparation` mirrors `ConGenModel` / `ConGenTask` / `ConGenTaskPreparation` structure. Shared `prepare_kb()` reuse is excellent.
- **Deprecation warnings:** Both `InteractiveTask` and `InteractiveLearner` emit `DeprecationWarning` in `__post_init__` / `__init__`. Clean migration path.
- **REDUCE integration is correct:** `_apply_reduce` uses `task.set_kb`, `task.assumptions`, `task.negation_map`, and `task.background` (as `set_bg`) via `NonIncrementalPySATChecker`. The assumption-guarded path works correctly. Note: Issue #1 does NOT affect REDUCE because REDUCE uses the checker with assumption guards.
- **Test coverage for new code:** 25 new tests across 5 test classes (`TestQuAcqTask`, `TestInteractiveModel`, `TestQuAcqWithAssumptionIDs`, `TestInteractiveResultAssumptionIDs`, `TestQueryGeneratorWithQuAcqTask`). Coverage of key data flows: creation, bias manipulation, KB resolution, serialization round-trip, empty-bias convergence, dual representation.
- **`InteractiveRunner`** cleanly integrates the new model, creates profiler session per run, handles both oracle and example modes.
- **`__init__.py` exports** are well-organized with clear new/deprecated sections.

---

## Test Coverage Assessment

| Component | Coverage | Notes |
|-----------|----------|-------|
| QuAcqTask dataclass | Good | Creation, mutation, clone, config conversion tested |
| InteractiveModel | Good | from_bias, prepare, resolve_kb, error handling tested |
| QuAcq + QuAcqTask (oracle) | Basic | max_queries=5/10, empty bias. No test for _find_conflict correctness |
| QuAcq + QuAcqTask (example) | None | No test for learn_from_examples with QuAcqTask |
| InteractiveRunner | None | No unit tests for InteractiveRunner (only tested via CV integration) |
| REDUCE integration | Indirect | Tested via quacq.learn() but no isolated test |
| FindScope/FindC + QuAcqTask | None | Duck typing not tested directly |
| Backward compat serialization | Good | Old format load tested |

**Missing tests (recommended):**
- `test_learn_from_examples_with_quacq_task` -- example-based mode with QuAcqTask
- `test_find_scope_with_quacq_task` -- verify duck typing works end-to-end
- `test_find_c_with_quacq_task` -- verify duck typing works end-to-end
- `test_interactive_runner_example_mode` -- InteractiveRunner integration
- `test_reduce_correctness_quacq` -- verify REDUCE produces correct non-redundant set

---

## Recommended Actions (Prioritized)

1. **[CRITICAL] Fix BG handling in oracle-mode path** -- `_find_conflict` and `QueryGenerator` must use raw BG clauses, not assumption IDs, when building raw SAT problems for `QuAcqTask`. See Issue #1 for fix options.

2. **[HIGH] Add test for `learn_from_examples` with `QuAcqTask`** -- this is the primary production path (via `InteractiveRunner`) and has zero direct test coverage.

3. **[HIGH] Narrow exception handling in `_apply_reduce`** -- catch specific exceptions, log traceback.

4. **[MEDIUM] Extract shared duck-typing helpers** -- consolidate `_get_clause_map` and `_get_negated_clauses` into one module.

5. **[MEDIUM] Fix `shuffle_seed` for set-based bias** -- either make bias ordered (`list` with O(n) removal) or document that seed only affects initial query generation order (not bias ordering).

6. **[LOW] Add type annotation to `InteractiveModel.prepare()` parameter.

7. **[LOW] Add `__repr__` to `QuAcqTask`.

---

## Metrics

- **Type Coverage:** Moderate. New files have type hints on public methods. Duck typing is intentional but creates gaps.
- **Test Coverage:** 54 tests, all passing. New classes well-tested. Example-based path and InteractiveRunner untested.
- **Linting Issues:** 0 syntax errors. DeprecationWarnings fire correctly (22 in test run).

---

## Unresolved Questions

1. For the BG fix (Issue #1): should `QuAcqTask.background` store raw clauses or keep assumption IDs? The REDUCE path needs assumption IDs (`set_bg`), while oracle-mode needs raw clauses. Dual storage (`background_clauses` + `bg_assumption_ids`) may be cleanest.

2. Is oracle-mode `learn()` with `QuAcqTask` actually used in production, or is example-based mode the only real path? If oracle-mode is not used, Issue #1 is latent rather than active.

3. Should `FindScope` and `FindC` be tested with `QuAcqTask` directly, or is the current indirect coverage (via `learn_from_examples` once tested) sufficient?
