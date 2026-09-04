# ConGenRunResult Class Exploration

**Date:** 2026-02-27  
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/congen_runner.py`  
**Lines:** 25-109

---

## Overview

`ConGenRunResult` is a **dataclass** that encapsulates the complete output of a ConGen constraint acquisition run, including:
- Learned knowledge base (KB) representation
- Performance metrics (runtime, memory, SAT solver calls)
- Extended profiler data (detailed timing breakdowns)

It serves as the primary return type from `ConGenRunner.run()` and enables cross-validation by capturing both KB results and performance statistics per fold.

---

## Class Definition

```python
@dataclass
class ConGenRunResult:
```

**Base Class:** None (dataclass decorator provides initialization)  
**Protocols Implemented:** None explicitly, but provides JSON serialization interface

---

## Dataclass Fields (Instance Variables)

### KB Result Fields (Required)

| Field | Type | Purpose |
|-------|------|---------|
| `kb_constraints` | `List[str]` | List of constraint IDs/names in learned KB |
| `kb_clauses` | `List[List[int]]` | CNF clauses of learned KB (literal format) |
| `bg_clauses` | `List[List[int]]` | Background knowledge clauses (root constraint) |
| `redundant_constraints` | `List[str]` | List of redundant constraint IDs/names |
| `n_bias` | `int` | Original number of bias constraints (size of B) |
| `n_mss` | `int` | Size of MSS before REDUCE phase |
| `n_kb` | `int` | Final KB size after acquisition |

### Core Performance Metrics (Required)

| Field | Type | Purpose |
|-------|------|---------|
| `runtime_ms` | `float` | Total execution time in milliseconds |
| `consistency_checks` | `int` | Number of SAT solver calls (paper-defined metric) |
| `memory_peak_mb` | `float` | Peak memory usage in MB |

### Extended Profiler Metrics (Optional, Default=0)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `congen_runtime_ms` | `float` | 0.0 | ConGen.acquire() total time |
| `acqmss_runtime_ms` | `float` | 0.0 | AcqMSS total time (sum of all recursive calls) |
| `acqmss_calls` | `int` | 0 | Number of AcqMSS recursive calls |
| `reduce_runtime_ms` | `float` | 0.0 | Reduce phase (redundancy elimination) time |
| `solver_time_ms` | `float` | 0.0 | SAT solver total time (sum of all checks) |
| `is_consistent_calls` | `int` | 0 | Checker.is_consistent() call count |
| `is_consistent_test_cases_calls` | `int` | 0 | Checker.is_consistent_test_cases() call count |
| `redundancy_consistency_checks` | `int` | 0 | Consistency checks in Reduce phase only |

### Profiler Data (Optional, Default=empty dict)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| `profiler_data` | `Dict[str, Any]` | `{}` | Full profiler snapshot (counters, timers, gauges) |

---

## Methods

### 1. `to_dict() -> dict`

**Signature:**
```python
def to_dict(self) -> dict:
```

**Purpose:** Convert instance to dictionary for JSON serialization.

**Implementation:**
- Flattens KB result fields (kb_constraints, bg_clauses, redundant_constraints, n_bias, n_mss, n_kb)
- Nests performance metrics under 'performance' key
- Includes extended profiler metrics and full profiler_data snapshot

**Returns:** `dict` with structure:
```python
{
    'kb_constraints': List[str],
    'bg_clauses': List[List[int]],
    'redundant_constraints': List[str],
    'n_bias': int,
    'n_mss': int,
    'n_kb': int,
    'performance': {
        'runtime_ms': float,
        'consistency_checks': int,
        'memory_peak_mb': float,
        'congen_runtime_ms': float,
        'acqmss_runtime_ms': float,
        'acqmss_calls': int,
        'reduce_runtime_ms': float,
        'solver_time_ms': float,
        'is_consistent_calls': int,
        'is_consistent_test_cases_calls': int,
        'redundancy_consistency_checks': int,
        'profiler': Dict[str, Any],
    }
}
```

---

### 2. `get_performance_metrics() -> PerformanceMetrics`

**Signature:**
```python
def get_performance_metrics(self) -> PerformanceMetrics:
```

**Purpose:** Extract performance metrics as a separate `PerformanceMetrics` dataclass object.

**Implementation:**
- Projects core and extended metrics from ConGenRunResult
- Excludes KB data and profiler snapshot
- Returns PerformanceMetrics object for aggregation/statistics

**Returns:** `PerformanceMetrics` instance with:
- `runtime_ms`, `consistency_checks`, `memory_peak_mb`
- `n_mss`, `n_kb`
- All extended profiler metrics (congen_runtime_ms, acqmss_runtime_ms, etc.)

**Note:** Does NOT include profiler_data; see PerformanceMetrics definition in `/Users/manleviet/Development/GitHub/AcqMSS/conacq/eval/performance_metrics.py`

---

## Data Flow & Dependencies

### Construction Flow (from ConGenRunner.run())

1. **ConGenRunner.run()** method:
   - Initializes profiler session with BENCHMARK preset
   - Starts memory tracking via tracemalloc
   - Shuffles bias constraint order (if seed provided)
   - Calls `model.prepare()` to run GenerateNE internally
   - Creates checker via CheckerFactory
   - Runs ConGen algorithm and collects result

2. **Metrics Collection** (post-ConGen):
   - Extracts timing data from profiler: `profiler.get_metric()`
   - Computes memory peak from tracemalloc: `tracemalloc.get_traced_memory()`
   - Collects consistency check count from profiler
   - Extracts extended profiler metrics (acqmss_runtime, reduce_runtime, etc.)
   - Gets profiler snapshot: `profiler.to_dict()`

3. **KB Transformation**:
   - Calls `model.resolve_result(result)` to convert assumption IDs → constraint names/clauses
   - Returns: (bg_clauses, kb_clauses, kb_names, redundant_names)

4. **Instance Creation**:
   ```python
   ConGenRunResult(
       kb_constraints=kb_names,
       kb_clauses=kb_clauses,
       bg_clauses=bg_clauses,
       redundant_constraints=redundant_names,
       n_bias=result.n_bias,
       n_mss=result.n_mss,
       n_kb=result.n_kb,
       runtime_ms=runtime_ms,
       consistency_checks=consistency_checks,
       memory_peak_mb=memory_peak_mb,
       congen_runtime_ms=congen_runtime_ms,
       acqmss_runtime_ms=acqmss_runtime_ms,
       acqmss_calls=acqmss_calls,
       reduce_runtime_ms=reduce_runtime_ms,
       solver_time_ms=solver_time_ms,
       is_consistent_calls=is_consistent_calls,
       is_consistent_test_cases_calls=is_consistent_test_cases_calls,
       redundancy_consistency_checks=redundancy_consistency_checks,
       profiler_data=profiler_snapshot
   )
   ```

### Key Dependencies

| Dependency | Type | Purpose |
|------------|------|---------|
| `conacq.eval.performance_metrics.PerformanceMetrics` | Class Import | Target type for `get_performance_metrics()` |
| `ConGenRunner.run()` | Calling Context | Primary producer of ConGenRunResult instances |
| `model.resolve_result()` | External Method | Transforms ConGen result into KB constraint names/clauses |
| Profiler (explanation.operations.algorithms.profiler) | Metrics Source | Provides timing data and counter metrics |
| tracemalloc | Stdlib Module | Provides memory peak measurement |

---

## Metrics Taxonomy

### Paper-Defined Metrics (Table 7-8)
- `runtime_ms` — total execution time
- `consistency_checks` — SAT solver call count
- `memory_peak_mb` — peak memory
- `n_mss` — MSS size before REDUCE
- `n_kb` — final KB size

### Extended Profiler Metrics (Breakdown)
- **ConGen Phases:**
  - `congen_runtime_ms` — ConGen.acquire() total
  - `acqmss_runtime_ms` — AcqMSS total (recursive)
  - `reduce_runtime_ms` — Reduce phase only

- **Solver Activity:**
  - `solver_time_ms` — SAT solver cumulative time
  - `is_consistent_calls` — Consistency check frequency
  - `is_consistent_test_cases_calls` — Test case check frequency
  - `redundancy_consistency_checks` — Checks in Reduce phase

- **Algorithm Activity:**
  - `acqmss_calls` — AcqMSS recursive invocations

---

## Serialization Interface

### JSON Export Path
```
ConGenRunResult.to_dict() 
  → dict with nested 'performance' object 
  → json.dumps() for file output
