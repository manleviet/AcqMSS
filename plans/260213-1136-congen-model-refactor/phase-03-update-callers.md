# Phase 3: Update Callers and Tests

## Context Links

- [Phase 1 - Refactor CONGENModel](phase-01-refactor-congen-model.md) -- prerequisite
- [Phase 2 - Add BG support](phase-02-add-bg-support.md) -- prerequisite
- [run_congen.py](../../apps/run_congen.py) -- caller 1
- [congen_runner.py](../../conacq/eval/congen_runner.py) -- caller 2
- [test_congen.py](../../tests/test_congen.py) -- caller 3
- [__init__.py](../../conacq/algorithms/__init__.py) -- exports

## Overview

- **Priority**: P2
- **Status**: pending
- **Description**: Update all 3 callers to use `model.prepare(mode)` instead of external `CONGENTaskPreparation`, and pass `background_knowledge=[root_id]` instead of `root_feature_id=root_id`.

## Key Insights

1. All 3 callers share identical pattern: create model -> create CONGENTaskPreparation -> call prepare -> extract task
2. After refactor: create model -> call model.prepare(mode) -> access model.task
3. GenerateNE flow stays unchanged (needs checker, remains caller responsibility)
4. `CONGENTaskPreparation` import can be removed from callers -- only used internally by model now
5. `__init__.py` should still export `CONGENTaskPreparation` for advanced use cases

## Requirements

### Functional
- All callers use `model.prepare(mode)` instead of external preparation
- All callers pass `background_knowledge=[root_feature_id]`
- All callers access `model.task` instead of `output.task`
- GenerateNE flow unchanged: uses `model.task` fields
- Tests pass with identical behavior

### Non-Functional
- Remove unused `CONGENTaskPreparation` imports from callers
- Reduce duplicated code across callers

## Related Code Files

- **Modify**: `apps/run_congen.py` (lines 138-153)
- **Modify**: `acqmss/eval/congen_runner.py` (lines 158-170)
- **Modify**: `tests/test_congen.py` (lines 91-105, helper function)
- **Review**: `acqmss/algorithms/__init__.py` (keep exports)

## Implementation Steps

### Step 1: Update `apps/run_congen.py`

**Before** (lines 132-153):

```python
from conacq.algorithms import (
    ConGen,
    ConGenModel,
    ConGenTaskPreparation
)

...
congen_model = ConGenModel.from_bias_and_examples(
    bias_constraints=bias_constraints,
    positive_examples=positive_examples,
    negative_examples=negative_examples,
    feature_ids=feature_ids,
    root_feature_id=root_feature_id
)

mode = "incremental-congen_root" if is_incremental else "non-incremental-congen_root"
preparation = ConGenTaskPreparation(mode)
output = preparation.prepare(congen_model)
task = output.task
```

**After**:

```python
from conacq.algorithms import ConGen, ConGenModel

...
congen_model = ConGenModel.from_bias_and_examples(
    bias_constraints=bias_constraints,
    positive_examples=positive_examples,
    negative_examples=negative_examples,
    feature_ids=feature_ids,
    background_knowledge=[root_feature_id] if root_feature_id is not None else []
)

mode = "incremental-congen_root" if is_incremental else "non-incremental-congen_root"
congen_model.prepare(mode)
task = congen_model.task
```

Then replace all subsequent `task` references -- no change needed since variable name stays `task`.

### Step 2: Update `acqmss/eval/congen_runner.py`

**Before** (lines 157-170):

```python
from conacq.algorithms.task_preparation import ConGenTaskPreparation

...
model = CONGENModel.from_bias_and_examples(
    bias_constraints=bias_clauses,
    positive_examples=positive_examples,
    negative_examples=negative_examples,
    feature_ids=self.feature_ids
)

mode = "incremental-congen_root" if self.use_incremental else "non-incremental-congen_root"
preparation = ConGenTaskPreparation(mode)
output = preparation.prepare(model)
task = output.task
```

**After**:

