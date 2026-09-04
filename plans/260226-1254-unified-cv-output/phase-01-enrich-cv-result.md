# Phase 1: Enrich CrossValidationResult with Descriptions

## Context Links
- `conacq/eval/cross_validation.py` — `CrossValidationFoldResult`, `CrossValidationResult`
- `conacq/eval/report.py` — `save_cv_kb_files()` (to be removed)
- `conacq/eval/result_loader.py` — `ConGenResultData`
- `conacq/eval/kb_comparator.py` — `ComparationResult`
- `conacq/bias/data_structures.py` — `Bias.get_description()`

## Overview
- Priority: P1
- Status: completed
- Enable kb_constraints to carry both IDs and descriptions; add evaluation/summary placeholders

## Key Insights
- `Bias.get_description(cid)` returns description string for any constraint ID
- Current `kb_constraints` are `List[str]` (just IDs like `"c94"`)
- `intersected_kb` is also `List[str]` (just IDs)
- Both need to become `List[Dict]` with `{"id": "c94", "description": "..."}`
- `ComparationResult` stores matched/missed/extra as flat string lists; needs enrichment for TP/FP/FN with id+description

## Requirements

### Functional
1. `CrossValidationFoldResult.to_dict()` must include `kb_constraints` as `[{"id", "description"}]`
2. `CrossValidationResult.to_dict()` must include `intersected_kb` section at top level with `kb_constraints`, `bg_clauses`, `n_kb`, `evaluation: null`
3. Each fold dict must include `evaluation: null` placeholder
4. Top-level `summary: null` placeholder
5. `ConGenResultData.from_dict()` classmethod to construct from in-memory dict (for run_compare fold iteration)
6. `ComparationResult.to_enriched_dict()` to produce TP/FP/FN with id+description objects

### Non-functional
- No breaking changes to `CrossValidationFoldResult` dataclass fields (descriptions resolved at serialization time)
- Keep file sizes under 200 lines

## Architecture

### Approach: Pass bias to serialization, not storage

Rather than adding `description` field to `CrossValidationFoldResult` dataclass (which would require threading Bias through the entire CV loop), add a **bias-aware serialization function** in `report.py`:

```python
def generate_unified_cv_dict(
    cv_result: CrossValidationResult,
    bias: Bias
) -> dict:
```

This function:
1. Takes existing `CrossValidationResult` + `Bias`
2. Resolves constraint IDs to `{"id", "description"}` objects
3. Adds `evaluation: null` and `summary: null` placeholders
4. Returns the unified dict ready for JSON serialization

### ConGenResultData.from_dict()

```python
@classmethod
def from_dict(cls, data: dict) -> 'ConGenResultData':
    """Construct from in-memory dict (fold data from unified JSON)."""
    # Extract constraint IDs from enriched format
    kb_raw = data.get('kb_constraints', [])
    if kb_raw and isinstance(kb_raw[0], dict):
        kb_ids = [c['id'] for c in kb_raw]
    else:
        kb_ids = kb_raw  # backward compat: plain string list

    stats = data.get('statistics', {})
    return cls(
        kb_constraints=kb_ids,
        n_bias=stats.get('n_bias', 0),
        n_mss=stats.get('n_mss', 0),
        n_kb=stats.get('n_kb', len(kb_ids)),
        bg_clauses=data.get('bg_clauses', []),
    )
```

### ComparationResult.to_enriched_dict()

```python
def to_enriched_dict(self, bias: Bias) -> dict:
    """Produce evaluation dict with id+description for TP/FP/FN."""
    def _enrich_ids(ids: List[str]) -> List[dict]:
        return [{"id": cid, "description": bias.get_description(cid)} for cid in ids]

    def _enrich_descriptions(descs: List[str]) -> List[dict]:
        """For FN in description strategy: no ID, just description."""
        return [{"id": None, "description": d} for d in descs]

    return {
        'metrics': self.metrics.to_dict(),
        'tp': _enrich_ids(self.matched_constraints),
        'fp': _enrich_ids(self.extra_constraints),
        'fn': (_enrich_descriptions(self.missed_constraints)
               if self.strategy == 'description'
               else [{"id": None, "description": str(c)} for c in self.missed_constraints]),
    }
```

