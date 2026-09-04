# Phase 2: Extend extract_results.py with Eval Metrics

**Parent**: [plan.md](plan.md) | **Independent of**: Phase 1
**Priority**: Medium | **Status**: pending | **Effort**: 30m

## Overview

Read `intersected_evaluation` from `_cv_*.json` into `CVResult` dataclass. Add table generators for description/clause eval metrics using existing DRY helpers.

## Related Code Files

- `apps/extract_results.py` — main target (~621 lines)

## Implementation Steps

1. **Extend `CVResult` dataclass** with intersected eval fields:
   - `desc_accuracy`, `desc_precision`, `desc_recall`, `desc_f1` (floats, default 0.0)
   - `clause_accuracy`, `clause_precision`, `clause_recall`, `clause_f1` (floats, default 0.0)
   - `has_strategy_eval: bool = False` (flag for tables to skip missing data)

2. **Update `load_cv_result()`:**
   - Read `data.get('intersected_evaluation', {})` from JSON
   - Extract description and clause metrics if present
   - Set `has_strategy_eval = True` if data exists

3. **Add table generators:**
   - `generate_eval_table(results, mode, fmt, strategy)` — using `_compact_grid_md`/`_compact_grid_latex`
   - Cell format: `acc/prec/rec/f1` (compact) for each KB × strategy grid
   - One table per evaluation strategy (description, clause)

4. **Wire into `main()`:**
   - Add eval tables after fold metrics section
   - Only generate if any result has `has_strategy_eval == True`

## Todo

- [ ] Extend CVResult with eval fields
- [ ] Update load_cv_result()
- [ ] Add table generators
- [ ] Wire into main()

## Success Criteria

- Tables generated when eval data present
- No tables generated for old CV JSON files without eval data (graceful fallback)
- Existing tables unchanged
