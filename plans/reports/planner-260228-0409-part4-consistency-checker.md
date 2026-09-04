# Planner Report: Part 4 ConsistencyChecker for Pruning

**Plan**: `plans/260228-0349-part4-consistency-checker/`
**Date**: 2026-02-28

## Summary

Created 7-phase plan to replace `violates_clauses()` (pure Boolean eval) with SAT-based `checker.is_consistent()` for pruning in QuAcq. Core change: thread Part 4 feature assignment assumptions from FMOracleTaskPreparation through BGData -> QuAcqTask -> QuAcqModel -> checker.

## Phases

1. **BGData Part 4 fields** -- 4 new fields on frozen dataclass (additive, backward-compat defaults)
2. **Oracle extract Part 4** -- FMOracleTaskPreparation populates Part 4 in BGData (data already computed, just needs capture)
3. **QuAcqTask Part 4** -- Task stores Part 4, preparation copies from BGData
4. **QuAcqModel combined KB** -- get_kb()/get_assumptions() include Part 4 (checker sees assignment guards)
5. **Prune with checker** -- _prune_rejecting_constraints uses checker.is_consistent() with fallback to legacy Boolean eval
6. **Runner params** -- Fix _learn_params_from_task (stale keys) + _run_oracle_mode (missing checker arg)
7. **Tests** -- Sync test helper, add Part 4 data flow + SAT prune coverage tests

## Pre-existing Bugs Discovered

1. `_run_oracle_mode` missing `checker` as first arg to `QuAcq.for_oracle()` (working tree)
2. `_learn_params_from_task` has `set_kb`/`assumptions` keys removed from learn() signature (working tree)

## Key Design Decisions

- **Backward compat**: Part 4 params default to None in learn(); if None, falls back to Boolean violates_clauses
- **Single checker**: Part 4 guarded clauses auto-satisfy when disabled (checker._compute_delta negates disabled assumptions)
- **No extra computation**: Part 4 data already exists in FMOracleTaskPreparation, just not exposed via BGData

## Effort Estimate

~2h total: Phases 1-4 are mechanical data plumbing (~45min). Phase 5 is the core logic change (~30min). Phase 6 is bug fixes + param sync (~15min). Phase 7 tests (~30min).
