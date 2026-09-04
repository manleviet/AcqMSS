# Phase 01: Core Refactoring

## Context
- Parent: [plan.md](plan.md)
- Brainstorm: `plans/reports/brainstorm-260218-0137-oracle-task-preparation-extraction.md`

## Overview
- **Priority**: High
- **Status**: complete
- **Description**: Refactor FMOracleModel and FMOracleTaskPreparation to separate set_c computation concerns

## Key Insights
- `_compute_base_set_c()` recomputes every `with_configuration` call — wasteful, should cache once
- `FMOracleTaskPreparation.prepare()` already assigns model state directly (e.g., `model._assignments_start_index`)
- Step 3 in `prepare()` already computes base set_c — just needs to also assign to `model._base_set_c`
- `with_configuration` currently returns `list`; callers don't chain, so return type change is safe

## Related Code Files
- **Modify**: `conacq/oracle/fm_oracle_model.py`

## Implementation Steps

### Step 1: Add `_base_set_c` field to `FMOracleModel.__init__`
- Add `self._base_set_c: list = []` after line 51 (alongside other prepare()-populated fields)

### Step 2: Update `FMOracleTaskPreparation.prepare()`
- Add `configuration=None` parameter
- After Step 3 (line 257-258), add: `model._base_set_c = result.set_c` (cache base set_c)
- After caching base_set_c, if `configuration` provided:
  - Convert config to assignment assumptions (same logic currently in `with_configuration`)
  - `result.set_c = model._base_set_c + active_assumptions`
- Accept both dict and Configuration objects (same `hasattr(configuration, 'elements')` check)

### Step 3: Update `FMOracleModel.prepare()`
- Change signature: `def prepare(self, configuration=None) -> DiagnosisTask`
- Pass configuration to `FMOracleTaskPreparation.prepare(self, configuration)`
- Store `_base_set_c` is handled by TaskPreparation directly

### Step 4: Update `FMOracleModel.with_configuration()`
- Remove `_compute_base_set_c()` call
- Use `self._base_set_c` directly: `set_c = self._base_set_c + active_assumptions`
- Change return type: return `self` instead of `set_c`
- Update docstring

### Step 5: Remove `_compute_base_set_c()`
- Delete the method entirely (lines 114-121)

## Todo
- [x] Add `_base_set_c` field to `__init__`
- [x] Add `configuration` param to `FMOracleTaskPreparation.prepare()`
- [x] Cache `base_set_c` in prepare via `model._base_set_c`
- [x] Handle configuration in prepare (compute full set_c)
- [x] Update `FMOracleModel.prepare()` signature
- [x] Update `with_configuration` to use cached `_base_set_c` and return `self`
- [x] Remove `_compute_base_set_c()`

## Success Criteria
- `FMOracleModel` no longer has `_compute_base_set_c`
- `with_configuration` returns `self`
- `prepare(configuration)` computes full set_c when config given

## Risk Assessment
- **Low**: Internal refactoring, well-bounded changes
- Config conversion logic duplicated between `with_configuration` and `prepare` — extract helper if needed
