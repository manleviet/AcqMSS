# QuAcq Test Suite Report
**Date:** 2026-02-28 | **Time:** 04:53
**Test File:** `tests/test_quacq.py`
**Command:** `PYTHONPATH=. pytest tests/test_quacq.py -v`

---

## Test Results Overview

| Metric | Value |
|--------|-------|
| **Total Tests** | 62 |
| **Passed** | 52 (83.9%) |
| **Failed** | 10 (16.1%) |
| **Skipped** | 0 |
| **Errors** | 0 |
| **Execution Time** | 1.53s |

---

## Critical Issue: API Mismatch

The test suite expects an outdated API that doesn't match the current `QuAcq` implementation.

### Root Cause
Recent refactoring unified `QueryGenerator` and `ExampleProvider` into a single `QueryProvider` class, but test expectations were not updated to reflect this change.

---

## Failed Tests (10 total)

### 1. TestQuAcq::test_quacq_learn_with_limit
**Status:** FAILED
**Error:** `AttributeError: 'QueryGenerator' object has no attribute 'generate_from_sat'`
**Location:** `conacq/algorithms/quacq/quacq.py:166`

```python
query, tested_c_id = self.query_provider.generate_from_sat(...)
```

**Issue:** Tests pass `QueryGenerator` directly to QuAcq, but the code expects `QueryProvider` which has `generate_from_sat()` method.

---

### 2. TestIntegration::test_full_learning_small_limit
**Status:** FAILED
**Error:** Same as above - `AttributeError: 'QueryGenerator' object has no attribute 'generate_from_sat'`

---

### 3. TestQuAcqWithAssumptionIDs::test_quacq_learn_with_quacq_task
**Status:** FAILED
**Error:** Same as above - `AttributeError: 'QueryGenerator' object has no attribute 'generate_from_sat'`

---

### 4. TestQuAcqWithAssumptionIDs::test_result_resolved_via_model
**Status:** FAILED
**Error:** Same as above - `AttributeError: 'QueryGenerator' object has no attribute 'generate_from_sat'`

---

### 5. TestQuAcqFactories::test_for_oracle_factory
**Status:** FAILED
**Error:** `AttributeError: 'QuAcq' object has no attribute 'query_generator'`
**Location:** `tests/test_quacq.py:642`

```python
def test_for_oracle_factory(self, oracle):
    query_gen = QueryGenerator()
    discrim_gen = DiscriminatingGenerator(...)
    quacq = QuAcq.for_oracle(checker, oracle, query_gen, discrim_gen)
    assert quacq.oracle is oracle
    assert quacq.query_generator is query_gen  # <- Wrong attribute name
    assert quacq.discriminating_generator is discrim_gen
    assert quacq.example_provider is None
```

**Issue:** Test expects `query_generator` and `example_provider` attributes that don't exist. Current implementation uses `query_provider` (unified).

---

### 6. TestQuAcqFactories::test_for_examples_factory
**Status:** FAILED
**Error:** `ImportError: cannot import name 'ExampleProvider' from 'conacq.example_generators'`
**Location:** `tests/test_quacq.py:648`

```python
from conacq.example_generators import ExampleProvider
provider = ExampleProvider([{'a': True}], seed=42)
quacq = QuAcq.for_examples(_minimal_checker(), oracle, provider)
```

**Issue:** `ExampleProvider` doesn't exist anymore (replaced by `QueryProvider`). Test API is completely outdated.

---

### 7. TestQuAcqModeValidation::test_oracle_mode_requires_query_generator
**Status:** FAILED
**Error:** `ValueError: query_provider is required (use for_oracle() or for_examples())`
**Match Expected:** `"query_generator"`
**Location:** `tests/test_quacq.py:671`

**Issue:** Test expects error message to mention "query_generator" but code says "query_provider". Attribute name changed.

---

### 8. TestQuAcqModeValidation::test_oracle_mode_requires_discrim_gen
**Status:** FAILED
**Error:** `TypeError: QuAcq.__init__() got an unexpected keyword argument 'query_generator'`
**Location:** `tests/test_quacq.py:676`

```python
quacq = QuAcq(_minimal_checker(), oracle, query_generator=QueryGenerator())
```

**Issue:** Constructor parameter renamed from `query_generator` to `query_provider`.

---

### 9. TestQuAcqModeValidation::test_example_mode_requires_provider
**Status:** FAILED
**Error:** `TypeError: QuAcq.__init__() got an unexpected keyword argument 'query_generator'`
**Location:** `tests/test_quacq.py:682`

Same issue as #8 - outdated parameter name.

---

### 10. TestQuAcqModeValidation::test_example_first_requires_query_generator
**Status:** FAILED
**Error:** `ImportError: cannot import name 'ExampleProvider' from 'conacq.example_generators'`
**Location:** `tests/test_quacq.py:688`

Same issue as #6 - `ExampleProvider` doesn't exist.

---

## Passed Tests (52 total)

