---
title: "Oracle Interface Refactoring"
description: "Slim Oracle ABC to core membership query, extract FM metadata and SAT capabilities"
status: complete
priority: P1
effort: 8h
branch: main
tags: [refactoring, oracle, architecture]
created: 2026-02-17
completed: 2026-02-17
---

# Oracle Interface Refactoring

## Goal
Slim Oracle ABC to **only** membership query methods (`is_valid`, `ask`). Extract FM metadata, SAT capabilities, and ground truth data into separate concerns.

## Phases

| # | Phase | Status | Effort | File |
|---|-------|--------|--------|------|
| 1 | Slim Oracle ABC + introduce FMData | complete | 1.5h | [phase-01](phase-01-slim-oracle-and-fm-data.md) |
| 2 | Refactor ExampleGenerator | complete | 1h | [phase-02](phase-02-refactor-example-generator.md) |
| 3 | Refactor InteractiveLearner + task_preparation | complete | 1.5h | [phase-03](phase-03-refactor-interactive-learner.md) |
| ~~4~~ | ~~Refactor GenerateNE~~ | **removed** | — | ~~[phase-04](phase-04-refactor-generate-ne.md)~~ |
| 5 | Refactor OracleData to GroundTruthData | complete | 1h | [phase-05](phase-05-refactor-oracle-data.md) |
| 6 | Clean up FeatureModelOracle + wrappers | complete | 1h | [phase-06](phase-06-cleanup-oracle-impls.md) |
| 7 | Update tests | complete | 1h | [phase-07](phase-07-update-tests.md) |

## Key Design Decisions

1. **FMData dataclass** holds features, feature_ids, root_feature, num_constraints, next_tseitin_var. Created once from FeatureModelOracle, passed around explicitly.
2. **complete_configuration** stays on FeatureModelOracle as a non-ABC method (callers already know the concrete type).
3. **ExampleGenerator** types `oracle: FeatureModelOracle` directly — honest about concrete dependency.
4. **GenerateNE** kept as-is (no refactoring — oracle dependency acceptable for internal algorithm).
5. **OracleData** renamed to **GroundTruthData**, reads FM directly. No `from_fm_oracle()` factory (YAGNI).
6. **InteractiveLearner.from_examples()**: refactored to use `oracle.is_valid()` per example instead of SAT-checking against CNF clauses. `get_cnf_clauses()` removed from FeatureModelOracle.

## Dependencies
- Phase 2-3 depend on Phase 1 (FMData must exist first)
- Phase 5 independent of 2-3
- Phase 6 after 1-5 (final cleanup)
- Phase 7 after all code phases

## Research
- [Oracle usage mapping](research/researcher-01-oracle-usage.md)
- [FM reading duplication](research/researcher-02-fm-reading-duplication.md)

## Validation Log

### Session 1 — 2026-02-17
**Trigger:** Initial plan creation validation
**Questions asked:** 6

#### Questions & Answers

1. **[Architecture]** FMData is planned as a frozen dataclass on FeatureModelOracle via get_fm_data(). But ExampleGenerator also needs complete_configuration() (SAT solving). How should ExampleGenerator receive its dependencies?
   - Options: Type FeatureModelOracle directly (Recommended) | Split: Oracle + FMData + solver function | Create ExampleGeneratorContext dataclass
   - **Answer:** Type FeatureModelOracle directly
   - **Rationale:** ExampleGenerator genuinely depends on FeatureModelOracle — it needs is_valid(), complete_configuration(), and fm_data. Honest typing.

2. **[Scope]** The plan keeps get_cnf_clauses() on FeatureModelOracle as concrete method. InteractiveLearner.from_examples() uses it for SAT-checking examples without going through Oracle. Should this stay?
   - Options: Keep get_cnf_clauses() on FeatureModelOracle | Remove and refactor from_examples() | Move to FMData or GroundTruthData
   - **Answer:** Remove and refactor from_examples()
   - **Rationale:** from_examples() should use oracle.is_valid() — Oracle answers all membership queries. Consistent with slimmed Oracle design.

3. **[Tradeoffs]** Phase 5 renames OracleData → GroundTruthData and refactors from_uvl() to read FM directly. Should we also keep from_fm_oracle() factory?
   - Options: Keep from_fm_oracle() (Recommended) | Remove from_fm_oracle() | Replace with from_fm_data(FMData, clauses)
   - **Answer:** Remove from_fm_oracle()
   - **Rationale:** YAGNI — only from_uvl() is currently used. Simpler class.

4. **[Architecture]** GenerateNE refactoring adds 3 new params to generate(). 8 total params. How to handle?
   - Options: Keep 8 params (Recommended) | Group into OracleKBData dataclass | Make standalone function
   - **Answer:** Không modify GenerateNE
   - **Rationale:** User decided GenerateNE stays as-is. Oracle dependency is acceptable for internal algorithm.

5. **[Clarification]** Keep GenerateNE as-is or different approach?
   - Options: Keep GenerateNE as-is | Different approach
   - **Answer:** Keep GenerateNE as-is
   - **Rationale:** Phase 4 removed from plan entirely.

6. **[Scope]** For InteractiveLearner.from_examples(): use oracle.is_valid() per example?
   - Options: Yes, use oracle.is_valid() | Remove from_examples() entirely | Keep but pass clauses from caller
   - **Answer:** Yes, use oracle.is_valid()
   - **Rationale:** Oracle answers all membership queries. Slower but architecturally consistent.

#### Confirmed Decisions
- ExampleGenerator: type `FeatureModelOracle` directly — simple, honest
- GenerateNE: keep as-is — no refactoring needed (Phase 4 removed)
- from_examples(): use oracle.is_valid() instead of CNF SAT-check
- GroundTruthData: only from_uvl() factory, no from_fm_oracle()
- get_cnf_clauses(): remove from FeatureModelOracle

#### Action Items
- [x] Remove Phase 4 from plan
- [ ] Update Phase 1: remove get_cnf_clauses() from FeatureModelOracle (not just remove from ABC)
- [ ] Update Phase 3: refactor from_examples() to use oracle.is_valid()
- [ ] Update Phase 5: remove from_fm_oracle() factory
- [ ] Update Phase 6: remove get_cnf_clauses() cleanup

#### Impact on Phases
- Phase 1: get_cnf_clauses() should be REMOVED from FeatureModelOracle entirely (not kept as concrete method)
- Phase 3: from_examples() must be refactored to use oracle.is_valid() instead of SAT-checking CNF clauses. Remove _fm_clauses field.
- Phase 4: REMOVED entirely
- Phase 5: Remove from_fm_oracle() factory method. Only from_uvl() remains.
- Phase 6: No get_cnf_clauses() to clean up. Scope reduced.
