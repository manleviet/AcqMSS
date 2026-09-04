# Phase 04: Create run_interactive.py + Simplify run_congen.py

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-fix-save-and-shared-config.md) (shared config, bg_clauses fix)

## Overview
- Priority: P2
- Status: completed
- Effort: 1h

Extract pure QuAcq learning into run_interactive.py. Simplify run_congen.py to use shared config.

## Key Insights
- run_interactive_eval.py currently does: learning + evaluate + CV + enrichment
- run_interactive.py should ONLY do: learning → save KB
- run_congen.py already mostly correct, just needs shared config + bg_clauses (Phase 01)

## Requirements

### run_interactive.py (NEW)
- Extract from run_interactive_eval.py: InteractiveLearner setup + learn()
- Keep profiler (BENCHMARK preset)
- No evaluation, no CV, no enrichment
- Output: `{name}_interactive_kb.json` (unified KB format: IDs + bg_clauses)
- Support: automated/interactive mode, max_queries, solver choice

### run_congen.py (SIMPLIFY)
- Use shared ModelConfig + load_pipeline_config() from conacq/eval/config.py
- Remove local ModelConfig, load_config(), parse_models()
- bg_clauses already fixed in Phase 01

## Related Code Files

### Source (extract from)
- `apps/run_interactive_eval.py` — process_model() learning logic (lines 121-204)

### Modify
- `apps/run_congen.py` — replace local config with shared module

### Create
- `apps/run_interactive.py`
- `apps/conf/run_interactive_config.toml` (example config)

## Implementation Steps

### run_interactive.py
1. CLI: `PYTHONPATH=. python apps/run_interactive.py apps/conf/run_interactive_config.toml [-v] [--interactive] [--max-queries N]`
2. Extract from run_interactive_eval.py:
   - InteractiveLearner.from_files() setup
   - learner.learn(mode, max_queries)
   - Save result via result.save() or save_kb_result()
   - Ensure bg_clauses included in output
3. Keep profiler setup (use_global_profiler + print_summary)
4. No evaluate(), no CV, no enrichment
5. Print summary table (model, queries, KB size, convergence, runtime)

### run_congen.py simplification
1. Replace local ModelConfig → import from conacq.eval.config
2. Replace local load_config() → import load_pipeline_config()
3. Replace local parse_models() → import parse_models()
4. Keep extract_sampling_type() (specific to congen naming)
5. Keep process_model() logic (ConGenRunner)

## Todo
- [ ] Create run_interactive.py with pure learning logic
- [ ] Create example TOML config
- [ ] Simplify run_congen.py imports to use shared config
- [ ] Test run_interactive.py in automated mode
- [ ] Verify KB output includes bg_clauses
- [ ] Run tests

## Success Criteria
- run_interactive.py learns KB same as current script (same n_queries, n_kb)
- Output JSON follows unified KB format
- run_congen.py still works after config simplification
- Profiler metrics printed in verbose mode
