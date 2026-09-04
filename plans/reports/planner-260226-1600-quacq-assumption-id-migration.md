# Planner Report: QuAcq Assumption ID Migration

**Date:** 2026-02-26
**Plan:** `plans/260226-1559-quacq-assumption-id-migration/`
**Status:** Plan created (7 phases)

## Summary

Created comprehensive implementation plan to migrate QuAcq from string constraint IDs (`str`) to assumption IDs (`int`), achieving symmetry with ConGen's representation.

## Approach: Parallel Structure (Option B)

New classes alongside old (deprecate, don't delete):
- **QuAcqTask** — parallel to ConGenTask, holds `Set[int]` bias, `Dict[int, clauses]` constraint_clauses
- **InteractiveModel** — parallel to ConGenModel, `.prepare(oracle)` pattern
- **InteractiveTaskPreparation** — reuses `prepare_kb()`, `negate_cnf_tseitin()`, `BGData`

## Key Design Decisions

1. **REDUCE direct call**: Delete `QuAcq._reduce_kb()` entirely (lines 376-446 of quacq.py). Replace with direct `Reduce.reduce(set_b_prime=task.learned_kb, set_neg_tv=[], set_bg=task.background, negation_map=task.negation_map)`.

2. **Dual-field InteractiveResult**: Keep `kb_constraints: List[str]` for backward compat, add `kb_assumption_ids: List[int]`. QuAcq resolves names via DescriptionProvider at result construction time.

3. **QuAcqTask extra fields**: Beyond ConGenTask's fields, QuAcqTask needs:
   - `constraint_clauses: Dict[int, List[List[int]]]` — raw clauses for violation checking
   - `negated_clauses: Dict[int, List[List[int]]]` — raw negated clauses for QueryGenerator and FindC._narrow_with_sat()

4. **prepare_kb() duck typing**: QuAcqTask has `set_kb`, `assumptions`, `negation_map` fields matching what `prepare_kb()` writes to. No subclassing of DiagnosisTask needed.

5. **Eval pipeline unchanged**: InteractiveRunResult.kb_constraints stays `List[str]` (resolved by runner). CV loop, AccuracyCalculator, result_loader — all unchanged.

## Phase Summary

| Phase | Effort | Files Created | Files Modified |
|-------|--------|---------------|----------------|
| 1: Create QuAcqTask/Model/Prep | 2h | 3 new files | __init__.py |
| 2: Update QuAcq algorithm | 1.5h | - | quacq.py, query_generator.py |
| 3: Update FindScope/FindC | 1h | - | findscope.py, findc.py |
| 4: Update Result/Runner | 1h | - | result.py, interactive_runner.py |
| 5: Update eval pipeline | 0.5h | - | Verification only |
| 6: Update tests | 1.5h | - | test_interactive.py |
| 7: Deprecate old classes | 0.5h | - | task.py, learner.py, __init__.py |
| **Total** | **8h** | **3** | **~10** |

## Risks Identified

1. **prepare_kb() type compat** — may need adapter if it type-checks DiagnosisTask. Mitigation: source inspection shows attribute-only access.
2. **QuickXPlain correctness** — algorithm is type-agnostic (str vs int doesn't affect logic). Verify with equivalence test.
3. **Non-determinism in equivalence test** — old path iterates str set, new path iterates int set. Different iteration order may produce different KB for small max_queries. Use large enough limit or accept set-equality comparison.
4. **Bias shuffle** — Set[int] doesn't preserve order. For reproducibility, may need sorted iteration. Not a correctness issue.

## Unresolved Questions

None — all decisions resolved in brainstorm session.
