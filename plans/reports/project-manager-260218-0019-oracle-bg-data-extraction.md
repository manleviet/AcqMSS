# Oracle BG Data Extraction Refactoring — Completion Report

**Plan**: `/Users/manleviet/Development/GitHub/AcqMSS/plans/260217-2344-oracle-bg-data-extraction/`
**Status**: COMPLETE
**Completion Date**: 2026-02-18
**Total Effort**: 2h (as estimated)

---

## Executive Summary

Oracle BG Data Extraction refactoring successfully completed across all 4 phases. Eliminated architectural duplication between Oracle and ConGen by introducing `BGData` frozen dataclass as single source of truth for root background knowledge constraints. All 302 tests pass with zero regressions.

---

## Deliverables

### New Files
- **`conacq/oracle/bg_data.py`** — `BGData` frozen dataclass containing root BG constraint pair, assumption IDs, negation mapping, descriptions, and next available ID for ConGen continuation.

### Modified Files
- **`conacq/oracle/fm_oracle_model.py`** — Added `bg_data` property + post-extraction logic to `OracleTaskPreparation.prepare()`. Renamed `_start_id_assignments` → `_assignments_index` for clarity.
- **`conacq/oracle/fm_oracle.py`** — Added `get_bg_data()` method exposing BGData to CallerModel.
- **`conacq/algorithms/acqmss/task_preparation.py`** — Eliminated `_prepare_bg()` function and FMData dependency. Replaced manual skip arithmetic with `bg_data.next_available_id`.
- **`conacq/algorithms/acqmss/congen_model.py`** — Removed dead code (lines 187-188: `fm_data` assignment) and updated `preparation.prepare()` call signature.
- **`conacq/oracle/__init__.py`** — Exported `BGData` class.

### Documentation Additions
- ID layout documented in both `OracleTaskPreparation.prepare()` and `ConGenTaskPreparation.prepare()` docstrings:
  - Oracle owns Parts 1-4 (feature vars, Tseitin, FM constraints, variable assignments)
  - ConGen owns Parts 5-8 (bias constraints, test cases, NE pairs)
  - BGData bridges the gap via `next_available_id`

---

## Key Achievements

1. **Eliminated Duplication**: `_prepare_bg()` was a degenerate case of `prepare_kb()` for single root constraint. Now root BG created once in Oracle, copied to ConGen via BGData.

2. **Removed Fragile Arithmetic**: Manual skip calculation `(num_fm_constraints - 1) * 2 + len(variables) * 2` replaced by Oracle's `next_available_id`. Less error-prone, easier to maintain.

3. **Simplified ConGen API**: `ConGenTaskPreparation.prepare()` no longer requires FMData parameter. Oracle/ConGen coupling reduced to single `BGData` dataclass.

4. **Clarified Assumption Layout**: Documented shared ID allocation across both classes via structured docstrings. Future developers can understand ID boundaries without tracing code.

5. **Improved Naming**: `_start_id_assignments` → `_assignments_index` clarifies it's an index position, not an ID value itself.

---

## Test Results

```
PYTHONPATH=. pytest tests/ -v
========================================
302 passed, 2 skipped (pre-existing data file failures)
========================================
```

**No new failures introduced.** All refactorings maintain backward compatibility with existing test expectations.

---

## Files Changed Summary

| File | Type | Changes |
|------|------|---------|
| `conacq/oracle/bg_data.py` | NEW | BGData dataclass |
| `conacq/oracle/fm_oracle_model.py` | MOD | bg_data property, post-extraction, _assignments_index rename |
| `conacq/oracle/fm_oracle.py` | MOD | get_bg_data() method |
| `conacq/algorithms/acqmss/task_preparation.py` | MOD | Remove _prepare_bg, FMData param, skip arithmetic |
| `conacq/algorithms/acqmss/congen_model.py` | MOD | Remove dead fm_data assignment, update prepare() call |
| `conacq/oracle/__init__.py` | MOD | Export BGData |

---

## Architecture Impact

**Before**: ConGen computed root BG independently from Oracle despite Oracle already having it.
**After**: Root BG computed once in Oracle, exposed via BGData, consumed by ConGen. Single source of truth.

**Assumption ID Layout** now explicitly documented at boundaries. Future refactors can reference these docstrings instead of inferring layout from code traces.

---

## Next Steps

- Monitor for any edge cases in production use of ConGen with new BGData-sourced root BG
- Consider similar extraction patterns for bias constraints if future refactors require their cross-component reuse
- Potential: Add type hints to BGData fields for IDE support (currently has type annotations via dataclass)

---

## Sign-Off

- **Phase 1** (BGData + Oracle): COMPLETE
- **Phase 2** (ConGen refactor): COMPLETE
- **Phase 3** (Documentation + cleanup): COMPLETE
- **Phase 4** (Test & verify): COMPLETE

All acceptance criteria met. Zero blockers. Code ready for production merge.
