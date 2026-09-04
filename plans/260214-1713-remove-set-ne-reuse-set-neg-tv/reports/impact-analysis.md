# Impact Analysis: Remove set_ne, Reuse set_neg_tv

## Summary

`ConGenTask.set_ne` and `TestCaseTask.set_neg_tv` are semantically identical: both hold negated negative test case assumption IDs. `set_ne` is redundant. This report maps all references.

## Semantic Equivalence

| Field | Class | Purpose | Populated By |
|-------|-------|---------|--------------|
| `set_neg_tv` | `TestCaseTask` (parent) | Negated negative test cases for KBDiag | `TestCaseTaskPreparationStrategy` |
| `set_ne` | `ConGenTask` (child) | Negated negative examples for CONGEN | `merge_ne_into_task()` |

Both store `List[int]` assumption IDs of negated negative examples/test cases.

## Impact Map

### Core Changes (Must Modify)

| File | Line(s) | Reference | Change |
|------|---------|-----------|--------|
| `acqmss/algorithms/task_preparation.py` | 38-51 | `ConGenTask.set_ne` field + docstring | Remove field, update docstring |
| `acqmss/algorithms/generate_ne.py` | 138 | `task.set_ne = ne_result.assumption_ids` | Change to `task.set_neg_tv` |
| `acqmss/algorithms/congen_model.py` | 170 | `return self.task.set_ne` | Change to `self.task.set_neg_tv` |
| `acqmss/algorithms/congen.py` | 72,86,93,98,102,128,138,162 | `set_ne` param name | Rename to `set_neg_tv` |
| `acqmss/algorithms/acqmss.py` | 52,60,68,77,94,98 | `set_ne` param name | Rename to `set_neg_tv` |
| `acqmss/algorithms/reduce.py` | 44,53,60,63,97,100 | `set_ne` param name | Rename to `set_neg_tv` |

### Caller Sites (Must Update)

| File | Line(s) | Current | New |
|------|---------|---------|-----|
| `acqmss/eval/congen_runner.py` | 179 | `set_ne=task.set_ne` | `set_neg_tv=task.set_neg_tv` |
| `apps/run_congen.py` | 129 | `set_ne=task.set_ne` | `set_neg_tv=task.set_neg_tv` |
| `tests/test_congen.py` | 90,134,179 | `set_ne=task.set_ne` | `set_neg_tv=task.set_neg_tv` |
| `acqmss/algorithms/interactive/quacq.py` | 436 | `set_ne=[]` | `set_neg_tv=[]` |

### Model/Getter Changes

| File | Method | Current | New |
|------|--------|---------|-----|
| `acqmss/algorithms/congen_model.py` | `get_ne()` | Returns `task.set_ne` | Rename to `get_neg_tv()` (already exists, returns `task.set_neg_tv`!) |

**Key insight**: `ConGenModel.get_neg_tv()` already exists (line 127-136) and returns `self.task.set_neg_tv`. After removing `set_ne`, `get_ne()` becomes unnecessary — callers should use `get_neg_tv()`.

### Documentation Changes

| File | Lines | Change |
|------|-------|--------|
| `CLAUDE.md` | 189 | `set_ne=model.task.set_ne` -> `set_neg_tv=model.task.set_neg_tv` |
| `docs/code-standards.md` | 261,270,293 | Update `set_ne` references |
| `docs/system-architecture.md` | 75,91,220,327,333 | Update `set_ne` references |
| `docs/codebase-summary.md` | N/A | Update if `set_ne` mentioned |

### Not Impacted

- `explanation/models/task_preparation.py` — `set_neg_tv` field definition stays unchanged
- `explanation/operations/algorithms/kbdiag.py` — already uses `set_neg_tv` param name
- `explanation/operations/algorithms/quickxplain_with_testcases.py` — already uses `set_neg_tv`
- `explanation/operations/algorithms/hsdag/labeler/` — already uses `set_neg_tv`
- `explanation/operations/pysat_testcase.py` — already uses `set_neg_tv`

## Rename Decision

The parameter name in `ConGen.acquire()`, `AcqMSS.find_mss()`, and `Reduce.reduce()` should change from `set_ne` to `set_neg_tv` to match the parent field name and the convention used in `explanation/` algorithms.

## Risk Assessment

- **Low risk**: Pure rename/field removal; no behavioral change
- **Data equivalence**: Both fields store `List[int]` assumption IDs, same data structure
- **Tests validate**: 3 test methods in `test_congen.py` cover incremental + non-incremental modes
