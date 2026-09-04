# Phase 2: QuAcq Root Propagation to background

## Context Links

- Source: `acqmss/algorithms/interactive/learner.py` (InteractiveLearner)
- Source: `acqmss/algorithms/interactive/task.py` (InteractiveTask)
- Source: `apps/run_interactive_eval.py` (caller)
- Pattern: Phase 1 CONGEN implementation

## Overview

**Priority**: P1
**Status**: Complete
**Effort**: 1h

Add root [1] to InteractiveTask.background in all factory methods (from_files, from_bias, from_examples, _build_task_from_bias).

## Key Insights

- InteractiveLearner creates InteractiveTask with background=[] (lines 155, 184)
- InteractiveTask.background is List[int] (assumption literals)
- Root should be [1] in background for incremental consistency with CONGEN
- All factory methods must populate background with root

## Requirements

**Functional**:
- _build_task_from_bias() adds [1] to background
- from_bias() adds bg_clauses (or [1] if None) to background
- from_files() populates background via _build_task_from_bias()
- from_examples() populates background via _build_task_from_bias()

**Non-functional**:
- No impact on existing interactive tests
- Backward compatible: existing callers get root automatically

## Architecture

### Data Flow

```
AutomatedOracle(fm_path)
    ↓ get_feature_ids() → {features}
    ↓ Root ID = 1 (default)
    ↓
InteractiveLearner._build_task_from_bias()
    ↓ background = [1]  # Root constraint
    ↓
InteractiveTask(background=[1])
    ↓
QuAcq uses background in KB ∪ BG for SAT checks
```

### Modified Methods

**_build_task_from_bias** (line 165):
```python
task = InteractiveTask(
    bias=[c.id for c in bias.constraints],
    learned_kb=[],
    background=[1],  # NEW: root constraint
    feature_ids=feature_ids,
    ...
)
```

**from_bias** (line 152):
```python
task = InteractiveTask(
    bias=[c.id for c in bias.constraints],
    learned_kb=[],
    background=bg_clauses if bg_clauses else [1],  # NEW: default to root
    ...
)
```

## Related Code Files

**Modify**:
- `acqmss/algorithms/interactive/learner.py` — Add [1] to background in factory methods

**Reference**:
- `acqmss/algorithms/interactive/task.py` — InteractiveTask.background definition
- `apps/run_interactive_eval.py` — Caller (may need update if constructing task directly)

## Implementation Steps

### Step 1: Modify _build_task_from_bias() (learner.py)

**File**: `acqmss/algorithms/interactive/learner.py`
**Line**: 181-189

Change:
```python
task = InteractiveTask(
    bias=[c.id for c in bias.constraints],
    learned_kb=[],
    background=[],  # OLD
    feature_ids=feature_ids,
    id_to_feature=id_to_feature,
    constraint_map=constraint_map,
    negated_constraint_map=negated_constraint_map
)
```

To:
```python
task = InteractiveTask(
    bias=[c.id for c in bias.constraints],
    learned_kb=[],
    background=[1],  # NEW: root constraint
    feature_ids=feature_ids,
    id_to_feature=id_to_feature,
    constraint_map=constraint_map,
    negated_constraint_map=negated_constraint_map
)
```

### Step 2: Modify from_bias() (learner.py)

**File**: `acqmss/algorithms/interactive/learner.py`
**Line**: 152-160

Change:
```python
task = InteractiveTask(
    bias=[c.id for c in bias.constraints],
    learned_kb=[],
    background=bg_clauses if bg_clauses else [],  # OLD
    feature_ids=feature_ids,
    id_to_feature=id_to_feature,
    constraint_map=constraint_map,
    negated_constraint_map=negated_constraint_map
)
```

To:
```python
task = InteractiveTask(
    bias=[c.id for c in bias.constraints],
    learned_kb=[],
    background=bg_clauses if bg_clauses else [1],  # NEW: default to root
    feature_ids=feature_ids,
    id_to_feature=id_to_feature,
    constraint_map=constraint_map,
    negated_constraint_map=negated_constraint_map
)
```

### Step 3: Verify factory methods chain

Check that from_files() and from_examples() both call _build_task_from_bias():
- from_files() (line 110): ✓ Calls _build_task_from_bias()
- from_examples() (line 223): ✓ Calls _build_task_from_bias()

No additional changes needed — they inherit the fix.

### Step 4: Check run_interactive_eval.py

**File**: `apps/run_interactive_eval.py`

Search for direct InteractiveTask construction. If found, update to include background=[1].

Expected: Uses InteractiveLearner.from_files() or from_examples() → inherits fix automatically.

## Todo List

- [ ] Change background=[] to background=[1] in _build_task_from_bias() (line 184)
- [ ] Change background default in from_bias() to [1] (line 155)
- [ ] Verify from_files() uses _build_task_from_bias() (line 110) ✓
- [ ] Verify from_examples() uses _build_task_from_bias() (line 223) ✓
- [ ] Check apps/run_interactive_eval.py for direct InteractiveTask construction
- [ ] Run mypy/pyright type check
- [ ] Run tests: `PYTHONPATH=. pytest tests/test_interactive.py -v`
- [ ] Verify background=[1] in debug logs

## Success Criteria

- InteractiveTask.background = [1] when created via any factory method
- from_bias(bg_clauses=None) defaults to [1]
- from_bias(bg_clauses=[5, 10]) uses [5, 10] (respects explicit override)
- All interactive tests pass
- Type checking passes

## Risk Assessment

**Low Risk**:
- Simple list initialization change
- All factory methods funnel through updated code

**Testing**: Focus on test_interactive.py. QuAcq should handle background=[1] transparently (already uses background in SAT checks).

## Security Considerations

None. Pure data initialization.

## Next Steps

After completion:
- Proceed to Phase 3 (Evaluator BG union)
- Verify background=[1] in QuAcq debug logs
- Test on REAL-FM-7 interactive run
