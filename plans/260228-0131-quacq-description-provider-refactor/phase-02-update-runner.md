# Phase 02: Update Runner to Resolve Names

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 01](phase-01-remove-from-algorithm.md)

## Overview
- **Priority:** High (completes the pattern)
- **Status:** completed
- **Description:** Runner resolves constraint names after `learn()` returns, using existing `model.resolve_kb()`

## Key Insights
- `model.resolve_kb()` already exists and is already called at line 200 for clauses
- Currently: `_, kb_clauses = self.model.resolve_kb(result.kb_assumption_ids)`
- After: `kb_names, kb_clauses = self.model.resolve_kb(result.kb_assumption_ids)`
- Then set `result.kb_constraints = kb_names` — or use `kb_names` directly in `QuAcqRunResult`

## Related Code Files

### Modify
- `conacq/runners/quacq_runner.py`

## Implementation Steps

### 1. Update `_run_oracle_mode()` (line 223-244)
- Remove `description_provider=self.model.description_provider` from `learn()` call (line 244)

### 2. Update `_run_example_mode()` (line 246-275)
- Remove `description_provider=self.model.description_provider` from `learn()` call (line 275)

### 3. Update `run()` result construction (line 199-216)
- Line 200 already does: `_, kb_clauses = self.model.resolve_kb(result.kb_assumption_ids)`
- Change to: `kb_names, kb_clauses = self.model.resolve_kb(result.kb_assumption_ids)`
- Line 204: change `kb_constraints=result.kb_constraints` to `kb_constraints=kb_names`

## Todo List
- [ ] Remove `description_provider=` kwarg from `_run_oracle_mode()` learn() call
- [ ] Remove `description_provider=` kwarg from `_run_example_mode()` learn() call
- [ ] Capture `kb_names` from existing `resolve_kb()` call
- [ ] Use `kb_names` in `QuAcqRunResult` construction

## Success Criteria
- No `description_provider` references in runner
- `kb_constraints` populated from `model.resolve_kb()` in runner layer
- Same output as before — names resolved identically

## Risk Assessment
- **Minimal:** `resolve_kb()` already called here; just using both return values now
