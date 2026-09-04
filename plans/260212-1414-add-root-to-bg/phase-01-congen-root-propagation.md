# Phase 1: CONGEN Root Propagation to set_b

## Context Links

- Source: `acqmss/algorithms/model.py` (CONGENModel)
- Source: `acqmss/algorithms/task_preparation.py` (task prep strategies)
- Source: `apps/run_congen.py` (caller)
- Pattern: `explanation/models/task_preparation.py:461-479` (how root added to set_b)

## Overview

**Priority**: P1
**Status**: Complete
**Effort**: 1.5h

Add root_feature_id parameter to CONGENModel, propagate through IncrementalCONGENTaskPreparation and NonIncrementalCONGENTaskPreparation to populate set_b with root [1].

## Key Insights

- Original DiagnosisModel always adds root to set_b (explanation/models/task_preparation.py:461-479)
- CONGENModel bypasses DiagnosisModel construction, so root never added
- Root ID = SAT variable for feature with no parent (typically 1)
- Both incremental and non-incremental modes need implementation
- Current: `set_b` always empty (line 83 task_preparation.py comment)

## Requirements

**Functional**:
- CONGENModel.from_bias_and_examples() accepts optional root_feature_id
- If root_feature_id provided, add [root_feature_id] to set_b in incremental mode
- If root_feature_id provided, add [[root_feature_id]] to set_b in non-incremental mode
- run_congen.py extracts root from FeatureModelOracle and passes to from_bias_and_examples()

**Non-functional**:
- No impact on existing tests (all pass)
- Backward compatible: root_feature_id=None → empty set_b (current behavior)

## Architecture

### Data Flow

```
FeatureModelOracle.get_feature_ids()
    ↓ Extract root (feature with no parent, ID=1)
    ↓
CONGENModel.from_bias_and_examples(root_feature_id=1)
    ↓ Store in CONGENModel
    ↓
IncrementalCONGENTaskPreparation.prepare()
    ↓ Add [root_feature_id] to result.set_b
    ↓
IncrementalCONGENTask.set_b = [1]  # Background knowledge
```

### Modified Classes

**CONGENModel**:
```python
@dataclass
class CONGENModel:
    constraint_map: Dict[str, List[List[int]]]
    negated_constraint_map: Dict[str, List[List[int]]]
    variables: Dict[str, int]
    task_input: TaskInput
    next_tseitin_var: int = 1
    root_feature_id: Optional[int] = None  # NEW

    @classmethod
    def from_bias_and_examples(
        cls,
        bias_constraints: Dict[str, List[List[int]]],
        positive_examples: List[Dict[str, bool]],
        negative_examples: List[Dict[str, bool]],
        feature_ids: Dict[str, int],
        root_feature_id: Optional[int] = None  # NEW
    ) -> 'ConGenModel':
        ...
        return cls(
            constraint_map=bias_constraints,
            ...,
            root_feature_id=root_feature_id  # NEW
        )
```

**IncrementalCONGENTaskPreparation**:
```python
def prepare(self, model: CONGENModel) -> PreparationOutput:
    ...
    # After preparing constraints/examples
    if model.root_feature_id is not None:
        result.set_b.append(model.root_feature_id)
    ...
```

**NonIncrementalCONGENTaskPreparation**:
```python
def prepare(self, model: CONGENModel) -> PreparationOutput:
    ...
    # After preparing constraints/examples
    if model.root_feature_id is not None:
        result.set_b.append([[model.root_feature_id]])
    ...
```

## Related Code Files

**Modify**:
- `acqmss/algorithms/model.py` — Add root_feature_id field and parameter
- `acqmss/algorithms/task_preparation.py` — Add root to set_b in both strategies
- `apps/run_congen.py` — Extract root from oracle, pass to from_bias_and_examples()

**Read** (for patterns):
- `explanation/models/task_preparation.py:461-479` — How original adds root to set_b
- `acqmss/testcases/oracle.py` — How to extract root from FM

## Implementation Steps

### Step 1: Modify CONGENModel (model.py)

1. Add `root_feature_id: Optional[int] = None` field to CONGENModel dataclass (after next_tseitin_var)
2. Add `root_feature_id: Optional[int] = None` parameter to from_bias_and_examples() signature
3. Pass root_feature_id to cls() constructor in return statement

**File**: `acqmss/algorithms/model.py`
**Lines**: 37 (add field), 45 (add param), 77 (pass to constructor)

### Step 2: Modify IncrementalCONGENTaskPreparation (task_preparation.py)

1. After line 85 (before `result.next_assumption_id = id_assumption`), add:
```python
# Add root constraint to background knowledge if provided
if model.root_feature_id is not None:
    result.set_b.append(model.root_feature_id)
```

**File**: `acqmss/algorithms/task_preparation.py`
**Lines**: Insert after 85, before 86

### Step 3: Modify NonIncrementalCONGENTaskPreparation (task_preparation.py)

1. After line 254 (before logging.debug), add:
```python
# Add root constraint to background knowledge if provided
if model.root_feature_id is not None:
    result.set_b.append([[model.root_feature_id]])
```

**File**: `acqmss/algorithms/task_preparation.py`
**Lines**: Insert after 254, before 256

### Step 4: Extract root from oracle (run_congen.py)

1. After loading oracle (line 104), extract root:
```python
# Extract root feature ID (feature with no parent, typically ID=1)
feature_ids = oracle.get_feature_ids()
root_feature_id = 1  # Default: root is typically variable 1
# Alternative: extract from FM structure if needed
```

2. Pass root to from_bias_and_examples() (line 133):
```python
congen_model = CONGENModel.from_bias_and_examples(
    bias_constraints=bias_constraints,
    positive_examples=positive_examples,
    negative_examples=negative_examples,
    feature_ids=oracle.get_feature_ids(),
    root_feature_id=root_feature_id  # NEW
)
```

**File**: `apps/run_congen.py`
**Lines**: Insert after 104, modify 133-138

## Todo List

- [ ] Add root_feature_id field to CONGENModel dataclass
- [ ] Add root_feature_id param to from_bias_and_examples()
- [ ] Pass root_feature_id to constructor in from_bias_and_examples()
- [ ] Add root to set_b in IncrementalCONGENTaskPreparation.prepare()
- [ ] Add root to set_b in NonIncrementalCONGENTaskPreparation.prepare()
- [ ] Extract root_feature_id in run_congen.py (after oracle load)
- [ ] Pass root_feature_id to from_bias_and_examples() in run_congen.py
- [ ] Run mypy/pyright type check
- [ ] Run existing tests: `PYTHONPATH=. pytest tests/test_congen.py -v`
- [ ] Verify set_b contains root in debug output

## Success Criteria

- CONGENModel has root_feature_id field
- from_bias_and_examples() accepts root_feature_id parameter
- IncrementalCONGENTask.set_b = [1] when root_feature_id=1
- NonIncrementalCONGENTask.set_b = [[[1]]] when root_feature_id=1
- All existing CONGEN tests pass (no regression)
- Type checking passes

## Risk Assessment

**Low Risk**:
- Backward compatible (root_feature_id=None → empty set_b)
- Optional parameter, no impact on existing callers

**Medium Risk**:
- Root ID extraction: assumes root=1, may differ in some FMs
- Mitigation: Use flamapy FM structure to identify root (feature.is_root() or parent check)

**Testing**: All 285 tests should pass. Focus on test_congen.py for validation.

## Security Considerations

None. Pure data propagation, no external input.

## Next Steps

After completion:
- Proceed to Phase 2 (QuAcq root propagation)
- Verify set_b in debug logs contains root
- Test on REAL-FM-7 to confirm root in set_b
