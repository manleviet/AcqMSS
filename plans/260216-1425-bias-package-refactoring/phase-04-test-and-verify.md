# Phase 4: Test and Verify

## Context Links
- Parent plan: `plans/260216-1425-bias-package-refactoring/plan.md`
- Depends on: Phase 1, Phase 2, Phase 3

## Overview
- **Priority**: P2
- **Status**: pending
- **Description**: Run all tests to verify refactoring preserves behavior. Check LOC counts.

## Implementation Steps

### Step 1: Run bias-specific tests
```bash
PYTHONPATH=. pytest tests/test_bias_module.py -v
```

### Step 2: Run integration tests (ConGen uses BiasIO)
```bash
PYTHONPATH=. pytest tests/test_congen.py -v
```

### Step 3: Run full test suite
```bash
PYTHONPATH=. pytest tests/ -v
```

### Step 4: Verify LOC counts
```bash
wc -l acqmss/bias/bias_generator.py acqmss/bias/config_loader.py acqmss/bias/bias_io.py
```
Target: all files ≤200 LOC or close with justified reasons.

### Step 5: Verify no public API changes
Check `acqmss/bias/__init__.py` exports unchanged.

## Todo
- [ ] All bias tests pass
- [ ] All congen integration tests pass
- [ ] All tests pass
- [ ] LOC counts verified
- [ ] Public API unchanged

## Success Criteria
- [ ] 0 test failures
- [ ] LOC targets met or justified
- [ ] `__init__.py` exports unchanged
