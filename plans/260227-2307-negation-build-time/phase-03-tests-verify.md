# Phase 3: Tests & Verify

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-congen-negation-build-time.md), [Phase 2](phase-02-quacq-negation-build-time.md)

## Overview
- Priority: High
- Status: complete
- Review: complete
- Run full test suite, verify idempotent behavior

## Implementation Steps

### Step 1: Run full test suite
```bash
PYTHONPATH=. pytest tests/ -v
```

### Step 2: Verify key behaviors
- ConGen tests pass (test_congen.py) — validates negation + prepare flow
- QuAcq tests pass (test_quacq.py) — validates negation + prepare flow
- Evaluation tests pass (test_evaluation.py) — validates CV multi-run

### Step 3: Verify idempotent behavior
- `prepare()` no longer writes to `negated_constraint_map` in either TaskPreparation
- ConGen multi-run (CV folds) produces identical results

## Todo
- [x] Run full test suite
- [x] All tests pass (340 tests)
- [x] Verify no regressions in ConGen CV
- [x] Verify no regressions in QuAcq modes

## Success Criteria
- 0 test failures
- No behavioral changes in output
