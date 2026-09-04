# C7 Implementation Report: Labeler Template Base + Algorithm Twins

**Date:** 2026-06-21  
**Branch:** feat/redesign-abc

---

## Phase Implementation Report

### Executed Phase
- Phase: 13 — C7 labeler template base + algorithm-twin parameterisation
- Plan: /Users/manleviet/Development/GitHub/AcqMSS/plans/260621-1416-redesign-abc
- Status: completed

---

### Files Modified

| File | Change |
|------|--------|
| `explanation/operations/algorithms/hsdag/labeler/labeler.py` | Added template base: concrete `get_type` (via `_labeler_type`), concrete `get_initial_parameters`; `get_label`/`identify_new_node_parameters`/`get_instance` remain abstract |
| `explanation/operations/algorithms/hsdag/labeler/fastdiag_labeler.py` | Removed `get_type`/`get_initial_parameters` (now inherited); set `_labeler_type = LabelerType.DIAGNOSIS` |
| `explanation/operations/algorithms/hsdag/labeler/quickxplain_labeler.py` | Same: removed `get_type`/`get_initial_parameters`; set `_labeler_type = LabelerType.CONFLICT` |
| `explanation/operations/algorithms/hsdag/labeler/kbdiag_labeler.py` | Same; set `_labeler_type = LabelerType.DIAGNOSIS` |
| `explanation/operations/algorithms/hsdag/labeler/quickxplain_with_testcases_labeler.py` | Same; set `_labeler_type = LabelerType.CONFLICT`; clarified call-shape comment (find_conflict_set vs find_conflict) |
| `explanation/operations/algorithms/quickxplain_with_testcases.py` | Fixed `find_conflict_set` docstring: return type is always `(List, List)` — `[]` when no conflict, `[tc]` (single-element list) when conflict found. No behaviour change. |
| `tests/test_diagnosis.py` | Migrated from `unittest.TestCase` + `@parameterized.expand` to pure pytest `@pytest.mark.parametrize`; aliased `TestSuiteReader` as `_TestSuiteReader` to eliminate `PytestCollectionWarning` |

---

### Labeler Base Design

**Shared (moved to `IHSLabelable` base):**
- `get_type() -> LabelerType` — reads `self._labeler_type` (class attribute set by each subclass)
- `get_initial_parameters() -> AbstractHSParameters` — returns `self.initial_parameters` (set in `__init__`)

**Overridden by each subclass (remains abstract or subclass-specific):**
- `get_label` — algorithm-specific (FastDiag, QuickXPlain, KBDiag, QXTC call different methods)
- `identify_new_node_parameters` — each subclass has different fields and logic; not shared
- `get_instance` — factory for fresh instance; each creates its own type

**Arity preservation (red-team):** Confirmed preserved.
- `QuickXPlainLabeler.get_label` calls `find_conflict(C, B)` — single return `List`
- `QuickXPlainWithTestCasesLabeler.get_label` calls `find_conflict_set(C, B, TC, neg_TV)` — two-value return `(test_case: List, conflict_set: List)`. The template base does NOT touch `get_label`, so both arities remain exactly as before.

---

### Algorithm Twins

**qx vs qxtc — decision: KEPT SEPARATE**

Rationale: the `@count_calls`/`@measure_time` decorators are bound at definition time to the decorated method. If `_qx` were shared, only one key set could be emitted. The distinct metric keys are:
- `quickxplain_calls` / `quickxplain_runtime` (outer `find_conflict`)
- `qx_calls` / `qx_runtime` (inner `_qx`)
- `quickxplain_with_testcases_calls` / `quickxplain_with_testcases_runtime` (outer `find_conflict_set`)
- `qx_with_testcases_calls` / `qx_with_testcases_runtime` (inner `_qx`)

These are already correctly distinct and separately decorated in each class. No changes made. Merging would require a single `_qx` with a runtime-selected key string — that changes the decorator pattern entirely and risks silencing C2's metric aggregation.

