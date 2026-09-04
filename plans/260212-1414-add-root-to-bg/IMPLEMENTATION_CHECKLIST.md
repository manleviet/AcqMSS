# Implementation Checklist

Quick reference for implementing all three phases.

## Phase 1: CONGEN Root Propagation ⏱️ 1.5h

### Code Changes

- [ ] **model.py** (3 edits)
  - [ ] Line 37: Add `root_feature_id: Optional[int] = None` field
  - [ ] Line 45: Add `root_feature_id: Optional[int] = None` param to from_bias_and_examples()
  - [ ] Line 77: Pass `root_feature_id=root_feature_id` to cls() constructor

- [ ] **task_preparation.py** (2 edits)
  - [ ] Line 85-86: Add root to set_b in IncrementalCONGENTaskPreparation
    ```python
    if model.root_feature_id is not None:
        result.set_b.append(model.root_feature_id)
    ```
  - [ ] Line 254-256: Add root to set_b in NonIncrementalCONGENTaskPreparation
    ```python
    if model.root_feature_id is not None:
        result.set_b.append([[model.root_feature_id]])
    ```

- [ ] **run_congen.py** (2 edits)
  - [ ] Line 104: Extract `root_feature_id = 1`
  - [ ] Line 137: Pass `root_feature_id=root_feature_id` to from_bias_and_examples()

### Testing
- [ ] Type check: `mypy acqmss/algorithms/ apps/run_congen.py`
- [ ] Tests: `PYTHONPATH=. pytest tests/test_congen.py -v`
- [ ] Debug: Verify set_b=[1] in logs

---

## Phase 2: QuAcq Root Propagation ⏱️ 1h

### Code Changes

- [ ] **interactive/learner.py** (2 edits)
  - [ ] Line 184: Change `background=[]` to `background=[1]` in _build_task_from_bias()
  - [ ] Line 155: Change `background=bg_clauses if bg_clauses else []` to `background=bg_clauses if bg_clauses else [1]` in from_bias()

### Verification
- [ ] Line 110: Confirm from_files() calls _build_task_from_bias() ✓
- [ ] Line 223: Confirm from_examples() calls _build_task_from_bias() ✓

### Testing
- [ ] Type check: `mypy acqmss/algorithms/interactive/`
- [ ] Tests: `PYTHONPATH=. pytest tests/test_interactive.py -v`
- [ ] Debug: Verify background=[1] in logs

---

## Phase 3: Evaluator BG Union ⏱️ 0.5h

### Code Changes

- [ ] **result_loader.py**
  - [ ] Add `bg_clauses: List[List[int]] = field(default_factory=list)` to CONGENResultData

- [ ] **congen.py**
  - [ ] Check if CONGENResult has bg_clauses field, add if missing
  - [ ] Populate bg_clauses in acquire(): `bg_clauses=[[task.set_b[0]]] if task.set_b else []`

- [ ] **evaluator.py**
  - [ ] Line 183: After building kb_clauses, add BG union:
    ```python
    if hasattr(result, 'bg_clauses') and result.bg_clauses:
        for clause in result.bg_clauses:
            normalized = tuple(sorted(clause))
            kb_clauses.add(normalized)
    ```

- [ ] **interactive/learner.py**
  - [ ] Line 327: Add to CONGENResultData: `bg_clauses=[self.task.background] if self.task.background else []`

### Testing
- [ ] Type check: `mypy acqmss/eval/ acqmss/algorithms/`
- [ ] Tests: `PYTHONPATH=. pytest tests/test_evaluation.py -v`
- [ ] Debug: Verify BG union in evaluator logs

---

## Integration Testing

- [ ] Full suite: `PYTHONPATH=. pytest tests/ -v` (all 285 tests pass)
- [ ] REAL-FM-7 manual run:
  ```bash
  PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v
  ```
- [ ] Check results: Root [1] in TP (not FN) for clause eval
- [ ] Verify: Description eval unchanged (root has no description)

---

## Final Verification

- [ ] set_b contains root in CONGEN debug logs
- [ ] background contains root in QuAcq debug logs
- [ ] Clause-based FN decreases by 1 for REAL-FM-7
- [ ] All type checks pass
- [ ] All tests pass
- [ ] No regression in existing functionality

---

## Notes

- Root ID defaults to 1 (typical for feature models)
- Backward compatible: None/empty BG preserves current behavior
- BG format differs: incremental=[1], non-incremental=[[[1]]]
- Phase order: Must do 1 → 2 → 3 (dependencies)
