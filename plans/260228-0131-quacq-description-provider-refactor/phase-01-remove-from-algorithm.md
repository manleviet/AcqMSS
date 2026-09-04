# Phase 01: Remove DescriptionProvider from Algorithm

## Context
- Parent: [plan.md](plan.md)
- Brainstorm: `plans/reports/brainstorm-260228-0131-quacq-description-provider-refactor.md`

## Overview
- **Priority:** High (core change)
- **Status:** completed
- **Description:** Remove `description_provider` param from `learn()` and name resolution from `_build_result()`

## Key Insights
- `_build_result()` has fallback `str(id)` when provider is None — confirms it's optional
- After this change, `_build_result()` should set `kb_constraints=[]` (runner fills it)
- Remove `DescriptionProvider` import from quacq.py entirely

## Related Code Files

### Modify
- `conacq/algorithms/quacq/quacq.py`

## Implementation Steps

### 1. Remove `description_provider` parameter from `learn()` (line 206)
- Remove from signature
- Remove from docstring (line 224)
- Remove from `_build_result()` call at line 365

### 2. Update `_build_result()` (line 390-433)
- Remove `description_provider` parameter (line 398)
- Remove lines 404-408 (name resolution block)
- Set `kb_constraints=[]` in QuAcqResult constructor (line 416)

### 3. Remove unused import
- Remove `from explanation.models.task_preparation import DescriptionProvider` (line 29)

## Todo List
- [ ] Remove `description_provider` param from `learn()` signature
- [ ] Remove `description_provider` from `learn()` docstring
- [ ] Remove `description_provider` from `_build_result()` signature and body
- [ ] Set `kb_constraints=[]` in result construction
- [ ] Remove `DescriptionProvider` import

## Success Criteria
- `learn()` has no `description_provider` parameter
- `_build_result()` has no name resolution logic
- `kb_constraints` defaults to empty list in result

## Risk Assessment
- **Low:** Mechanical removal, runner will fill names in Phase 02
- Between Phase 01 and 02, `kb_constraints` will be empty — acceptable for refactor sequence
