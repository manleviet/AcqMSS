# Brainstorm: InteractiveRunner Dual-Mode Support

## Problem Statement

**Asymmetry**: `ConGenRunner` serves both standalone (`run_congen.py`) and CV (`run_cv.py`), but `InteractiveRunner` only serves CV (example-based mode). `run_interactive.py` bypasses the runner entirely, using `InteractiveLearner` directly with its own profiler/memory/save logic — duplicating concerns.

**Goal**: Make `InteractiveRunner` symmetric with `ConGenRunner` — file-path-based constructor, single `run()` method supporting both oracle-based and example-pool modes, full profiler integration.

## Current Architecture

```
ConGenRunner                          InteractiveRunner (current)
├─ __init__(bias_path, fm_path, ...)  ├─ __init__(bias_clauses, feature_ids, ...)
│  → builds model + oracle internally │  → stores raw data only
│  → reusable across folds           │  → no model/oracle construction
├─ run(pos, neg, seed)                ├─ run(pos, neg, seed)
│  → profiler_session + tracemalloc   │  → manual perf_counter + tracemalloc
│  → model.prepare → checker → ConGen │  → creates fresh InteractiveLearner per call
│  → resolve result → ConGenRunResult │  → example-pool mode ONLY
└─ cleanup()                          └─ (no cleanup)

run_interactive.py (standalone — NO runner)
├─ InteractiveLearner.from_files() directly
├─ learner.learn(mode='automated')
├─ manual profiler + verbose printing
└─ save_kb_result()
```

## Proposed Design

### Constructor: File-Path Based (like ConGenRunner)

```python
class InteractiveRunner:
    def __init__(self, bias_path, fm_path,
                 solver_name='glucose4',
                 max_queries=1000,
                 query_mode='example_only'):
        self.bias_path = bias_path
        self.fm_path = fm_path
        self.solver_name = solver_name
        self.max_queries = max_queries
        self.query_mode = query_mode

        # Load bias once (for clause resolution + reuse)
        self.bias = BiasIO.load_from_json(bias_path)
        self.bias_clauses = {c.id: c.clauses for c in self.bias.constraints}

        # Create oracle (reused across runs)
        self.oracle = FeatureModelOracle(fm_path, solver_name=solver_name)
```

### Single run() with mode param

```python
def run(self, positive_examples=None, negative_examples=None,
        mode='example_only', shuffle_seed=None) -> InteractiveRunResult:
    """
    mode: 'automated' | 'interactive' | 'example_only' | 'example_first'
      - automated/interactive: oracle-based, examples ignored
      - example_only/example_first: example-pool-based
    """
```

**Oracle path** (mode='automated'/'interactive'):
- `InteractiveLearner.from_files()` → `learner.learn(mode, max_queries)`
- No examples needed (generates queries via SAT or prompts user)

**Example path** (mode='example_only'/'example_first'):
- `InteractiveLearner.from_examples()` → `learner.learn_from_examples(query_mode, max_queries)`
- Requires pos + neg examples

### Unified profiler integration

Use `profiler_session(ProfilerPreset.BENCHMARK)` context manager like ConGenRunner, replacing manual `time.perf_counter()`.

### cleanup()

```python
def cleanup(self):
    if self.oracle:
        self.oracle.cleanup()
```

## Breaking Changes

### `n_fold_cross_validation_interactive()` in `cross_validation.py`

**Current call** (line ~398-410):
```python
runner = InteractiveRunner(
    bias_clauses=bias_clauses,
    feature_ids=feature_ids,
    fm_path=fm_path,
    bias_path=bias_path,
    solver_name=solver_name,
    max_queries=max_queries,
    query_mode=query_mode
)
```

**New call**:
```python
runner = InteractiveRunner(
    bias_path=bias_path,
    fm_path=fm_path,
    solver_name=solver_name,
    max_queries=max_queries,
    query_mode=query_mode
)
```

Remove `bias_clauses` and `feature_ids` params from `n_fold_cross_validation_interactive()` signature. These were pre-loaded by the caller — now the runner loads internally.

### `run_interactive.py`

**Current**: Uses `InteractiveLearner.from_files()` directly with manual profiler + save logic.
**New**: Uses `InteractiveRunner(bias_path, fm_path, ...).run(mode='automated')` — then saves result.

### `InteractiveRunResult`

Add `bg_clauses` field (currently missing, ConGenRunResult has it). Needed for symmetry and for `AccuracyCalculator`.

## Evaluated Approaches

### Approach A: Refactor InteractiveRunner (Recommended)

**Pros**: Symmetric with ConGenRunner, DRY, single responsibility, clean break.
**Cons**: Breaking change requires updating 2 callers.
**Risk**: Low — only 2 call sites: `cross_validation.py` and `run_interactive.py`.

### Approach B: Keep InteractiveRunner, add OracleRunner

**Pros**: No breaking change.
**Cons**: Violates DRY (two runners for same algorithm), confusing naming.
**Verdict**: Rejected — KISS violation.

### Approach C: Merge into InteractiveLearner itself

**Pros**: No separate runner class.
**Cons**: Mixes algorithm logic with orchestration (profiler, memory, save). ConGenRunner exists separately from ConGen for good reason — separation of concerns.
**Verdict**: Rejected — SRP violation.

## Implementation Considerations

1. **Oracle reuse**: In oracle mode, `InteractiveLearner.from_files()` creates its own `FeatureModelOracle`. Runner also creates one. Need to either:
   - Pass runner's oracle to learner (add `from_oracle()` factory) — cleanest
   - Let learner create its own, accept the duplication — simpler
   - **Recommendation**: Let learner create its own for now (KISS). Oracle is lightweight.

2. **Bias shuffle in oracle mode**: Doesn't apply — oracle mode generates queries from SAT, bias ordering doesn't matter.

3. **profiler_data field**: Add to `InteractiveRunResult` like `ConGenRunResult` has. Currently missing.

4. **bg_clauses**: Extract from learner's task after learning. Add to result.

## Files to Modify

| File | Change |
|---|---|
| `conacq/runners/interactive_runner.py` | Rewrite constructor + run() |
| `apps/run_interactive.py` | Use InteractiveRunner instead of direct InteractiveLearner |
| `conacq/eval/cross_validation.py` | Update `n_fold_cross_validation_interactive()` call site |
| `conacq/runners/__init__.py` | No change (exports same names) |

## Success Criteria

- `run_interactive.py` uses `InteractiveRunner` (not `InteractiveLearner` directly)
- `run_cv.py` with `algorithm=interactive` still works identically
- Both oracle-based and example-based modes produce correct `InteractiveRunResult`
- All existing tests pass
- Symmetric API pattern with ConGenRunner

## Risks

- **Low**: `InteractiveLearner.from_files()` in oracle mode creates internal oracle that conflicts with runner's oracle → mitigated by letting each create its own (no shared state).
- **Low**: `run_interactive.py` currently reads `learner.task.bias` and `learner.task.background` for verbose output and `bg_clauses`. Runner needs to expose these or extract after learning.

## Next Steps

1. Create implementation plan with phased approach
2. Phase 1: Refactor InteractiveRunner (constructor + run + cleanup)
3. Phase 2: Update run_interactive.py to use runner
4. Phase 3: Update cross_validation.py caller
5. Phase 4: Run tests + verify both modes
