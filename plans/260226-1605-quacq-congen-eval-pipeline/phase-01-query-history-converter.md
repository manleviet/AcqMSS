# Phase 1: Expose Query History + Converter

## Context

- Parent plan: [plan.md](plan.md)
- Dependencies: None (independent)
- Blocks: Phase 3 (progressive evaluation needs converter)

## Overview

- **Date**: 2026-02-26
- **Priority**: P1
- **Status**: pending
- **Effort**: 1h

Two changes: (1) propagate `query_history` from inner `InteractiveResult` to `InteractiveRunResult` at runner layer, (2) create utility to convert query history into `ExampleSet` for ConGen consumption.

## Key Insights

<!-- Updated: Validation Session 1 - Added source tagging requirement -->
- `InteractiveResult` (algo layer, `conacq/algorithms/interactive/result.py:64`) already has `query_history: List[Tuple[Dict[str, bool], bool]]` with full serialization support (`to_dict`/`load`).
- `InteractiveRunResult` (runner layer, `conacq/runners/interactive_runner.py:22-54`) drops it at line 227-239 during construction.
- Fix is minimal: add field + one line in constructor.
- Query config dicts are `{feature_name: True/False}` — same format as `Example.assignments`. No transformation needed.
- `ExampleSet.add()` dispatches by `ExampleType`. `ExampleIO.save_json()` handles persistence.
- **Validation decision**: Only main loop queries used for ConGen. Add `source` param to `record_query()` to tag `'main'` vs `'findc'`. Converter filters by `source='main'`.

## Requirements

### Functional
1. `InteractiveRunResult.query_history` field available after `InteractiveRunner.run()`
2. `query_history` included in `InteractiveRunResult.to_dict()` serialization
3. `queries_to_examples(query_history) -> ExampleSet` utility function
4. Converter assigns IDs like `q0+`, `q1-`, etc.

### Non-functional
- No new dependencies
- Backward compatible (query_history defaults to empty list)

## Related Code Files

### Modify
| File | Change |
|------|--------|
| `conacq/runners/interactive_runner.py` | Add `query_history` field to `InteractiveRunResult`; propagate from `result.query_history` |
| `conacq/algorithms/interactive/quacq_task.py` | Add `source` param to `record_query(config, answer, source='main')` — store as `List[Tuple[Dict, bool, str]]` |
| `conacq/algorithms/interactive/task.py` | Same source tagging for deprecated `InteractiveTask.record_query()` (backward compat) |
| `conacq/algorithms/interactive/quacq.py` | Pass `source='main'` at L93 and L179 (main loop calls) |
| `conacq/algorithms/interactive/findc.py` | Pass `source='findc'` at L119 and L160 (FindC calls) |

**NOTE (post-refactor update 2026-02-26):** Runner now uses `InteractiveModel + QuAcq` directly (not `InteractiveLearner`). `result` comes from `quacq.learn()` → `InteractiveResult`. `QuAcqTask` is the primary task class; `InteractiveTask` is deprecated.

### Create
| File | Description |
|------|-------------|
| `conacq/examples/query_converter.py` | `queries_to_examples()` utility (~50 lines) |
| `tests/test_query_converter.py` | Unit tests for converter |

## Implementation Steps

### Step 1: Add `query_history` to `InteractiveRunResult`

In `conacq/runners/interactive_runner.py`:

1. Add field to dataclass (after `profiler_data`, line ~54):
   ```python
   # Query history for evaluation pipeline
   query_history: List[Tuple[Dict[str, bool], bool]] = field(default_factory=list)
   ```
2. Add import `Tuple` to the typing imports (line 1).
3. In `run()` method, add to `InteractiveRunResult(...)` constructor at line 227-239:
   ```python
   query_history=result.query_history,
   ```
4. In `to_dict()` method, add serialization:
   ```python
   'query_history': [
       {'config': config, 'answer': answer}
       for config, answer in self.query_history
   ]
   ```

### Step 2: Create `query_converter.py`

New file `conacq/examples/query_converter.py`:

