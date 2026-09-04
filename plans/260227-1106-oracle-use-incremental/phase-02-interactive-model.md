# Phase 2: InteractiveModel use_incremental

## Context
- Parent: [plan.md](plan.md)
- Depends on: [Phase 1](phase-01-runner-oracle-plumbing.md)

## Overview
- Priority: P2
- Status: complete
- Add `use_incremental` support to InteractiveModel (future-proofing per user request)

## Key Insights
- InteractiveModel currently has no `use_incremental` — uses OneShotModel (hardcoded False)
- OneShotModel stays as-is (correct for disposable one-shot checkers)
- This is future-proofing: store the flag so it can be used when InteractiveModel gets its own persistent checker

## Related Code Files
- `conacq/algorithms/interactive/interactive_model.py` — add use_incremental property
- `conacq/runners/interactive_runner.py` — pass use_incremental to model

## Implementation Steps

1. **`InteractiveModel`** — add `use_incremental` field
   ```python
   def __init__(self) -> None:
       ...
       self.use_incremental: bool = True
   ```

2. **`InteractiveModel.from_bias`** — accept optional `use_incremental` param
   ```python
   @classmethod
   def from_bias(cls, bias_path: str, use_incremental: bool = True) -> 'InteractiveModel':
       model = cls()
       model.use_incremental = use_incremental
       ...
   ```

3. **`InteractiveRunner.__init__`** — pass `use_incremental` to model
   ```python
   self.model = InteractiveModel.from_bias(bias_path, use_incremental=use_incremental)
   ```

## Todo
- [x] Add use_incremental field to InteractiveModel.__init__
- [x] Update from_bias to accept use_incremental
- [x] Update InteractiveRunner to pass use_incremental to model

## Success Criteria
- InteractiveModel stores use_incremental value
- Value flows from config → InteractiveRunner → InteractiveModel
- No behavioral change yet (OneShotModel still used)
