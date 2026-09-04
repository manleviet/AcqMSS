# ConGenRunner Class Exploration Report

**Project:** AcqMSS (Constraint Acquisition With Maximum Satisfiable Subsets)  
**File:** `/Users/manleviet/Development/GitHub/AcqMSS/conacq/runners/congen_runner.py`  
**Date:** 2026-02-27  

---

## Class Hierarchy & Implementation

### ConGenRunResult (Dataclass)
**Type:** `@dataclass`  
**Purpose:** Result container for a single ConGen execution with metrics

#### Attributes:
```
# KB Result
kb_constraints: List[str]           # Constraint names in learned KB
kb_clauses: List[List[int]]         # CNF clauses of learned KB
bg_clauses: List[List[int]]         # Background knowledge clauses (root constraint)
redundant_constraints: List[str]    # Constraint names marked as redundant
n_bias: int                         # Original number of bias constraints
n_mss: int                          # MSS size before REDUCE phase
n_kb: int                           # Final KB size after REDUCE

# Core Performance Metrics (Paper Table 7-8)
runtime_ms: float                   # Total execution time in milliseconds
consistency_checks: int             # Number of SAT solver calls
memory_peak_mb: float               # Peak memory usage in MB

# Extended Profiler Metrics
congen_runtime_ms: float = 0.0      # ConGen.acquire() runtime
acqmss_runtime_ms: float = 0.0      # AcqMSS total runtime (sum of recursive calls)
acqmss_calls: int = 0               # Number of AcqMSS recursive calls
reduce_runtime_ms: float = 0.0      # REDUCE phase runtime
solver_time_ms: float = 0.0         # SAT solver cumulative time
is_consistent_calls: int = 0        # Checker.is_consistent() invocation count
is_consistent_test_cases_calls: int = 0  # Checker.is_consistent_test_cases() count
redundancy_consistency_checks: int = 0   # Consistency checks during redundancy detection

profiler_data: Dict[str, Any]       # Full profiler snapshot (counters, timers, gauges)
```

#### Methods:
1. **`to_dict() -> dict`**
   - Converts entire result to dictionary for JSON serialization
   - Organizes metrics under 'kb_constraints', 'bg_clauses', 'redundant_constraints', 'n_*', 'performance' keys
   - Returns structure suitable for JSON export

2. **`get_performance_metrics() -> PerformanceMetrics`**
   - Extracts core metrics into PerformanceMetrics dataclass
   - Bridges ConGenRunResult → PerformanceMetrics (from `conacq.eval.performance_metrics`)
   - Useful for aggregation across multiple runs (CV folds)

---

## ConGenRunner Class

### Purpose
Orchestrates ConGen algorithm execution with integrated performance monitoring. Designed for cross-validation workflows where:
- Model built once from file paths (no examples)
- Reused via `prepare()` for each CV fold
- Metrics collected per fold (runtime, memory, SAT solver calls, KB sizes)

### Constructor: `__init__(...)`

**Signature:**
```python
def __init__(
    self,
    bias_path: str,
    fm_path: str,
    solver_name: str = 'glucose4',
    use_incremental: bool = True
)
```

**Parameters:**
- `bias_path` (str): Path to bias JSON file containing constraint definitions
- `fm_path` (str): Path to feature model (.uvl format file)
- `solver_name` (str, default='glucose4'): SAT solver name (passed to CheckerFactory)
- `use_incremental` (bool, default=True): Enable incremental solver mode

**Instance Variables Initialized:**
```python
self.solver_name: str                          # Saved solver name
self.use_incremental: bool                     # Saved incremental mode flag

self.model: ConGenModel                        # Built via ConGenModelBuilder
                                               # (bias only, no examples)
self.oracle: FeatureModelOracle                # FM oracle, reused across folds
                                               # use_incremental=False (caller
                                               # manages FM lifetime)

self._original_bias_constraint_order: List[str]  # Key ordering before shuffle
                                                  # Used to restore order if needed
```

**Initialization Flow:**
1. Store solver configuration (name, incremental mode)
2. Build ConGenModel from bias file using fluent builder pattern:
   - `ConGenModelBuilder.from_bias(bias_path)` → loads bias constraints
   - `.use_incremental(use_incremental)` → configure solver
   - `.build()` → returns unprepared ConGenModel
3. Create FeatureModelOracle from FM file (incremental=False for oracle)
4. Cache original bias constraint ordering for shuffle restore

---

### Main Method: `run(...)`

**Signature:**
```python
def run(
    self,
    positive_examples: List[Dict[str, bool]],
    negative_examples: List[Dict[str, bool]],
    shuffle_seed: Optional[int] = None
) -> ConGenRunResult
```

