---
title: "FindScope/FindC IJCAI 2013 Paper Alignment"
description: "Refactor FindScope/FindC to use oracle.is_valid() and C_L[Y] (learned KB) instead of FM clauses/OneShotModel"
status: completed
priority: P1
effort: 3h
branch: main
tags: [refactoring, quacq, correctness, paper-alignment]
created: 2026-02-27
---

# FindScope/FindC IJCAI 2013 Paper Alignment

## Problem

Current FindScope/FindC deviates from IJCAI 2013 paper in 5 ways:
1. Oracle mode `learn()` uses QuickXPlain instead of FindScope+FindC
2. FindScope checks partials via SAT (OneShotModel) instead of `oracle.is_valid()`
3. FindC generates examples from FM clauses (ground truth) instead of C_L[Y] (learned KB)
4. FindC checks validity via SAT instead of `oracle.is_valid()`
5. FindScope missing `record_query` calls (query counting)

## Phase Overview

| Phase | Description | Effort | Status |
|-------|-------------|--------|--------|
| [Phase 1](phase-01-discriminating-generator.md) | Create DiscriminatingGenerator (C_L[Y] + BG) | 30min | pending |
| [Phase 2](phase-02-refactor-findscope.md) | FindScope: oracle.is_valid() + record_query | 30min | pending |
| [Phase 3](phase-03-refactor-findc.md) | FindC: oracle + DiscriminatingGenerator | 45min | pending |
| [Phase 4](phase-04-refactor-quacq.md) | QuAcq.learn() FindScope+FindC; learn_from_examples() oracle | 45min | pending |
| [Phase 5](phase-05-cleanup.md) | Update callers, delete dead code, update tests | 30min | pending |

## Key Dependencies

- Phase 2 and 3 depend on Phase 1 (DiscriminatingGenerator)
- Phase 4 depends on Phases 2 and 3 (updated FindScope/FindC signatures)
- Phase 5 depends on Phase 4 (all internal changes landed)

## Key Files

- `conacq/algorithms/quacq/findscope.py` (122 LOC)
- `conacq/algorithms/quacq/findc.py` (205 LOC)
- `conacq/algorithms/quacq/quacq.py` (551 LOC)
- `conacq/algorithms/quacq/discriminating_generator.py` (NEW ~50 LOC)
- `conacq/runners/quacq_runner.py` (241 LOC)
- `conacq/oracle/fm_oracle_model.py` (OneShotModel removal)
- `tests/test_quacq.py`, `tests/test_oracle_model.py`

## Success Criteria

- [x] All oracle queries go through `oracle.is_valid()` (no direct SAT checks)
- [x] FindC uses C_L[Y] + BG (not FM clauses) for discriminating examples
- [x] All queries counted via `record_query` (FindScope + FindC)
- [x] Oracle mode `learn()` uses FindScope+FindC (not QuickXPlain)
- [x] OneShotModel deleted (no production usage)
- [x] All existing tests pass (or updated for new signatures)

## Reference

- Brainstorm: `plans/reports/brainstorm-260227-1614-findscope-findc-oracle-refactor.md`
- Paper: IJCAI 2013 QuAcq (Algorithms 1-3)

## Validation Log

### Session 1 — 2026-02-27
**Trigger:** Initial plan creation validation
**Questions asked:** 4

#### Questions & Answers

1. **[Fallback]** Phase 4 switches learn() from QuickXPlain (finds minimal conflict sets = potentially multiple constraints) to FindScope+FindC (finds exactly 1 constraint per negative answer). Should we keep _find_conflict as fallback when FindScope returns empty scope?
   - Options: No fallback (Recommended) | Keep QuickXPlain fallback | Keep fallback only in learn()
   - **Answer:** No fallback (Recommended)
   - **Rationale:** Paper-faithful. FindScope empty → log warning + add tested_c_id. Remove QuickXPlain entirely from both learn() and learn_from_examples().

2. **[Pool removal]** Phase 3 removes _narrow_with_pool() from FindC. FindC always uses SAT-based DiscriminatingGenerator. OK with this?
   - Options: Remove pool from FindC (Recommended) | Keep pool narrowing in FindC | Move pool logic to DiscriminatingGenerator
   - **Answer:** Keep pool narrowing in FindC
   - **Rationale:** Hybrid approach: try pool first (oracle.is_valid instead of SAT), then DiscriminatingGenerator. Keeps `example_provider` param in find_c(). Retains optimization for example-based mode.

3. **[BG in formula]** DiscriminatingGenerator includes BG clauses (BG + C_L[Y] + c_i + ¬c_j). Paper strictly says C_L[Y] only. Confirm?
   - Options: Include BG (Recommended) | Exclude BG (strict paper)
   - **Answer:** Include BG (Recommended)
   - **Rationale:** Practical optimization: avoids wasting oracle queries on BG-violating examples.

4. **[Delete class]** OneShotModel deleted since all production usages removed. Any concern?
   - Options: Delete OneShotModel (Recommended) | Keep but deprecate
   - **Answer:** Delete OneShotModel (Recommended)
   - **Rationale:** YAGNI. No production usage after refactoring.

#### Confirmed Decisions
- No QuickXPlain fallback: remove `_find_conflict` entirely
- Keep pool narrowing in FindC: hybrid pool-first + DiscriminatingGenerator
- BG in formula: `BG + C_L[Y] + c_i + ¬c_j`
- Delete OneShotModel: clean removal + test deletion

#### Action Items
- [ ] Phase 3: Keep `_narrow_with_pool` but replace `_check_fm_consistency` with `oracle.is_valid()`. Keep `example_provider` param.
- [ ] Phase 3: Keep `query_mode` param to control pool-first vs generator-only flow.
- [ ] Phase 4: Remove QuickXPlain fallback in both `learn()` and `learn_from_examples()`.

#### Impact on Phases
- Phase 3: Keep `_narrow_with_pool` (modified: oracle.is_valid replaces SAT). Keep `example_provider` and `query_mode` params. `_narrow_with_sat` still replaced by DiscriminatingGenerator loop.
- Phase 4: Remove QuickXPlain fallback in `learn_from_examples()` — use simple tested_c_id addition (same as learn()).
