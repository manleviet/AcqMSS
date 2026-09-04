# Documentation Update: BG Assumption Bug Fix

**Date**: 2026-02-26
**Status**: Complete
**Report Path**: /Users/manleviet/Development/GitHub/AcqMSS/plans/reports/docs-manager-260226-1806-bg-clauses-fix.md

---

## Summary

Updated project documentation to reflect BG assumption bug fix changes. New `background_clauses` field in `QuAcqTask`, shared duck-typing helpers module `_task_compat.py`, and improved exception handling in REDUCE algorithm.

---

## Changes Made

### 1. Code Changes Documented

| Component | Change | Impact |
|-----------|--------|--------|
| `QuAcqTask` | Added `background_clauses: List[List[int]]` field | Dual storage pattern: assumption IDs + raw CNF |
| `_task_compat.py` | New module with 3 helper functions | Duck-typing support for QuAcqTask/InteractiveTask compatibility |
| `_find_conflict()` | Uses `get_bg_clauses()` | Fixes misinterpretation of assumption IDs as clause indices |
| `QueryGenerator` | Uses `get_bg_clauses()` | Correct clause-based query discrimination |
| `_apply_reduce()` | Exception narrowing | `except (RuntimeError, KeyError, ValueError)` instead of `except Exception` |
| `tests/test_interactive.py` | Added 9 new tests | Coverage for BG clause extraction and dual storage |

### 2. Files Updated

#### docs/codebase-summary.md

**Changes**:
- Updated interactive sub-package file count: 10 → 11 files, ~2,200 → ~2,300 LOC
- Added `_task_compat.py` to file listing (39 LOC, duck-typing helpers)
- Updated `quacq_task.py` description: mentioned `background_clauses` field
- Expanded "Recent Changes" section with BG bug fix details:
  - New module purpose
  - QuAcqTask enhancement
  - Bug fixes in findc and QueryGenerator
  - Exception handling narrowing

**Rationale**: Reflects new module and structural changes to QuAcqTask.

#### docs/quacq.md

**Changes**:
- Updated core implementation list to include `_task_compat.py`
- Enhanced "Assumption ID Architecture" section with detailed QuAcqTask fields:
  - `background` vs `background_clauses` distinction
  - `constraint_clauses` and `negated_clauses` mappings
  - Helper function references
- Added "Dual Storage Pattern" subsection explaining:
  - Bug source (assumption ID misinterpretation)
  - Fix implementation (`get_bg_clauses()` usage)
  - SAT violation detection improvement

**Rationale**: Clarifies storage strategy and bug context for QuAcq developers.

#### docs/system-architecture.md

**Changes**:
- Updated "Last Updated" timestamp: reflects BG bug fix date
- Enhanced "QuAcq Interactive/Batch Flow" with:
  - Dual storage pattern details in flow diagram
  - `background` vs `background_clauses` initialization
  - `constraint_clauses` and `negated_clauses` population
  - Helper function calls in FindScope/FindC
  - New "Key Changes (Bug Fix)" subsection covering:
    - QuAcqTask dual storage
    - Shared duck-typing helpers
    - Exception handling narrowing

**Rationale**: Provides comprehensive architecture context for integration points.

---

## Verification

### Content Accuracy
- Verified all field names match actual code (QuAcqTask, _task_compat.py)
- Confirmed helper function signatures and purposes
- Validated file counts and LOC estimates

### Cross-Reference Consistency
- All three docs consistently reference `_task_compat.py`
- Dual storage pattern explained consistently across files
- Helper function names match codebase exactly

### Line Count Management
All docs remain well under 800 LOC limit:
- `codebase-summary.md`: ~545 LOC
- `quacq.md`: ~262 LOC
- `system-architecture.md`: ~745 LOC

---

## Files Updated
1. `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md`
2. `/Users/manleviet/Development/GitHub/AcqMSS/docs/quacq.md`
3. `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md`

---

## Key Documentation Highlights

### New Module: `_task_compat.py`
- **Purpose**: Shared duck-typing helpers for QuAcqTask/InteractiveTask compatibility
- **Functions**:
  - `get_clause_map(task)` — Normalize constraint→clauses mapping
  - `get_negated_clauses(task, c_id)` — Normalize negated clause lookup
  - `get_bg_clauses(task)` — Extract raw BG clauses (fixes assumption ID bug)
- **Location**: `conacq/algorithms/interactive/_task_compat.py`

### QuAcqTask Dual Storage
```python
# Assumption IDs (for KB operations)
background: List[int]

# Raw CNF clauses without assumption guards (for SAT discrimination)
background_clauses: List[List[int]]

# Per-constraint storage
constraint_clauses: Dict[int, List[List[int]]]    # Raw CNF by assumption ID
negated_clauses: Dict[int, List[List[int]]]       # Negated CNF by assumption ID
```

### Bug Fix Context
- **Before**: `_find_conflict()` misinterpreted assumption IDs as clause list indices
- **After**: Uses `get_bg_clauses()` to extract raw BG CNF for proper violation checking
- **Impact**: Correct SAT-based discrimination in FindScope/FindC algorithms

---

## Integration Notes

### Backward Compatibility
- `InteractiveTask` (deprecated) still supported via duck-typing
- `_task_compat.py` helpers normalize both old and new task types
- No breaking changes to public APIs

### Testing Coverage
- 9 new tests in `tests/test_interactive.py` verify:
  - Background clause extraction
  - Dual storage consistency
  - Duck-typing helper correctness
  - FindScope/FindC with BG clause discrimination

---

## Next Steps

1. **Code Review**: Verify all changes align with team standards
2. **Testing**: Run full test suite to confirm 9 new tests pass
3. **Integration**: Monitor for any additional duck-typing edge cases
4. **Future Maintenance**: Update docs when additional task compat features added

---

## Unresolved Questions

None at this time. All documentation changes complete and verified against codebase.
