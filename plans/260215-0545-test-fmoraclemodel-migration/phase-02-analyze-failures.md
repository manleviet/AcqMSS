# Phase 2: Analyze Failures & Categorize Root Causes

## Context
- **Parent plan**: [plan.md](plan.md)
- **Dependencies**: Phase 1 (baseline results)
- **Docs**: [system-architecture](../../docs/system-architecture.md)

## Overview
- **Priority**: P1
- **Status**: completed
- **Description**: Categorize test failures by root cause to guide fix prioritization

## Key Insights

### Anticipated Failure Categories

**Category A: Import/API Changes**
- `OracleModel` → `FMOracleModel` rename
- `from_fm()` → `from_fm_data()` factory method rename
- `config_to_active_assumptions()` → `with_configuration()` API change
- `use_incremental` property → `_use_incremental` (private)

**Category B: Data Structure Changes**
- `NEResult.new_assumptions` → `NEResult.set_neg_tv`
- `NEResult.assumption_ids` removed (commented out)
- `NEResult.neg_map` removed (commented out)
- `ConGenTask.e_neg_literals` commented out
- `ConGenTask.next_assumption_id` commented out

**Category C: Logic/Behavioral Changes**
- `_prepare_bg()` adds root feature constraints not previously present
- ID reservation scheme changes assumption ID numbering
- NE generation no longer creates negated forms → `neg_c_map` missing entries
- `merge_ne_into_task()` partially active (commented-out lines)
- `_run_generate_ne()` creates new FeatureModelOracle per call

**Category D: Test-Specific Issues**
- `test_oracle_valid_config` commented out in test_interactive.py
- `with_configuration()` returns `self` (FMOracleModel) instead of list of assumption IDs
- Tests asserting `model._use_incremental` instead of `model.use_incremental`

## Implementation Steps

1. Read Phase 1 test output
2. For each failure, classify into Category A/B/C/D
3. Identify cascading failures (one root cause → multiple test failures)
4. Map each failure to specific code change in commit 012a9db
5. Prioritize: Category C (logic) > Category A (API) > Category B (data) > Category D (test)

## Related Code Files (risk analysis)

| File | Key Change | Risk |
|------|-----------|------|
| `fm_oracle_model.py:95-104` | `with_configuration()` returns self, modifies `_task.set_c` in-place | HIGH - side effect + return type mismatch with tests |
| `task_preparation.py:153-157` | ID reservation gaps for FM constraints/variables | HIGH - assumption ID numbering changed |
| `generate_ne.py:84-97` | No negated forms created | MEDIUM - REDUCE may fail |
| `congen_model.py:213-237` | New FeatureModelOracle in `_run_generate_ne()` | HIGH - oracle construction per prepare() |

## Root Causes Identified

7 root causes identified from 233 failures:
1. **Learner.py crash on Oracle.ask()** - Type mismatch in interactive.py
2. **get_cnf_clauses semantic change** - Returns new CNF structure
3. **is_valid type error** - Requires list, receives single int
4. **generate_ne fallback missing** - REDUCE fails without negated forms
5. **get_num_constraints undefined** - New field in FMOracleModel
6. **with_configuration() side effect** - Returns self, modifies in-place
7. **ID reservation gaps** - Assumption ID numbering changed

## Todo
- [x] Parse Phase 1 test results
- [x] Categorize each failure
- [x] Identify root causes and cascading patterns
- [x] Create failure summary table
- [x] Save analysis to report

## Success Criteria
- Every failure has a root cause classification ✓
- Cascading failures grouped under single root cause ✓
- Clear mapping: failure → code change → category ✓
