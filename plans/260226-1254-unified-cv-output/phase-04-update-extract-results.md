# Phase 4: Update extract_results.py for Unified Format

## Context Links
- `apps/extract_results.py` — Result extraction and table generation (755 lines)
- Phase 1-3 deliverables: unified JSON format with embedded evaluation and summary

## Overview
- Priority: P2
- Status: completed
- Update `extract_results.py` to read evaluation and summary data from inside the unified CV JSON, eliminating the need to discover separate `*_eval.json` files

## Key Insights

### Current loading logic
1. `load_cv_result()` reads `*_cv_*.json` for core CV data (accuracy, performance, folds)
2. `_find_matching_eval()` searches for separate `*_eval.json` files to get strategy evaluation
3. `load_all_results()` merges both sources

### New unified format
- Evaluation is embedded at `data['intersected_kb']['evaluation']`
- Summary is at `data['summary']` (mean/std of P, R, F1)
- Fold-level eval at `data['folds'][i]['evaluation']`
- No need to search for separate eval files

### Backward compatibility
- Must still work with old separate eval files (for any legacy data not yet re-processed)
- Priority order: unified embedded > separate eval file > nothing

## Requirements

### Functional
1. Read evaluation from unified JSON's embedded `intersected_kb.evaluation` field
2. Read summary from `summary` field for fold-level aggregated metrics
3. Fall back to separate `*_eval.json` files if embedded evaluation is null
4. Remove code that generates intersected evaluation filenames (no longer needed as primary source)

### Non-functional
- Minimal changes; no table generation changes
- Keep total file reasonable (it's already 755 lines — tables are unavoidably large)

## Related Code Files

### Modify
- `apps/extract_results.py` — `load_cv_result()`, `load_all_results()`

## Implementation Steps

### Step 1: Update `load_cv_result()` to read embedded evaluation

Current code reads strategy eval from `data.get('intersected_evaluation', {})` (old embedded format). Update to also check the new unified location:

```python
# In load_cv_result(), replace the intersected_eval extraction block:

# Try unified format first: intersected_kb.evaluation
intersected_data = data.get('intersected_kb', {})
if isinstance(intersected_data, dict):
    intersected_eval = intersected_data.get('evaluation') or {}
else:
    intersected_eval = {}

# Fallback: old embedded format
if not intersected_eval:
    intersected_eval = data.get('intersected_evaluation', {})

has_strategy_eval = bool(intersected_eval)
desc_eval = intersected_eval.get('description', {}).get('metrics', {})
clause_eval = intersected_eval.get('clause', {}).get('metrics', {})
```

### Step 2: Read summary for fold-level aggregated P/R/F1

The unified format has a `summary` field with mean/std of P, R, F1 per strategy. We can use this directly instead of computing from per-fold data. But the current `CVResult` dataclass computes fold metrics from per-fold `metrics` (accuracy metrics, not strategy eval). These are different things:

- `fold.metrics` = accuracy P/R/F1 (from AccuracyCalculator on test examples)
- `fold.evaluation` = strategy P/R/F1 (from KBComparator comparing KB vs oracle)

The current fold_precisions/recalls/f1s extraction (lines 134-147) reads fold-level **accuracy metrics**, not strategy eval. This should stay unchanged because it serves a different purpose (Table: Fold Metrics).

For **strategy evaluation summary**, the new `summary` field provides pre-computed means:

```python
# After the existing intersected_eval extraction, also read summary
summary = data.get('summary', {})
if summary:
    desc_summary = summary.get('description', {})
    clause_summary = summary.get('clause', {})
    # These could override the intersected-only values if desired
    # For now, intersected_kb eval is the primary source for tables
```

Decision: **Keep using intersected_kb evaluation** for the strategy eval tables (Tables like "Strategy Eval on Intersected KB"). The `summary` field gives fold-averaged strategy metrics which is a different view. Both are now available from the same file.

### Step 3: Update `load_all_results()` to prefer embedded over external

The current code tries `_find_matching_eval()` to load separate eval files. Update to only do this when embedded eval is absent:

```python
def load_all_results(results_dir: Path) -> Dict[str, Dict[str, Dict[str, CVResult]]]:
    """Load all CV results. Returns: {model: {strategy: {mode: CVResult}}}

    Priority: embedded eval in unified JSON > separate *_eval.json > nothing
    """
    results = {}
    for filepath in results_dir.glob('*_cv_*.json'):
        result = load_cv_result(filepath)
        if result:
            # Only look for external eval if embedded is absent
            if not result.has_strategy_eval:
                ext_eval = _find_matching_eval(results_dir, result.model,
                                               result.strategy, result.mode)
                if ext_eval:
                    # ... existing merge logic ...
                    result.has_strategy_eval = True

            results.setdefault(result.model, {}).setdefault(result.strategy, {})[result.mode] = result
    return results
```

### Step 4: Handle enriched kb_constraints format

The unified format stores `intersected_kb` as a nested object (not a flat list). The current `n_intersected` extraction reads `data.get('n_intersected', 0)`. Update to also check inside `intersected_kb`:

```python
# Current:
n_intersected = data.get('n_intersected', 0)

# New (handles both formats):
intersected_data = data.get('intersected_kb', {})
if isinstance(intersected_data, dict):
    n_intersected = intersected_data.get('n_kb', 0)
else:
    n_intersected = data.get('n_intersected', 0)
```

## Todo List
- [ ] Update `load_cv_result()` to read embedded `intersected_kb.evaluation`
- [ ] Update `n_intersected` extraction for nested `intersected_kb` format
- [ ] Update `load_all_results()` to prefer embedded eval over external files
- [ ] Keep backward compat with old format (separate eval files, flat intersected_kb list)
- [ ] Run `python -m apps.extract_results apps/conf/extract_results_config.toml` to verify

## Success Criteria
- `extract_results.py` reads evaluation from unified JSON without needing separate `*_eval.json`
- Still works with old-format files (backward compat)
- All table generators produce identical output
- No new fields needed on `CVResult` dataclass

## Risk Assessment
- **Risk**: `intersected_kb` format change (dict vs list) breaks n_intersected extraction
  - **Mitigation**: isinstance check handles both formats
- **Risk**: Summary field not used by any current table
  - **Mitigation**: Available for future tables; no current table needs to change
