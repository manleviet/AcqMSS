# Phase 3: Update Consumers and Tests

## Context Links

- [Plan overview](plan.md)
- [Phase 1: Make task immutable](phase-01-make-task-immutable.md)
- [Phase 2: Internalize state in algorithm](phase-02-internalize-state-in-algorithm.md)
- [QuAcqRunner source](../../conacq/runners/quacq_runner.py)
- [Cross-validation source](../../conacq/eval/cross_validation.py)
- [Progressive evaluation source](../../conacq/eval/progressive_evaluation.py)
- [Tests source](../../tests/test_quacq.py)

## Overview

- **Date**: 2026-02-27
- **Priority**: P2
- **Status**: pending
- **Description**: Update QuAcqRunner, cross_validation, progressive_evaluation, and tests to work with immutable QuAcqTask (no more task.bias/learned_kb/n_queries/query_history reads). Verify all tests pass.

## Key Insights

1. **QuAcqRunner** (lines 162-165) reads/writes `task.bias` for shuffle — must shuffle `task.set_c` (a list) instead
2. **cross_validation.py** does NOT access QuAcqTask fields directly — it uses `runner.run()` which returns `QuAcqRunResult`. No changes needed.
3. **progressive_evaluation.py** does NOT access QuAcqTask fields directly — it uses `QuAcqRunResult`. No changes needed.
4. **query_generator.py** changes already handled in Phase 2
5. **Tests**: 6 test methods directly test mutable methods (`test_add_to_kb`, `test_remove_from_bias`, `test_record_query`, `test_clone`). These must be removed or rewritten. Other tests that read `task.bias` should use `task.set_c`.
6. **`__init__.py`** exports need no change (QuAcqTask still exists, just fewer methods)

## Requirements

### Functional
- QuAcqRunner.run(): shuffle `task.set_c` (list) instead of `task.bias` (deleted)
- Tests: remove tests for deleted methods; update `task.bias` reads to `task.set_c`
- All tests pass: `PYTHONPATH=. pytest tests/test_quacq.py -v`
- Full suite passes: `PYTHONPATH=. pytest tests/ -v`

### Non-Functional
- No test behavior changes for integration/algorithm tests (QuAcq still produces same results)

## Related Code Files

### Modify
- `conacq/runners/quacq_runner.py` (lines 162-165)
- `tests/test_quacq.py` (multiple test classes)

### Verify (no changes expected)
- `conacq/eval/cross_validation.py`
- `conacq/eval/progressive_evaluation.py`
- `conacq/examples/query_converter.py`
- `apps/run_quacq.py`
- `apps/run_evaluation.py`
- `apps/run_cv.py`

## Implementation Steps

### Step 1: Update QuAcqRunner.run() bias shuffle

In `conacq/runners/quacq_runner.py` (lines 162-165):

**Before**:
```python
if shuffle_seed is not None:
    keys = sorted(task.bias)
    random.Random(shuffle_seed).shuffle(keys)
    task.bias = set(keys)
    logging.debug('Shuffled bias with seed=%d', shuffle_seed)
```

**After**:
```python
if shuffle_seed is not None:
    random.Random(shuffle_seed).shuffle(task.set_c)
    logging.debug('Shuffled bias (set_c) with seed=%d', shuffle_seed)
```

Note: `task.set_c` is `List[int]` — shuffle in place works. No need for set conversion. This is actually an improvement: sets discard order, but list shuffle is meaningful for iteration order in QueryGenerator.

### Step 2: Update tests/test_quacq.py — TestQuAcqTask class

#### 2a: test_task_creation (line 386)

**Before**:
```python
assert len(task.bias) > 0
assert len(task.learned_kb) == 0
```

**After**:
```python
assert len(task.set_c) > 0
```

Remove `learned_kb` assertion (field no longer exists).

#### 2b: test_bias_has_clause_mappings (line 398)

**Before**:
```python
for aid in task.bias:
    assert aid in task.constraint_clauses
    assert aid in task.negated_clauses
```

**After**:
```python
for aid in task.set_c:
    assert aid in task.constraint_clauses
    assert aid in task.negated_clauses
```

#### 2c: DELETE test_add_to_kb (lines 406-412)

Method `add_to_kb()` no longer exists. Delete entire test.

#### 2d: DELETE test_remove_from_bias (lines 414-421)

Method `remove_from_bias()` no longer exists. Delete entire test.

#### 2e: DELETE test_record_query (lines 423-430)

Method `record_query()` no longer exists. Delete entire test.

#### 2f: test_get_kb_clauses (lines 441-448)

**Before**:
```python
aid = next(iter(task.bias))
task.add_to_kb(aid)
clauses = task.get_kb_clauses()
```

**After**:
```python
aid = task.set_c[0]
clauses = task.get_kb_clauses([aid])
assert isinstance(clauses, list)
assert len(clauses) > 0
```

#### 2g: DELETE test_clone (lines 450-458)

