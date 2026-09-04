# Phase 4: Docs Update

## Context Links
- [Plan overview](plan.md)
- [Phase 3: App + Config + Tests](phase-03-app-config-tests.md) (prerequisite)

## Overview
- **Priority**: Medium
- **Status**: pending
- **Effort**: 20m

Update 9 docs files + CLAUDE.md + README.md to reflect renamed package, classes, files, and app script.

## Key Insights
- 93 total occurrences of "interactive" across 9 docs files -- not all need changing
- Keep `'interactive'` mode string references (oracle UX mode)
- Keep `n_fold_cross_validation_interactive` function name (describes mode)
- Keep `[evaluation.interactive]` TOML section in run_cv docs
- Change: file paths, class names, import paths, app script references

## Related Code Files

### Docs to Update (with approximate occurrence counts)

| File | Occurrences | What to Change |
|------|-------------|----------------|
| `docs/quacq.md` | 28 | Import paths, class names, file paths, runner references |
| `docs/codebase-summary.md` | 19 | File table entries, class names, package paths |
| `docs/system-architecture.md` | 17 | Import examples, file references, architecture descriptions |
| `docs/eval-pipeline.md` | 14 | App script references, config file names, pipeline descriptions |
| `docs/project-roadmap.md` | 6 | App script mentions, milestone references |
| `docs/project-overview-pdr.md` | 5 | File tree, app references |
| `docs/code-standards.md` | 2 | InteractiveLearner example, facade pattern reference |
| `docs/congen.md` | 1 | Cross-reference to interactive package |
| `docs/README.md` | 1 | Package reference |
| `README.md` (root) | ~5 | Import examples, file tree, usage commands |
| `CLAUDE.md` | ~3 | Quick commands, test file reference |

## Implementation Steps

### Step 1: High-impact docs (quacq.md, codebase-summary.md)
1. `docs/quacq.md`:
   - All `conacq.algorithms.interactive` -> `conacq.algorithms.quacq`
   - `InteractiveModel` -> `QuAcqModel`
   - `InteractiveTaskPreparation` -> `QuAcqTaskPreparation`
   - `interactive_model.py` -> `quacq_model.py`
   - `interactive_task_preparation.py` -> `quacq_task_preparation.py`
   - `interactive_runner.py` -> `quacq_runner.py`
   - `InteractiveRunner` -> `QuAcqRunner`
   - `InteractiveRunResult` -> `QuAcqRunResult`
   - `run_interactive.py` -> `run_quacq.py`
   - `run_interactive_config.toml` -> `run_quacq_config.toml`

2. `docs/codebase-summary.md`:
   - Package header: "Interactive Sub-package (`interactive/`)" -> "QuAcq Sub-package (`quacq/`)"
   - File table entries for renamed files
   - Class name references
   - Runner section entries
   - App section entries
   - Config file list
   - Test file references

### Step 2: Architecture and pipeline docs
3. `docs/system-architecture.md`:
   - Import examples
   - File path references
   - Architecture diagrams/descriptions

4. `docs/eval-pipeline.md`:
   - `run_interactive.py` -> `run_quacq.py` in all usage examples
   - `run_interactive_config.toml` -> `run_quacq_config.toml`
   - Config table references

### Step 3: Other docs
5. `docs/project-roadmap.md`: app script references
6. `docs/project-overview-pdr.md`: file tree
7. `docs/code-standards.md`: `InteractiveLearner` example (keep as deprecated mention or update)
8. `docs/congen.md`: cross-reference update
9. `docs/README.md`: package reference

### Step 4: Root files
10. `README.md`: import examples, file tree, usage commands
11. `CLAUDE.md`: test file reference (`test_interactive.py` -> `test_quacq.py`), quick commands

### Selective Replacement Rules
- **DO change**: `interactive_model.py`, `interactive_task_preparation.py`, `interactive_runner.py`, `InteractiveModel`, `InteractiveRunner`, `InteractiveRunResult`, `InteractiveTaskPreparation`, `run_interactive.py`, `run_interactive_config.toml`, `test_interactive.py`, `conacq/algorithms/interactive/`, `conacq.algorithms.interactive`
- **DO NOT change**: `'interactive'` mode string, `n_fold_cross_validation_interactive`, `[evaluation.interactive]`, `--interactive` CLI flag, `InteractiveLearner` (deprecated class, stays), `InteractiveTask` (deprecated class, stays)

## Todo List

- [ ] Update docs/quacq.md
- [ ] Update docs/codebase-summary.md
- [ ] Update docs/system-architecture.md
- [ ] Update docs/eval-pipeline.md
- [ ] Update docs/project-roadmap.md
- [ ] Update docs/project-overview-pdr.md
- [ ] Update docs/code-standards.md
- [ ] Update docs/congen.md
- [ ] Update docs/README.md
- [ ] Update root README.md
- [ ] Update CLAUDE.md

## Success Criteria
- All docs reflect new naming
- No stale `conacq/algorithms/interactive` path references in docs (except deprecated class mentions)
- Mode string `'interactive'` preserved everywhere
- Usage examples compile and run correctly

## Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| Over-replacement breaks mode string references | Docs misleading | Use selective replacement, not global find-replace |
| Missed reference in large doc file | Inconsistency | Grep for `interactive` post-update, manually verify each hit |

## Next Steps
- All phases complete. Run full test suite. Commit.
