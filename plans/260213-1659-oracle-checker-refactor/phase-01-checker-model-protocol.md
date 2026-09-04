# Phase 1: Extract CheckerModel Protocol

## Context Links
- [Parent plan](plan.md)
- [checker.py](../../explanation/operations/algorithms/checker.py) — CheckerFactory.create_from_model

## Overview
- **Priority**: P1 (blocks all other phases)
- **Status**: pending
- **Description**: Extract a `CheckerModel` Protocol from `CheckerFactory.create_from_model`'s requirements so OracleModel and QuAcq models can use the factory without inheriting DiagnosisModel.

## Key Insights
1. `CheckerFactory.create_from_model(model: DiagnosisModel)` only uses 3 things: `model.get_kb()`, `model.get_assumptions()`, `model.use_incremental`
2. DiagnosisModel is 280+ lines with diagnosis-specific logic (constraint_map, prepare strategies, etc.) — too heavyweight for Oracle/QuAcq
3. Python Protocol enables structural subtyping — any class with the right methods works without inheritance

## Requirements
- Define `CheckerModel` Protocol with: `get_kb() -> List[List[int]]`, `get_assumptions() -> List[int]`, `use_incremental: bool`
- Update `CheckerFactory.create_from_model` type hint from `DiagnosisModel` to `CheckerModel`
- Zero behavior change — existing DiagnosisModel callers unaffected (DiagnosisModel satisfies the protocol)

## Related Code Files
### Files to Modify
- `explanation/operations/algorithms/checker.py` — add Protocol, update type hint

### Files NOT Modified
- `explanation/models/pysat_diagnosis_model.py` — DiagnosisModel already satisfies the protocol

## Implementation Steps

1. Add import at top of `checker.py`:
   ```python
   from typing import Protocol, runtime_checkable
   ```

2. Define `CheckerModel` Protocol (before CheckerFactory class):
   ```python
   @runtime_checkable
   class CheckerModel(Protocol):
       """Protocol for models compatible with CheckerFactory."""
       use_incremental: bool
       def get_kb(self) -> List[List[int]]: ...
       def get_assumptions(self) -> List[int]: ...
   ```

3. Update `CheckerFactory.create_from_model` signature:
   ```python
   @staticmethod
   def create_from_model(model: CheckerModel,
                         solver_name: str = 'glucose3',
                         profiler_instance: AbstractProfiler = None) -> ConsistencyChecker:
   ```
   Body unchanged.

4. Remove `DiagnosisModel` import from checker.py (if it was only used for the type hint).

## Todo List
- [ ] Add `CheckerModel` Protocol to checker.py
- [ ] Update `create_from_model` type hint
- [ ] Clean up unused DiagnosisModel import
- [ ] Verify existing tests still pass

## Success Criteria
- All existing tests pass unchanged
- `CheckerFactory.create_from_model` works with both DiagnosisModel and new OracleModel

## Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DiagnosisModel doesn't satisfy Protocol | Very Low | Low | It has get_kb(), get_assumptions(), use_incremental already |

## Next Steps
- Phase 2: Create OracleModel implementing CheckerModel