Method `clone()` no longer exists. Delete entire test.

#### 2h: test_assumptions_and_negation_map (lines 468-475)

**Before**: `for aid in task.bias:`
**After**: `for aid in task.set_c:`

### Step 3: Update tests/test_quacq.py — TestQueryGenerator class

#### test_generate_query (line 167)

**Before** (lines 174, 180):
```python
if task.bias:
    ...
    assert tested_c_id in task.bias
```

**After**:
```python
if task.set_c:
    ...
    assert tested_c_id in task.set_c
```

### Step 4: Update tests/test_quacq.py — TestQuAcqModel class

#### test_description_provider (line 492)

**Before**: `aid = next(iter(task.bias))`
**After**: `aid = task.set_c[0]`

#### test_resolve_kb (line 501)

**Before**: `aid = next(iter(task.bias))`
**After**: `aid = task.set_c[0]`
Remove `task.add_to_kb(aid)` call.

### Step 5: Update tests/test_quacq.py — TestQuAcq class

#### test_quacq_empty_bias (line 212)

**Before**:
```python
task = QuAcqTask(
    bias=set(),
    feature_ids={'root': 1},
    id_to_feature={1: 'root'},
)
```

**After**:
```python
task = QuAcqTask(
    feature_ids={'root': 1},
    id_to_feature={1: 'root'},
)
```

(`set_c` defaults to `[]` from DiagnosisTask — empty bias)

### Step 6: Update tests/test_quacq.py — TestQuAcqWithAssumptionIDs class

#### test_quacq_empty_bias_quacq_task (line 547)

Same change as Step 5 — remove `bias=set()`.

### Step 7: Update tests/test_quacq.py — TestQueryGeneratorWithQuAcqTask class

#### test_generate_with_quacq_task (line 717)

**Before**: `assert tested_c_id in task.bias`
**After**: `assert tested_c_id in task.set_c`

### Step 8: Update tests/test_quacq.py — TestTaskCompat class

#### test_get_clause_map_quacq (line 668)

No change needed — `constraint_clauses` field still exists.

#### test_get_bg_clauses_quacq_task (line 654)

No change needed — `background_clauses` field still exists.

### Step 9: Update conacq/algorithms/quacq/__init__.py

No changes needed. `QuAcqTask` still exported, just with fewer methods.

### Step 10: Update documentation in docstrings

Update `QuAcqModel.prepare()` docstring to note that `task.set_c` holds bias IDs (not `task.bias`).

Update `QuAcqModelBuilder` docstring example to remove `task.bias` references.

### Step 11: Run tests

```bash
PYTHONPATH=. pytest tests/test_quacq.py -v
PYTHONPATH=. pytest tests/ -v
```

Verify all tests pass.

## Todo List

- [ ] Update QuAcqRunner.run() shuffle to use task.set_c
- [ ] Delete test_add_to_kb, test_remove_from_bias, test_record_query, test_clone
- [ ] Update test_task_creation: task.bias → task.set_c, remove learned_kb check
- [ ] Update test_bias_has_clause_mappings: task.bias → task.set_c
- [ ] Update test_get_kb_clauses: use get_kb_clauses([aid]) signature
- [ ] Update test_assumptions_and_negation_map: task.bias → task.set_c
- [ ] Update test_generate_query: task.bias → task.set_c
- [ ] Update test_description_provider: use task.set_c[0]
- [ ] Update test_resolve_kb: use task.set_c[0], remove add_to_kb call
- [ ] Update test_quacq_empty_bias: remove bias=set()
- [ ] Update test_quacq_empty_bias_quacq_task: remove bias=set()
- [ ] Update test_generate_with_quacq_task: task.bias → task.set_c
- [ ] Update QuAcqModel docstrings
- [ ] Run test_quacq.py — all pass
- [ ] Run full test suite — all pass

## Success Criteria

- `PYTHONPATH=. pytest tests/test_quacq.py -v` — all pass
- `PYTHONPATH=. pytest tests/ -v` — all pass
- `grep -rn "task\.bias\|task\.learned_kb\|task\.n_queries\|task\.query_history\|add_to_kb\|remove_from_bias\|record_query" conacq/ tests/` returns zero matches (excluding `_task_compat.py` comments and non-QuAcqTask code)
- QuAcqRunner produces identical QuAcqRunResult for same inputs

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missed task.bias reference in app files | Low | Apps access QuAcqRunResult, not task |
| Shuffle behavior change | Low | List shuffle is actually better than set(shuffled) |
| Test data fixtures break | Low | Only field names change, not data |

## Security Considerations

None — pure refactoring.

## Unresolved Questions

1. **Should `task.set_c` be frozen after preparation?** Currently `List[int]` (from DiagnosisTask) is mutable. QuAcqRunner shuffles it in place. If we want true immutability, we'd need a different approach for shuffle (copy `set_c` to local list before shuffle). Consider for future — not blocking for this refactoring.