**Parameters:**
- `positive_examples`: List of E+ (valid configurations), each a dict {feature: True/False}
- `negative_examples`: List of E- (invalid configurations), each a dict {feature: True/False}
- `shuffle_seed` (Optional[int]): If provided, shuffle bias constraint order using this seed

**Return Type:** `ConGenRunResult`

**Detailed Execution Flow:**

```
┌─────────────────────────────────────────────────────────┐
│ run(positive_examples, negative_examples, shuffle_seed) │
└────────────┬────────────────────────────────────────────┘
             │
    Step 1: Shuffle (optional)
             │
             ├─ if shuffle_seed is not None:
             │    - Get original bias constraint keys
             │    - Shuffle keys using Random(shuffle_seed)
             │    - Reorder model.constraint_map
             │
    Step 2: Memory Profiling Setup
             │
             ├─ profiler_session(ProfilerPreset.BENCHMARK) context
             ├─ tracemalloc.start()
             ├─ profiler.timer("congen_total_time")
             │
    Step 3: Model Preparation (Generates NE)
             │
             ├─ model.prepare(oracle, pos_examples, neg_examples)
             │    └─ Runs ConGenTaskPreparation internally
             │       ├─ Loads BGData from oracle
             │       ├─ Generates NE (negative examples via GenerateNE)
             │       └─ Creates ConGenTask with set_neg_tv populated
             │
    Step 4: Checker Initialization
             │
             ├─ CheckerFactory.create_from_model(model, solver_name, profiler)
             │
    Step 5: ConGen Execution
             │
             ├─ congen = ConGen(checker, profiler)
             ├─ congen.acquire(
             │    set_b=task.set_c,           # Bias constraints
             │    set_bg=task.set_b,          # Background (root) constraints
             │    set_tc=task.set_tc,         # Positive test cases
             │    set_neg_tv=task.set_neg_tv, # Negated negative examples
             │    negation_map=task.negation_map
             │  )
             │    └─ Returns ConGenResult with kb_assumption_ids, redundant_ids, n_*, metadata
             │
    Step 6: Memory & Profiler Extraction
             │
             ├─ Stop memory tracking (get peak)
             ├─ Extract metrics from profiler:
             │    - congen_total_time (list, sum → runtime_ms)
             │    - paper_consistency_checks (scalar)
             │    - congen_runtime, acqmss_runtime, reduce_runtime, solver_time (lists, sum)
             │    - acqmss_calls, is_consistent_calls, is_consistent_test_cases_calls, etc.
             │
    Step 7: Result Resolution
             │
             ├─ model.resolve_result(result)
             │    ├─ Converts assumption IDs → constraint names/clauses
             │    └─ Returns (bg_clauses, kb_clauses, kb_names, redundant_names)
             │
    Step 8: Package Results
             │
             ├─ Create ConGenRunResult with:
             │    - KB constraints, clauses, redundancies
             │    - All performance metrics
             │    - Full profiler snapshot
             │
             └─ Return ConGenRunResult
```

**Error Handling:**
```python
try:
    # Steps 3-5 (model prep, checker init, ConGen execution)
finally:
    # Always cleanup
    tracemalloc.stop()
    if checker is not None:
        checker.cleanup()
```

**Key Metrics Extracted:**
- `runtime_ms`: Total execution (profiler timer "congen_total_time" × 1000)
- `consistency_checks`: Paper-defined metric (profiler counter "paper_consistency_checks")
- `memory_peak_mb`: Peak memory from tracemalloc / (1024*1024)
- `congen_runtime_ms`: Sum of "congen_runtime" list × 1000
- `acqmss_runtime_ms`: Sum of "acqmss_runtime" list × 1000
- `reduce_runtime_ms`: Sum of "reduce_runtime" list × 1000
- `solver_time_ms`: Sum of "solver_time" list × 1000
- `acqmss_calls`, `is_consistent_calls`, etc.: Direct profiler counter values

---

### Cleanup Method: `cleanup()`

**Signature:**
```python
def cleanup(self)
```

**Purpose:** Release oracle resources (especially FM solver handle)

**Implementation:**
```python
if hasattr(self, 'oracle') and self.oracle is not None:
    self.oracle.cleanup()
```

**Usage:** Call when runner is no longer needed (e.g., after CV fold loop)

---

## Dependencies & Data Flow

### Imported Classes:

1. **`ConGen`** (from `conacq.algorithms.acqmss.congen`)
   - Main constraint acquisition algorithm
   - Takes checker, profiler; performs acquire(set_b, set_bg, set_tc, set_neg_tv, negation_map)
   - Returns ConGenResult with kb_assumption_ids, redundant_ids, n_bias, n_mss, n_kb

