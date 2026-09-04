# Test Execution Report
**Date:** 2026-02-14 | **Time:** 15:57

## Executive Summary
- **Total Tests Run:** 40
- **Passed:** 37 (92.5%)
- **Failed:** 3 (7.5%)
- **Warnings:** 1 unknown pytest mark
- **Status:** BLOCKING FAILURES

## Test Results by Suite

### test_interactive.py
✓ **PASSED** - All 27 tests passed

```
27 passed, 1 warning in 0.49s
```

**Coverage:**
- Task creation, modification (add KB, remove bias, record query)
- Result creation, serialization, persistence
- Oracle creation and configuration
- Cached oracle functionality
- Query generation
- QuAcq algorithm
- Interactive learner
- Full integration workflow
- Evaluation framework

**Warning:** Unknown pytest.mark.slow at line 367 (non-blocking, register custom mark if needed)

---

### test_congen.py
✗ **FAILED** - 3 failures out of 13 tests

```
3 failed, 10 passed in 1.09s
```

**Test Breakdown:**
| Test Name | Status | Issue |
|-----------|--------|-------|
| test_congen_incremental_with_rs_examples | FAILED | Missing `.with_profiler()` |
| test_congen_non_incremental_with_rs_examples | FAILED | Missing `.with_profiler()` |
| test_congen_incremental_with_ff_examples | FAILED | Missing `.with_profiler()` |
| test_acqmss_empty_bias | PASSED | |
| test_acqmss_single_constraint | PASSED | |
| test_reduce_empty | PASSED | |
| test_generate_ne_empty | PASSED | |
| test_oracle_ids_match_flamapy (3 variants) | PASSED | |
| test_oracle_ids_match_bias (3 variants) | PASSED | |

---

## Failure Analysis

### ROOT CAUSE: Missing API Method

**Error:** `AttributeError: 'ConGenModelBuilder' object has no attribute 'with_profiler'`

**Location:** `/Users/manleviet/Development/GitHub/AcqMSS/tests/test_congen.py:56`

**Affected Tests:**
1. `test_congen_incremental_with_rs_examples` (line 77)
2. `test_congen_non_incremental_with_rs_examples` (line 121)
3. `test_congen_incremental_with_ff_examples` (line 166)

**Code Context:**
```python
def create_checker_and_task(...):
    model = (ConGenModelBuilder
             .from_bias_and_fm_uvl(bias_path, fm_path)
             .with_examples(examples_path)
             .use_incremental(is_incremental)
             .with_profiler(profiler)  # ← METHOD DOES NOT EXIST
             .build())
```

**Issue:** `ConGenModelBuilder` in `acqmss/algorithms/congen_model_builder.py` does NOT have a `with_profiler()` method. The class stores profiler references differently.

**Actual Available Methods:**
- `from_bias_and_fm_fide()`
- `from_bias_and_fm_uvl()`
- `with_examples()`
- `with_examples_data()`
- `use_incremental()`
- `build()` ← This is where profiler should be handled

---

## Analysis

### Test Quality
- **Interactive tests:** Comprehensive coverage, well-isolated, deterministic
- **ConGen tests:** Good functional coverage but API mismatch with builder
- **Test isolation:** No cross-test dependencies observed
- **Data files:** Conditionally skipped if test data missing (graceful degradation)

### API Issues
The test expectations don't match the `ConGenModelBuilder` API. The builder:
1. Does NOT accept profiler in constructor chain
2. Stores solver config internally with `_solver_name` and `_profiler` attributes but these are NOT initialized
3. The `build()` method references `self._solver_name` and `self._profiler` but these are never set

**Builder Bug:** Missing implementation for:
- `with_solver()` method (only `_solver_name` exists)
- `with_profiler()` method (only `_profiler` exists)
- Initialization of `_solver_name` and `_profiler` in `__init__()`

---

## Recommendations

### CRITICAL - Fix ConGenModelBuilder API
1. Add `_solver_name` and `_profiler` initialization to `__init__()`
2. Implement `with_solver(solver_name: str)` method
3. Implement `with_profiler(profiler: AbstractProfiler)` method
4. Update `build()` to use these attributes properly

### Priority 1
- Fix the three failing tests by adding missing builder methods
- Tests will pass once API is complete

### Priority 2
- Register custom pytest mark `@pytest.mark.slow` in `pytest.ini`
- Update documentation with proper builder usage

---

## Unresolved Questions
- Should `_solver_name` default to 'glucose4' if not set?
- Should profiler default to `get_global_profiler()` if not provided?
- Are there other builder methods planned that haven't been implemented yet?
