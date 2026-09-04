# Documentation Update: Extract prune_rejecting() Function

**Status**: ✅ MINIMAL UPDATE REQUIRED
**Timestamp**: 2026-02-28
**Report ID**: docs-manager-260228-0719-prune-rejecting-merge

## Summary

The `prune_rejecting()` function has been extracted from FindScope and QuAcq into a shared utility in `sat_utils.py`. This is a **code refactoring with minimal documentation impact** — sat_utils.py is already documented as containing shared SAT utilities, so the new function just extends the existing file without requiring structural changes.

## Current Documentation State

### codebase-summary.md (Line 36)
**Current entry** (93 LOC file):
```
| `sat_utils.py` | 93 | Standalone SAT utilities: config_to_assumptions, violates_clauses, get_kb_clauses — NEW |
```

**Listed functions**:
- `config_to_assumptions()` — Convert config dict to assumptions
- `violates_clauses()` — Check if assignment violates clauses
- `get_kb_clauses()` — Extract CNF clauses from learned KB

### system-architecture.md
- No specific mention of `sat_utils.py` (file-level docs not required at architecture level)

## Changes Made

### New Function: prune_rejecting()
**Location**: `conacq/algorithms/quacq/sat_utils.py` lines 89-113

**Signature**:
```python
@count_calls('prune_calls')
def prune_rejecting(
    checker,
    model,
    remaining_bias: set,
    assignment: dict,
    root_assumption: int,
) -> list:
```

**Purpose**: Shared SAT-based pruning loop
- Removes constraints from `remaining_bias` that are inconsistent with a given assignment
- Called by FindScope (partial query pruning) and QuAcq (positive example pruning)
- Returns list of pruned constraint assumption IDs
- Mutates `remaining_bias` in-place

**Profiler Metrics Added**:
1. `@count_calls('prune_calls')` — Decorator counts function invocations
2. `profiler.increment('prune_is_consistent_calls')` — Manual counter per consistency check in loop (lines 109-110)

### Usage
- **FindScope** (`findscope.py` line 93): Prunes bias constraints during binary search (partial query scope)
- **QuAcq** (`quacq.py` line 277): Prunes bias constraints given positive example assignment

## Documentation Updates Required

### Option A: Update sat_utils.py description (MINIMAL)
**Current**: Lists 3 functions explicitly
**Proposed**: List all 6 functions or update description to be more general

**Minimal change** (recommended): Keep current description generic + add new function to entry count

**Before**:
```
| `sat_utils.py` | 93 | Standalone SAT utilities: config_to_assumptions, violates_clauses, get_kb_clauses — NEW |
```

**After**:
```
| `sat_utils.py` | 123 | Standalone SAT utilities: config_to_assumptions, partial_config_to_assumptions, get_constraint_vars, violates_clauses, prune_rejecting, get_constraints_with_scope, get_kb_clauses |
```

**Alternative** (simpler, generic):
```
| `sat_utils.py` | 123 | Standalone SAT utilities for QuAcq: constraint filtering, scope management, assumption conversion, consistency checking |
```

### Option B: No changes (VALID ALTERNATIVE)
The generic description "Standalone SAT utilities" already covers the new function without requiring an update. The specific function list was provided for completeness, but adding `prune_rejecting()` to that list requires also listing `partial_config_to_assumptions()` and `get_constraint_vars()` for consistency.

## Recommendation

**Update codebase-summary.md line 36** with generic description:

```markdown
| `sat_utils.py` | 123 | Standalone SAT utilities for QuAcq: constraint filtering, scope matching, assumption conversion, consistency pruning |
```

**Rationale**:
1. ✅ Reflects all functions (including `prune_rejecting()`, `get_constraint_vars()`, `partial_config_to_assumptions()`)
2. ✅ File count updated from 93 to 123 LOC (actual current size)
3. ✅ Avoids need to list every utility function (maintainability)
4. ✅ Keeps sat_utils.py file description at 1 line (consistency with other files)

## Files Affected

| Document | Change Type | Impact |
|----------|------------|--------|
| `docs/codebase-summary.md` | Minor update (1 line) | Line 36: Update description + LOC count |
| `docs/system-architecture.md` | No change | sat_utils.py not mentioned at architecture level |

## Verification

- ✅ `sat_utils.py` exists at `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/sat_utils.py`
- ✅ `prune_rejecting()` function present (lines 89-113)
- ✅ Function called from FindScope.py (line 93) and QuAcq.py (line 277)
- ✅ Profiler metrics configured (count_calls decorator + manual increment)
- ✅ Current LOC is ~123 (verified)

## Implementation Completed

### Changes Made

#### 1. codebase-summary.md (Line 36)
**Before**:
```
| `sat_utils.py` | 93 | Standalone SAT utilities: config_to_assumptions, violates_clauses, get_kb_clauses — NEW |
```

**After**:
```
| `sat_utils.py` | 123 | Standalone SAT utilities for QuAcq: constraint filtering, scope matching, assumption conversion, consistency pruning |
```

**Reason**: Reflects addition of `prune_rejecting()` + other utilities, updated LOC count to 123 (actual file size)

#### 2. codebase-summary.md (Line 48 - Session Changes)
**Before**:
```
- ✅ **Moved behavior to sat_utils.py** — Standalone functions: config_to_assumptions, violates_clauses, get_kb_clauses
```

**After**:
```
- ✅ **Moved behavior to sat_utils.py** — Shared SAT utilities: config_to_assumptions, violates_clauses, get_kb_clauses, prune_rejecting, constraint scope matching
```

**Reason**: Documents new `prune_rejecting()` function as part of this session's refactoring

#### 3. quacq.md (Line 187)
**Before**:
```
- `conacq/algorithms/quacq/sat_utils.py` — Standalone utility functions (config_to_assumptions, violates_clauses, get_kb_clauses) — NEW
```

**After**:
```
- `conacq/algorithms/quacq/sat_utils.py` — Shared SAT utilities (config/scope conversion, consistency pruning, constraint clause extraction)
```

**Reason**: Generic description covers all functions including new `prune_rejecting()`, removes "— NEW" marker

### Verification
- ✅ codebase-summary.md: 590 LOC (under 800 limit)
- ✅ quacq.md: 453 LOC (under 800 limit)
- ✅ system-architecture.md: No changes needed (sat_utils.py not mentioned at architecture level)
- ✅ All changes are backward compatible (generic descriptions still accurate)

## Conclusion

**Status**: ✅ COMPLETE

**Changes Summary**:
- 3 minor updates across 2 doc files
- Updated sat_utils.py entry to reflect `prune_rejecting()` extraction + actual LOC count
- Updated session changelog to document shared SAT utilities refactoring
- All changes descriptive, no breaking documentation changes

**Effort**: Minimal (3 targeted edits)
**Risk**: Low (generic descriptions, no API changes documented)
**Coverage**: ✅ All functions now represented generically; `prune_rejecting()` explicitly mentioned in changelog
