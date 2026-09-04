# Phase 3: Extend `extract_results.py` — Read Fold Metrics

**Parent**: [plan.md](plan.md) | **Independent of**: Phase 1-2
**Priority**: Medium | **Status**: pending | **Effort**: 40m

## Overview

`_cv_*.json` contains per-fold `metrics` (precision, recall, F1, specificity, TP/TN/FP/FN) but `extract_results.py` ignores them. Extend to read and expose these metrics for paper tables.

## Key Insights

Each fold in `_cv_*.json` has:
```json
"metrics": {
    "accuracy": 0.333,
    "precision": 1.0,
    "recall": 0.2,
    "f1_score": 0.333,
    "specificity": 1.0,
    "true_positives": 1,
    "true_negatives": 1,
    "false_positives": 0,
    "false_negatives": 4
}
```

## Related Code Files

- `apps/extract_results.py` — main target

## Implementation Steps

1. Add fields to `CVResult` dataclass:
   - `precision_mean`, `precision_std`
   - `recall_mean`, `recall_std`
   - `f1_mean`, `f1_std`
   - `specificity_mean`, `specificity_std`

2. Update `load_cv_result()`:
   - Iterate `data['folds']` to collect `metrics.precision`, `metrics.recall`, `metrics.f1_score`, `metrics.specificity`
   - Compute mean/std for each
   - Handle missing metrics gracefully (old files may lack them)

3. Add table generators (if needed for paper):
   - Precision/Recall/F1 compact table (MD + LaTeX)
   - Or integrate into existing accuracy tables

4. Wire new tables into `main()` output

## Todo

- [ ] Extend `CVResult` dataclass
- [ ] Update `load_cv_result()` with fold metric aggregation
- [ ] Add table generators for new metrics
- [ ] Test with existing `_cv_*.json` files

## Success Criteria

- `CVResult` contains precision/recall/F1 mean/std
- Tables generated with new metrics
- Existing tables unchanged
