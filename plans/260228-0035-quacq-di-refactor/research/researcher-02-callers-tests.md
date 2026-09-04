# QuAcq Construction & Caller Patterns

Date: 2026-02-28
Focus: How external code constructs QuAcq, calls learn/learn_from_examples, and what the target DI pattern should be.

---

## 1. Current QuAcq Constructor

`QuAcq()` — zero-argument, no DI. Solver name injected optionally:

```python
# tests
quacq = QuAcq()                      # uses default 'glucose4'
quacq = QuAcq()                      # runner uses solver_name separately

# runner
quacq = QuAcq(self.solver_name, profiler)   # positional: solver_name, profiler
```

`QuAcq.__init__` accepts `(solver_name='glucose4', profiler=None)` — no task, no oracle injected.

---

## 2. QuAcqRunner (conacq/runners/quacq_runner.py)

### Construction
```python
# __init__: builds model once
self.model = (QuAcqModelBuilder
              .from_bias(bias_path)
              .with_oracle(self.oracle)
              .use_incremental(use_incremental)
              .build())
```

### Per-run flow in `run()`
```python
self.model.prepare(self.oracle)   # fresh task, reuses negation
task = self.model.task

quacq = QuAcq(self.solver_name, profiler)   # constructed per run

# Oracle mode
quacq.learn(task, oracle, description_provider, max_queries=...)

# Example mode
quacq.learn_from_examples(task, example_provider, oracle,
                           description_provider,
                           query_mode=mode, max_queries=...)
```

### Data extracted from model/task post-run
```python
self.model.resolve_kb(result.kb_assumption_ids)   # -> (names, clauses)
self.oracle.get_root_clauses()                     # -> bg_clauses
len(self.model.constraint_map)                    # -> n_bias
```

---

## 3. Tests (tests/test_quacq.py)

### Fixture chain
```python
oracle = FeatureModelOracle(FM_PATH)

model = (QuAcqModelBuilder
         .from_bias(BIAS_PATH)
         .with_oracle(oracle)
         .build())          # already prepared by builder

task = model.task           # QuAcqTask
```

### learn() call pattern
```python
quacq = QuAcq()
result = quacq.learn(task, oracle, model.description_provider, max_queries=5)
# description_provider is OPTIONAL (None-safe in empty-bias tests):
result = quacq.learn(task, oracle, max_queries=100)   # no provider → only works when bias empty
```

### learn_from_examples — not tested directly in test_quacq.py
Only the runner calls `learn_from_examples`; no standalone test exists.

### Minimal QuAcqTask construction in tests
```python
task = QuAcqTask(
    feature_ids={'root': 1},
    id_to_feature={1: 'root'},
)
# or
task = QuAcqTask()                         # all defaults (empty bias)
task = QuAcqTask(background_clauses=[[1], [2, -3]])
task = QuAcqTask(set_b=[5,6], background_clauses=...)
task = QuAcqTask(constraint_clauses={10: [[1,2]]})
```

---

## 4. QuAcqModel Exposed API

| Attribute/Method | Type | Purpose |
|---|---|---|
| `constraint_map` | `Dict[str, List[List[int]]]` | name → raw CNF |
| `negated_constraint_map` | same | name → negated CNF |
| `variables` | `Dict[str, int]` | feature → SAT var |
| `next_available_id` | `int` | assumption ID counter |
| `use_incremental` | `bool` | solver mode flag |
| `task` | `QuAcqTask` (property) | prepared task |
| `description_provider` | `DescriptionProvider` (property) | ID → name resolver |
| `prepare(oracle)` | → `QuAcqTask` | creates fresh task |
| `resolve_kb(ids)` | → `(names, clauses)` | post-run resolution |

Runner accesses: `model.task`, `model.oracle` (via `self.oracle`), `model.description_provider`, `model.constraint_map`, `model.resolve_kb()`.

---

## 5. ConGen Target DI Pattern (reference)

```python
class ConGen:
    def __init__(self, checker: ConsistencyChecker,
                 profiler_instance: AbstractProfiler = None) -> None:
        self.checker = checker
        self.profiler = profiler_instance or get_global_profiler()

    def acquire(self, set_b, set_bg, set_tc,
                set_neg_tv=None, negation_map=None) -> ConGenResult:
        ...
```

Key DI properties:
- `checker` injected at construction (not per-call)
- `profiler` injected at construction (optional, falls back to global)
- All data (`set_b`, `set_bg`, etc.) passed per-call to `acquire()`
- No task object at `__init__` — task data decomposed into primitives

---

## 6. Required Changes Summary

| Caller | Current | Change Required |
|---|---|---|
| `QuAcqRunner.run()` | `QuAcq(solver_name, profiler)` per run | Pass checker to `QuAcq.__init__` if DI refactor adds checker |
| `QuAcqRunner.run()` | `quacq.learn(task, oracle, provider, ...)` | Signature stays or task decomposed into primitives |
| `tests/test_quacq.py` | `QuAcq()` no args | Must remain zero-arg or add optional kwargs only |
| `tests/test_quacq.py` | `quacq.learn(task, oracle, provider, max_queries)` | Signature must stay compatible |
| `TestQuAcq.test_quacq_empty_bias` | `quacq.learn(task, oracle, max_queries=100)` (no provider) | Provider must stay optional |

---

## 7. Observations

- `QuAcq` is currently a stateless algorithm object (no DI beyond solver/profiler).
- The runner re-creates `QuAcq` each run but this is not required — could be shared.
- `description_provider` optional on `learn()` is a test convenience only; runner always passes it.
- No `learn_from_examples` tests exist; refactor there has no test coverage risk.
- `ConGen` pattern (checker injected at `__init__`, data at `acquire()`) is cleaner than current QuAcq pattern.

---

## Unresolved Questions

1. Will the DI refactor inject a `ConsistencyChecker` into `QuAcq.__init__` (like ConGen) or keep solver-name-based construction?
2. Is `description_provider` to remain a parameter on `learn()` or move to `__init__`?
3. Should `learn()` accept a `QuAcqTask` (current) or decomposed primitives (`set_b`, `set_bg`, etc.) to fully match ConGen's `acquire()` pattern?
