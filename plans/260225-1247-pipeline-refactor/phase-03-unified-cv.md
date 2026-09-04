# Phase 03: Create run_cv.py (Unified Cross-Validation)

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-fix-save-and-shared-config.md) (shared config)

## Overview
- Priority: P1
- Status: completed
- Effort: 1.5h

Unified CV script replacing CV logic from both run_congen_eval.py and run_interactive_eval.py.

## Key Insights
- CV orchestration (fold splitting, accuracy, intersect KB) is identical for both algorithms
- Only "train step" differs: ConGenRunner vs InteractiveLearner
- Existing functions: `n_fold_cross_validation()` and `n_fold_cross_validation_interactive()` in cross_validation.py
- No comparison/enrichment — delegated to run_compare.py (Phase 02)

## Requirements
- TOML config with `algorithm = "congen"` or `"interactive"` field
- Reuse existing CV functions from conacq/eval/cross_validation.py
- Output: `*_cv_{mode}.json` (fold results, accuracy, intersected KB — IDs only)
- Save fold KB files + intersected KB via save_cv_kb_files()
- Support: n_folds, solver modes (inc/non-inc/all), pre-generated folds, shuffle_bias

## Related Code Files

### Reuse
- `conacq/eval/cross_validation.py` — n_fold_cross_validation(), n_fold_cross_validation_interactive()
- `conacq/eval/report.py` — generate_cv_report(), save_cv_kb_files()
- `conacq/eval/__init__.py` — load_folds()
- `conacq/eval/config.py` — shared config (Phase 01)
- `conacq/examples/example_io.py` — ExampleIO
- `conacq/bias/bias_io.py` — BiasIO

### Create
- `apps/run_cv.py`
- `apps/conf/run_cv_config.toml` (example config)

## Implementation Steps

1. **Create run_cv.py CLI**
   ```
   PYTHONPATH=. python apps/run_cv.py apps/conf/run_cv_config.toml [-v] [--debug]
   ```

2. **TOML config structure**
   ```toml
   [general]
   seed = 42
   output_dir = "data/results/congen"
   verbose = false

   [evaluation]
   algorithm = "congen"  # or "interactive"
   n_folds = 5
   solver_mode = "all"   # "incremental" | "non-incremental" | "all"
   solver_name = "glucose4"
   shuffle_bias = false

   [evaluation.interactive]  # only when algorithm = "interactive"
   max_queries = 1000
   query_mode = "example_only"

   [[models]]
   name = "REAL-FM-7_rs_1n"
   oracle = "data/fms/REAL-FM-7.uvl"
   bias = "data/bias/REAL-FM-7-bias.json"
   examples = "data/examples/REAL-FM-7_rs_1n.json"
   folds_path = "data/folds/REAL-FM-7_rs_1n_folds.json"
   ```

3. **Main logic**
   - Load config, parse models
   - For each model, for each solver_mode:
     - If algorithm == "congen": call `n_fold_cross_validation()`
     - If algorithm == "interactive": call `n_fold_cross_validation_interactive()`
   - Generate CV report (print)
   - Serialize CV result (to_dict()) — IDs only, no enrichment
   - Save CV JSON + fold KB files + intersected KB

4. **Remove comparison/enrichment** — no KBComparator, no enrich_constraints()

## Todo
- [ ] Create run_cv.py with algorithm dispatch
- [ ] Create example TOML config
- [ ] Test with ConGen algorithm
- [ ] Test with Interactive algorithm
- [ ] Verify output format matches current CV JSONs (minus evaluation fields)

## Success Criteria
- run_cv.py produces same CV results (accuracy, fold KBs) as current scripts
- Output JSON has no `intersected_evaluation` or `strategy_evaluation` fields
- Works for both congen and interactive algorithms
- Pre-generated folds loading works

## Risk
- Interactive CV has extra params (max_queries, query_mode) — handle via `[evaluation.interactive]` config section