```python
# Remove: from acqmss.algorithms.task_preparation import ConGenTaskPreparation
...
model = CONGENModel.from_bias_and_examples(
    bias_constraints=bias_clauses,
    positive_examples=positive_examples,
    negative_examples=negative_examples,
    feature_ids=self.feature_ids
    # No BG needed here -- congen_runner doesn't pass root_feature_id currently
)

mode = "incremental-congen_root" if self.use_incremental else "non-incremental-congen_root"
model.prepare(mode)
task = model.task
```

Note: `congen_runner.py` currently does NOT pass `root_feature_id`. Keep as-is (empty BG).

### Step 3: Update `tests/test_congen.py`

**Before** (helper function lines 67-129):

```python
from conacq.algorithms import (
    ConGen, AcqMSS, Reduce, GenerateNE,
    ConGenModel,
    ConGenTaskPreparation
)

...


def create_checker_and_task(oracle, bias, examples, is_incremental=True):
    ...
    model = ConGenModel.from_bias_and_examples(
        bias_constraints=bias_constraints,
        ...
    root_feature_id = root_id
    )

    mode = "incremental-congen_root" if is_incremental else "non-incremental-congen_root"
    preparation = ConGenTaskPreparation(mode)
    output = preparation.prepare(model)
    task = output.task
    ...
```

**After**:

```python
from conacq.algorithms import (
    ConGen, AcqMSS, Reduce, GenerateNE,
    ConGenModel
)

...


def create_checker_and_task(oracle, bias, examples, is_incremental=True):
    ...
    model = ConGenModel.from_bias_and_examples(
        bias_constraints=bias_constraints,
        ...
    background_knowledge = [root_id]
    )

    mode = "incremental-congen_root" if is_incremental else "non-incremental-congen_root"
    model.prepare(mode)
    task = model.task
    ...
```

Rest of helper (GenerateNE, checker creation) stays identical -- still uses `task` variable.

### Step 4: Review `acqmss/algorithms/__init__.py`

Keep `CONGENTaskPreparation` in exports -- still a public API for advanced users who want direct control. No changes needed.

### Step 5: Verify no other callers

Search for `CONGENTaskPreparation` and `root_feature_id` usage across codebase:

```bash
PYTHONPATH=. grep -rn "CONGENTaskPreparation" --include="*.py"
PYTHONPATH=. grep -rn "root_feature_id" --include="*.py"
```

Update any additional references found.

## Todo List

- [ ] Update `apps/run_congen.py`: use model.prepare(), background_knowledge param
- [ ] Remove `CONGENTaskPreparation` import from `apps/run_congen.py`
- [ ] Update `acqmss/eval/congen_runner.py`: use model.prepare()
- [ ] Remove `CONGENTaskPreparation` import from `acqmss/eval/congen_runner.py`
- [ ] Update `tests/test_congen.py`: use model.prepare(), background_knowledge param
- [ ] Remove `CONGENTaskPreparation` import from `tests/test_congen.py`
- [ ] Search for other `root_feature_id` / `CONGENTaskPreparation` references
- [ ] Keep `__init__.py` exports unchanged
- [ ] Run full test suite: `PYTHONPATH=. pytest tests/test_congen.py -v`
- [ ] Run type check: `mypy acqmss/ apps/ tests/test_congen.py`
- [ ] Run linting: `ruff check acqmss/ apps/ tests/test_congen.py`

## Success Criteria

- All 3 callers use `model.prepare(mode)` pattern
- No caller imports `CONGENTaskPreparation` directly
- No references to `root_feature_id` remain (except possibly in comments/docs)
- `PYTHONPATH=. pytest tests/test_congen.py -v` passes all tests
- Runtime BG content in `task.set_b` identical to before refactor
- Test assertions for `root_id in task.set_b` and `[root_id] in result.bg_clauses` still pass

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Missed caller reference | Low | Medium | Grep search in Step 5 |
| Test behavior differs | Low | High | Run full test suite, compare output |
| congen_runner BG regression | Low | Low | It never passed root_id, stays empty |
| Import removal breaks re-export | None | None | __init__.py exports unchanged |

## Security Considerations

- No security impact -- caller-level refactor only

## Next Steps

- Run full test suite to verify all phases
- Update docs if CONGENModel usage is documented
- Consider updating `congen_runner.py` to accept BG in future (separate task)
