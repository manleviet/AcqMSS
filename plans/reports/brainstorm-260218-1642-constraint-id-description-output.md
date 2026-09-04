# Brainstorm: Add Constraint Descriptions to Output

## Problem Statement

In `run_congen_eval.py`, `kb_constraints`, `redundant_constraints`, and `matched_constraints` output only IDs (e.g., `"c1"`). User wants both ID and description (e.g., `{"id": "c1", "description": "A requires B"}`).

## Evaluated Approaches

### A: Change internal data types to `List[dict]` everywhere
- **Pros**: Single source of truth
- **Cons**: ~15+ file refactor. Breaks all consumers iterating `kb_constraints` as strings. Violates KISS.
- **Rejected**

### B: Pass Bias into `to_dict()` methods
- **Pros**: Clean separation
- **Cons**: Changes method signatures of 5+ data classes. Threads Bias into data structures.
- **Rejected**

### C: Enrich at output boundary (SELECTED)
- **Pros**: Zero internal changes. Single file change. KISS/YAGNI.
- **Cons**: Description lookup at presentation layer (acceptable — it's a presentation concern).

## Final Solution — Approach C

### Changes: `apps/run_congen_eval.py` only

1. **Load Bias + Oracle once** in `evaluate_model()` via `BiasIO.load_from_json()` and `GroundTruthData.from_uvl()`. Pass to `Evaluator(oracle, bias)` constructor (avoids double-loading).

2. **Helper function**:
   ```python
   def enrich_constraints(ids: List[str], bias: Bias) -> List[dict]:
       return [{"id": cid, "description": bias.get_description(cid)} for cid in ids]
   ```

3. **Enrich JSON output** — after `cv_result.to_dict()`, replace constraint ID lists with `[{id, description}]` in:
   - Each fold's `kb_constraints`, `redundant_constraints`
   - Top-level `intersected_kb`
   - Strategy evaluation: `kb_constraints`, `matched_constraints`, `missed_constraints`, `extra_constraints`

4. **Console output** (verbose only, `-v` flag):
   - Print all constraint lists with ID + description after fold results
   - Include: `kb_constraints`, `redundant_constraints`, `matched_constraints`, `missed_constraints`, `extra_constraints`

### Files Modified
- `apps/run_congen_eval.py` — add helper, load Bias early, enrich output

### No Changes To
- `conacq/eval/cross_validation.py`
- `conacq/eval/evaluator.py`
- `conacq/eval/report.py`
- `conacq/eval/result_loader.py`
- Any internal data structures

## Risk Assessment
- **Low risk**: No internal API changes, only output formatting
- **Bias loading**: Reuse loaded Bias for both enrichment and Evaluator (avoid loading twice)
- **`missed_constraints`**: In description strategy, these are already descriptions (not IDs). Handle by passing them through as-is or wrapping as `{"id": null, "description": "..."}`.

## Success Criteria
- JSON output contains `[{"id": "c1", "description": "A requires B"}]` for all constraint lists
- Console output with `-v` shows `c1: A requires B` format
- All existing tests pass unchanged
