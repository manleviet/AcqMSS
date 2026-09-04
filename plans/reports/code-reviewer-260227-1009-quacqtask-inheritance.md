# Code Review: QuAcqTask Inheritance Refactoring

**Date:** 2026-02-27
**Reviewer:** code-reviewer
**Scope:** QuAcqTask inherits DiagnosisTask, `background` renamed to `set_b`

## Scope

- **Files reviewed:** 8 changed files
  - `conacq/algorithms/interactive/quacq_task.py` (179 lines)
  - `conacq/algorithms/interactive/interactive_task_preparation.py` (100 lines)
  - `conacq/algorithms/interactive/_task_compat.py` (38 lines)
  - `conacq/algorithms/interactive/quacq.py` (485 lines)
  - `conacq/algorithms/interactive/learner.py` (386 lines)
  - `conacq/algorithms/interactive/task.py` (206 lines)
  - `conacq/example_generators/query_generator.py` (174 lines)
  - `tests/test_interactive.py` (980 lines)
- **LOC changed:** ~1,664 (1,211 added / 453 removed across full diff)
- **Focus:** Inheritance refactoring + field rename

## Overall Assessment

**PASS** -- Clean, correct refactoring. QuAcqTask properly inherits DiagnosisTask, eliminating duplicate fields. The `background` -> `set_b` rename is complete across all production and test code. No stale references found.

## Critical Issues

None.

## High Priority

None.

## Medium Priority

### 1. `clone()` omits inherited `set_c` field

`QuAcqTask.clone()` copies `set_kb`, `assumptions`, `negation_map`, `set_b` from the parent but **not `set_c`**. Currently safe because `set_c` is never populated in QuAcq paths, but a future change that populates `set_c` would silently lose data on clone.

**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/interactive/quacq_task.py:160-178`

**Recommendation:** Either add `set_c=list(self.set_c)` to `clone()` for completeness, or add a comment explicitly documenting the omission. Prefer the former for safety.

### 2. File size: `quacq.py` (485 lines) exceeds ~200-line threshold

Pre-existing issue, not introduced by this refactoring. Contains core algorithm + QuickXPlain + Reduce integration + result building. The `_quickxplain_constraints` and `_apply_reduce` methods (~100 lines each) are candidates for extraction.

### 3. File size: `test_interactive.py` (980 lines) exceeds threshold

Pre-existing. Consider splitting by test category (unit tests for task classes, integration tests for learning, evaluation tests).

## Low Priority

### 1. `InteractiveLearner` deprecation warning placement

The deprecation warning in `InteractiveLearner.__init__` is good. The docstring-level `.. deprecated::` annotation in the module docstring is also present. Consistent.

### 2. `background` parameter name in `_quickxplain_constraints`

The QuickXPlain internal method parameter is still named `background=`. This is **intentional and correct** -- it refers to the algorithm's "background" concept (clauses assumed true during the split), not the task field. No action needed.

## Edge Cases Verified

| Edge Case | Status |
|-----------|--------|
| Stale `.background` field access in production code | None found |
| Stale `background=` kwargs in task constructors | None found (only QuickXPlain internal param) |
| `set_c` accidentally used in interactive paths | Not used anywhere |
| `get_cf()` inherited but called in interactive context | Not called |
| Dataclass field ordering (parent defaults + child defaults) | Valid -- all fields have defaults |
| `_task_compat.get_bg_clauses()` handles both task types | Correct: checks `background_clauses` first, falls back to `set_b` |
| `background_clauses` correctly NOT renamed | Correct -- no parent equivalent, QuAcq-specific raw CNF |
| Docs reference `set_b` and `background_clauses` correctly | Verified in `docs/quacq.md` |

## Positive Observations

1. **Clean inheritance**: DiagnosisTask fields (`set_kb`, `assumptions`, `negation_map`, `set_b`) are inherited without duplication. QuAcqTask adds only its unique fields.
2. **Compat layer**: `_task_compat.py` gracefully bridges InteractiveTask (string IDs) and QuAcqTask (int IDs) without branching in algorithm code.
3. **Consistent naming**: `set_b` aligns with DiagnosisTask / ConGenTask conventions across the codebase.
4. **Test coverage**: 63 interactive tests + 360 total pass. Rename verified in both unit and integration test paths.
5. **Deprecation path**: InteractiveTask and InteractiveLearner are properly deprecated with warnings and docstring annotations, maintaining backward compat.

## Recommended Actions

1. **(Medium)** Add `set_c=list(self.set_c)` to `QuAcqTask.clone()` -- defensive against future changes
2. **(Low)** Consider splitting `quacq.py` and `test_interactive.py` in a future pass (not blocking)

## Metrics

- **Type Coverage:** Partial -- dataclass fields have type hints; methods use `TaskType = Union[QuAcqTask, InteractiveTask]`
- **Test Coverage:** 63 interactive tests pass, 360 total
- **Linting Issues:** Not run (no pre-existing ruff/mypy config observed)

## Unresolved Questions

1. Should `QuAcqTask` override `get_cf()` to raise `NotImplementedError` or return a QuAcq-appropriate value? Currently inherits `set_b + set_c` which could be misleading if called accidentally.
