# Phase 3: Progressive Evaluation Engine

## Context

- Parent plan: [plan.md](plan.md)
- Dependencies: Phase 1 (query converter), Phase 2 (semantic equivalence)
- Blocks: Phase 4 (evaluation script orchestrates this engine)

## Overview

- **Date**: 2026-02-26
- **Priority**: P1
- **Status**: pending
- **Effort**: 1.5h

Engine that runs ConGen at multiple query-budget checkpoints (e.g., 10%, 25%, 50%, 75%, 100% of QuAcq queries) and compares each resulting KB against ground truth C_T. Produces a learning curve showing how ConGen's KB quality improves with more training data.

## Key Insights

- `ConGenRunner.run(pos, neg)` is already designed for repeated calls with different example sets (used by CV loop). Reuse directly.
- `queries_to_assignment_lists()` from Phase 1 returns `(pos, neg)` lists directly usable by `ConGenRunner.run()`.
- `KBComparator.compare()` supports description and clause strategies; Phase 2 adds semantic.
- Checkpoints are percentages of total query count. Floor division handles edge cases.
- QuAcq's final KB comparison is a single `KBComparator` call (no progressive needed).
- `ConGenRunner` reuses model across runs — just call `run()` per checkpoint with different slices.

## Requirements

### Functional
1. `ProgressiveEvaluator` class orchestrating checkpoint-based ConGen runs
2. Configurable checkpoints as percentages (e.g., `[10, 25, 50, 75, 100]`)
3. At each checkpoint: slice queries, convert to examples, run ConGen, compare vs C_T
4. Collect all checkpoint results + QuAcq final comparison into `ProgressiveResult`
5. JSON-serializable output via `to_dict()`

### Non-functional
- Reuse existing `ConGenRunner` (no duplicate ConGen logic)
- Reuse existing `KBComparator` for structural comparison
- Reuse `SemanticEquivalenceChecker` for semantic comparison
- Log progress at each checkpoint

## Architecture

```
ProgressiveEvaluator
    |
    +--- __init__(congen_runner, comparator, groundtruth, checkpoints_pct)
    |
    +--- evaluate(query_history, quacq_run_result)
            |
            For each pct in checkpoints_pct:
            |   N = floor(pct/100 * len(query_history))
            |   queries[:N] -> queries_to_assignment_lists() -> pos, neg
            |   congen_runner.run(pos, neg) -> ConGenRunResult
            |   ConGenResultData.from_run_result(congen_run_result)
            |   comparator.compare(result, DESCRIPTION)
            |   comparator.compare(result, CLAUSE)
            |   SemanticEquivalenceChecker(...).check_equivalence()
            |   -> CheckpointResult
            |
            Compare QuAcq final KB vs C_T (description + clause + semantic)
            |
            -> ProgressiveResult
```

## Related Code Files

### Create
| File | Description |
|------|-------------|
| `conacq/eval/progressive_evaluation.py` | `ProgressiveEvaluator`, `CheckpointResult`, `ProgressiveResult` (~150 lines) |
| `tests/test_progressive_evaluation.py` | Unit tests with mocked runners |

### Modify
| File | Change |
|------|--------|
| `conacq/eval/__init__.py` | Export new classes |

## Implementation Steps

### Step 1: Define `CheckpointResult` dataclass

```python
@dataclass
class CheckpointResult:
    """Result at a single query-budget checkpoint.

    Attributes:
        checkpoint_pct: Percentage of total queries used
        n_queries: Absolute number of queries used
        n_positive: Number of positive examples
        n_negative: Number of negative examples
        n_kb: ConGen KB size at this checkpoint
        description_comparison: ComparationResult (description strategy)
        clause_comparison: ComparationResult (clause strategy)
        semantic_result: SemanticResult
        congen_runtime_ms: ConGen execution time
    """
```

Add `to_dict()`.

### Step 2: Define `ProgressiveResult` dataclass

```python
@dataclass
class ProgressiveResult:
    """Complete progressive evaluation result.

    Attributes:
        checkpoints: List of CheckpointResult (ConGen at each N)
        quacq_description: ComparationResult for QuAcq final KB (description)
        quacq_clause: ComparationResult for QuAcq final KB (clause)
        quacq_semantic: SemanticResult for QuAcq final KB
        total_queries: Total queries QuAcq asked
        metadata: Additional info (FM name, timestamps, etc.)
    """
```

Add `to_dict()` that serializes all checkpoints + QuAcq final.

### Step 3: Implement `ProgressiveEvaluator`

```python
class ProgressiveEvaluator:
    """Run ConGen at progressive query budgets and compare vs ground truth."""

    def __init__(
        self,
        congen_runner: ConGenRunner,
        comparator: KBComparator,
        groundtruth: GroundTruthData,
        checkpoints_pct: List[int] = None,
        comparison_strategies: List[str] = None
    ):
        self.congen_runner = congen_runner
        self.comparator = comparator
        self.groundtruth = groundtruth
        self.checkpoints_pct = checkpoints_pct or [10, 25, 50, 75, 100]
        self.strategies = comparison_strategies or ['description', 'clause', 'semantic']
```

