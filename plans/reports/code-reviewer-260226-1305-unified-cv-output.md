# Code Review: Unified CV Output JSON

**Reviewer:** code-reviewer
**Date:** 2026-02-26
**Commit:** af37e3a

---

## Scope

- **Files reviewed:** 11 source files + 5 config/doc files
- **LOC:** +1485 / -1305 (net +180)
- **Focus:** Unified CV JSON consolidation, backward compatibility, edge cases
- **Key files:**
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/report.py` -- `_enrich_constraints()`, `generate_unified_cv_dict()`
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/result_loader.py` -- `ConGenResultData.from_dict()`
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/kb_comparator.py` -- `ComparationResult.to_enriched_dict()`
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/config.py` -- `find_cv_files()`
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/__init__.py` -- updated exports
  - `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_cv.py` -- unified JSON output
  - `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_compare.py` -- idempotent write-back
  - `/Users/manleviet/Development/GitHub/AcqMSS/apps/extract_results.py` -- dual-format reader
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/acqmss/congen_model.py` -- `resolve_result()`
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/acqmss/congen.py` -- `bg_clauses` removal
  - `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/congen_runner.py` -- uses `model.resolve_result()`

---

## Overall Assessment

Solid refactoring. Consolidates 45+ files per model into a single unified JSON, cleanly separating concerns: `run_cv.py` produces data + description enrichment, `run_compare.py` adds evaluation, `extract_results.py` reads either format. The idempotent write-back pattern is well-implemented and the backward compatibility layer in `extract_results.py` correctly handles both old and new formats.

Test suite: 308/310 pass. The 2 failures are **pre-existing** -- they reference `REAL-FM-7_rs_1n_non-incremental_fold1_kb.json` which was removed in a prior refactoring (old per-fold KB files).

---

## Critical Issues

None.

---

## High Priority

### H1. `find_cv_files` glob matches too broadly

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/config.py` line 99
**Issue:** The glob `*_cv_*.json` matches any JSON file containing `_cv_` in the name, including potential `_eval.json` files that contain `_cv_` in their stem (e.g., `model_cv_incremental_eval.json`).

In practice, `run_compare.py` CLI mode writes `{kb_stem}_eval.json` but unified mode writes back to the same `*_cv_*.json` file. If someone manually creates an eval file with `_cv_` in its name under `kb_dir`, it would be picked up.

