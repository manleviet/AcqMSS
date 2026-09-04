# Phase 5: Tests and Cleanup

## Context Links
- `tests/test_evaluation.py` — Existing eval tests
- All files modified in Phases 1-4
- `conacq/eval/__init__.py` — Public API exports

## Overview
- Priority: P2
- Status: completed
- Verify all existing tests pass, add targeted tests for new functionality, clean up deprecated code

## Requirements

### Functional
1. All existing tests pass: `PYTHONPATH=. pytest tests/ -v`
2. New unit tests for:
   - `generate_unified_cv_dict()` — produces correct structure with descriptions
   - `ConGenResultData.from_dict()` — handles enriched and legacy formats
   - `ComparationResult.to_enriched_dict()` — produces id+description items
   - `find_cv_files()` — finds correct files
   - `compute_summary()` — correct mean/std calculation
3. Integration smoke test: run full pipeline (run_cv -> run_compare -> extract_results) on REAL-FM-7

### Non-functional
- No test mocking of real computation; use real data where possible
- Tests under 200 lines per file

## Implementation Steps

### Step 1: Run existing tests

```bash
PYTHONPATH=. pytest tests/ -v
```

Fix any breakages caused by:
- Removed `save_cv_kb_files` from `__init__.py`
- Changed `intersected_kb` format in `CrossValidationResult.to_dict()`

### Step 2: Test `generate_unified_cv_dict()`

In `tests/test_evaluation.py` or a new `tests/test_unified_output.py`:

```python
def test_generate_unified_cv_dict_structure():
    """Verify unified dict has correct top-level keys and eval placeholders."""
    # Create minimal CrossValidationResult + mock Bias
    # Assert structure: n_folds, fold_accuracies, intersected_kb (dict), folds, summary=None
    # Assert fold kb_constraints are [{id, description}]
    # Assert intersected_kb.evaluation is None
```

### Step 3: Test `ConGenResultData.from_dict()`

```python
def test_from_dict_enriched_format():
    """from_dict handles [{"id": "c1", "description": "..."}] format."""
    data = {
        'kb_constraints': [{"id": "c1", "description": "a => b"}],
        'bg_clauses': [[1]],
        'statistics': {'n_bias': 10, 'n_mss': 8, 'n_kb': 1},
    }
    result = ConGenResultData.from_dict(data)
    assert result.kb_constraints == ["c1"]
    assert result.n_kb == 1

def test_from_dict_legacy_format():
    """from_dict handles legacy ["c1", "c2"] format."""
    data = {
        'kb_constraints': ["c1", "c2"],
        'bg_clauses': [[1]],
        'statistics': {'n_bias': 10, 'n_mss': 8, 'n_kb': 2},
    }
    result = ConGenResultData.from_dict(data)
    assert result.kb_constraints == ["c1", "c2"]
```

### Step 4: Test `ComparationResult.to_enriched_dict()`

```python
def test_to_enriched_dict():
    """to_enriched_dict produces tp/fp/fn with id+description."""
    # Create ComparationResult with known matched/missed/extra
    # Call to_enriched_dict(bias)
    # Assert tp items have {"id": ..., "description": ...}
    # Assert fn items for description strategy have {"id": None, "description": ...}
```

### Step 5: Test `compute_summary()`

```python
def test_compute_summary():
    """Summary computes correct mean/std across folds."""
    data = {
        'folds': [
            {'evaluation': {'description': {'metrics': {'precision': 0.8, 'recall': 0.9, 'f1_score': 0.85}}}},
            {'evaluation': {'description': {'metrics': {'precision': 0.9, 'recall': 0.8, 'f1_score': 0.85}}}},
        ]
    }
    summary = compute_summary(data, [ComparationStrategy.DESCRIPTION])
    assert summary['description']['precision']['mean'] == 0.85
    assert summary['description']['f1_score']['std'] == 0.0
```

### Step 6: Integration smoke test

```bash
# Full pipeline on REAL-FM-7 with 2cov strategy only
PYTHONPATH=. python -m apps.run_cv apps/conf/run_cv_config.toml -v
PYTHONPATH=. python -m apps.run_compare apps/conf/run_compare_config.toml -v
PYTHONPATH=. python -m apps.extract_results apps/conf/extract_results_config.toml
```

Verify:
- Single `*_cv_*.json` files in `data/results/congen/`
- No separate `*_fold*_kb.json` or `*_intersected_kb.json` files created
- After run_compare: `evaluation` fields populated in unified files
- `summary` field populated
- extract_results produces tables with strategy eval data

### Step 7: Cleanup

1. Update `conacq/eval/__init__.py`:
   - Remove `save_cv_kb_files` from imports and `__all__`
   - Add `generate_unified_cv_dict` to imports and `__all__`
   - Add `find_cv_files` to imports and `__all__`

2. Update docstrings:
   - `run_cv.py` module docstring: mention unified JSON output
   - `run_compare.py` module docstring: mention reading/enriching unified JSON
   - `report.py`: update module docstring

3. Optionally deprecate (but keep for now):
   - `find_kb_files()` — still used by CLI mode in run_compare
   - `ConGenResultData.from_json()` — still useful for standalone KB files
   - `save_kb_result()` — may still be used by non-CV workflows

## Todo List
- [ ] Run existing tests, fix breakages
- [ ] Test `generate_unified_cv_dict()` structure
- [ ] Test `ConGenResultData.from_dict()` both formats
- [ ] Test `ComparationResult.to_enriched_dict()` output
- [ ] Test `compute_summary()` math
- [ ] Integration smoke test with real data
- [ ] Update `__init__.py` exports
- [ ] Update module docstrings

## Success Criteria
- `PYTHONPATH=. pytest tests/ -v` — all green
- Integration pipeline produces correct unified output
- No separate fold/intersected KB or eval files produced by new pipeline
- Public API updated cleanly

## Risk Assessment
- **Risk**: Existing tests import `save_cv_kb_files`
  - **Mitigation**: Search tests for usage; if found, update to use `generate_unified_cv_dict`
- **Risk**: Integration test produces different table numbers
  - **Mitigation**: Expected — old data had separate eval files, new data is embedded. Tables should show same values if comparison logic is unchanged.
