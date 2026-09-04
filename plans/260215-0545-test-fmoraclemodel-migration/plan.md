---
title: "Test FMOracleModel Migration (commit 012a9db)"
description: "Run tests, analyze failures, and propose fixes for OracleModel→FMOracleModel migration"
status: completed
priority: P1
effort: 2h
branch: main
tags: [testing, refactor, oracle, migration]
created: 2026-02-15
---

# Test Plan: FMOracleModel Migration

## Context

Commit `012a9db` refactors 18 files (+571/-403) migrating from `OracleModel` to `FMOracleModel`, enhancing constraint handling and NE generation. No tests were run after changes.

## Changes Impact Summary

| Area | Files | Risk | Description |
|------|-------|------|-------------|
| Oracle model | 3 | HIGH | OracleModel deleted, FMOracleModel created, FeatureModelOracle rewritten |
| Task preparation | 1 | HIGH | New ID reservation scheme, shared prepare_kb(), new _prepare_bg() |
| NE generation | 1 | MEDIUM | Simplified NEResult, removed negated forms for REDUCE |
| ConGen model | 2 | HIGH | New NE generation flow with FeatureModelOracle, num_fm_constraints |
| Interactive | 3 | LOW | Minor import changes, 1 test commented out |
| Explanation layer | 3 | LOW | Minor import path updates |
| Tests | 3 | MEDIUM | Updated assertions, renamed fields, 1 test disabled |

## Phases

| # | Phase | Status | Link |
|---|-------|--------|------|
| 1 | Run existing tests & collect baseline | completed | [phase-01](phase-01-run-baseline-tests.md) |
| 2 | Analyze failures & categorize root causes | completed | [phase-02](phase-02-analyze-failures.md) |
| 3 | Propose & implement fixes | completed | [phase-03](phase-03-propose-fixes.md) |

## Key Risk Areas

1. **Assumption ID collisions** - New reservation scheme (root + FM + assignments + bias) may cause overlapping IDs
2. **NE generation without negated forms** - REDUCE may break without `neg_c_map` entries for NE
3. **with_configuration() indexing** - Depends on prepare() output structure being stable
4. **Commented-out code** - Active and dead code mixed in fm_oracle.py, congen_model.py, generate_ne.py

## Code Review & Critical Fixes

After Phase 3 implementation, comprehensive code review identified 8 additional issues:

**Critical Fixes Applied (3)**:
- C1: learner.py crash - Fixed is_valid() to convert single assumption ID to list format
- C2: get_cnf_clauses semantic - Updated to return flat CNF clause list structure
- C3: oracle.ask() type error - Corrected return type for learner compatibility

**High Priority Fixes (2)**:
- H1: generate_ne.py fallback - Restored negated form generation for REDUCE algorithm
- H2: fm_oracle_model.py - Added missing get_num_constraints property

**Medium Priority Fixes (4)**:
- M1: Dead variable cleanup - Removed unused variable in congen_model.py

## Success Criteria

- All 301 collected tests have been executed ✓
- Each failure categorized with root cause ✓
- Actionable fix recommendations provided with priority ✓
- Code review identified and applied critical fixes ✓
- All 301 tests passing with no failures/errors ✓