## Related Code Files

### Modify
- `conacq/eval/report.py` — Add `generate_unified_cv_dict()`, remove `save_cv_kb_files()`
- `conacq/eval/result_loader.py` — Add `ConGenResultData.from_dict()`
- `conacq/eval/kb_comparator.py` — Add `ComparationResult.to_enriched_dict()`
- `conacq/eval/__init__.py` — Update exports (remove `save_cv_kb_files`, add `generate_unified_cv_dict`)

## Implementation Steps

### Step 1: Add `generate_unified_cv_dict()` to `report.py`

Replace `save_cv_kb_files()` with:

```python
def _enrich_constraints(constraint_ids: List[str], bias: Bias) -> List[dict]:
    """Convert constraint ID list to [{id, description}]."""
    result = []
    for cid in constraint_ids:
        desc = bias.get_description(cid) if bias.has_constraint(cid) else cid
        result.append({"id": cid, "description": desc})
    return result


def generate_unified_cv_dict(
    cv_result: CrossValidationResult,
    bias: Bias
) -> dict:
    """Build unified CV output dict with descriptions and eval placeholders.

    Args:
        cv_result: CrossValidationResult from CV loop
        bias: Bias for resolving constraint descriptions

    Returns:
        Dict ready for JSON serialization as unified CV output
    """
    folds = []
    for fr in cv_result.fold_results:
        fold_dict = fr.to_dict()
        fold_dict['kb_constraints'] = _enrich_constraints(fr.kb_constraints, bias)
        fold_dict['evaluation'] = None
        folds.append(fold_dict)

    return {
        'n_folds': cv_result.n_folds,
        'fold_accuracies': cv_result.fold_accuracies,
        'mean_accuracy': cv_result.mean_accuracy,
        'std_accuracy': cv_result.std_accuracy,
        'total_runtime_ms': cv_result.total_runtime_ms,
        'intersected_kb': {
            'kb_constraints': _enrich_constraints(cv_result.intersected_kb, bias),
            'bg_clauses': cv_result.bg_clauses,
            'n_kb': len(cv_result.intersected_kb),
            'evaluation': None,
        },
        'folds': folds,
        'performance': cv_result.performance.to_dict(),
        'summary': None,
    }
```

### Step 2: Add `ConGenResultData.from_dict()` to `result_loader.py`

Add classmethod that handles both enriched `[{"id", "description"}]` and legacy `["c1", "c2"]` formats.

### Step 3: Add `ComparationResult.to_enriched_dict()` to `kb_comparator.py`

Returns dict with `metrics`, `tp`, `fp`, `fn` — each item has `id` + `description`.

### Step 4: Remove `save_cv_kb_files` from `report.py` and update `__init__.py`

- Delete `save_cv_kb_files()` function
- Add `generate_unified_cv_dict` to exports
- Remove `save_cv_kb_files` from exports and `__all__`

## Todo List
- [ ] Add `_enrich_constraints()` helper to `report.py`
- [ ] Add `generate_unified_cv_dict()` to `report.py`
- [ ] Remove `save_cv_kb_files()` from `report.py`
- [ ] Add `ConGenResultData.from_dict()` classmethod
- [ ] Add `ComparationResult.to_enriched_dict()` method
- [ ] Update `conacq/eval/__init__.py` exports

## Success Criteria
- `generate_unified_cv_dict()` produces dict matching target JSON structure
- `ConGenResultData.from_dict()` handles both enriched and legacy formats
- `ComparationResult.to_enriched_dict()` produces TP/FP/FN with id+description
- All existing tests still pass

## Risk Assessment
- **Risk**: Changing `kb_constraints` format may break downstream consumers
  - **Mitigation**: `ConGenResultData.from_dict()` handles both formats; `from_json()` still works for legacy files
- **Risk**: `report.py` exceeds 200 lines
  - **Mitigation**: Removing `save_cv_kb_files` offsets the new code