### Step 4: Implement `evaluate()` method

```python
def evaluate(
    self,
    query_history: List[Tuple[Dict[str, bool], bool]],
    quacq_run_result: InteractiveRunResult
) -> ProgressiveResult:
```

<!-- Updated: Validation Session 1 - No skipping, always run ConGen (AcqMSS handles empty E- correctly) -->
Logic:
1. Compute total = `len(query_history)` (filtered by `source='main'`)
2. For each pct in `checkpoints_pct`:
   - `n = max(1, int(pct / 100 * total))`
   - `sliced = query_history[:n]` (main-loop queries only)
   - `pos, neg = queries_to_assignment_lists(sliced, source_filter='main')`
   - Always run — ConGen/AcqMSS handles empty E- correctly (result depends on E+)
   - `congen_result = self.congen_runner.run(pos, neg)`
   - Build `ConGenResultData` from `congen_result` (using `from_run_result()` helper or direct construction)
   - Run comparisons (description, clause, semantic)
   - Append `CheckpointResult`
3. Compare QuAcq final KB:
   - Build `ConGenResultData` from `quacq_run_result` (map fields)
   - Run same comparisons
4. Return `ProgressiveResult`

### Step 5: Helper — `ConGenResultData` from run results

Need a bridge from `ConGenRunResult` / `InteractiveRunResult` to `ConGenResultData` (which `KBComparator.compare()` expects). Add a classmethod or helper function:

```python
def _run_result_to_comparator_input(
    self,
    kb_constraints: List[str],
    bg_clauses: List[List[int]],
    n_bias: int,
    n_kb: int
) -> ConGenResultData:
    """Bridge runner results to KBComparator input format."""
    return ConGenResultData(
        kb_constraints=kb_constraints,
        n_bias=n_bias,
        n_kb=n_kb,
        bg_clauses=bg_clauses,
    )
```

### Step 6: Helper — semantic check from run result

```python
def _run_semantic_check(
    self,
    kb_clauses: List[List[int]],
    bg_clauses: List[List[int]]
) -> SemanticResult:
    """Run semantic equivalence check."""
    checker = SemanticEquivalenceChecker(
        kb_clauses=kb_clauses,
        ct_clauses=self.groundtruth.clauses,
        bg_clauses=bg_clauses
    )
    return checker.check_equivalence()
```

### Step 7: Update `__init__.py` exports

Add to `conacq/eval/__init__.py`:
```python
from .progressive_evaluation import (
    ProgressiveEvaluator, ProgressiveResult, CheckpointResult
)
```

### Step 8: Unit tests

`tests/test_progressive_evaluation.py`:

1. **Basic flow**: mock ConGenRunner + KBComparator, verify checkpoints created
2. **Checkpoint calculation**: 100 queries, [10,50,100] -> N=[10,50,100]
3. **Skip empty**: if N=0 queries or no neg examples, skip checkpoint
4. **QuAcq final included**: verify quacq_description/clause/semantic populated
5. **to_dict() serialization**: verify JSON structure roundtrips
6. **Single checkpoint**: [100] -> one ConGen run at full budget

## Todo List

- [ ] Create `conacq/eval/progressive_evaluation.py`
- [ ] Define `CheckpointResult` dataclass with `to_dict()`
- [ ] Define `ProgressiveResult` dataclass with `to_dict()`
- [ ] Implement `ProgressiveEvaluator.__init__()`
- [ ] Implement `evaluate()` with checkpoint loop
- [ ] Implement `_run_result_to_comparator_input()` bridge helper
- [ ] Implement `_run_semantic_check()` helper
- [ ] Update `conacq/eval/__init__.py` exports
- [ ] Create `tests/test_progressive_evaluation.py`
- [ ] Run `PYTHONPATH=. pytest tests/test_progressive_evaluation.py -v`
- [ ] Run full test suite

## Success Criteria

1. `ProgressiveEvaluator.evaluate()` produces correct number of checkpoints
2. Each checkpoint contains all three comparison results (description, clause, semantic)
3. QuAcq final comparison included in result
4. `ProgressiveResult.to_dict()` produces valid JSON-serializable dict
5. All existing tests pass

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| ConGen fails on small example sets | Low | AcqMSS handles empty E- correctly (depends on E+). Always run, log warning if E- empty |
| ConGenRunner state leaks between runs | Low | `ConGenRunner.run()` already calls `model.prepare()` each time, resetting state |
| Memory from many ConGen runs | Low | Each run is independent; GC reclaims between runs. Log memory per checkpoint. |
| Checkpoint with 0 queries | Low | Guard: `n = max(1, ...)` and skip if sliced produces no pos or neg |

## Next Steps

After completion:
- Phase 4 orchestrates: load config -> run QuAcq -> call `ProgressiveEvaluator.evaluate()` -> save JSON