```python
"""Convert InteractiveRunner query history to ExampleSet for ConGen."""

from typing import List, Tuple, Dict, Optional
from .data_structures import Example, ExampleSet, ExampleType


def queries_to_examples(
    query_history: List[Tuple[Dict[str, bool], bool, str]],
    source_filter: str = 'main',
    metadata: Optional[Dict] = None
) -> ExampleSet:
    """Convert query history from QuAcq into ExampleSet for ConGen.

    Each (config, answer, source) triple becomes one Example if source matches filter:
    - answer=True  -> ExampleType.POSITIVE (valid configuration)
    - answer=False -> ExampleType.NEGATIVE (violates constraint)

    Args:
        query_history: List of (config_dict, oracle_answer, source) tuples
        source_filter: Only include queries with this source tag (default: 'main')
        metadata: Optional metadata dict for the ExampleSet

    Returns:
        ExampleSet with positive and negative examples
    """
    es = ExampleSet(metadata=metadata or {})
    idx = 0
    for config, answer, source in query_history:
        if source != source_filter:
            continue
        example_type = ExampleType.POSITIVE if answer else ExampleType.NEGATIVE
        suffix = "+" if answer else "-"
        example = Example(
            id=f"q{idx}{suffix}",
            assignments=config,
            example_type=example_type
        )
        es.add(example)
        idx += 1
    return es


def queries_to_assignment_lists(
    query_history: List[Tuple[Dict[str, bool], bool, str]],
    source_filter: str = 'main'
) -> Tuple[List[Dict[str, bool]], List[Dict[str, bool]]]:
    """Split query history into positive/negative assignment lists.

    Returns format directly usable by ConGenRunner.run(pos, neg).

    Args:
        query_history: List of (config_dict, oracle_answer, source) tuples
        source_filter: Only include queries with this source tag (default: 'main')

    Returns:
        (positive_assignments, negative_assignments) tuple
    """
    positive = [config for config, answer, source in query_history
                if answer and source == source_filter]
    negative = [config for config, answer, source in query_history
                if not answer and source == source_filter]
    return positive, negative
```

### Step 3: Unit tests

New file `tests/test_query_converter.py`:

Test cases:
1. Empty query_history -> empty ExampleSet
2. Mixed positive/negative -> correct split and counts
3. All positive -> only E+, no E-
4. All negative -> only E-, no E+
5. IDs follow `q{i}{+/-}` pattern
6. `queries_to_assignment_lists` returns correct split
7. Metadata propagated to ExampleSet

## Todo List

- [ ] Add `query_history` field to `InteractiveRunResult` dataclass
- [ ] Add `Tuple` to typing imports in `interactive_runner.py`
- [ ] Propagate `result.query_history` in `run()` constructor call
- [ ] Add `query_history` to `InteractiveRunResult.to_dict()`
- [ ] Create `conacq/examples/query_converter.py` with `queries_to_examples()` and `queries_to_assignment_lists()`
- [ ] Create `tests/test_query_converter.py` with unit tests
- [ ] Run `PYTHONPATH=. pytest tests/test_query_converter.py -v`
- [ ] Run full test suite to verify no regressions

## Success Criteria

1. `InteractiveRunner.run(mode='automated')` returns result with populated `query_history`
2. `queries_to_examples()` produces correct ExampleSet from sample data
3. `queries_to_assignment_lists()` returns correct (pos, neg) tuple
4. All existing tests pass (no regressions from adding defaulted field)

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| FindC sub-queries as training examples | Low | Only top-level QuAcq queries are recorded via `task.record_query()` in the main loop; FindC queries also go through `record_query()` but are discriminating queries — these are still valid examples for ConGen |
| Partial configs in query_history | Low | QuAcq main loop uses complete configs; FindC uses partial configs but these still form valid constraints |
| Large query_history serialization | Low | Only serialized when explicitly requested; default is empty list for backward compat |

## Next Steps

After completion:
- Phase 3 can use `queries_to_assignment_lists()` to feed ConGen at each checkpoint
- Phase 4 can save query history alongside results via `ExampleIO.save_json()`
