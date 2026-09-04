# Plan: QuAcqModel config_to_assumptions

**Status:** in-progress
**Branch:** main
**Brainstorm:** [brainstorm report](../reports/brainstorm-260228-0432-quacq-model-config-assumptions.md)

## Overview

Move `pos/neg_assignment_to_assumption` dicts behind `QuAcqModel.config_to_assumptions()` API. Pass model to `QuAcq.__init__` instead of flat dict params.

## Implementation Steps

### Step 1: Add `config_to_assumptions()` to QuAcqModel
- File: `conacq/algorithms/quacq/quacq_model.py`
- Add method delegating to task's pos/neg dicts

### Step 2: Add `model` param to QuAcq.__init__
- File: `conacq/algorithms/quacq/quacq.py`
- Optional `model: QuAcqModel = None`

### Step 3: Update QuAcq.learn() and _prune_
- Remove `pos_assignment_to_assumption`, `neg_assignment_to_assumption` from learn()
- Update `_prune_rejecting_constraints()` to use `self.model.config_to_assumptions()`
- Condition: `if self.model and root_assumption is not None`

### Step 4: Update runner
- File: `conacq/runners/quacq_runner.py`
- Pass model to QuAcq constructor
- Remove 2 entries from `_learn_params_from_task()`

### Step 5: Update tests
- File: `tests/test_quacq.py`
- Update QuAcq creation and learn() calls

### Step 6: Run tests

## Success Criteria
- [x] All tests pass
- [x] `config_to_assumptions()` centralized in QuAcqModel
- [x] `learn()` has 2 fewer params
- [x] No regression in SAT-based pruning