2. **`ConGenModelBuilder`** (from `conacq.algorithms.acqmss.congen_model_builder`)
   - Fluent builder for ConGenModel
   - Loads bias, optionally configures oracle/examples
   - Supports auto-prepare pattern or manual prepare

3. **`FeatureModelOracle`** (from `conacq.oracle`)
   - Provides ground truth via SAT-based FM validation
   - Methods: is_valid(assignments), get_fm_data(), cleanup()
   - Injected at prepare() time (not in __init__)

4. **`CheckerFactory`** (from `explanation.operations.algorithms.checker`)
   - Factory for creating solver checkers
   - `create_from_model(model, solver_name, profiler)` → ConsistencyChecker instance
   - Supports multiple solver types

5. **`Profiler`, `profiler_session`, `ProfilerPreset`** (from `explanation.operations.algorithms.profiler`)
   - Collects metrics: counters, timers (as lists), gauges
   - `ProfilerPreset.BENCHMARK` configuration
   - Methods: get_metric(key, default), to_dict()

6. **`PerformanceMetrics`** (from `conacq.eval.performance_metrics`)
   - Dataclass for single-run metrics
   - Methods: to_dict()

---

## Data Flow Diagram (ASCII)

```
┌─────────────────────────────────────────────────────┐
│ ConGenRunner.__init__(bias_path, fm_path, ...)      │
│                                                     │
│  ConGenModelBuilder                                 │
│    .from_bias(bias_path)                            │
│    .use_incremental(...)                            │
│    .build()  →  ConGenModel (unprepared)            │
│                                                     │
│  FeatureModelOracle(fm_path)  →  self.oracle        │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│ ConGenRunner.run(E+, E-, shuffle_seed)              │
│                                                     │
│  1. [Optional] Shuffle bias order                   │
│  2. model.prepare(oracle, E+, E-)                   │
│      │                                              │
│      ├─ ConGenTaskPreparation.prepare()             │
│      │   ├─ BGData extraction from oracle           │
│      │   ├─ GenerateNE for E-                       │
│      │   └─ → ConGenTask (with set_neg_tv)         │
│      │                                              │
│      └─ Store task, description_provider           │
│                                                     │
│  3. CheckerFactory.create_from_model(...)           │
│      └─ → Solver checker instance                   │
│                                                     │
│  4. ConGen(checker, profiler).acquire(...)          │
│      ├─ IsConsistent check                          │
│      ├─ AcqMSS (MSS search)                         │
│      ├─ REDUCE (redundancy elimination)             │
│      └─ → ConGenResult (assumption IDs)             │
│                                                     │
│  5. Profiler extraction                             │
│      ├─ Memory peak from tracemalloc                │
│      ├─ Timers: sum all calls                       │
│      └─ Counters: direct values                     │
│                                                     │
│  6. model.resolve_result(ConGenResult)              │
│      ├─ Assumption IDs → Constraint names/clauses   │
│      └─ → (bg_clauses, kb_clauses, kb_names, ...)  │
│                                                     │
│  7. Package into ConGenRunResult                    │
│      └─ Include KB, metrics, profiler snapshot      │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
                  ConGenRunResult
```

---

## Key Design Patterns

### 1. **Builder Pattern** (ConGenModelBuilder)
- Fluent API for model construction
- Supports optional parameters (oracle, examples, incremental mode)
- Auto-prepare if oracle + examples present, else manual prepare

### 2. **Strategy Pattern** (CheckerFactory)
- Decouples solver selection from algorithm logic
- Multiple solver implementations (glucose4, etc.)

### 3. **Separation of Concerns**
- **ConGenRunner**: Orchestration, metrics collection
- **ConGenModel**: Data container (constraints, variables)
- **ConGen**: Algorithm logic (AcqMSS + REDUCE)
- **FeatureModelOracle**: Ground truth provider

### 4. **Context Manager** (profiler_session)
- Automatic profiler lifecycle management
- Memory/time tracking within scope

### 5. **Cross-Validation Pattern**
- Build model once (`__init__`)
- Reuse with different folds (`prepare()` per fold)
- Metrics collected per fold in single ConGenRunResult

---

## Integration Points

### With ConGenModel:
- `prepare(oracle, positive_examples, negative_examples)` → ConGenTask
- `resolve_result(ConGenResult)` → (bg_clauses, kb_clauses, kb_names, redundant_names)
- `constraint_map`: Maps constraint names to CNF clauses
- `variables`: Feature name → ID mapping

