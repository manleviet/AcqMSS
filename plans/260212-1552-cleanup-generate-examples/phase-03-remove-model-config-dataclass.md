# Phase 03: Remove ModelConfig Dataclass

## Context Links

- [generate_examples.py](../../apps/generate_examples.py) (lines 37-67)
- [generate_examples_config.toml](../../apps/conf/generate_examples_config.toml)

## Overview

- **Priority**: P2
- **Status**: completed
- **Effort**: 20m

`ModelConfig` dataclass (lines 37-44) and `parse_models()` (lines 53-67) add indirection without value. The TOML config already provides dict with exactly the same fields. Replace with direct dict access.

## Key Insights

- `ModelConfig` fields: `path`, `strategies`, `n`, `valid_configs`, `m` -- all Optional except path
- `parse_models()` just maps TOML dicts to dataclass instances 1:1
- `process_model()` accesses: `model_config.path`, `.strategies`, `.valid_configs`, `.m`
- `.n` field is never used (n_features computed from oracle at runtime)
- Direct dict access: `model['path']`, `model.get('strategies')`, etc.

## Requirements

- Remove `ModelConfig` dataclass
- Remove `parse_models()` function
- Update `process_model()` signature to accept `dict` instead of `ModelConfig`
- Remove `dataclass` import
- No behavior change

## Architecture

Before:
```
TOML -> parse_models() -> List[ModelConfig] -> process_model(ModelConfig)
```

After:
```
TOML -> config['models'] -> List[dict] -> process_model(dict)
```

## Related Code Files

- **Modify**: `apps/generate_examples.py`

## Implementation Steps

1. Remove `from dataclasses import dataclass`
2. Remove `ModelConfig` dataclass (lines 37-44)
3. Remove `parse_models()` function (lines 53-67)
4. Update `process_model()` signature: change `model_config: ModelConfig` to `model_config: Dict[str, Any]`
5. Update field access in `process_model()`:
   - `model_config.path` -> `model_config['path']`
   - `model_config.strategies` -> `model_config.get('strategies')`
   - `model_config.valid_configs` -> `model_config.get('valid_configs')`
   - `model_config.m` -> `model_config.get('m')`
6. Update `main()`: replace `models = parse_models(config)` with `models = config.get('models', [])`
7. Verify: `PYTHONPATH=. python apps/generate_examples.py apps/conf/generate_examples_config.toml -v`

## Todo List

- [x] Remove `dataclass` import
- [x] Remove `ModelConfig` class
- [x] Remove `parse_models()` function
- [x] Update `process_model()` to use dict
- [x] Update `main()` to pass dicts directly
- [x] Run verification command

## Success Criteria

- No `ModelConfig` or `parse_models` in codebase
- Example generation produces identical output
- ~20 lines saved

## Risk Assessment

- **Low risk**: TOML already returns dicts with same keys
- Tradeoff: lose IDE autocomplete on config fields, but config shape is simple and documented in TOML file
- The unused `.n` field is silently dropped (it was never read anyway)

## Next Steps

Proceed to Phase 04
