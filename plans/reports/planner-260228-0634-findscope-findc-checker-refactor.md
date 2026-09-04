# Planner Report: FindScope/FindC ConsistencyChecker Refactor

**Date**: 2026-02-28
**Plan**: `plans/260228-0634-findscope-findc-checker-refactor/`

## Summary

Created 3-phase plan to replace `violates_clauses()` (pure Boolean eval) with `checker.is_consistent()` (SAT-based) in FindScope and FindC. Same proven pattern already used by `QuAcq._prune_rejecting_constraints`.

## Phases

| # | Phase | Effort | Key Changes |
|---|-------|--------|-------------|
| 1 | Inject checker into FindScope/FindC | 45min | Add checker+model to constructors, rewrite pruning logic, remove scope filter |
| 2 | Update QuAcq callsites | 30min | Pass checker+model+root_assumption at instantiation sites |
| 3 | Update tests | 45min | Pass model to QuAcq in tests exercising negative-example path |

## Files Modified (4 total)

- `conacq/algorithms/quacq/findscope.py` — constructor + _prune_rejecting_partial rewrite
- `conacq/algorithms/quacq/findc.py` — constructor + rejecting filter rewrite
- `conacq/algorithms/quacq/quacq.py` — callsite updates
- `tests/test_quacq.py` — pass model to QuAcq in 3 tests

## Key Decisions

1. **Inject checker+model via constructor** (DI pattern, same as QuAcq)
2. **Remove scope filter** `c_vars.issubset(R)` from FindScope — SAT handles unassigned vars
3. **Lazy model validation** — check model in learn() negative-example branch, not _validate_mode() (keeps empty-bias tests working)
4. **root_assumption = set_b[0]** — already proven pattern from _prune_rejecting_constraints

## Risk: Low

Same proven pattern. IncrementalPySATChecker efficient with assumption toggles. No external API changes.
