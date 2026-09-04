# Phase 05: Refactor extract_results.py

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 02](phase-02-compare-and-describe.md) (run_compare.py output format), [Phase 03](phase-03-unified-cv.md) (CV output format)

## Overview
- Priority: P2
- Status: completed
- Effort: 45m

Adapt extract_results.py to load comparison data from separate *_eval.json files (from run_compare.py) instead of embedded `intersected_evaluation` in CV JSONs.

## Key Insights
- Current: CV JSON contains both accuracy data AND strategy evaluation (tightly coupled)
- New: CV JSON has accuracy only, evaluation in separate *_eval.json
- Must still generate Tables 7, 9, 10, 11 for paper
- KB mapping (KB1=REAL-FM-7, etc.) and filename parsing need review

## Requirements
- Load *_cv_*.json for accuracy/runtime/checks data (same as before)
- Load *_eval.json for strategy evaluation data (P/R/F1) — new source
- Merge both into CVResult dataclass
- Generate same paper tables
- Backward compat: handle old CV JSONs that have embedded evaluation

## Related Code Files

### Modify
- `apps/extract_results.py` — adapt data loading

## Implementation Steps

1. **Add eval file loader**
   - `load_eval_result(filepath)` → parse *_eval.json from run_compare.py
   - Extract desc/clause P/R/F1 metrics

2. **Update load_all_results()**
   - After loading CV files, scan for matching *_eval.json
   - Match by model name + mode (e.g., `REAL-FM-7_rs_1n_eval_incremental.json`)
   - Merge eval metrics into CVResult

3. **Backward compatibility**
   - If CV JSON contains `intersected_evaluation` → use it (old format)
   - If separate *_eval.json exists → use that (new format)
   - Prefer new format when both exist

4. **Verify output** — compare generated tables with current output

## Todo
- [ ] Add load_eval_result() function
- [ ] Update load_all_results() to merge eval data
- [ ] Add backward compat for old CV JSON format
- [ ] Verify Tables 7, 9, 10, 11 output unchanged
- [ ] Test with both old and new result formats

## Success Criteria
- Paper tables identical to current output
- Works with new separated file layout
- Backward compat with existing data/results/