### Coverage by Category
- **QuAcqResult:** 3 tests ✓
- **FeatureModelOracle:** 2 tests ✓
- **CachedOracle:** 1 test ✓
- **QueryGenerator:** 2 tests ✓
- **QuAcq Basic:** 1 test ✓
- **QuAcqTask:** 6 tests ✓
- **QuAcqModel:** 7 tests ✓
- **Assumption IDs:** 2 tests ✓
- **Task Compatibility:** 3 tests ✓
- **Background Clauses:** 4 tests ✓
- **QueryGenerator with QuAcqTask:** 1 test ✓
- **SAT Utils:** 12 tests ✓
- **Other/Validation:** 5 tests ✓

---

## Issues Summary

### Issue 1: Import Error (Fixed)
**Severity:** CRITICAL
**Status:** RESOLVED ✓

**Problem:** `QueryGenerator` not exported from `conacq/example_generators/__init__.py`
**Fix Applied:** Added import and export in `__init__.py`

```python
from .query_generator import QueryGenerator

__all__ = [
    ...
    'QueryGenerator',
    ...
]
```

---

### Issue 2: API Mismatch - QueryProvider vs QueryGenerator
**Severity:** CRITICAL
**Status:** UNRESOLVED

**Problem:** Tests instantiate `QueryGenerator` directly and pass to QuAcq, but QuAcq expects `QueryProvider`.

**Expected Behavior:**
- `QueryProvider` is the unified query provider (replaces both `QueryGenerator` + `ExampleProvider`)
- QuAcq should receive `QueryProvider` instance
- `QueryProvider.generate_from_sat()`, `generate_from_pool()`, `generate()` methods handle mode dispatch

**Current Test Issues:**
- Lines 199, 262, 445, 519: Pass `QueryGenerator()` instead of `QueryProvider()`
- Lines 640-654: Expect `query_generator` and `example_provider` attributes (don't exist)
- Lines 676, 682: Use `query_generator=` parameter (should be `query_provider=`)

---

### Issue 3: Missing ExampleProvider Class
**Severity:** CRITICAL
**Status:** UNRESOLVED

**Problem:** Tests import non-existent `ExampleProvider` class

**Lines Affected:**
- Line 648: `from conacq.example_generators import ExampleProvider`
- Line 688: Same import

**Fix Required:** Either:
1. Recreate `ExampleProvider` as wrapper around `QueryProvider` for backward compatibility, OR
2. Update all tests to use `QueryProvider` directly

---

### Issue 4: QuAcq Constructor Parameter Rename
**Severity:** HIGH
**Status:** UNRESOLVED

**Changes:**
- Old: `query_generator=`, `example_provider=`
- New: `query_provider=`, `model=`, `discriminating_generator=`

**Test Lines:**
- 676, 682, 690: Use old parameter names
- Missing parameter: `query_provider`

---

### Issue 5: Error Message Text Mismatch
**Severity:** MEDIUM
**Status:** UNRESOLVED

**Lines Affected:** 671

**Current Code Message:** `"query_provider is required (use for_oracle() or for_examples())"`
**Test Expected:** Regex match for `"query_generator"`

---

## Recommendations

### Priority 1: Update Test API Calls (BLOCKING)
Update all test instantiations to use correct API:

**Before:**
```python
query_gen = QueryGenerator()
quacq = QuAcq.for_oracle(checker, oracle, query_gen, discrim_gen)
```

**After:**
```python
query_provider = QueryProvider()
quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)
```

**Affected Methods:**
- Lines 199, 262: Update `_learn_params_from_task()` usage
- Lines 445, 519: Update test instantiation
- Lines 640-654: Fix factory test assertions
- Lines 676, 682, 690: Fix parameter names in constructor calls

### Priority 2: Create ExampleProvider Alias (OPTIONAL)
Consider backward-compat alias in `example_generators/__init__.py`:

```python
# Backward compatibility alias
ExampleProvider = QueryProvider
```

This would make tests pass without modification.

### Priority 3: Update Assertion Checks
Fix factory test assertions to check correct attributes:

```python
# OLD (fails)
assert quacq.query_generator is query_gen
assert quacq.example_provider is None

# NEW (correct)
assert quacq.query_provider is query_provider
assert quacq.discriminating_generator is discrim_gen
```

### Priority 4: Update Error Message Tests
Line 671: Update expected error message text to match new implementation.

---

## Next Steps

1. **Decide backward compatibility approach:**
   - Option A: Add `ExampleProvider` alias (1-minute fix, no test changes)
   - Option B: Update all tests to new API (thorough, aligns with refactoring)

2. **Update test assertions** to use correct attribute names (`query_provider` instead of `query_generator`/`example_provider`)

3. **Fix test instantiations** to pass `QueryProvider` instead of `QueryGenerator`

4. **Run tests again** to verify all 62 tests pass

5. **Add tests** for new `QueryProvider` unified behavior (if not already covered)

---

## Unresolved Questions

1. Was `ExampleProvider` intentionally removed or is this an oversight?
2. Should backward-compat alias be provided for `ExampleProvider`?
3. Are there other codebases/examples using old `QueryGenerator` + `ExampleProvider` API that need updating?
4. Should `QuAcq` factory methods' signatures be updated to accept `QueryProvider` more explicitly?
