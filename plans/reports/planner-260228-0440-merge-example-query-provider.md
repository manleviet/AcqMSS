# Planner Report: Merge ExampleProvider + QueryGenerator into QueryProvider

**Date**: 2026-02-28
**Status**: Plan created
**Plan**: `plans/260228-0420-merge-example-query-provider/`

## Summary

Created 6-phase implementation plan to merge ExampleProvider + QueryGenerator into unified QueryProvider class. Key changes:

1. **QueryProvider** (`query_provider.py`, ~200 LOC) -- single class with `generate_from_pool()` (paper-filtered), `generate_from_sat()` (current SAT logic), `generate()` (pool+SAT fallback)
2. **QuAcq simplified** -- single `query_provider` param replaces `query_generator` + `example_provider`; mode dispatch maps directly to QueryProvider methods
3. **FindC simplified** -- `_narrow_with_pool` deleted (not in paper Algorithm 3); FindC uses only DiscriminatingGenerator
4. **QuAcqRunner updated** -- constructs QueryProvider instead of two separate classes
5. **Old files deleted** -- example_provider.py, query_generator.py removed
6. **Docs updated** -- quacq.md, codebase-summary.md, code-standards.md

## Files Created

- `plans/260228-0420-merge-example-query-provider/plan.md`
- `plans/260228-0420-merge-example-query-provider/phase-01-create-query-provider.md`
- `plans/260228-0420-merge-example-query-provider/phase-02-update-quacq.md`
- `plans/260228-0420-merge-example-query-provider/phase-03-simplify-findc.md`
- `plans/260228-0420-merge-example-query-provider/phase-04-update-runner-consumers.md`
- `plans/260228-0420-merge-example-query-provider/phase-05-delete-update-tests.md`
- `plans/260228-0420-merge-example-query-provider/phase-06-update-docs.md`

## Key Design Decision: Import Path

QueryProvider in `example_generators/` imports `config_to_assumptions` and `violates_clauses` from `conacq.algorithms.quacq.sat_utils`. Acceptable because:
- sat_utils contains pure functions (no circular dependency risk)
- QueryGenerator already does inline SAT solving at same coupling level
- Alternative (duplicating functions) violates DRY

## Effort Estimate

Total: ~3 hours across 6 phases. Phase 1 (create QueryProvider) is the largest at ~45 min.

## Unresolved Questions

None -- all decisions agreed in brainstorm.
