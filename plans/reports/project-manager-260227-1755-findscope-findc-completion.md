---
date: 2026-02-27
status: completed
plan: 260227-1616-findscope-findc-refactor
---

# FindScope/FindC IJCAI 2013 Paper Alignment — Completion Report

## Summary

Successfully completed full refactoring of FindScope/FindC algorithms to achieve IJCAI 2013 paper compliance. All 5 phases delivered:

- **Phase 1**: DiscriminatingGenerator created (C_L[Y] + BG-based example generation)
- **Phase 2**: FindScope refactored (oracle.is_valid + query recording)
- **Phase 3**: FindC refactored (oracle + DiscriminatingGenerator, pool-first hybrid)
- **Phase 4**: QuAcq refactored (FindScope+FindC in learn(), oracle.is_valid in learn_from_examples)
- **Phase 5**: Callers updated, OneShotModel deleted, tests updated

All changes merged to main branch. Test suite: **338 passed, 2 failed (pre-existing — missing data file, unrelated to refactoring)**.

---

## Achievements

### Core Correctness Fixes
1. **Oracle-driven validation**: All queries now go through `oracle.is_valid()` instead of ground-truth FM clauses
2. **Paper-faithful discriminating examples**: FindC uses C_L[Y] (learned KB restricted to scope) instead of FM clauses
3. **Query recording**: FindScope + FindC both record all queries for counting
4. **Paper-correct learn()**: Switched from QuickXPlain (multiple constraints) to FindScope+FindC (single constraint per negative answer)

### Code Quality
1. **Dead code removed**: OneShotModel deleted (21 LOC, no production usage after refactoring)
2. **Quacq.py simplified**: 551 LOC → ~350 LOC (removed 5 dead methods: _find_conflict, _quickxplain_constraints, _check_consistency_with_fm, _get_clauses_for_constraints, _is_consistent)
3. **No SAT imports in FindScope/FindC**: SAT encapsulated in DiscriminatingGenerator
4. **Clean exports**: DiscriminatingGenerator added to quacq package __init__.py

### Additional Bug Fixes During Implementation
1. **findscope.py sparse config guard**: `{k: e[k] for k in R}` → `{k: e[k] for k in R if k in e}` (fixed KeyError on missing keys in partial assignment)
2. **quacq.py query counting guard**: Added `if n_queries < max_queries` check in record_query callback (prevents query count overflow)

---

## Test Results

| Component | Result |
|-----------|--------|
| Full test suite | 338 passed, 2 failed (pre-existing) |
| test_quacq.py | 53 passed |
| test_oracle_model.py | Refactored (OneShotModel tests deleted) |
| Integration tests | All passing |

**Pre-existing failures** (data file missing, unrelated to refactoring):
- Not addressed in scope — noted in test output

---

## Implementation Details

### Files Modified
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/discriminating_generator.py` — NEW (~60 LOC)
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/findscope.py` — 122 LOC → ~85 LOC
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/findc.py` — 205 LOC → ~140 LOC
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/quacq.py` — 551 LOC → ~350 LOC
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/quacq_runner.py` — Minor caller update
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/fm_oracle_model.py` — OneShotModel deleted
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/oracle/__init__.py` — Removed OneShotModel export
- `/Users/manleviet/Development/GitHub/AcqMSS/conacq/algorithms/quacq/__init__.py` — Added DiscriminatingGenerator export
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_quacq.py` — New test class: TestDiscriminatingGenerator
- `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_oracle_model.py` — Removed TestOneShotModel

### Key Design Decisions Implemented
1. **Pool-first hybrid** (FindC): Keep `_narrow_with_pool()` with oracle.is_valid replacement (optimization retained)
2. **BG in formula**: DiscriminatingGenerator includes BG clauses (practical optimization)
3. **No QuickXPlain fallback**: learn() uses simple tested_c_id addition when FindScope empty
4. **Immutable FindScope/FindC**: Both treat task as read-only (learned_kb, remaining_bias passed separately)

---

## Risk Assessment

### Low Risk
- OneShotModel deletion: Only used by deleted code
- Caller updates: Mechanical parameter swaps
- New DiscriminatingGenerator: Standalone, no external dependencies

### Medium Risk
- learn() behavioral change: FindScope+FindC finds single constraints vs QuickXPlain's multiple. This is paper-faithful but may slightly change learning dynamics on degenerate cases.
- Pool consumption: Pool now only used in learn_from_examples, not in learn(). This is paper-correct but changes interaction patterns.

### Mitigation
- Full test suite passing (338/340 pass, 2 pre-existing failures)
- Paper compliance validated in design phase
- All refactoring targets test-driven (53 tests in test_quacq.py cover FindScope/FindC)

---

## Next Steps

1. **Update roadmap**: Document refactoring completion in project roadmap
2. **Update changelog**: Record this refactoring as milestone
3. **Validation**: Verify with domain experts that learning behavior aligns with paper
4. **Documentation**: Consider updating docs/quacq.md if needed for clarity

---

## Unresolved Questions

None. All acceptance criteria met. All TODOs completed. Plan ready for archive.
