# Brainstorm: FindScope/FindC ConsistencyChecker Refactor

**Date**: 2026-02-28
**Status**: Agreed — proceeding to plan

## Problem

`FindScope._prune_rejecting_partial` and `FindC.run` use `violates_clauses()` (pure Boolean eval) — misses implied violations detectable only through SAT solving with full KB. `QuAcq._prune_rejecting_constraints` already uses `checker.is_consistent()` correctly.

## Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Motivation | Correctness | violates_clauses misses implied violations |
| Scope | All checking in FindScope/FindC | Replace all violates_clauses usage |
| Root assumption | Include | Same pattern as QuAcq._prune_rejecting_constraints |
| Checker sharing | Share QuAcq's checker | No extra overhead, consistent KB state |

## Current vs Proposed

### violates_clauses Callers

| Location | Current | After |
|----------|---------|-------|
| FindScope._prune_rejecting_partial | violates_clauses (Boolean) | checker.is_consistent (SAT) |
| FindC.run filter | violates_clauses (Boolean) | checker.is_consistent (SAT) |
| QuAcq._prune_rejecting_constraints | checker.is_consistent | No change |
| QuAcq._prune_rejecting_constraints_legacy | violates_clauses | No change (legacy fallback) |
| QueryProvider._filter_pool | violates_clauses | No change (different context) |

### Constructor Changes

- `FindScope(oracle)` → `FindScope(oracle, checker)`
- `FindC(oracle, generator)` → `FindC(oracle, checker, generator)`
- Both `run()` add `root_assumption: int` parameter

### Key Insight: Scope Filter Removal

FindScope._prune_rejecting_partial has `c_vars.issubset(R)` guard — unnecessary with SAT checker. SAT solver handles unassigned variables by exploring all possible values. UNSAT with partial assignment = constraint truly conflicts regardless of free variables. Stronger pruning.

### Removable Code

- `get_constraint_vars` import from FindScope
- `violates_clauses` import from FindScope and FindC
- `id_to_feature` param potentially removable from FindScope._prune_rejecting_partial
- Scope filter (`c_vars.issubset(R)`) in FindScope

## Performance Trade-off

violates_clauses: O(clauses) per call, misses implied violations → more algorithm iterations.
checker.is_consistent: O(SAT) per call, catches all violations → fewer iterations. IncrementalPySATChecker efficient with assumption add/remove.

## Risk

- Low: same proven pattern as _prune_rejecting_constraints
- Monitor SAT call count in FindScope recursive binary search
- No external API change; internal DI only
