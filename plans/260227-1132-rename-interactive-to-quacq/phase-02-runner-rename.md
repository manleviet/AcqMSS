# Phase 2: Runner Rename

## Context Links
- [Plan overview](plan.md)
- [Phase 1: Package Rename](phase-01-package-rename.md) (prerequisite)

## Overview
- **Priority**: High (runner is widely consumed)
- **Status**: pending
- **Effort**: 20m

Rename `interactive_runner.py` -> `quacq_runner.py`, rename classes `InteractiveRunner` -> `QuAcqRunner`, `InteractiveRunResult` -> `QuAcqRunResult`. Update all consumers.

## Key Insights
- `InteractiveRunner` imported by 5 consumers: `runners/__init__.py`, `eval/__init__.py`, `eval/cross_validation.py`, `apps/run_interactive.py`, `apps/run_evaluation.py`
- `InteractiveRunResult` imported by 4 consumers: `runners/__init__.py`, `eval/__init__.py`, `eval/progressive_evaluation.py`, `apps/run_interactive.py`
- Backward-compat aliases in `runners/__init__.py` keep old names working for any external code

## Related Code Files

### Rename (git mv)
| From | To |
|------|-----|
| `conacq/runners/interactive_runner.py` | `conacq/runners/quacq_runner.py` |

### Class Renames
| From | To | File |
|------|-----|------|
| `InteractiveRunner` | `QuAcqRunner` | `quacq_runner.py` |
| `InteractiveRunResult` | `QuAcqRunResult` | `quacq_runner.py` |

### Import Updates

| File | Old Import | New Import |
|------|-----------|------------|
| `conacq/runners/__init__.py` | `from .interactive_runner import InteractiveRunner, InteractiveRunResult` | `from .quacq_runner import QuAcqRunner, QuAcqRunResult` + aliases |
| `conacq/eval/__init__.py` | `from conacq.runners import InteractiveRunner, InteractiveRunResult` | `from conacq.runners import QuAcqRunner, QuAcqRunResult` + aliases |
| `conacq/eval/cross_validation.py` L403 | `from conacq.runners import InteractiveRunner` | `from conacq.runners import QuAcqRunner` |
| `conacq/eval/progressive_evaluation.py` L18 | `from conacq.runners.interactive_runner import InteractiveRunResult` | `from conacq.runners.quacq_runner import QuAcqRunResult` |
| `apps/run_interactive.py` L18 | `from conacq.runners import InteractiveRunner` | `from conacq.runners import QuAcqRunner` |
| `apps/run_evaluation.py` L20 | `from conacq.runners import InteractiveRunner, ConGenRunner` | `from conacq.runners import QuAcqRunner, ConGenRunner` |

## Implementation Steps

1. `git mv conacq/runners/interactive_runner.py conacq/runners/quacq_runner.py`
2. In `quacq_runner.py`:
   - Rename class `InteractiveRunResult` -> `QuAcqRunResult`
   - Rename class `InteractiveRunner` -> `QuAcqRunner`
   - Update docstrings/comments referencing old names
   - Update lazy import from `conacq.algorithms.quacq.quacq_model` (already done in Phase 1)
   - Update lazy import from `conacq.algorithms.quacq.quacq` (already done in Phase 1)
   - Update logging message: `'InteractiveRunner.run'` -> `'QuAcqRunner.run'`
3. Update `conacq/runners/__init__.py`:
   - `from .quacq_runner import QuAcqRunner, QuAcqRunResult`
   - Add backward-compat aliases: `InteractiveRunner = QuAcqRunner`, `InteractiveRunResult = QuAcqRunResult`
   - Update `__all__` to include both new and old names
   - Update module docstring
4. Update `conacq/eval/__init__.py`:
   - Import new names; add backward-compat aliases in `__all__`
5. Update `conacq/eval/cross_validation.py` L403: `QuAcqRunner`
6. Update `conacq/eval/progressive_evaluation.py` L18: `from conacq.runners.quacq_runner import QuAcqRunResult`
7. Update `apps/run_interactive.py` L18: `QuAcqRunner` (will be renamed in Phase 3, but fix import now)
8. Update `apps/run_evaluation.py` L20: `QuAcqRunner`
9. Delete `conacq/runners/__pycache__/` (if exists)
10. Run `PYTHONPATH=. pytest tests/ -v`

## Todo List

- [ ] git mv interactive_runner.py -> quacq_runner.py
- [ ] Rename InteractiveRunner -> QuAcqRunner (class + docstrings)
- [ ] Rename InteractiveRunResult -> QuAcqRunResult (class + docstrings)
- [ ] Update runners/__init__.py (imports, aliases, __all__)
- [ ] Update eval/__init__.py
- [ ] Update eval/cross_validation.py
- [ ] Update eval/progressive_evaluation.py
- [ ] Update apps/run_interactive.py (temporary -- Phase 3 renames file)
- [ ] Update apps/run_evaluation.py
- [ ] Delete __pycache__
- [ ] Run tests -- all pass

## Success Criteria
- `from conacq.runners import QuAcqRunner, QuAcqRunResult` works
- Backward compat: `InteractiveRunner = QuAcqRunner` alias exported from `runners/__init__.py`
- All tests pass
- No `interactive_runner` import path in `.py` files (except plans/docs)

## Risk Assessment
| Risk | Impact | Mitigation |
|------|--------|------------|
| Consumer misses import update | ImportError | Backward-compat aliases in __init__.py as safety net |
| eval/__init__.py re-exports stale names | Consumers break | Update __all__ to export both old and new names |

## Next Steps
- Phase 3: App + Config + Tests + Example Mode