**wipeoutr_fm vs wipeoutr_t — decision: KEPT SEPARATE**

Structural difference (red-team confirmed):
- `wipeoutr_fm`: `for c_alpha in set_c` → `c_delta.remove(c_alpha)` (in-place, order from original `set_c`)
- `wipeoutr_t`: `while t_pi: t_alpha = t_pi.pop()` → nested `for t_gamma in candidates` → `t_pi.remove(t_gamma)` (pop order from copied list, early-remove from candidates)

Merging would change iteration semantics. Kept separate. Metric keys already distinct:
- `wipeoutr_fm_calls` / `wipeoutr_fm_runtime` / `wipeoutr_fm_nonredundant_runtime`
- `wipeoutr_t_calls` / `wipeoutr_t_runtime` / `wipeoutr_t_nonredundant_runtime`

Both key sets preserved — confirmed by 509 passing tests including wipeoutr_fm and wipeoutr_t test paths.

---

### qxtc `find_conflict_set` Return-Type Fix

Docstring corrected in `quickxplain_with_testcases.py`:
- Old: "test_case: The test case that caused the conflict, or None if no conflict" — misleading (code never returns `None`)
- New: documents that return is always `(List, List)`; no-conflict case returns `([], [])`; conflict case returns `([tc], conflict_set)` where `[tc]` is a single-element list

No code change (behaviour was already correct). The caller in `_copy_tc_without_testcases_before` already unwraps via `current_testcase[0]` and this is now documented.

---

### test_diagnosis Migration

**Before:** `unittest.TestCase` class with `@parameterized.expand` + `@_skip_disabled` (using `unittest.skipIf`)  
**After:** Pure pytest module-level functions with `@pytest.mark.parametrize` + `@_skip_if_disabled` (using `pytest.mark.skipif`)

**Param count:** 206 before → 206 after (identical). Breakdown:
- 34 test functions × STANDARD_PARAMS (6 combos) = 204
- 1 test function × SAT4J_ONLY_PARAMS (2 combos) = 2
- Total = 206

**ENABLED_TESTS / ENABLED_PARAMS toggles:** Fully preserved. Both dicts unchanged. `_skip_if_disabled(name)` helper uses `ENABLED_TESTS.get(name, True)` — same semantics as before (unknown keys default True).

**PytestCollectionWarning eliminated:** `TestSuiteReader` aliased as `_TestSuiteReader` at import. No `Test*`-named symbol visible to pytest collector.

---

### Tests Status

- Collection: 206 tests collected from `test_diagnosis.py` (same as pre-migration)
- Full suite: **509 passed, 0 warnings** in ~55s
- Known flaky test (`test_consistency_check_count_parity`): passed in this run

```
509 passed in 55.46s
```

---

### Issues Encountered

None. All three parts implemented cleanly.

---

### Deviations from Spec

1. `identify_new_node_parameters` NOT moved to base — the 5 labelers differ enough (different assertion types, different field operations) that sharing would require subclass-overridable field lists, adding complexity without DRY benefit. The template base covers the two truly identical methods (`get_type` / `get_initial_parameters`).

2. `quickxplain.py` / `quickxplain_with_testcases.py` / `wipeoutr_fm.py` / `wipeoutr_t.py`: no structural merge performed — per red-team binding constraint (metric-key preservation + structural difference). Both metric key sets are already correct and distinct.

---

**Status:** DONE  
**Summary:** Labeler base template eliminates `get_type`/`get_initial_parameters` duplication across 5 labelers. Algorithm twins (qx/qxtc, wipeoutr_fm/t) kept separate per red-team spec — both distinct metric key sets preserved. `find_conflict_set` return-type docstring corrected. `test_diagnosis.py` migrated to pytest (206 → 206 tests, zero warnings). Full suite 509 passed.  
**Concerns:** None.
