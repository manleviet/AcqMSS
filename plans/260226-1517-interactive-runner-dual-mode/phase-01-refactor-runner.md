# Phase 01: Refactor InteractiveRunner + InteractiveRunResult

## Context Links

- Parent: [plan.md](plan.md)
- Brainstorm: [brainstorm report](../reports/brainstorm-260226-1517-interactive-runner-dual-mode.md)
- Reference: `conacq/runners/congen_runner.py` (target pattern)

## Overview

- **Priority**: High
- **Status**: complete
- **Description**: Rewrite `InteractiveRunner` constructor to file-path-based, add dual-mode `run()`, add `cleanup()`, update `InteractiveRunResult` with new fields.

## Key Insights

- ConGenRunner builds model+oracle in `__init__`, reuses across `run()` calls
- InteractiveRunner currently receives raw data — no internal model construction
- For oracle mode, `InteractiveLearner.from_files()` creates its own oracle internally (no sharing needed)
- For example mode, `InteractiveLearner.from_examples()` also creates its own oracle
- Runner's oracle only needed for `feature_ids` (variable mapping) exposed to CV loop
- Lazy import of `InteractiveLearner` must be preserved (circular dep)

## Related Code Files

| File | Action | Current LOC |
|------|--------|-------------|
| `conacq/runners/interactive_runner.py` | **Rewrite** | 198 |
| `conacq/runners/__init__.py` | Verify (no change expected) | 15 |

## Implementation Steps

### 1. Update `InteractiveRunResult` dataclass

Add fields for symmetry with `ConGenRunResult`:

```python
@dataclass
class InteractiveRunResult:
    kb_constraints: List[str]
    kb_clauses: List[List[int]]
    bg_clauses: List[List[int]]          # NEW — root constraint clauses
    n_bias: int
    n_kb: int
    n_queries: int
    convergence_reason: str
    runtime_ms: float
    consistency_checks: int
    memory_peak_mb: float
    profiler_data: Dict[str, Any] = field(default_factory=dict)  # NEW
```

Update `to_dict()` and `get_performance_metrics()` accordingly.

### 2. Rewrite `InteractiveRunner.__init__`

```python
def __init__(self, bias_path: str, fm_path: str,
             solver_name: str = 'glucose4',
             max_queries: int = 1000,
             query_mode: str = 'example_only'):
    self.bias_path = bias_path
    self.fm_path = fm_path
    self.solver_name = solver_name
    self.max_queries = max_queries
    self.query_mode = query_mode

    # Load bias (for clause resolution + feature_ids)
    from conacq.bias import BiasIO
    bias = BiasIO.load_from_json(bias_path)
    self.bias_clauses = {c.id: c.clauses for c in bias.constraints}
    self.feature_ids = bias.feature_ids  # exposed for _run_cv_loop
```

Note: No oracle created here — each `InteractiveLearner` factory creates its own.

### 3. Rewrite `run()` with mode param

```python
def run(self, positive_examples=None, negative_examples=None,
        mode='example_only', shuffle_seed=None) -> InteractiveRunResult:
```

**Mode dispatch**:
- `mode in ('automated', 'interactive')` → oracle path via `InteractiveLearner.from_files()` → `learner.learn(mode, max_queries)`
- `mode in ('example_only', 'example_first')` → example path via `InteractiveLearner.from_examples()` → `learner.learn_from_examples(query_mode, max_queries)`

**Both paths share**:
- `profiler_session(ProfilerPreset.BENCHMARK)` context manager
- `tracemalloc` for memory tracking
- Extract `bg_clauses` from `learner.task.background`
- Resolve `kb_clauses` from `self.bias_clauses`
- Build `InteractiveRunResult` with all fields

### 4. Add `cleanup()` method

```python
def cleanup(self):
    """Release resources. No-op currently — oracle per-learner."""
    pass
```

Placeholder for symmetry. Oracle is created per-learner, not shared.

### 5. Expose `variables` property

The `_run_cv_loop` needs `variables` for `AccuracyCalculator`. Currently line 410 passes `feature_ids` param. New runner stores `self.feature_ids` from bias loading.

## Todo List

- [ ] Update `InteractiveRunResult` — add `bg_clauses`, `profiler_data`
- [ ] Update `to_dict()` — include new fields
- [ ] Rewrite `__init__` — file-path-based, load bias internally
- [ ] Rewrite `run()` — dual-mode dispatch with profiler_session
- [ ] Add `cleanup()` method
- [ ] Verify `__init__.py` exports unchanged

## Success Criteria

- `InteractiveRunner(bias_path, fm_path)` constructor works
- `run(mode='automated')` returns valid `InteractiveRunResult`
- `run(pos, neg, mode='example_only')` returns valid `InteractiveRunResult`
- `InteractiveRunResult` has `bg_clauses` and `profiler_data` fields
- `runner.feature_ids` accessible for CV loop

## Risk Assessment

- **Low**: Lazy import of `InteractiveLearner` must remain inside `run()`, not at module level
- **Low**: `from_files()` creates oracle that isn't shared — acceptable overhead for standalone mode

## Next Steps

→ Phase 02: Update `run_interactive.py` to use the refactored runner
