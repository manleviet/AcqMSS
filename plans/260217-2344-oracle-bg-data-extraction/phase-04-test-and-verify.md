# Phase 4: Test and Verify

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 3](phase-03-document-and-cleanup.md)

## Overview
- **Priority**: High
- **Status**: complete
- **Description**: Run full test suite, verify refactoring correctness, review code quality

## Implementation Steps

### 1. Run full test suite
```bash
PYTHONPATH=. pytest tests/ -v
```

### 2. Verify specific test areas
- `tests/test_oracle_model.py` — Oracle model tests (BGData extraction doesn't change assertion counts)
- `tests/test_congen.py` — ConGen tests (API unchanged: `model.prepare(oracle, pos, neg)`)
- `tests/test_interactive.py` — Interactive tests (FMData usage unchanged)

### 3. Verify BGData correctness
Check that `oracle.get_bg_data()` returns:
- `set_kb`: exactly 2 clauses (`[root_id, -a]` and `[-root_id, -a_neg]`)
- `assumptions`: tuple of 2 IDs (original + negated)
- `negation_map`: single entry `{original: negated}`
- `descriptions`: 2 entries with root feature name
- `next_available_id`: equals end of Part 4

### 4. Code review
Delegate to `code-reviewer` agent to verify:
- No dead code left behind
- ID layout documentation is accurate
- No regressions in ConGen task structure

### 5. Update documentation
Delegate to `docs-manager` agent to update `docs/codebase-summary.md` and `docs/system-architecture.md` if needed.

## Todo
- [ ] Run full test suite — all tests pass
- [ ] Verify BGData correctness manually in test output
- [ ] Code review
- [ ] Update documentation if needed

## Success Criteria
- All tests pass with zero failures
- No new warnings introduced
- BGData values match expected root BG constraint data
- Code review passes with no high-priority issues
