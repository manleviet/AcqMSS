# Phase 2: Add BG (Background Knowledge) Support

## Context Links

- [Phase 1 - Refactor CONGENModel](phase-01-refactor-congen-model.md) -- prerequisite
- [CONGENModel](../../conacq/algorithms/congen_model.py) -- field change
- [CONGENTaskPreparation](../../conacq/algorithms/task_preparation.py) -- consumes BG
- [CONGENTaskPreparation.prepare() line 76](../../conacq/algorithms/task_preparation.py) -- current root_feature_id usage

## Overview

- **Priority**: P2
- **Status**: pending
- **Description**: Replace `root_feature_id: Optional[int]` with `background_knowledge: List[int]` to support arbitrary BG literals, not just root feature.

## Key Insights

1. Current `root_feature_id` is used in one place: `CONGENTaskPreparation.prepare()` line 76 appends it to `result.set_b`
2. `set_b` is `List[int]` -- already supports multiple BG literals
3. All 3 callers extract root_feature_id from oracle, pass as single int
4. Generalizing to `List[int]` is backward-compatible if callers wrap `[root_feature_id]`
5. `congen_runner.py` already has `background_clauses` param (unused) -- different concept (clauses vs literals)

## Requirements

### Functional
- `CONGENModel.background_knowledge: List[int]` replaces `root_feature_id: Optional[int]`
- `from_bias_and_examples()` accepts `background_knowledge: Optional[List[int]] = None`
- `CONGENTaskPreparation.prepare()` iterates `model.background_knowledge` instead of checking `model.root_feature_id`
- Callers pass `background_knowledge=[root_feature_id]` where they previously passed `root_feature_id=root_feature_id`

### Non-Functional
- No behavioral change -- same BG content in set_b
- Type hints updated

## Architecture

```
Before:
  model.root_feature_id = 1          # Optional[int]
  preparation: if model.root_feature_id is not None:
                   result.set_b.append(model.root_feature_id)

After:
  model.background_knowledge = [1]   # List[int]
  preparation: result.set_b.extend(model.background_knowledge)
```

## Related Code Files

- **Modify**: `acqmss/algorithms/model.py` -- field rename
- **Modify**: `acqmss/algorithms/task_preparation.py` -- consume new field

## Implementation Steps

### Step 1: Update CONGENModel field (in model.py)

In `__init__` (from Phase 1):

```python
# Before (Phase 1 state)
self.root_feature_id: Optional[int] = None

# After
self.background_knowledge: List[int] = []
```

### Step 2: Update `from_bias_and_examples()` signature

```python
@classmethod
def from_bias_and_examples(
        cls,
        bias_constraints: Dict[str, List[List[int]]],
        positive_examples: List[Dict[str, bool]],
        negative_examples: List[Dict[str, bool]],
        feature_ids: Dict[str, int],
        background_knowledge: Optional[List[int]] = None
) -> 'ConGenModel':
    ...
    model.background_knowledge = background_knowledge or []
    return model
```

### Step 3: Update CONGENTaskPreparation.prepare() (in task_preparation.py)

```python
# Before (lines 75-77)
if model.root_feature_id is not None:
    result.set_b.append(model.root_feature_id)

# After
if model.background_knowledge:
    result.set_b.extend(model.background_knowledge)
```

### Step 4: Remove `Optional[int]` import if no longer needed

Check if `Optional` is still used elsewhere in model.py. With Phase 1 changes, `Optional` is used for `_task` and `_description_provider`, so keep it.

## Todo List

- [ ] Replace `root_feature_id` field with `background_knowledge: List[int]` in `__init__`
- [ ] Update `from_bias_and_examples()` parameter: `background_knowledge: Optional[List[int]] = None`
- [ ] Update factory body: `model.background_knowledge = background_knowledge or []`
- [ ] Update `CONGENTaskPreparation.prepare()`: `result.set_b.extend(model.background_knowledge)`
- [ ] Remove old `root_feature_id` references from model.py docstring
- [ ] Run type check: `mypy acqmss/algorithms/model.py acqmss/algorithms/task_preparation.py`

## Success Criteria

- `CONGENModel` has no `root_feature_id` field
- `background_knowledge` is `List[int]`, defaults to `[]`
- `CONGENTaskPreparation` uses `extend` on BG list
- Callers updated in Phase 3 pass `[root_feature_id]`
- `set_b` content identical at runtime

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Callers still use root_feature_id before Phase 3 | Certain | Low | Apply Phases 1-3 together |
| BG order affects solver | None | None | extend preserves order |
| Empty BG breaks algorithms | Low | Low | Empty list = no BG, same as None before |

## Security Considerations

- No security impact -- field rename only

## Next Steps

- Phase 3: Update all callers to pass `background_knowledge=[root_feature_id]`
