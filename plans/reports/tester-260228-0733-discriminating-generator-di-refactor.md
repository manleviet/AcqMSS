# Test Report: DiscriminatingGenerator DI Refactor
Date: 2026-02-28 | Suite: `tests/test_quacq.py`

## Test Results Overview
- Total: 62 | Passed: 62 | Failed: 0 | Skipped: 0
- Runtime: 1.56s
- Status: ALL PASS

## Fixes Applied (3 bugs introduced by refactor)

### 1. Stale `id_to_feature` param in test calls
- **Files**: `tests/test_quacq.py` lines 192–197, 604–609
- **Tests**: `TestQueryProvider::test_generate_from_sat`, `TestQueryProviderWithQuAcqTask::test_generate_from_sat_with_quacq_task`
- **Root cause**: Refactor dropped `id_to_feature` from `QueryProvider.generate_from_sat()` signature; tests still passed it as kwarg
- **Fix**: Removed `id_to_feature=task.id_to_feature` from both call sites

### 2. Circular import in `quacq.py`
- **File**: `conacq/algorithms/quacq/quacq.py` line 28
- **Error**: `ImportError: cannot import name 'QuAcqModel' from partially initialized module 'conacq.algorithms'`
- **Root cause**: `from .. import QuAcqModel` triggered circular import via `algorithms/__init__.py` → `acqmss/__init__` → `quacq/__init__` → `quacq.py` → back to `algorithms/__init__` before `QuAcqModel` was defined
- **Fix**: Replaced with direct sibling import `from .quacq_model import QuAcqModel`

### 3. `self.model.variables.keys()` crash when `model=None`
- **File**: `conacq/algorithms/quacq/quacq.py` line 145–146
- **Tests**: `TestQuAcq::test_quacq_empty_bias`, `TestQuAcqWithAssumptionIDs::test_quacq_empty_bias_quacq_task`, `TestQuAcqModeValidation::test_example_only_works_without_discrim_gen`
- **Root cause**: Refactor replaced `set(feature_ids.keys())` with `set(self.model.variables.keys())` — but `model` is optional (None for lightweight/test construction); the old line was even left as a comment
- **Fix**: Restored `all_variables = set(feature_ids.keys())` (removed dead replacement)

## Build Status
- No import errors, no syntax errors
- 1 pytest warning: `pytest.mark.slow` unregistered (pre-existing, not a blocker)

## Recommendations
- `from .. import X` pattern in `quacq/` subpackage risks circular imports; prefer direct sibling imports (`from .module import X`)
- Guard `self.model` usages with `if self.model is not None` where `model` is optional
- Consider removing the dead comment left alongside the replaced line

## Unresolved Questions
None.
