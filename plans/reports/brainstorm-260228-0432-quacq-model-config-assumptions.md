# Brainstorm: QuAcqModel config_to_assumptions

**Date:** 2026-02-28
**Status:** Agreed — proceeding to implementation

## Problem

`pos_assignment_to_assumption` and `neg_assignment_to_assumption` dicts passed through 5 layers:
`FMOracleModel → BGData → QuAcqTask → _learn_params_from_task() → QuAcq.learn()`

`QuAcq.learn()` has 13 parameters — cumbersome. Config→assumptions conversion logic duplicated in `FMOracleModel._config_to_assumptions()` and inline in `QuAcq._prune_rejecting_constraints()`.

## Agreed Solution

Minimal scope — only move assignment dicts behind QuAcqModel API:

1. **QuAcqModel** — add `config_to_assumptions(config: Dict[str, bool]) -> List[int]`
2. **QuAcq.__init__** — add `model: QuAcqModel = None` parameter
3. **QuAcq.learn()** — remove `pos_assignment_to_assumption`, `neg_assignment_to_assumption` params
4. **QuAcq._prune_rejecting_constraints()** — use `self.model.config_to_assumptions()` instead of raw dicts
5. **_learn_params_from_task()** — remove 2 entries
6. **Tests** — update QuAcq creation and learn() calls

### Design Decisions
- `config_to_assumptions()` does NOT include root_assumption (it's BG, not config assignment)
- `model` is optional in __init__ for backward compat
- Legacy fallback `_prune_rejecting_constraints_legacy()` still works when model=None
- `root_assumption` stays as learn() param

## Files Affected
- `conacq/algorithms/quacq/quacq_model.py` — add method
- `conacq/algorithms/quacq/quacq.py` — __init__, learn(), _prune_ changes
- `conacq/runners/quacq_runner.py` — pass model to QuAcq, update _learn_params_from_task
- `tests/test_quacq.py` — update test helpers and calls
