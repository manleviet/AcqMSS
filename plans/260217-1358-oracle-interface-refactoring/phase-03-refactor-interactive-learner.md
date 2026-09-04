# Phase 3: Refactor InteractiveLearner + Task Preparation

## Context Links
- [Plan overview](plan.md)
- [Phase 1: Slim Oracle](phase-01-slim-oracle-and-fm-data.md)
- InteractiveLearner: `acqmss/algorithms/interactive/learner.py`
- ConGenTaskPreparation: `acqmss/algorithms/task_preparation.py`

## Overview
- **Priority**: P1
- **Status**: complete
- **Effort**: 1.5h

InteractiveLearner uses `oracle.get_feature_ids()`, `oracle.get_root_feature()`, `oracle.get_cnf_clauses()`. ConGenTaskPreparation uses `oracle.get_root_feature()`, `oracle.get_num_constraints()`. Both should use FMData instead of querying oracle directly.

## Key Insights

### InteractiveLearner
- `_build_task_from_bias()` calls `oracle.get_feature_ids()` and `oracle.get_root_feature()` — both FM metadata
- `from_examples()` calls `oracle.get_cnf_clauses()` for FM clause caching
- `__init__` stores generic `Oracle` but `_build_task_from_bias` requires `FeatureModelOracle`
- `from_files()` and `from_examples()` create `FeatureModelOracle` internally
- `learn()` can switch to `UserPromptOracle` for interactive mode — only needs `is_valid()`

### ConGenTaskPreparation
- `prepare()` calls `oracle.get_root_feature()` and `oracle.get_num_constraints()`
- Both are FM metadata, available from FMData

## Requirements

### Functional
1. `_build_task_from_bias()` receives `FMData` instead of calling oracle metadata methods
2. `from_examples()` refactored: uses `oracle.is_valid()` per example instead of SAT-checking CNF clauses. Remove `_fm_clauses` field entirely. `get_cnf_clauses()` no longer exists on oracle.
3. `ConGenTaskPreparation.prepare()` receives `FMData` for root_feature and num_constraints
4. `InteractiveLearner.__init__` keeps `oracle: Optional[Oracle]` for runtime `is_valid()` queries
5. `from_bias()` keeps working with generic `Oracle` (only uses `is_valid()` at runtime)
<!-- Updated: Validation Session 1 - from_examples() uses oracle.is_valid(), get_cnf_clauses() removed -->

### Non-functional
- Minimal signature changes for callers

## Architecture

```
InteractiveLearner
├── __init__(task, oracle: Optional[Oracle], ...)   # oracle for is_valid() only
├── from_files(fm_path, bias_path)
│   ├── oracle = FeatureModelOracle(fm_path)
│   ├── fm_data = oracle.get_fm_data()
│   └── task = _build_task_from_bias(bias, fm_data)
├── from_examples(fm_path, bias_path, examples)
│   ├── oracle = FeatureModelOracle(fm_path)
│   ├── fm_data = oracle.get_fm_data()
│   ├── task = _build_task_from_bias(bias, fm_data)
│   └── (no _fm_clauses — uses oracle.is_valid() at runtime)
├── from_bias(bias, oracle: Oracle, ...)            # generic Oracle OK
└── _build_task_from_bias(bias, fm_data: FMData)    # static, no oracle

ConGenTaskPreparation
└── prepare(model, fm_data: FMData)                 # oracle no longer param
```

## Related Code Files

### Modify
| File | Changes |
|------|---------|
| `acqmss/algorithms/interactive/learner.py` | `_build_task_from_bias` takes FMData instead of oracle. `from_files` and `from_examples` extract FMData from oracle. |
| `acqmss/algorithms/task_preparation.py` | `ConGenTaskPreparation.prepare()` takes `fm_data: FMData` instead of `oracle: FeatureModelOracle`. Extract root_feature and num_constraints from FMData. |
| `acqmss/algorithms/congen_model.py` | `prepare()` creates FMData from oracle, passes to ConGenTaskPreparation |

## Implementation Steps

### 1. Update `_build_task_from_bias` in learner.py

