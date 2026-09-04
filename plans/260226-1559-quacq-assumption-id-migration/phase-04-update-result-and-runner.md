# Phase 4: Update InteractiveResult + InteractiveRunner

## Context Links
- [Parent Plan](plan.md) | [Phase 2](phase-02-update-quacq-algorithm.md) | [Phase 3](phase-03-update-findscope-findc.md)
- Source: `conacq/algorithms/interactive/result.py` (138 LOC)
- Source: `conacq/runners/interactive_runner.py` (283 LOC)
- Pattern: `conacq/algorithms/acqmss/congen.py` (ConGenResult with assumption IDs)

## Overview
- **Priority**: P1
- **Status**: completed
- **Depends on**: Phase 2, Phase 3
- **Description**: Update InteractiveResult to hold `List[int]` assumption IDs and InteractiveRunner to use InteractiveModel instead of InteractiveLearner.

## Key Insights
1. InteractiveResult.kb_constraints is `List[str]`. Change to `kb_assumption_ids: List[int]`. Add optional DescriptionProvider ref for name resolution.
2. InteractiveResult.to_dict() and save/load must handle both int IDs and human-readable names (via DescriptionProvider).
3. InteractiveRunner creates InteractiveLearner internally. Must switch to InteractiveModel + QuAcq directly.
4. InteractiveRunResult.kb_constraints is `List[str]`. Must resolve assumption IDs -> names via model.resolve_kb().
5. Cross-validation loop (`_run_cv_loop`) uses `run_result.kb_constraints` as `List[str]` for set intersection. Must still produce string names at runner level for backward compat with eval pipeline.

## Requirements

### Functional
- InteractiveResult stores `kb_assumption_ids: List[int]`
- InteractiveResult provides `kb_constraint_names(provider)` for display
- InteractiveResult.to_dict() outputs names + IDs for serialization
- InteractiveRunner uses InteractiveModel.prepare(oracle) + QuAcq
- InteractiveRunResult continues to expose kb_constraints as `List[str]` (resolved)

### Non-functional
- Backward-compatible serialization format (to_dict includes string names)
- InteractiveResult.load() handles both old (str) and new (int) formats

## Related Code Files

### Files to Modify
| File | Changes |
|------|---------|
| `conacq/algorithms/interactive/result.py` | kb_constraints -> kb_assumption_ids, add provider |
| `conacq/runners/interactive_runner.py` | Use InteractiveModel, resolve IDs to names |

## Implementation Steps

### Step 1: Update InteractiveResult (result.py)

```python
@dataclass
class InteractiveResult:
    """Result of interactive constraint acquisition."""

    # Learned KB as assumption IDs (primary representation)
    kb_assumption_ids: List[int] = field(default_factory=list)

    # Learned KB as constraint names (resolved from assumption IDs)
    # Populated by QuAcq._build_result() via DescriptionProvider
    kb_constraints: List[str] = field(default_factory=list)

    # Query statistics
    n_queries: int = 0
    n_kb: int = 0
    convergence_reason: str = ""
    runtime_ms: float = 0.0
    consistency_checks: int = 0
    metadata: Dict = field(default_factory=dict)
    query_history: List[Tuple[Dict[str, bool], bool]] = field(default_factory=list)
    evaluation: Optional[Dict] = None

    def __post_init__(self):
        if self.n_kb == 0:
            self.n_kb = len(self.kb_assumption_ids) or len(self.kb_constraints)
```

Dual representation: `kb_assumption_ids` is the primary data; `kb_constraints` is the resolved human-readable form. Both populated at construction time by QuAcq._build_result().

#### to_dict() update
```python
def to_dict(self) -> Dict:
    result = {
        'kb_constraints': self.kb_constraints,       # str names for backward compat
        'kb_assumption_ids': self.kb_assumption_ids,  # int IDs for new consumers
        'n_queries': self.n_queries,
        'n_kb': self.n_kb,
        # ... rest unchanged
    }
    return result
```

#### load() update — handle both formats
```python
@classmethod
def load(cls, filepath: str) -> 'InteractiveResult':
    with open(filepath, 'r') as f:
        data = json.load(f)

    return cls(
        kb_assumption_ids=data.get('kb_assumption_ids', []),
        kb_constraints=data.get('kb_constraints', []),
        # ... rest unchanged
    )
```

### Step 2: Update QuAcq._build_result() (in quacq.py, from Phase 2)

After _apply_reduce returns `List[int]`:
```python
def _build_result(self, task: QuAcqTask, start_time: float,
                  convergence_reason: str,
                  description_provider: DescriptionProvider) -> InteractiveResult:
    final_kb_ids = self._apply_reduce(task)
    runtime_ms = (time.perf_counter() - start_time) * 1000

    # Resolve names via DescriptionProvider
    kb_names = [description_provider.get_description(aid) for aid in final_kb_ids]

    self.result = InteractiveResult(
        kb_assumption_ids=final_kb_ids,
        kb_constraints=kb_names,
        n_queries=task.n_queries,
        n_kb=len(final_kb_ids),
        convergence_reason=convergence_reason,
        runtime_ms=runtime_ms,
        # ...
    )
    return self.result
```

Note: QuAcq.learn() and learn_from_examples() must pass `description_provider` to _build_result(). The provider comes from InteractiveModel._description_provider, so QuAcq needs access to it. Options:
- (a) Pass provider as argument to learn()/learn_from_examples()
- (b) Store provider on QuAcq during learn call

Recommendation: (a) — pass as parameter. Clean, explicit.

```python
def learn(self, task: QuAcqTask, oracle: Oracle,
          description_provider: DescriptionProvider,
          max_queries: int = 1000) -> InteractiveResult:
```

