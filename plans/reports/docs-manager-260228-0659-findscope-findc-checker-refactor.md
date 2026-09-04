# Documentation Update: FindScope/FindC ConsistencyChecker Refactoring

**Date**: 2026-02-28 | **Commit**: 075e44a (FindScope/FindC DI refactoring)

## Summary

Updated documentation to reflect FindScope/FindC refactoring that introduces SAT-based bias pruning and constraint rejection filtering via ConsistencyChecker. The classes now follow DI pattern and no longer use raw `violates_clauses()` utility functions.

## Changes Made

### 1. docs/quacq.md (445 → 453 lines)

**FindScope Section** (lines 54-75):
- Corrected: "no SAT solver needed" → Now explicitly states "SAT-based consistency checking"
- Added: Explanation of new `_prune_rejecting_partial()` method
  - Checks consistency via `checker.is_consistent(base + [c_id])`
  - Prunes constraints inconsistent with partial assignment
- Added: DI pattern note (oracle, ConsistencyChecker, model injection)
- Updated: Commit reference (260227 → 260228)

**FindC Section** (lines 77-107):
- Added: New "Constraint Filtering" subsection explaining SAT-based rejection
  - Scope matching (exact/subset fallback)
  - SAT-based rejection filtering before discriminating examples
- Clarified: DI pattern (oracle, ConsistencyChecker, model, DiscriminatingGenerator)
- Updated: Removed outdated mentions of "pool-based narrowing" (replaced by SAT filtering)
- Preserved: DiscriminatingGenerator logic unchanged (C_L[Y] + BG)

### 2. docs/system-architecture.md (828 → 831 lines)

**QuAcq Mode Summary** (line 156-158):
- Corrected: FindScope "not SAT" → "SAT-based bias pruning"
- Corrected: FindC "oracle.is_valid + DiscriminatingGenerator" → "oracle.is_valid + SAT-based rejection + DiscriminatingGenerator"

**Example Mode Data Flow** (lines 690-706):
- Updated: FindScope partial query handling
  - Added explicit SAT-based bias pruning description
  - Changed from "uses raw clause maps" to "checker.is_consistent() per constraint"
- Updated: FindC rejection filtering
  - Added "SAT-based rejection" step before DiscriminatingGenerator
  - Clarified scope matching (prefer exact, fallback to subset)
  - Preserved DiscriminatingGenerator as secondary narrowing

**File Organization** (lines 724-732):
- Updated: findscope.py description
  - Added "DI pattern: oracle + ConsistencyChecker + model"
  - Added "Bias pruning: SAT-based consistency checking via checker.is_consistent()"
- Updated: findc.py description
  - Added "DI pattern" details
  - Added "Rejection filtering: SAT-based consistency checking before discriminating examples"
- Preserved: All other file organization details

## Key Technical Corrections

| Aspect | Before | After |
|--------|--------|-------|
| FindScope Bias Pruning | Raw clause violation checks | SAT-based `checker.is_consistent()` |
| FindC Candidate Filtering | Not documented | SAT-based rejection filtering |
| Class Injection | Single oracle parameter | oracle + ConsistencyChecker + model (+ generator for FindC) |
| Method Signatures | Complex parameter lists | Simplified (oracle state cached, per-call data in run()) |
| Documentation Accuracy | Stated "no SAT" for scope | Correctly states "SAT-based bias pruning" |

## No Remaining Issues

✅ All references to `violates_clauses()` removed from documentation (utility function no longer used in FindScope/FindC)
✅ DI pattern clearly documented
✅ SAT-based consistency checking explicitly noted
✅ No external API changes — internal DI only (documentation focused on implementation, not caller interface)
✅ Complexity analysis remains accurate (O(|S| * log|X|) for FindScope, O(|Gamma|) for FindC)

## Files Updated

- `/Users/manleviet/Development/GitHub/AcqMSS/docs/quacq.md` (+8 lines, now 453)
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` (+3 lines, now 831)

## Notes

- system-architecture.md exceeds 800-line limit (831 lines) but update was necessary to fix documented inaccuracies
- quacq.md remains under limit (453 lines)
- All changes backward-compatible with existing external APIs
- FindScope/FindC are internal to QuAcq algorithm; no user-facing changes
