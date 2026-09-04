# Phase 3: Evaluator BG Union in Clause Comparison

## Context Links

- Source: `acqmss/eval/evaluator.py` (_evaluate_by_clause method)
- Source: `acqmss/algorithms/interactive/learner.py` (evaluate method)
- Issue: Root [1] in BG but not counted in KB during evaluation

## Overview

**Priority**: P1
**Status**: Complete
**Effort**: 0.5h

Modify clause-based evaluation to compare (KB ∪ BG) against Oracle, not just KB. Currently evaluator only looks at result.kb_constraints, ignoring background.

## Key Insights

- Clause eval compares kb_clauses (from KB) vs oracle.clause_set
- Background knowledge (BG) not included in comparison
- Root [1] is in BG after Phase 1/2, but evaluator doesn't see it
- Description eval unaffected (root has no description)
- Need access to BG clauses from task or result

## Requirements

**Functional**:
- _evaluate_by_clause() must union BG clauses with KB clauses before comparison
- BG clauses = [[1]] (root constraint as single-literal clause)
- Only affects CLAUSE strategy, not DESCRIPTION

**Non-functional**:
- No API changes to Evaluator.evaluate()
- Backward compatible: if no BG provided, uses KB only (current behavior)

## Architecture

### Current Flow (Incorrect)

```
CONGENResultData.kb_constraints
    ↓ Convert to kb_clauses
    ↓
Compare: kb_clauses vs oracle.clause_set
    ↓
Metrics: TP, FP, FN (root [1] counted as FN)
```

### New Flow (Correct)

```
CONGENResultData.kb_constraints + BG
    ↓ Convert to kb_clauses ∪ bg_clauses
    ↓
Compare: (kb_clauses ∪ bg_clauses) vs oracle.clause_set
    ↓
Metrics: TP, FP, FN (root [1] counted as TP)
```

### Challenge: Accessing BG

**Problem**: CONGENResultData doesn't include BG. Evaluator has no access to task.set_b or task.background.

**Solutions**:
1. **Option A** (Recommended): Add bg_clauses field to CONGENResultData
2. **Option B**: Pass BG separately to evaluate()
3. **Option C**: Hardcode [1] in evaluator (brittle)

**Chosen**: Option A — cleanest, no API change to evaluate().

## Related Code Files

**Modify**:
- `acqmss/eval/result_loader.py` — Add bg_clauses to CONGENResultData
- `acqmss/eval/evaluator.py` — Union BG in _evaluate_by_clause()
- `acqmss/algorithms/congen.py` — Save BG in result (if not already)
- `acqmss/algorithms/interactive/learner.py` — Pass BG to CONGENResultData in evaluate()

**Read**:
- `acqmss/eval/result_loader.py` — CONGENResultData structure

## Implementation Steps

### Step 1: Add bg_clauses to CONGENResultData (result_loader.py)

**File**: `acqmss/eval/result_loader.py`

Add field to CONGENResultData:
```python
@dataclass
class CONGENResultData:
    kb_constraints: List[str]
    redundant_constraints: List[str]
    n_bias: int
    n_mss: int
    n_kb: int
    bg_clauses: List[List[int]] = field(default_factory=list)  # NEW
```

**Estimated Line**: After n_kb field

### Step 2: Save BG in CONGEN result (congen.py)

**File**: `acqmss/algorithms/congen.py`

Check if CONGENResult already has bg_clauses field. If not, add:
```python
@dataclass
class CONGENResult:
    ...
    bg_clauses: List[List[int]] = field(default_factory=list)  # NEW
```

In CONGEN.acquire(), populate bg_clauses:
```python
result = CONGENResult(
    kb_constraints=...,
    ...
    bg_clauses=[[task.set_b[0]]] if task.set_b else []  # NEW: [[1]] for root
)
```

**Note**: Check actual task.set_b structure (int or List[int]) to format correctly.

### Step 3: Modify _evaluate_by_clause() (evaluator.py)

**File**: `acqmss/eval/evaluator.py`
**Line**: 164-212 (_evaluate_by_clause method)

After line 174 (where kb_clauses is built), add:
```python
# Union background clauses (KB ∪ BG)
if hasattr(result, 'bg_clauses') and result.bg_clauses:
    for clause in result.bg_clauses:
        normalized = tuple(sorted(clause))
        kb_clauses.add(normalized)
```

**Insertion Point**: After line 183 (after kb_clauses loop, before bias_clauses)

### Step 4: Update InteractiveLearner.evaluate() (learner.py)

**File**: `acqmss/algorithms/interactive/learner.py`
**Line**: 292-344 (evaluate method)

When creating CONGENResultData (line 322-328), add:
```python
congen_result = CONGENResultData(
    kb_constraints=result.kb_constraints,
    redundant_constraints=[],
    n_bias=len(self.task.bias) + len(result.kb_constraints),
    n_mss=0,
    n_kb=result.n_kb,
    bg_clauses=[self.task.background] if self.task.background else []  # NEW
)
```

**Note**: self.task.background is List[int] (e.g., [1]), wrap in list to get List[List[int]].

### Step 5: Verify in tests

Run evaluation tests to ensure BG included in clause comparison:
```bash
PYTHONPATH=. pytest tests/test_evaluation.py -v
```

Check debug logs for BG clauses in evaluator.

## Todo List

- [ ] Add bg_clauses field to CONGENResultData (result_loader.py)
- [ ] Check/add bg_clauses to CONGENResult (congen.py)
- [ ] Populate bg_clauses in CONGEN.acquire() (congen.py)
- [ ] Union bg_clauses in _evaluate_by_clause() (evaluator.py, after line 183)
- [ ] Pass bg_clauses in InteractiveLearner.evaluate() (learner.py, line 322-328)
- [ ] Run type check (mypy/pyright)
- [ ] Run tests: `PYTHONPATH=. pytest tests/test_evaluation.py -v`
- [ ] Verify BG union in debug logs
- [ ] Test on REAL-FM-7: confirm root [1] counted as TP, not FN

## Success Criteria

- CONGENResultData has bg_clauses field
- _evaluate_by_clause() unions kb_clauses with bg_clauses
- REAL-FM-7 clause eval: FN decreases by 1 (root [1] now TP)
- Description eval unchanged (root has no description)
- All evaluation tests pass

## Risk Assessment

**Low Risk**:
- Additive change (bg_clauses optional, defaults to [])
- No impact if bg_clauses empty (current behavior)

**Medium Risk**:
- Need to verify CONGENResult structure in congen.py
- BG format: List[int] vs List[List[int]] — must wrap correctly

**Testing**: Focus on test_evaluation.py and manual REAL-FM-7 run.

## Security Considerations

None. Pure data aggregation.

## Next Steps

After completion:
- Run full test suite: `PYTHONPATH=. pytest tests/ -v`
- Verify REAL-FM-7 results: clause FN should drop from N to N-1
- Document BG inclusion in evaluator docstrings
- Close issue/ticket

## Unresolved Questions

1. Does CONGENResult already have bg_clauses? Check `acqmss/algorithms/congen.py`
2. Is task.set_b a List[int] or int in incremental mode? Verify format
3. Should description eval also include BG? (Likely NO — root has no description)