### With ConGen:
- Passes: set_b, set_bg, set_tc, set_neg_tv, negation_map
- Receives: ConGenResult with kb_assumption_ids, redundant_ids, n_bias, n_mss, n_kb

### With FeatureModelOracle:
- Injected at `prepare()` time
- Used for BGData extraction and GenerateNE
- Cleanup via `cleanup()` method

### With Profiler:
- Captures metrics from ConGen execution
- Tracks: counters (consistency checks), timers (runtime), gauges (memory)
- Supports multiple metric aggregations (sum, mean, etc.)

---

## Performance Monitoring Metrics

### Core Metrics (Paper Table 7-8)
| Metric | Type | Source | Purpose |
|--------|------|--------|---------|
| `runtime_ms` | float | profiler timer "congen_total_time" | Total execution time |
| `consistency_checks` | int | profiler counter "paper_consistency_checks" | SAT solver invocations |
| `memory_peak_mb` | float | tracemalloc | Peak memory usage |
| `n_bias` | int | ConGenResult | Original bias size |
| `n_mss` | int | ConGenResult | MSS size before REDUCE |
| `n_kb` | int | ConGenResult | Final KB size |

### Extended Metrics (Profiler Breakdown)
| Metric | Source | Purpose |
|--------|--------|---------|
| `congen_runtime_ms` | profiler timer "congen_runtime" | ConGen.acquire() time |
| `acqmss_runtime_ms` | profiler timer "acqmss_runtime" | AcqMSS total time |
| `acqmss_calls` | profiler counter | Number of AcqMSS calls |
| `reduce_runtime_ms` | profiler timer "reduce_runtime" | REDUCE phase time |
| `solver_time_ms` | profiler timer "solver_time" | SAT solver cumulative time |
| `is_consistent_calls` | profiler counter | Checker.is_consistent() calls |
| `is_consistent_test_cases_calls` | profiler counter | Checker.is_consistent_test_cases() calls |
| `redundancy_consistency_checks` | profiler counter | Consistency checks in REDUCE only |

---

## Cross-Validation Support

**Pattern:**
```python
runner = ConGenRunner(bias_path, fm_path)

for fold_idx, (fold_pos, fold_neg) in enumerate(folds):
    result = runner.run(fold_pos, fold_neg)
    metrics_list.append(result.get_performance_metrics())

runner.cleanup()

# Aggregate metrics across folds
from conacq.eval.performance_metrics import aggregate_metrics
agg = aggregate_metrics([m for m in metrics_list])
```

**Benefits:**
- Model built once (expensive constraint loading)
- Reused across folds (efficient memory)
- Per-fold metrics collected
- Aggregation support via `aggregate_metrics()`

---

## Example Usage

```python
from conacq.runners.congen_runner import ConGenRunner

# Initialize
runner = ConGenRunner(
    bias_path='data/bias/model.json',
    fm_path='data/fms/model.uvl',
    solver_name='glucose4',
    use_incremental=True
)

# Run ConGen
result = runner.run(
    positive_examples=[{'root': True, 'feature1': True, ...}],
    negative_examples=[{'root': True, 'feature1': False, ...}],
    shuffle_seed=42  # Optional
)

# Access results
print(f"KB size: {result.n_kb}")
print(f"Runtime: {result.runtime_ms}ms")
print(f"Checks: {result.consistency_checks}")
print(f"Memory: {result.memory_peak_mb}MB")

# Get performance metrics
metrics = result.get_performance_metrics()

# Export to JSON
import json
with open('result.json', 'w') as f:
    json.dump(result.to_dict(), f, indent=2)

# Cleanup
runner.cleanup()
```

---

## Summary Table

| Aspect | Details |
|--------|---------|
| **Purpose** | Orchestrate ConGen execution with integrated metrics collection for CV workflows |
| **Base Classes** | None (standalone class) |
| **Constructor Params** | bias_path, fm_path, solver_name, use_incremental |
| **Main Method** | `run(positive_examples, negative_examples, shuffle_seed)` → ConGenRunResult |
| **Helper Methods** | `cleanup()` |
| **Result Type** | ConGenRunResult (dataclass with KB + metrics) |
| **Metrics Collected** | 13 performance metrics (runtime, checks, memory, n_mss, n_kb, + 8 extended) |
| **Dependencies** | ConGenModel, ConGen, FeatureModelOracle, CheckerFactory, Profiler |
| **Lifecycle** | Create once per CV run, call run() multiple times (once per fold), cleanup() at end |
| **Error Handling** | try/finally with checker.cleanup() guarantee |
| **CV Support** | Model reuse via prepare() per fold, metrics per fold |

