# Brainstorm: Unified Runner Lifecycle

## Problem Statement

ConGenRunner and InteractiveRunner share ~70% structural overlap but differ in resource lifecycle (build-once vs build-per-run), result fields, and CV integration. Goal: unify both to enable a single polymorphic evaluation pipeline.

## Key Finding

InteractiveModel and FeatureModelOracle are both safe to reuse across runs. Only QuAcqTask accumulates state, but `model.prepare()` already creates fresh tasks per run — same pattern as ConGenRunner.

## Agreed Solution

### Unified Lifecycle

```
__init__():  Load bias → Create model → Create oracle (BUILD ONCE)
run():       model.prepare(...) → algorithm → result (RUN MANY)
cleanup():   oracle.cleanup() (CLEANUP ONCE)
```

### Class Hierarchy

```
BaseRunner (ABC)
├── __init__(bias_path, fm_path, solver_name)
├── run(pos_ex=None, neg_ex=None, shuffle_seed=None) -> BaseRunResult
├── cleanup()
│
├── ConGenRunner        # adds: use_incremental
└── InteractiveRunner   # adds: max_queries, query_mode, mode param in run()

BaseRunResult (dataclass)
├── 9 shared fields
├── to_dict(), get_performance_metrics()
│
├── ConGenRunResult         # adds: n_mss, redundant_constraints, 8 profiler metrics
└── InteractiveRunResult    # adds: n_queries, convergence_reason, query_history
```

### Design Decisions

1. **run() signature**: Optional examples for both. Each subclass validates its own requirements.
2. **CV integration**: Single unified CV function accepting BaseRunner polymorphically.
3. **PerformanceMetrics**: `n_mss` becomes `Optional[int] = None` — no more `n_mss=0` hack.

### Shared Result Fields (BaseRunResult)

| Field | Type |
|-------|------|
| `kb_constraints` | `List[str]` |
| `kb_clauses` | `List[List[int]]` |
| `bg_clauses` | `List[List[int]]` |
| `n_bias` | `int` |
| `n_kb` | `int` |
| `runtime_ms` | `float` |
| `consistency_checks` | `int` |
| `memory_peak_mb` | `float` |
| `profiler_data` | `Dict[str, Any]` (default `{}`) |

### InteractiveRunner Changes

- Move oracle + model creation from `run()` → `__init__()`
- Make `cleanup()` meaningful (release oracle)
- Expose `feature_ids` from model (already done)

### PerformanceMetrics Changes

- `n_mss: int` → `n_mss: Optional[int] = None`
- Update all callers/consumers to handle None

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Dataclass inheritance field ordering | Medium | Use `kw_only=True` or put defaults only in child classes |
| `to_dict()` output format changes | Medium | Keep backward-compatible structure; update `extract_results.py` |
| CV function complexity | Low | Polymorphic dispatch keeps it simple |

## Implementation Phases

1. **BaseRunResult** — Extract shared fields + methods into base dataclass
2. **PerformanceMetrics** — Make `n_mss` optional
3. **BaseRunner** — Extract ABC with shared `__init__`/`cleanup` pattern
4. **InteractiveRunner** — Align lifecycle to build-once pattern
5. **Unified CV function** — Single function for both runner types
6. **Tests** — Verify both pipelines produce identical evaluation flow
7. **Cleanup** — Remove duplicate code, update docs

## Success Criteria

- Both runners follow identical lifecycle (build once, run many, cleanup once)
- Single CV function works with either runner
- All existing tests pass
- `extract_results.py` works with both result types
