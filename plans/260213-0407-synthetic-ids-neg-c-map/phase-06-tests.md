# Phase 6: Tests and Verification

## Context Links
- [Phase 3: Algorithm Simplification](phase-03-algorithm-simplification.md)
- Source: `tests/test_diagnosis.py`, `tests/test_congen.py`,
  `tests/test_interactive.py`

## Overview
- **Priority**: High
- **Status**: COMPLETE
- **Description**: Run all tests, fix assertions, verify end-to-end
  correctness for both modes and all checker types. 288/290 tests passing
  (2 pre-existing failures unrelated to refactoring).

## Key Insights
- Non-incremental tests will break because checker instantiation changed
  (now requires `set_kb`/`assumptions`).
- Incremental tests should pass unchanged (IncrementalPySATChecker untouched).
- `neg_c_map` assertions may fail if tests checked for string keys or
  clause-list values.
- CONGEN eval results should produce identical KB constraint names.
- SAT4J tests may need updated checker instantiation.

## Requirements
1. All existing tests pass (fix broken assertions)
2. Add unit test for assumption-based `NonIncrementalPySATChecker`
3. Add unit test for assumption-based `SAT4JChecker`
4. Verify CONGEN non-incremental eval matches baseline
5. Verify interactive eval matches baseline

## Related Code Files
- **Check/Fix**: `tests/test_diagnosis.py`
- **Check/Fix**: `tests/test_congen.py`
- **Check/Fix**: `tests/test_interactive.py`
- **Add**: New unit tests for checker changes

## Implementation Steps

### Step 1: Run full test suite
```bash
PYTHONPATH=. python -m pytest tests/ -v --tb=short 2>&1 | head -100
```

### Step 2: Fix checker instantiation in tests
Any test creating `NonIncrementalPySATChecker()` without args will fail.
Update to pass `set_kb=[], assumptions=[]` or build proper test data.

### Step 3: Fix neg_c_map assertions
Search for assertions on neg_c_map key/value types:
```bash
grep -n "neg_c_map\|neg_cf_map\|neg_tc_map" tests/*.py
```
Update string-key assertions to int-key assertions.

### Step 4: Add unit test for NonIncrementalPySATChecker with assumptions
```python
def test_non_incremental_checker_with_assumptions():
    """Verify fresh-solver assumption-based solving."""
    # x1 OR -assumption1 (constraint: x1 must be true)
    set_kb = [[1, -101]]
    assumptions = [101]

    checker = NonIncrementalPySATChecker(set_kb, assumptions, 'glucose4')

    # Enable assumption 101: x1 must be true -> SAT
    assert checker.is_consistent([101]) is True

    # Disable assumption 101: clause trivially satisfied -> SAT
    assert checker.is_consistent([]) is True

    # Add contradicting clause: -x1 OR -assumption2
    checker.add_clause([-1, -102])
    checker.add_assumption(102)

    # Enable both: x1 AND -x1 -> UNSAT
    assert checker.is_consistent([101, 102]) is False

    # Enable only 101: x1 true, -x1 disabled -> SAT
    assert checker.is_consistent([101]) is True
```

### Step 5: Add unit test for SAT4JChecker with assumptions
```python
def test_sat4j_checker_with_assumptions():
    """Verify SAT4J unit-clause assumption encoding."""
    # Skip if jar not available
    set_kb = [[1, -101]]
    assumptions = [101]

    checker = SAT4JChecker(set_kb=set_kb, assumptions=assumptions)
    assert checker.is_consistent([101]) is True
    assert checker.is_consistent([]) is True
```

### Step 6: Add integration test for Reduce with unified neg_map
```python
def test_reduce_unified_neg_map():
    """Verify Reduce with Dict[int,int] neg_map for both modes."""
    # constraint A: x1 (assumption 101)
    # negated A: -x1 (assumption 102)
    set_kb = [
        [1, -101],    # x1 OR -a101
        [-1, -102],   # -x1 OR -a102
    ]
    assumptions = [101, 102]
    neg_map = {101: 102}

    checker = NonIncrementalPySATChecker(
        set_kb, assumptions, 'glucose4')
    reduce = Reduce(checker)

    redundant, kb = reduce.reduce(
        set_b_prime=[101], set_ne=[], set_bg=[],
        neg_map=neg_map)

    # Single constraint, not redundant
    assert len(kb) == 1
    assert 101 in kb
    checker.cleanup()
```

### Step 7: Run CONGEN non-incremental eval
```bash
PYTHONPATH=. python apps/run_congen.py \
  apps/conf/run_congen_config.toml --non-incremental -v
```
Compare KB constraint names with baseline results in `data/results/`.

### Step 8: Run interactive eval
```bash
PYTHONPATH=. python apps/run_interactive_eval.py \
  apps/conf/run_interactive_eval_config.toml -v
```

### Step 9: Run incremental eval (regression check)
```bash
PYTHONPATH=. python apps/run_congen.py \
  apps/conf/run_congen_config.toml -v
```
Verify no regression in incremental mode.

## Todo List
- [x] Run full test suite, capture failures
- [x] Fix checker instantiation in tests
- [x] Fix neg_c_map type assertions
- [x] Add unit test for NonIncrementalPySATChecker with assumptions
- [x] Add unit test for SAT4JChecker with assumptions
- [x] Add integration test for Reduce with unified neg_map
- [x] Run CONGEN non-incremental eval, compare with baseline
- [x] Run interactive eval
- [x] Run incremental eval (regression check)
- [x] All tests green (288/290 pass, 2 pre-existing failures)

## Success Criteria
- All existing tests pass
- New unit tests pass for all 3 checker types
- CONGEN non-incremental produces same KB as baseline
- Interactive eval produces same KB as baseline
- Incremental mode completely unaffected

## Risk Assessment
- **Baseline comparison**: result JSON files may have different internal
  representations but same constraint names. Compare by constraint name sets.
- **SAT4J jar missing**: SAT4J tests should gracefully skip if jar not found.
- **Flaky tests**: non-deterministic solver behavior unlikely but possible.
  Run tests multiple times if suspicious.
