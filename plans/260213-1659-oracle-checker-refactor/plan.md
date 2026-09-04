---
title: "Oracle & QuAcq ConsistencyChecker Refactor"
description: "Unify SAT solving through ConsistencyChecker for Oracle and QuAcq components"
status: complete
priority: P2
effort: 3h
branch: main
tags: [refactor, oracle, checker, sat-solver]
created: 2026-02-13
revised: 2026-02-13
---

# Oracle & QuAcq ConsistencyChecker Refactor

## Goal

Replace raw PySAT `Solver` in Oracle and QuAcq with `ConsistencyChecker` via `CheckerFactory.create_from_model`. Reuse same data structure pattern as DiagnosisModel/CONGENModel.

## Key Design Decisions

1. **CheckerModel Protocol** — structural subtyping so `CheckerFactory.create_from_model` accepts any object with `get_kb()`, `get_assumptions()`, `use_incremental`. DiagnosisModel/CONGENModel satisfy it automatically.

2. **OracleModel follows CONGENModel pattern** — uses `constraint_map` + `variables` + `prepare()` (NOT custom `fm_clauses`/`feature_ids`). FM clauses → `constraint_map`, feature_ids → `variables`. Same data structure as DiagnosisModel/CONGENModel.

3. **Assumption-guarded feature clauses** — `[-a_pos_i, fid]` means "if a_pos_i active, feature must be true". FM clauses go directly into set_kb (always active). `is_valid(config)` → `checker.is_consistent(feature_assumptions)`.

4. **`_compute_delta` is stateless** — `self.assumptions` fixed at init, never changes. `_compute_delta(set_c)` returns `(set_c, assumptions \ set_c)` every call. No `solve()` needed.

## Scope

**In scope** (5 files modified, 2 new):
- `checker.py` — Extract `CheckerModel` Protocol, update factory type hint
- `fm_oracle.py` — Use checker for `is_valid()`, keep raw Solver for `get_valid_configuration()`
- `findscope.py`, `findc.py`, `quacq.py` — Use factory-created NonIncremental checkers

**Out of scope** (keep raw Solver): query_generator, generators, accuracy, `get_valid_configuration()`, `_narrow_with_sat()`

## Phases

| # | Phase | Effort | Status |
|---|-------|--------|--------|
| 1 | [Extract CheckerModel Protocol](phase-01-checker-model-protocol.md) | 20m | complete |
| 2 | [Create OracleModel + Preparation](phase-02-oracle-model.md) | 50m | complete |
| 3 | [Refactor FeatureModelOracle](phase-03-refactor-oracle.md) | 40m | complete |
| 4 | [Refactor QuAcq components](phase-04-refactor-quacq.md) | 40m | complete |
| 5 | [Tests & verification](phase-05-tests.md) | 30m | complete |

## Dependencies

- Phase 2,3,4 depend on Phase 1
- Phase 3 depends on Phase 2
- Phase 5 depends on Phases 3 and 4
