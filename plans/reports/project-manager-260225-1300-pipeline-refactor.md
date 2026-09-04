# Project Report: Pipeline Scripts Refactor (Completion)

**Status:** COMPLETED
**Date:** 2026-02-25
**Plan:** [260225-1247-pipeline-refactor](../260225-1247-pipeline-refactor/plan.md)

## Executive Summary

Pipeline refactoring complete. 4 monolithic scripts successfully decomposed into 6 focused SRP scripts. All phases verified complete. Test suite stable at 308/310 passes with 2 pre-existing unrelated failures.

## Phases Completed

| Phase | Deliverable | Status |
|:---|:---|:---|
| 01 | Fix save_kb_result() + shared config module | ✓ completed |
| 02 | Create run_compare.py + describe_kb.py | ✓ completed |
| 03 | Create run_cv.py (unified cross-validation) | ✓ completed |
| 04 | Create run_interactive.py + simplify run_congen.py | ✓ completed |
| 05 | Refactor extract_results.py | ✓ completed |
| 06 | Cleanup old scripts + E2E test | ✓ completed |

## Key Achievements

### New Scripts Created
- **run_interactive.py** — QuAcq learning → KB output (extracted from run_interactive_eval.py)
- **run_cv.py** — Unified N-fold CV for both ConGen and Interactive algorithms
- **run_compare.py** — KB vs GroundTruth comparison (new responsibility)
- **describe_kb.py** — KB IDs → human-readable descriptions

### Scripts Refactored
- **run_congen.py** — Now uses shared config module, bg_clauses fix applied
- **extract_results.py** — Adapted to load comparison data from separate *_eval.json files

### Legacy Scripts Removed
- run_congen_eval.py (monolithic congen + eval + CV)
- run_interactive_eval.py (monolithic interactive + eval + CV)

### Shared Infrastructure
- **conacq/eval/config.py** — Unified ModelConfig, load_pipeline_config(), parse_models()
- Eliminates 3x duplication across scripts

## Design Principles Implemented

✓ KB files store IDs + bg_clauses only (no descriptions embedded)
✓ Compare script always requires bias (resolves ID→description)
✓ Enrichment delegated to presentation layer (verbose output + extract_results.py)
✓ bg_clauses consistent across all KB outputs (run_congen, run_interactive, run_cv)
✓ Single responsibility per script (learn → CV → compare → describe → extract)

## Test Results

- **Total:** 310 tests
- **Passing:** 308 (99.4%)
- **Failing:** 2 (pre-existing, unrelated to refactoring)
- **Status:** STABLE

## Code Review Findings

All code review issues addressed:

1. **DRY — find_kb_files()** — Extracted to shared utility
2. **parse_models validation** — Added type checks and error handling
3. **Type hints** — Applied throughout new scripts
4. **Interactive bg_clauses fix** — Verified in run_interactive.py output format

## Data Flow (Final Architecture)

```
Step 1: Learn KB
  run_congen.py | run_interactive.py → {name}_kb.json

Step 2: Cross-Validate
  run_cv.py → {name}_cv_{mode}.json + fold KBs

Step 3: Compare
  run_compare.py → {name}_eval_{strategy}.json

Step 4: Describe (optional)
  describe_kb.py → {name}_described.json|txt

Step 5: Extract Tables
  extract_results.py → paper tables (MD + LaTeX)
```

## Artifacts

- **Plan:** /Users/manleviet/Development/GitHub/AcqMSS/plans/260225-1247-pipeline-refactor/plan.md
- **Brainstorm:** /Users/manleviet/Development/GitHub/AcqMSS/plans/reports/brainstorm-260225-1219-pipeline-refactor.md
- **New Scripts:** apps/run_*.py (run_interactive.py, run_cv.py, run_compare.py)
- **Utility:** apps/describe_kb.py
- **Shared Config:** conacq/eval/config.py

## Outstanding Items

### Documentation Updates (In Progress)
- README.md updates with new pipeline workflow
- TOML config examples for run_interactive.py, run_cv.py
- Pipeline usage guide in docs/

### Deferred (Low Priority)
- Profiler metric optimization in run_interactive.py (can refactor later)
- Advanced run_compare.py batch mode enhancements

## Sign-Off

All 6 phases marked completed. Test suite stable. Code review issues resolved. Ready for documentation updates and downstream integration.

Refactoring successfully delivers:
- Reduced cyclomatic complexity per script
- Eliminated configuration duplication
- Clear separation of concerns
- Flexible pipeline orchestration (pick script combinations as needed)
- Backward compatible with existing data/results/ directory
