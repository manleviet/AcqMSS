# Phase 3: Add Unit Tests for Extracted Methods

## Context

- Parent plan: [plan.md](plan.md)
- Depends on: Phase 1 + Phase 2 complete
- Test file: `tests/test_congen.py` (existing, add new test classes)

## Overview

- **Priority**: Medium
- **Status**: pending
- **Description**: Add targeted unit tests for the newly extracted helper methods to ensure they work correctly in isolation

## Key Insights

- Currently **zero direct tests** for `ConGenTaskPreparation` or `prepare()`
- Only end-to-end ConGen tests exist (which call `prepare()` indirectly)
- `TestGenerateNE` only has `test_generate_ne_empty` — minimal coverage
- New extracted methods need focused tests to catch regressions

## Coverage Gaps to Address

| Method | Current Coverage | Priority |
|--------|-----------------|----------|
| `prepare()` (overall) | Indirect only via ConGen e2e | High |
| `_prepare_negative_examples()` | None | High |
| `_find_minimal_conflict_literals()` | None | Medium |
| `_combine_ne_constraints()` | None | High |
| `_create_negated_ne()` | None | High |
| `_assign_sets()` | None | Medium |

## Requirements

- Tests must use real feature model data (existing test fixtures in `data/`)
- No mocks for SAT solver — test actual encoding behavior
- Verify assumption ID correctness (critical for SAT encoding)
- Verify clause structure correctness

## Related Code Files

- `tests/test_congen.py` — add new test classes here
- `acqmss/algorithms/task_preparation.py` — code under test
- `data/fms/` and `data/bias/` — test fixtures

## Implementation Steps

1. **Add `TestConGenTaskPreparation` class** in `tests/test_congen.py`

2. **Test `prepare()` with positive examples only** (no E-)
   - Build model with only E+, call prepare()
   - Assert: `set_c` non-empty (bias), `set_tc` non-empty (E+), `set_neg_tv` empty
   - Assert: assumption IDs are sequential and non-overlapping

3. **Test `prepare()` with both E+ and E-**
   - Build model with E+ and E-, call prepare()
   - Assert: `set_neg_tv` non-empty (NE generated)
   - Assert: `neg_tc_map` maps NE → negated NE
   - Assert: all NE IDs present in `assumptions`

4. **Test `_combine_ne_constraints()` with single NE**
   - Single negative example → single NE assumption, no conjunction needed
   - Assert: exactly 1 entry in `set_neg_tv`

5. **Test `_combine_ne_constraints()` with multiple NEs**
   - Multiple negative examples → conjunction of NEs
   - Assert: implication clauses created for each NE
   - Assert: single combined assumption ID in `set_neg_tv`

6. **Test `_create_negated_ne()` correctness**
   - Verify negated form: ¬(¬e1 ∧ ¬e2) = (e1 ∨ e2)
   - Assert: negated clause structure matches expected disjunction

7. **Test guard clause for None oracle**
   - Build model without oracle, call prepare() with E-
   - Assert: raises `ValueError` with descriptive message

8. **Test `_assign_sets()` partitioning**
   - After Steps 0-2, verify set_b, set_c, set_tc correctly partitioned
   - Assert: no overlapping IDs between sets

## Todo

- [ ] Create TestConGenTaskPreparation class
- [ ] Test prepare() with E+ only
- [ ] Test prepare() with E+ and E-
- [ ] Test single NE combine
- [ ] Test multiple NE combine
- [ ] Test negated NE correctness
- [ ] Test oracle None guard
- [ ] Test _assign_sets partitioning

## Success Criteria

- 8 new test cases, all passing
- Direct coverage of `prepare()` and all extracted helpers
- Tests validate SAT encoding correctness (IDs + clauses), not just "no crash"

## Risk Assessment

- **Test data dependency**: Tests need valid FM + bias + examples. Mitigation: reuse existing test fixtures from `data/` directory already used by `TestCONGEN`.
- **Fragile ID assertions**: If encoding changes, ID-based assertions break. Mitigation: test structural properties (non-overlap, containment) rather than exact values where possible.