```python
@staticmethod
def _build_task_from_bias(bias: Bias, fm_data: FMData) -> InteractiveTask:
    """Build InteractiveTask from Bias and FMData."""
    feature_ids = fm_data.feature_ids
    id_to_feature = {v: k for k, v in feature_ids.items()}

    root_feature_id = feature_ids.get(fm_data.root_feature)
    background = [root_feature_id] if root_feature_id is not None else []

    constraint_map, negated_constraint_map, _ = bias.to_constraint_maps_with_negation()

    task = InteractiveTask(
        bias=[c.id for c in bias.constraints],
        learned_kb=[],
        background=background,
        feature_ids=feature_ids,
        id_to_feature=id_to_feature,
        constraint_map=constraint_map,
        negated_constraint_map=negated_constraint_map
    )
    return task
```

### 2. Update `from_files()` and `from_examples()`

```python
@classmethod
def from_files(cls, fm_path, bias_path, ...):
    bias = BiasIO.load_from_json(bias_path)
    oracle = FeatureModelOracle(fm_path)
    fm_data = oracle.get_fm_data()
    task = cls._build_task_from_bias(bias, fm_data)
    return cls(task, oracle, ...)

@classmethod
def from_examples(cls, fm_path, bias_path, examples, ...):
    bias = BiasIO.load_from_json(bias_path)
    oracle = FeatureModelOracle(fm_path)
    fm_data = oracle.get_fm_data()
    task = cls._build_task_from_bias(bias, fm_data)
    learner = cls(task, oracle, ...)
    learner._fm_clauses = oracle.get_cnf_clauses()
    return learner
```

### 3. Update `from_bias()`
- Already uses `bias.feature_ids` for feature_ids — no oracle metadata needed
- `oracle` param type stays `Oracle` (only used for `is_valid()` at learn time)
- No changes needed here

### 4. Update `ConGenTaskPreparation.prepare()`

```python
def prepare(self, model: ConGenModel, fm_data: FMData) -> PreparationOutput:
    result = ConGenTask()
    provider = DescriptionProvider()
    task_input = model.task_input

    root_feature = fm_data.root_feature
    num_fm_constraints = fm_data.num_constraints
    # ... rest unchanged
```

Also update `_prepare_negative_examples` — currently takes `oracle` for GenerateNE. Keep oracle param here (Phase 4 will address GenerateNE).

### 5. Update `ConGenModel.prepare()`

```python
def prepare(self, oracle: FeatureModelOracle, ...):
    self.next_tseitin_var = oracle.get_next_tseitin_var()
    fm_data = oracle.get_fm_data()
    # ...
    preparation = ConGenTaskPreparation()
    output = preparation.prepare(self, fm_data)  # pass fm_data not oracle
```

But `_prepare_negative_examples` still needs oracle for GenerateNE → keep oracle passed through for now. Refactored in Phase 4.

**Interim approach for ConGenTaskPreparation.prepare():**
```python
def prepare(self, model: ConGenModel, fm_data: FMData, oracle: FeatureModelOracle) -> PreparationOutput:
```
Takes both FMData (for metadata) and oracle (for GenerateNE). Phase 4 will remove oracle param from GenerateNE.

## Todo List
- [x] Update `_build_task_from_bias()` signature: `(bias, fm_data: FMData)`
- [x] Update `from_files()` to extract FMData
- [x] Update `from_examples()` to extract FMData
- [x] Update `ConGenTaskPreparation.prepare()` to take `fm_data: FMData` + `oracle` (interim)
- [x] Update `ConGenModel.prepare()` to create FMData and pass through
- [x] Import FMData in all modified files

## Success Criteria
- `_build_task_from_bias()` has no oracle parameter
- ConGenTaskPreparation extracts root/num_constraints from FMData, not oracle
- `from_bias()` still works with generic Oracle type
- Interactive and ConGen learning paths both functional

## Risk Assessment
- **Risk**: Signature change in `ConGenTaskPreparation.prepare()` breaks callers
- **Mitigation**: Only one caller (`ConGenModel.prepare()`). Update together.
- **Risk**: `from_bias()` path may need FMData too
- **Mitigation**: `from_bias()` builds its own feature_ids from Bias object, never queries oracle for metadata. No change needed.

## Next Steps
- Phase 4: Refactor GenerateNE to remove oracle dependency
