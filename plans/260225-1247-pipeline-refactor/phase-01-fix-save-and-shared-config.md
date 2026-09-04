# Phase 01: Fix save_kb_result + Shared Config Module

## Context
- Parent: [plan.md](plan.md)
- Brainstorm: [brainstorm report](../reports/brainstorm-260225-1219-pipeline-refactor.md)

## Overview
- Priority: P1 (blocks all other phases)
- Status: completed
- Effort: 45m

Fix `save_kb_result()` to include bg_clauses. Extract shared config utilities (DRY).

## Key Insights
- `save_kb_result()` in `conacq/eval/report.py` lacks `bg_clauses` param
- `run_congen.py` output missing root constraint because of this
- `load_config()`, `parse_models()`, `ModelConfig` duplicated 3x across scripts

## Requirements
1. Add `bg_clauses` param to `save_kb_result()`
2. Update `run_congen.py` to pass `result.bg_clauses`
3. Create `conacq/eval/config.py` with shared utilities

## Related Code Files

### Modify
- `conacq/eval/report.py` — add bg_clauses to save_kb_result()
- `apps/run_congen.py` — pass bg_clauses when calling save_kb_result()

### Create
- `conacq/eval/config.py` — shared ModelConfig, load_pipeline_config(), parse_models()

## Implementation Steps

1. **Fix save_kb_result() in report.py**
   - Add `bg_clauses: list = None` parameter
   - Include in output dict: `'bg_clauses': bg_clauses or []`
   - Keep backward compatible (default None)

2. **Update run_congen.py**
   - Pass `result.bg_clauses` to `save_kb_result()` in `process_model()`

3. **Create conacq/eval/config.py**
   ```python
   @dataclass
   class ModelConfig:
       name: str
       oracle: str
       bias: str
       examples: str = None
       folds_path: str = None

   def load_pipeline_config(config_path: str) -> Dict[str, Any]:
       """Load TOML config file."""

   def parse_models(config: Dict) -> List[ModelConfig]:
       """Parse [[models]] section from config."""
   ```

4. **Update run_congen.py imports** to use shared config

5. **Verify**: `PYTHONPATH=. pytest tests/ -v`

## Todo
- [ ] Add bg_clauses to save_kb_result()
- [ ] Update run_congen.py to pass bg_clauses
- [ ] Create conacq/eval/config.py
- [ ] Update run_congen.py to use shared config
- [ ] Run tests

## Success Criteria
- run_congen.py output JSON includes `bg_clauses` field
- Shared config module importable by all scripts
- All existing tests pass
