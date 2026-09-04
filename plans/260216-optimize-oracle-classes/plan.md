---
title: "Optimize Oracle Module"
description: "Clean up dead code, extract CTC parser, cache descriptions, refine architecture"
status: complete
priority: P2
effort: 3h
branch: main
tags: [refactor, oracle, performance, cleanup]
created: 2026-02-16
---

# Optimize Oracle Module

## Context

Oracle module (`acqmss/oracle/`) has ~590 LOC across 2 main files with ~100 lines dead code, no caching on expensive operations, double FM loading, and SRP violations. Refactor improves maintainability and performance.

## Research

- [Class Internals Analysis](research/researcher-01-class-internals.md)
- [Callers & Dependencies](research/researcher-02-callers-dependencies.md)

## Phases

| # | Phase | File | Status | Effort |
|---|-------|------|--------|--------|
| 1 | Remove dead code + unused methods | [phase-01](phase-01-cleanup-dead-code.md) | complete | 30m |
| 2 | Extract CTC description parser | [phase-02](phase-02-extract-ctc-parser.md) | complete | 45m |
| 3 | Performance: caching + lazy init | [phase-03](phase-03-performance-optimization.md) | complete | 45m |
| 4 | Architecture refinements | [phase-04](phase-04-architecture-refine.md) | complete | 30m |

## Key Constraints

- Maintain backward compatibility with CheckerModel protocol
- All existing tests must pass (test_oracle_model.py, test_congen.py, test_interactive.py)
- Python ~200 LOC per file guideline
- Follow Builder, DI, CheckerModel patterns

## Dependencies

- Phase 1 is independent (start here)
- Phase 2 depends on Phase 1 (dead code removed first)
- Phase 3 depends on Phase 2 (CTC parser extracted before caching)
- Phase 4 can run after Phase 1

## Success Criteria

- `fm_oracle.py` reduced from 333 to ~180 LOC
- `fm_oracle_model.py` reduced from 259 to ~220 LOC
- New `constraint_description.py` ~80 LOC
- All tests pass
- No functional changes to public API

## Validation Log

### Session 1 — 2026-02-16
**Trigger:** Initial plan creation validation
**Questions asked:** 4

#### Questions & Answers

1. **[Architecture]** Phase 2: How should get_constraint_descriptions() delegate to the new module?
   - Options: Lazy import inside method (Recommended) | Module-level import | Remove delegation entirely
   - **Answer:** Lazy import inside method
   - **Rationale:** Avoids forcing flamapy load on every import of fm_oracle.py. Only loads when descriptions actually needed.

2. **[Tradeoff]** Phase 3: How should we handle the double FM loading problem?
   - Options: Lazy property only (Recommended) | Extract FM from FMOracleModel.build() | Pass FM to constructor
   - **Answer:** Lazy property only
   - **Rationale:** No coupling to FMOracleModel internals. Double-load only occurs when descriptions needed, which most callers (ConGen, QuAcq) never request.

3. **[Scope]** Phase 4: Keep OneShotModel in fm_oracle_model.py (YAGNI, 18 LOC)?
   - Options: Keep in same file (Recommended) | Move to own file
   - **Answer:** Keep in same file
   - **Rationale:** 18 LOC too small to justify separate file. Combined file stays ~220 LOC, within guideline.

4. **[Architecture]** Phase 4: Where should the shared set_c computation logic live?
   - Options: Instance method _compute_base_set_c() (Recommended) | Module-level function
   - **Answer:** Instance method _compute_base_set_c()
   - **Rationale:** Natural home on FMOracleModel since it accesses self._task and self._start_id_assignments. Keeps encapsulation.

#### Confirmed Decisions
- **Import style**: Lazy import — preserves fast import time
- **FM loading**: Lazy property — no coupling, on-demand only
- **OneShotModel**: Keep in-place — YAGNI, 18 LOC
- **DRY fix**: Instance method — natural encapsulation

#### Action Items
- None — all decisions align with plan as written

#### Impact on Phases
- No phase changes required — all recommended options were selected
