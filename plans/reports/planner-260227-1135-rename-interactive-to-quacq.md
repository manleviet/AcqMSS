# Planner Report: Rename interactive -> QuAcq + Add Example Modes

**Date**: 2026-02-27
**Plan**: `/Users/manleviet/Development/GitHub/AcqMSS/plans/260227-1132-rename-interactive-to-quacq/`

## Summary

Created 4-phase implementation plan for renaming the `conacq/algorithms/interactive/` package to `conacq/algorithms/quacq/` and adding example_only/example_first mode support to the app script.

## Research Findings

### Blast Radius Analysis
- **15 Python files** need import/class name changes
- **2 TOML configs** need section rename + content updates
- **9 docs files + README + CLAUDE.md** need text updates
- **93 total "interactive" occurrences** across docs (not all need changing -- mode string stays)

### Key Design Decisions
1. Mode string `'interactive'` stays -- it describes oracle UX, not algorithm
2. `[evaluation.interactive]` in `run_cv_config.toml` stays -- it's algorithm selection config, not package name
3. `n_fold_cross_validation_interactive` function name stays -- describes mode
4. Backward-compat aliases: `InteractiveModel = QuAcqModel`, `InteractiveRunner = QuAcqRunner`, etc.
5. Example loading follows established `run_congen.py` pattern: `ExampleIO.load_json()` -> `[e.assignments for e in examples.positive]`

### Critical Finding: ExampleSet API
`ExampleSet` has no `get_positive_assignments()` method. Must use list comprehension: `[e.assignments for e in examples.positive]`. Documented in Phase 3.

## Plan Structure

| Phase | Effort | Dependencies | Files Changed |
|-------|--------|-------------|---------------|
| 1: Package Rename | 40m | None | ~12 .py files |
| 2: Runner Rename | 20m | Phase 1 | ~7 .py files |
| 3: App + Config + Tests + Example Mode | 40m | Phase 2 | 3 renamed + 3 modified |
| 4: Docs Update | 20m | Phase 3 | 11 docs files |
| **Total** | **2h** | Sequential | **~30 files touched** |

## Files Created

- `plans/260227-1132-rename-interactive-to-quacq/plan.md`
- `plans/260227-1132-rename-interactive-to-quacq/phase-01-package-rename.md`
- `plans/260227-1132-rename-interactive-to-quacq/phase-02-runner-rename.md`
- `plans/260227-1132-rename-interactive-to-quacq/phase-03-app-config-tests.md`
- `plans/260227-1132-rename-interactive-to-quacq/phase-04-docs-update.md`
