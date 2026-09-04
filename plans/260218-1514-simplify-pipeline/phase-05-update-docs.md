# Phase 5: Update Docs & Configs

**Parent**: [plan.md](plan.md) | **Depends on**: Phase 1-4
**Priority**: Low | **Status**: pending | **Effort**: 10m

## Overview

Update documentation to reflect simplified pipeline.

## Related Docs (grep results)

- `docs/codebase-summary.md` — lists all 4 scripts, line counts, usage examples
- `docs/project-overview-pdr.md` — lists `run_congen.py` and `run_congen_eval.py`
- `docs/project-roadmap.md` — marks all 4 scripts as completed
- `docs/system-architecture.md` — references scripts in architecture diagram

## Implementation Steps

1. `docs/codebase-summary.md`:
   - Remove `evaluate_congen_results.py` entry (line 204)
   - Update `run_congen_eval.py` description and line count
   - Update `extract_results.py` line count
   - Remove `evaluate_congen_config.toml` reference if present
   - Update usage examples

2. `docs/project-roadmap.md`:
   - Remove `evaluate_congen_results.py` line (line 85)
   - Note pipeline simplification

3. `docs/system-architecture.md`:
   - Update architecture diagram if it shows pipeline flow

4. `docs/project-overview-pdr.md`:
   - Update apps listing if needed

## Todo

- [ ] Update codebase-summary.md
- [ ] Update project-roadmap.md
- [ ] Update system-architecture.md
- [ ] Update project-overview-pdr.md
- [ ] Verify all doc references consistent

## Success Criteria

- No docs reference deleted files
- Pipeline description matches actual code