### Step 3: Update InteractiveRunner (interactive_runner.py)

#### Constructor changes
```python
class InteractiveRunner:
    def __init__(self, bias_path, fm_path, solver_name='glucose4',
                 max_queries=1000, query_mode='example_only'):
        self.bias_path = bias_path
        self.fm_path = fm_path
        self.solver_name = solver_name
        self.max_queries = max_queries
        self.query_mode = query_mode

        # Load bias for feature_ids (still needed for AccuracyCalculator in CV)
        from conacq.bias import BiasIO
        bias = BiasIO.load_from_json(bias_path)
        self.feature_ids = bias.feature_ids
```

Remove `self.bias_clauses` — no longer needed for clause resolution (model.resolve_kb does this).

#### _run_oracle_mode() changes
```python
def _run_oracle_mode(self, mode, shuffle_seed):
    from conacq.algorithms.interactive import InteractiveModel, QuAcq
    from conacq.oracle import FeatureModelOracle

    oracle = FeatureModelOracle(self.fm_path)
    model = InteractiveModel.from_bias(self.bias_path)
    model.prepare(oracle)
    task = model.task

    if shuffle_seed is not None:
        keys = list(task.bias)
        random.Random(shuffle_seed).shuffle(keys)
        task.bias = set(keys)  # Still a set, shuffle just for iteration order

    quacq = QuAcq(self.solver_name, profiler)
    result = quacq.learn(task, oracle, model.description_provider,
                         max_queries=self.max_queries)
    return result, model
```

Note: Bias shuffle for QuAcq — QuAcq iterates bias in `_find_conflict()` via `list(task.bias)`. Set iteration order in Python 3.7+ is insertion order. Shuffling requires converting to list, shuffling, converting back to set — but set loses order. Alternative: store bias as `List[int]` with a `Set[int]` shadow for O(1) removal. Or: bias iteration order doesn't matter for correctness (QuickXPlain splits arbitrarily). Keep Set[int] — shuffling not meaningful for sets.

#### _run_example_mode() changes
```python
def _run_example_mode(self, positive_examples, negative_examples,
                      mode, shuffle_seed):
    from conacq.algorithms.interactive import InteractiveModel, QuAcq
    from conacq.oracle import FeatureModelOracle
    from conacq.example_generators import ExampleProvider

    oracle = FeatureModelOracle(self.fm_path)
    model = InteractiveModel.from_bias(self.bias_path)
    model.prepare(oracle)
    task = model.task

    mixed_examples = list(positive_examples) + list(negative_examples)
    example_provider = ExampleProvider(mixed_examples, shuffle_seed)
    fm_clauses = oracle.get_cnf_clauses()

    quacq = QuAcq(self.solver_name, profiler)
    result = quacq.learn_from_examples(
        task, example_provider, fm_clauses,
        model.description_provider,
        query_mode=mode, max_queries=self.max_queries
    )
    return result, model
```

#### Result construction changes
```python
# After getting result from QuAcq:
# result.kb_constraints already has string names (resolved by QuAcq._build_result)
# result.kb_assumption_ids has int IDs

# Resolve clauses for AccuracyCalculator
kb_names, kb_clauses = model.resolve_kb(result.kb_assumption_ids)

# BG clauses from oracle root constraint
bg_clauses = oracle.get_root_clauses() or []

run_result = InteractiveRunResult(
    kb_constraints=result.kb_constraints,  # str names (backward compat)
    kb_clauses=kb_clauses,
    bg_clauses=bg_clauses,
    n_bias=len(model.constraint_map),
    n_kb=result.n_kb,
    n_queries=result.n_queries,
    convergence_reason=result.convergence_reason,
    # ...
)
```

### Step 4: Update InteractiveRunResult (minor)

InteractiveRunResult.kb_constraints stays `List[str]` — it's the resolved form for CV loop. No change needed.

## Todo List
- [ ] Update InteractiveResult: add kb_assumption_ids field, keep kb_constraints for compat
- [ ] Update InteractiveResult.to_dict() to include both fields
- [ ] Update InteractiveResult.load() to handle both old/new formats
- [ ] Update QuAcq._build_result() to accept and use DescriptionProvider
- [ ] Update QuAcq.learn() signature to accept description_provider
- [ ] Update QuAcq.learn_from_examples() signature to accept description_provider
- [ ] Update InteractiveRunner._run_oracle_mode() to use InteractiveModel
- [ ] Update InteractiveRunner._run_example_mode() to use InteractiveModel
- [ ] Update InteractiveRunner result construction to use model.resolve_kb()
- [ ] Remove self.bias_clauses from InteractiveRunner constructor

## Success Criteria
- InteractiveResult stores both int IDs and resolved string names
- InteractiveResult.to_dict() output backward-compatible (kb_constraints field present)
- InteractiveRunner uses InteractiveModel.prepare() flow
- InteractiveRunResult.kb_constraints contains resolved string names
- CV loop (`_run_cv_loop`) works unchanged with runner

## Risk Assessment
1. **Backward compat**: Existing JSON result files have `kb_constraints: List[str]`. New format adds `kb_assumption_ids`. `load()` handles both. Consumers reading `kb_constraints` continue to work.
2. **Bias shuffle**: Set[int] doesn't preserve insertion order for iteration. If shuffle matters for QuAcq convergence behavior, may need ordered bias representation. For correctness, order doesn't matter — QuickXPlain is order-independent. For reproducibility, may need to sort or use list.

## Security Considerations
- No changes to external input handling

## Next Steps
- Phase 5: Update eval pipeline