```

### Metrics Export Path
```
ConGenRunResult.get_performance_metrics() 
  → PerformanceMetrics dataclass 
  → PerformanceMetrics.to_dict() for serialization
  → aggregate_metrics(List[PerformanceMetrics]) for cross-validation stats
```

---

## Use Cases

1. **Cross-Validation:** Store one ConGenRunResult per fold, aggregate metrics via PerformanceMetrics
2. **Result Logging:** to_dict() → JSON file output for reproducibility
3. **Profiler Analysis:** profiler_data field for detailed breakdown inspection
4. **KB Validation:** kb_clauses, kb_constraints for correctness checking
5. **Performance Benchmarking:** Extended metrics enable bottleneck identification (ConGen vs AcqMSS vs Reduce vs Solver)

---

## Related Classes & Modules

| Module | Class/Function | Relation |
|--------|---|----------|
| `conacq.runners.congen_runner` | ConGenRunner | Producer of ConGenRunResult |
| `conacq.eval.performance_metrics` | PerformanceMetrics, AggregatedPerformanceMetrics, aggregate_metrics() | Consumer/aggregation |
| `conacq.algorithms.acqmss.congen` | ConGen | Algorithm executed within run() |
| `conacq.algorithms.acqmss.congen_model_builder` | ConGenModelBuilder | Model preparation |
| `conacq.oracle` | FeatureModelOracle | Ground truth oracle |
| `explanation.operations.algorithms.profiler` | Profiler, profiler_session, ProfilerPreset | Metrics collection |

---

## Summary Table

| Aspect | Details |
|--------|---------|
| **Classification** | Dataclass (result/value object) |
| **Constructor** | Auto-generated by @dataclass decorator |
| **Fields** | 23 total (7 required KB + 3 required metrics + 12 optional extended + 1 profiler dict) |
| **Methods** | 2 public (to_dict, get_performance_metrics) |
| **Primary Role** | Encapsulate ConGen run output + metrics for cross-validation |
| **Serialization** | to_dict() → JSON; get_performance_metrics() → aggregation |
| **Key Metric Groups** | Core (runtime/checks/memory), Extended (profiler breakdown) |
| **Typical Lifetime** | Created once per ConGen run; stored in evaluation results; aggregated across folds |