**Impact:** Low in current usage (eval files don't match the pattern), but the glob should be more specific.

**Fix suggestion:**
```python
# More precise: match only the exact naming convention from run_cv.py
return sorted(cv_path.glob('*_cv_incremental.json')) + sorted(cv_path.glob('*_cv_non-incremental.json'))
```

---

## Medium Priority

### M1. `compare_model_unified` crashes on `model.kb_dir = None`

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/apps/run_compare.py` line 96
**Issue:** `Path(model.kb_dir)` raises `TypeError` if `kb_dir` is `None`. This only happens if a TOML model entry omits `kb_dir`, which the current config always provides -- but no guard exists.

**Fix suggestion:**
```python
def compare_model_unified(model, strategies, verbose):
    if not model.kb_dir:
        print(f"  Warning: No kb_dir for {model.name}, skipping")
        return 0
    kb_path = Path(model.kb_dir)
```

### M2. Type annotation mismatch on `bg_clauses` (pre-existing)

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/cross_validation.py` line 117
**Issue:** `bg_clauses: List[str]` declared but actual runtime type is `List[List[int]]` (CNF clauses). The unified JSON propagates this value correctly, but the type hint is misleading.

**Fix suggestion:**
```python
bg_clauses: List[List[int]] = field(default_factory=list)
```

### M3. Minor enrichment logic duplication

**Files:**
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/report.py` line 219: `_enrich_constraints()`
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/kb_comparator.py` line 67: `_enrich_ids()` (inline lambda)

**Issue:** Both convert constraint IDs to `{"id": cid, "description": desc}` dicts using the same `bias.has_constraint()` / `bias.get_description()` pattern. Not a DRY violation per se (they serve different contexts), but could be unified into a shared utility.

**Impact:** Low. Maintenance cost is minimal given the small scope.

### M4. Two pre-existing test failures need updating

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_evaluation.py` lines 441-476
**Issue:** `test_evaluate_real_fm_7` and `test_accuracy_with_real_examples` reference `data/results/REAL-FM-7_rs_1n_non-incremental_fold1_kb.json` which no longer exists. These should be updated to use the new unified CV JSON format or generate test data fixtures.

---

## Low Priority

### L1. `_enrich_constraints` does not skip `ne_` constraints

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/report.py` line 219
**Issue:** Unlike the comparator which skips `ne_` prefixed constraint IDs, `_enrich_constraints` enriches all IDs. For `ne_` constraints not in bias, it falls back to `description = cid` which is acceptable behavior. Verified that `ne_` constraints are not present in bias files (they're generated dynamically).

**Impact:** None in practice. The behavior is correct.

### L2. `from_dict` uses `n_kb` key at top level for intersected_kb but `statistics.n_kb` for folds

**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/result_loader.py` line 53
**Issue:** The `from_dict` method looks for `n_kb` in `data['statistics']` with fallback to `len(kb_ids)`. The intersected_kb dict has `n_kb` at the top level (not nested in `statistics`). The fallback `len(kb_ids)` correctly handles this case.

**Impact:** None. Works correctly via the fallback.

---

## Edge Cases Verified

| Scenario | Result |
|----------|--------|
| `ConGenResultData.from_dict` with enriched `[{id, description}]` format | Correctly extracts IDs |
| `ConGenResultData.from_dict` with legacy `["c1"]` format | Passes through as-is |
| `ConGenResultData.from_dict` with empty `{}` | Returns empty defaults (n_kb=0) |
| `ConGenResultData.from_dict` on intersected_kb (no `statistics`) | n_kb uses `len(kb_ids)` fallback |
| Idempotent write-back (run_compare on already-evaluated CV) | from_dict ignores `evaluation` field, comparison re-runs cleanly |
| `find_cv_files` with non-existent path | Returns `[]` |
| `find_cv_files` with empty directory | Returns `[]` |
| `find_cv_files` with mixed file types | Matches only `*_cv_*.json` |
| `extract_results.py` unified format (intersected_kb.evaluation) | Reads correctly |
| `extract_results.py` old format (intersected_evaluation at root) | Falls back correctly |
| `extract_results.py` n_intersected from unified dict vs old int | isinstance check works |

---

## Positive Observations

1. **Clean separation of concerns:** `run_cv.py` produces data, `run_compare.py` enriches with evaluation, `extract_results.py` reads -- each script does one thing well.
2. **Idempotent write-back:** `run_compare.py` reads and writes the same file, allowing re-evaluation without data loss.
3. **Backward compatibility:** `extract_results.py` gracefully handles both old and new formats with explicit fallback chains.
4. **Bias loaded once per model** in `run_cv.py` (line 131), avoiding redundant I/O across solver modes.
5. **`ConGenModel.resolve_result()`** cleanly centralizes assumption-to-clause resolution, removing scattered logic from `ConGenRunner`.
6. **`bg_clauses` moved from `ConGenResult` to `ConGenModel._root_constraint`** -- correct architectural decision since BG is model-level, not per-run.

---

## Recommended Actions

1. **[M4]** Update the 2 failing tests in `test_evaluation.py` to use unified CV JSON fixtures or generate test data in-memory.
2. **[M1]** Add guard for `model.kb_dir is None` in `compare_model_unified()`.
3. **[H1]** Consider tightening the `find_cv_files` glob to match only `*_cv_incremental.json` and `*_cv_non-incremental.json`.
4. **[M2]** Fix `bg_clauses` type annotation from `List[str]` to `List[List[int]]` in `CrossValidationResult`.
5. **[M3]** Optional: extract shared enrichment helper if the pattern proliferates further.

---

## Metrics

- **Test Suite:** 308/310 pass (2 pre-existing failures)
- **New Imports:** All resolve correctly (`generate_unified_cv_dict`, `find_cv_files`)
- **Backward Compat:** Verified dual-format handling in `extract_results.py` and `ConGenResultData.from_dict`

---

## Unresolved Questions

1. Should the 2 pre-existing test failures (`test_evaluate_real_fm_7`, `test_accuracy_with_real_examples`) be fixed as part of this refactoring or tracked separately?
2. Should `find_cv_files` also support `interactive` algorithm outputs (e.g., `*_cv_interactive_*.json`) or is the current glob sufficient?
