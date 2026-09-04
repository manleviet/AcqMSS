# Phase 06: Cleanup + End-to-End Test

## Context
- Parent: [plan.md](plan.md)
- Depends on: All previous phases (01-05)

## Overview
- Priority: P2
- Status: completed
- Effort: 1h

Remove old scripts, verify full pipeline works end-to-end.

## Requirements
- Remove run_congen_eval.py and run_interactive_eval.py
- Verify no imports reference removed scripts
- Full pipeline test: learn → CV → compare → describe → extract
- Update TOML example configs

## Related Code Files

### Remove
- `apps/run_congen_eval.py`
- `apps/run_interactive_eval.py`

### Verify
- No remaining imports of removed scripts
- apps/conf/ has configs for all 6 scripts

## Implementation Steps

1. **Remove old scripts**
   - Delete apps/run_congen_eval.py
   - Delete apps/run_interactive_eval.py

2. **Check references**
   - Grep for `run_congen_eval` and `run_interactive_eval` across codebase
   - Update any docs, README, comments referencing old scripts

3. **Full pipeline test**
   ```bash
   # Step 1: Learn (pick one model)
   PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v

   # Step 2: CV
   PYTHONPATH=. python apps/run_cv.py apps/conf/run_cv_config.toml -v

   # Step 3: Compare
   PYTHONPATH=. python apps/run_compare.py --kb data/results/ --bias <path> --oracle <path> -v

   # Step 4: Describe
   PYTHONPATH=. python apps/describe_kb.py --kb data/results/ --bias <path>

   # Step 5: Extract tables
   PYTHONPATH=. python apps/extract_results.py --results-dir data/results/
   ```

4. **Run test suite**: `PYTHONPATH=. pytest tests/ -v`

5. **Verify configs**
   - apps/conf/run_congen_config.toml (existing)
   - apps/conf/run_interactive_config.toml (new)
   - apps/conf/run_cv_config.toml (new)

## Todo
- [ ] Delete old scripts
- [ ] Grep for stale references
- [ ] Run full pipeline (learn → CV → compare → describe → extract)
- [ ] Run pytest
- [ ] Update README if needed
- [ ] Verify example TOML configs

## Success Criteria
- No references to old scripts remain
- Full pipeline produces correct output
- `PYTHONPATH=. pytest tests/ -v` all pass
- Paper tables generated correctly
- TOML configs exist for all scripts

## Risk
- Existing test files may reference old eval scripts → update test imports
- data/results/ may have old format files → backward compat in extract_results.py (Phase 05)
