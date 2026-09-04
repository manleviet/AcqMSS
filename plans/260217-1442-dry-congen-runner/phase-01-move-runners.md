# Phase 01: Move Runners to acqmss/runners/

## Context Links
- [Plan](plan.md)
- Branch: `refactor/dry-congen-runner`

## Overview
- **Priority**: High (Phase 2 depends on this)
- **Status**: pending
- **Description**: Extract ConGenRunner + InteractiveRunner from `acqmss/eval/` into new `acqmss/runners/` package

## Key Insights
- Both runners are execution harnesses (build → run → collect metrics), not evaluation logic
- Both import `PerformanceMetrics` from `acqmss.eval.performance_metrics` via relative import — needs absolute import after move
- `InteractiveRunner` has lazy import of `InteractiveLearner` to avoid circular dep — preserving as-is
- No tests directly import runner classes

## Related Code Files

**Move:**
- `acqmss/eval/congen_runner.py` → `acqmss/runners/congen_runner.py`
- `acqmss/eval/interactive_runner.py` → `acqmss/runners/interactive_runner.py`

**Create:**
- `acqmss/runners/__init__.py`

**Update imports:**
- `acqmss/eval/__init__.py` — re-export from `acqmss.runners` for backward compat
- `acqmss/eval/cross_validation.py` — line 22: `from .congen_runner import ConGenRunner` → `from acqmss.runners import ConGenRunner`; line 362: `from .interactive_runner import InteractiveRunner` → `from acqmss.runners import InteractiveRunner`

**No change needed:**
- `acqmss/__init__.py` — no direct runner imports
- `apps/run_congen.py` — doesn't use runners yet (Phase 2)

## Implementation Steps

1. Create `acqmss/runners/__init__.py`:
   ```python
   from .congen_runner import ConGenRunner, ConGenRunResult
   from .interactive_runner import InteractiveRunner, InteractiveRunResult

   __all__ = [
       'ConGenRunner', 'ConGenRunResult',
       'InteractiveRunner', 'InteractiveRunResult',
   ]
   ```

2. Move `acqmss/eval/congen_runner.py` → `acqmss/runners/congen_runner.py`:
   - Change `from .performance_metrics import PerformanceMetrics` → `from acqmss.eval.performance_metrics import PerformanceMetrics`

3. Move `acqmss/eval/interactive_runner.py` → `acqmss/runners/interactive_runner.py`:
   - Change `from .performance_metrics import PerformanceMetrics` → `from acqmss.eval.performance_metrics import PerformanceMetrics`

4. Update `acqmss/eval/__init__.py`:
   - Replace direct imports with re-exports:
     ```python
     # Runners (re-exported from acqmss.runners for backward compat)
     from conacq.runners import ConGenRunner, ConGenRunResult
     from conacq.runners import InteractiveRunner, InteractiveRunResult
     ```

5. Update `acqmss/eval/cross_validation.py`:
   - Line 22: `from .congen_runner import ConGenRunner` → `from acqmss.runners import ConGenRunner`
   - Line 362: `from .interactive_runner import InteractiveRunner` → `from acqmss.runners import InteractiveRunner`

6. Delete old files:
   - `acqmss/eval/congen_runner.py`
   - `acqmss/eval/interactive_runner.py`

7. Run validation:
   ```bash
   PYTHONPATH=. python -c "from acqmss.runners import ConGenRunner, InteractiveRunner; print('OK')"
   PYTHONPATH=. python -c "from acqmss.eval import ConGenRunner, InteractiveRunner; print('backward compat OK')"
   PYTHONPATH=. pytest tests/ -v
   ```

## Todo List
- [ ] Create `acqmss/runners/__init__.py`
- [ ] Move + fix imports in `congen_runner.py`
- [ ] Move + fix imports in `interactive_runner.py`
- [ ] Update `acqmss/eval/__init__.py` re-exports
- [ ] Update `acqmss/eval/cross_validation.py` imports
- [ ] Delete old files
- [ ] Validate imports + tests

## Success Criteria
- `from acqmss.runners import ConGenRunner` works
- `from acqmss.eval import ConGenRunner` still works (backward compat)
- All existing tests pass

## Risk Assessment
- **Low risk**: Pure mechanical move + import updates
- Circular import risk from `InteractiveRunner` lazy import — already handled in original code
