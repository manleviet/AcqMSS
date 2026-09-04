# Research: QuAcq Query Flow & InteractiveRunner

Date: 2026-02-26

---

## 1. query_history Population

**Source of truth**: `InteractiveTask.record_query()` — line 95–98 of `conacq/algorithms/interactive/task.py`

```python
def record_query(self, config: Dict[str, bool], answer: bool) -> None:
    self.n_queries += 1
    self.query_history.append((config.copy(), answer))
```

**Call sites** (all inside `conacq/algorithms/interactive/`):

| File | Line | Context |
|------|------|---------|
| `quacq.py` | 99 | Main QuAcq loop — after oracle answers membership query |
| `quacq.py` | 185 | `learn_from_examples()` — after example provider resolves query |
| `findc.py` | 131 | FindC subroutine — discriminating queries |
| `findc.py` | 172 | FindC subroutine — repeated discriminating queries |

**Data shape**: `List[Tuple[Dict[str, bool], bool]]`
- `config`: `{feature_name: True/False}` — full or partial feature assignment
- `answer`: `True` = positive (valid config), `False` = negative (violates constraint)

**Propagated to InteractiveResult**: `quacq.py` line 291
```python
query_history=task.query_history
```

---

## 2. InteractiveRunResult Fields (and what's missing)

**Defined**: `conacq/runners/interactive_runner.py` lines 22–54

| Field | Type | Notes |
|-------|------|-------|
| `kb_constraints` | `List[str]` | Resolved constraint names |
| `kb_clauses` | `List[List[int]]` | CNF clauses of learned KB |
| `bg_clauses` | `List[List[int]]` | Root constraint clauses |
| `n_bias` | `int` | Original bias size |
| `n_kb` | `int` | Final KB size |
| `n_queries` | `int` | Total membership queries |
| `convergence_reason` | `str` | Why learning stopped |
| `runtime_ms` | `float` | Wall-clock time |
| `consistency_checks` | `int` | SAT solver calls |
| `memory_peak_mb` | `float` | Peak memory |
| `profiler_data` | `Dict` | Full profiler snapshot |

**Missing from InteractiveRunResult**:
- `query_history` — exists in `InteractiveResult` (inner algo result, line 64 of `result.py`) but NOT propagated to `InteractiveRunResult`
- `kb_assumption_ids` — also dropped during conversion at runner line 227–239

**Where it gets dropped**: `InteractiveRunner.run()` lines 227–239 — constructs `InteractiveRunResult` from inner `result` but ignores `result.query_history`.

---

## 3. ExampleSet JSON Format

**Defined by**: `ExampleIO.save_json()` in `conacq/examples/io_utils.py` lines 41–64

```json
{
  "metadata": { "...": "..." },
  "statistics": {
    "total": 10,
    "n_positive": 6,
    "n_negative": 4,
    "pos_ratio": 0.6,
    "neg_ratio": 0.4
  },
  "positive": [
    { "id": "q0+", "assignments": { "feature_A": true, "feature_B": false } }
  ],
  "negative": [
    { "id": "q1-", "assignments": { "feature_A": false, "feature_B": true } }
  ]
}
```

**Load path**: `ExampleIO.load_json()` lines 67–100 — reconstructs `Example` objects with `ExampleType.POSITIVE/NEGATIVE`.

---

## 4. query_history → ExampleSet Conversion

Direct mapping — each `(config, answer)` pair becomes one `Example`:

```python
from conacq.examples.data_structures import Example, ExampleSet, ExampleType
from conacq.examples.io_utils import ExampleIO

def query_history_to_example_set(query_history, metadata=None):
    es = ExampleSet(metadata=metadata or {})
    for i, (config, answer) in enumerate(query_history):
        example_type = ExampleType.POSITIVE if answer else ExampleType.NEGATIVE
        suffix = "+" if answer else "-"
        example = Example(
            id=f"q{i}{suffix}",
            assignments=config,
            example_type=example_type
        )
        es.add(example)
    return es
```

No transformation of `config` needed — it's already `Dict[str, bool]` matching `Example.assignments` format.

---

## 5. Key Code Locations

| Concern | File | Lines |
|---------|------|-------|
| `query_history` field definition | `conacq/algorithms/interactive/task.py` | 65 |
| `record_query()` method | `conacq/algorithms/interactive/task.py` | 95–98 |
| QuAcq oracle-mode call site | `conacq/algorithms/interactive/quacq.py` | 99 |
| QuAcq example-mode call site | `conacq/algorithms/interactive/quacq.py` | 185 |
| Propagation to InteractiveResult | `conacq/algorithms/interactive/quacq.py` | 291 |
| `InteractiveResult.query_history` | `conacq/algorithms/interactive/result.py` | 64 |
| `InteractiveResult.to_dict()` serialization | `conacq/algorithms/interactive/result.py` | 85–88 |
| `InteractiveResult.load()` deserialization | `conacq/algorithms/interactive/result.py` | 107–138 |
| `InteractiveRunResult` (runner level) | `conacq/runners/interactive_runner.py` | 22–54 |
| query_history **dropped** here | `conacq/runners/interactive_runner.py` | 227–239 |
| `ExampleIO.save_json()` | `conacq/examples/io_utils.py` | 26–64 |
| `ExampleIO.load_json()` | `conacq/examples/io_utils.py` | 66–100 |
| `ExampleSet` data structure | `conacq/examples/data_structures.py` | 143–217 |
| `Example` data structure | `conacq/examples/data_structures.py` | 20–140 |

---

## Summary

- `query_history` is populated inside the QuAcq algorithm (both oracle and example modes) via `task.record_query()`, then propagated into `InteractiveResult.query_history`.
- **Gap**: `InteractiveRunResult` (runner layer) does NOT carry `query_history` — it is discarded at runner line 227–239.
- To extract query_history for ConGen eval pipeline: either (a) add `query_history` field to `InteractiveRunResult` and propagate it, or (b) access it from the inner `result` before it goes out of scope inside `InteractiveRunner.run()`.
- Conversion from `query_history` to `ExampleSet` is trivial — config dicts map directly, boolean answer maps to `ExampleType`.
- `ExampleIO` provides ready-to-use JSON save/load — no new I/O code needed.

---

## Unresolved Questions

1. Should `query_history` be added to `InteractiveRunResult.to_dict()`? If so, does it need to match `InteractiveResult`'s serialization format (`{'config': ..., 'answer': ...}`) for consistency?
2. Are FindC sub-queries (from `findc.py`) meaningful as training examples for ConGen, or should only the top-level QuAcq queries be captured?
3. Do configs in `query_history` always cover ALL features, or can they be partial (FindScope partial configs)? Partial configs may not be valid as ConGen examples.
