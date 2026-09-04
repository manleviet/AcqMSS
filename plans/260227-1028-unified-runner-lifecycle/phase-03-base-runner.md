# Phase 03: Extract BaseRunner ABC

## Context
- Parent: [plan.md](plan.md)
- Depends on: Phase 01

## Overview
- **Priority**: High
- **Status**: Complete
- **Progress**: 100%
- **Description**: Extract BaseRunner ABC with shared constructor pattern, abstract run(), and cleanup()

## Key Insights
- Both runners share: `bias_path`, `fm_path`, `solver_name`, `feature_ids`
- Both create oracle from fm_path (ConGen in __init__, Interactive currently in run())
- Both have `run()` returning a result and `cleanup()` for resource release
- `_run_cv_loop` already duck-types the runner — BaseRunner formalizes the contract

## Requirements
- BaseRunner ABC with `__init__(bias_path, fm_path, solver_name)`
- Abstract `run(pos_ex=None, neg_ex=None, shuffle_seed=None) -> BaseRunResult`
- Concrete `cleanup()` that releases oracle
- Property `feature_ids: Dict[str, int]` (needed by CV loop for AccuracyCalculator)
- ConGenRunner and InteractiveRunner inherit BaseRunner

## Architecture

```python
class BaseRunner(ABC):
    def __init__(self, bias_path, fm_path, solver_name='glucose4'):
        self.bias_path = bias_path
        self.fm_path = fm_path
        self.solver_name = solver_name
        self.oracle = FeatureModelOracle(fm_path, use_incremental=False)

    @abstractmethod
    def run(self, pos_ex=None, neg_ex=None, shuffle_seed=None) -> BaseRunResult: ...

    @property
    @abstractmethod
    def feature_ids(self) -> Dict[str, int]: ...

    def cleanup(self):
        if hasattr(self, 'oracle') and self.oracle is not None:
            self.oracle.cleanup()
```

## Related Code Files
- **Modify**: `conacq/runners/base_runner.py` (add BaseRunner ABC alongside BaseRunResult)
- **Modify**: `conacq/runners/congen_runner.py` (inherit BaseRunner)
- **Modify**: `conacq/runners/interactive_runner.py` (inherit BaseRunner)
- **Modify**: `conacq/runners/__init__.py` (export BaseRunner)

## Implementation Steps

1. Add BaseRunner ABC to `base_runner.py`
2. Define shared `__init__` with `bias_path`, `fm_path`, `solver_name`
3. Create oracle in BaseRunner.__init__() (shared across both runners)
4. Define abstract `run()` with optional examples + shuffle_seed
5. Define abstract `feature_ids` property
6. Implement concrete `cleanup()` releasing oracle
7. Update ConGenRunner to inherit BaseRunner, call `super().__init__()`, keep `use_incremental`
8. Update InteractiveRunner to inherit BaseRunner, call `super().__init__()`, keep `max_queries`, `query_mode`
9. Remove duplicate oracle creation and cleanup logic from both runners
10. Update `__init__.py` exports

## Todo
- [x] Add BaseRunner ABC to base_runner.py
- [x] Update ConGenRunner to inherit
- [x] Update InteractiveRunner to inherit
- [x] Update __init__.py exports
- [x] Verify both runners construct correctly

## Completion Summary
- BaseRunner ABC created in base_runner.py with:
  - __init__(bias_path, fm_path, solver_name) creating oracle instance
  - abstract run() method returning BaseRunResult
  - abstract feature_ids property
  - cleanup() releasing oracle resources
- ConGenRunner inherits BaseRunner, calls super().__init__()
- InteractiveRunner inherits BaseRunner, calls super().__init__()
- Both runners follow identical build-once lifecycle
- Oracle created once per runner instance, reusable across CV folds

## Success Criteria
- Both runners inherit BaseRunner
- Oracle created once in __init__, cleaned up in cleanup()
- `feature_ids` property works on both runners
- Existing test creation patterns unchanged

## Risk Assessment
- **Oracle profiler**: ConGenRunner creates oracle without profiler; InteractiveRunner creates oracle with profiler. Solution: BaseRunner creates oracle without profiler (profiler is per-run, not per-instance).
- **Oracle use_incremental**: ConGenRunner passes `use_incremental=False` for oracle. Verify InteractiveRunner also uses non-incremental oracle.

## Next Steps
- Phase 04 uses BaseRunner to align InteractiveRunner lifecycle
