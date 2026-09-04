# Phase 1: Clean `run_congen_eval.py`

**Parent**: [plan.md](plan.md)
**Priority**: High | **Status**: pending | **Effort**: 30m

## Overview

Remove Option 1 (pre-computed result evaluation) from `run_congen_eval.py`. This code path is dead — CV mode (Option 2) already produces all needed metrics per fold.

## Key Insights

- `result` field in ModelConfig has author's own TODO: `# TODO: necessary?`
- Option 1 imports (`ConGenResultData`, `BiasData`, `AccuracyCalculator`, `generate_evaluation_report`, `generate_accuracy_report`) become unused after removal
- Option 2 (CV) is the only code path used in paper pipeline

## Related Code Files

- `apps/run_congen_eval.py` — main target
- `apps/conf/run_congen_eval_config.toml` — may reference `result` field

## Implementation Steps

1. Remove `result` field from `ModelConfig` dataclass (line 50)
2. Remove `result=m.get('result')` from `parse_models()` (line 69)
3. Remove Option 1 block in `evaluate_model()` (lines 156-207: the `if model_config.result:` block)
4. Remove `BiasData` loading that was shared with Option 1 (lines 146-148: `bias = BiasData.from_json(...)` and `bias_clauses = ...`) — check if CV block uses it
5. Clean imports: remove `BiasData`, `ConGenResultData`, `AccuracyCalculator`, `generate_evaluation_report`, `generate_accuracy_report`
6. Update module docstring (remove "Evaluate pre-computed ConGen results" mention)
7. Check `run_congen_eval_config.toml` — remove `result` fields if present in model entries

## Todo

- [ ] Remove `result` from ModelConfig
- [ ] Remove Option 1 block
- [ ] Clean unused imports
- [ ] Update docstring
- [ ] Update config file
- [ ] Run tests: `PYTHONPATH=. pytest tests/ -v`

## Success Criteria

- `run_congen_eval.py` only has CV mode
- No unused imports
- All tests pass
- Config file has no `result` references
