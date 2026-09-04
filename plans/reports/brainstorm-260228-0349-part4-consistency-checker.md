# Brainstorm: Part 4 ConsistencyChecker for Pruning

## Problem
`_prune_rejecting_constraints` uses `violates_clauses()` (pure Boolean eval) — misses implied violations detectable only through SAT solving with BG knowledge.

## Agreed Design

### Data Flow
1. **BGData** gains 4 fields: `assignment_clauses`, `assignment_assumptions`, `pos_assignment_to_assumption`, `neg_assignment_to_assumption`
2. **FMOracleTaskPreparation.prepare()** extracts Part 4 data into BGData
3. **QuAcqTask** stores Part 4 data from BGData
4. **QuAcqModel.get_kb()/get_assumptions()** include Part 4 data
5. **Single checker** (replaces existing) — used for both Reduce and prune

### Checker Composition
- KB = QuAcqTask.set_kb (root + bias clauses) + assignment_clauses (Part 4)
- Assumptions = QuAcqTask.assumptions (root + bias) + assignment_assumptions (Part 4)

### Prune Logic Change
```python
# OLD: violates_clauses(raw_clauses, assignment)
# NEW:
config_assumptions = [pos_map[feat] if val else neg_map[feat] for feat, val in example.items()]
base = [root_assumption] + config_assumptions
if not self.checker.is_consistent(base + [aid]):
    pruned.append(aid)
```

### Key Decisions
- **BGData scope**: Full Part 4 (dicts + clauses + assumption IDs)
- **Checker count**: Single checker replaces existing (Part 4 doesn't affect Reduce — disabled assumptions auto-satisfy guarded clauses)
- **Checker lifecycle**: QuAcqRunner creates via CheckerFactory.create_from_model() (unchanged API)

### Files to Modify
| File | Change |
|------|--------|
| `conacq/oracle/bg_data.py` | Add 4 Part 4 fields |
| `conacq/oracle/fm_oracle_model.py` | Extract Part 4 into BGData |
| `conacq/algorithms/quacq/task_preparation.py` | QuAcqTask stores Part 4, prep copies from BGData |
| `conacq/algorithms/quacq/quacq_model.py` | get_kb()/get_assumptions() include Part 4 |
| `conacq/algorithms/quacq/quacq.py` | _prune uses checker.is_consistent() |
| `conacq/runners/quacq_runner.py` | _learn_params_from_task adds pos/neg dicts + root_assumption |
| `tests/test_quacq.py` | Update tests |
