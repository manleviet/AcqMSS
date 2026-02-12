# AcqMSS System Architecture

## High-Level Overview

AcqMSS is organized in a **two-layer architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│ Application Layer (apps/)                                   │
│ generate_bias_config.py, generate_examples.py,              │
│ run_congen.py, run_interactive.py, run_evaluation.py        │
└─────────────────┬───────────────────────────────────────────┘
                  │ TOML Configuration Files
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Core Acquisition Algorithms (acqmss/)                       │
│ ├─ CONGEN: GenerateNE → ACQMSS → REDUCE                     │
│ ├─ QuAcq: GenerateQuery → Oracle → Update KB                │
│ ├─ Bias generation from feature models                      │
│ ├─ Example generation (RS, FF, 2-COV strategies)            │
│ └─ Evaluation framework (CV, accuracy metrics, profiling)    │
└─────────────────┬───────────────────────────────────────────┘
                  │ Dependencies
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ SAT Infrastructure (explanation/)                           │
│ ├─ Diagnosis Algorithms                                      │
│ │  ├─ FastDiag: Breadth-first minimal diagnosis             │
│ │  ├─ QuickXPlain: Minimal conflict finding                 │
│ │  ├─ KBDiag: Kernel-based diagnosis                        │
│ │  └─ WipeOutR: FM and test case variants                   │
│ ├─ HSDAG: Tree search optimization (10x speedup)            │
│ ├─ Solver Abstraction Layer                                  │
│ │  ├─ IncrementalPySATChecker (persistent solver)           │
│ │  ├─ NonIncrementalPySATChecker (fresh solver)             │
│ │  └─ SAT4JChecker (external Java solver)                   │
│ ├─ Model Transformation (FM → SAT, DIMACS conversion)       │
│ └─ Profiling Infrastructure (timing, memory, call counting)  │
└─────────────────────────────────────────────────────────────┘
                  │ SAT Solvers
                  ▼
        ┌────────┴──────────┐
        │                   │
        ▼                   ▼
    PySAT Solvers      SAT4J (Java)
    (glucose4,         (external)
     minisat,
     lingeling)
```

## Package Organization

### acqmss/ — Constraint Acquisition Core

**Purpose**: Implement constraint discovery algorithms independent of SAT solver details.

#### acqmss/algorithms/ — Acquisition Algorithms

**Core API**:
```python
from acqmss.algorithms import CONGEN, CONGENModel, ACQMSS, REDUCE
from acqmss.algorithms.interactive import QuAcq, InteractiveLearner

# Passive learning
model = CONGENModel.from_bias_and_examples(bias, e_plus, e_minus, features)
congen = CONGEN(checker, profiler)
result = congen.acquire(task)  # → KB + metadata

# Interactive learning
learner = InteractiveLearner.from_files(fm_path, bias_path)
result = learner.learn(mode='automated')  # → KB + query history
```

**Algorithms**:
1. **CONGEN** — Passive constraint acquisition
   - Input: Bias (candidate constraints), E+ (valid configs), E- (invalid configs)
   - Process: GenerateNE → ACQMSS → REDUCE
   - Output: KB (learned constraint set)

2. **GenerateNE** — Create negated examples from negatives
   - Convert E- to their logical negation (for conflict detection)
   - Required by ACQMSS to find MSS

3. **ACQMSS** — Divide-and-conquer maximum satisfiable subset finding
   - Recursively partition bias constraints
   - Find MSS via KBDiag (kernel-based diagnosis)
   - Core to CONGEN accuracy

4. **REDUCE** — Remove redundant constraints
   - Iterate over learned KB
   - Check if each constraint is necessary (via consistency check)
   - Clean results of false positives

5. **QuAcq** — Interactive and batch learning (two modes)
   - **Oracle mode** (original): GenerateQuery → Oracle → Update KB
   - **Example mode** (new): learn_from_examples() with FindScope/FindC
   - Prune constraints that reject oracle answer or valid examples
   - Add conflicts from invalid configurations via FindScope/FindC
   - Converge when bias fully explored or examples exhausted

**Dependencies**: Uses `explanation.operations.algorithms` (FastDiag, QuickXPlain, KBDiag) for diagnosis operations.

#### acqmss/bias/ — Bias Generation

**Purpose**: Extract constraints from feature models for use as bias in learning.

**Components**:
- `bias_generator.py` — Extract hierarchical + cross-tree constraints from FM
- `clause_generator.py` — Convert constraints to CNF clauses
- `bias_io.py` — Load/save bias in JSON/YAML formats
- `config_loader.py` — TOML configuration for bias generation

**Data Flow**:
```
Feature Model (UVL) ──→ BiasGenerator ──→ Constraints
                         (via flamapy)    ├─ Hierarchical
                                          │  (mandatory, optional, etc.)
                                          └─ Cross-tree
                                             (requires, excludes)
                            ↓
                        JSON/YAML/DIMACS
                        (configuration files)
```

#### acqmss/testcases/ — Example Generation

**Purpose**: Generate diverse positive/negative configurations for training.

**Strategies**:
1. **RandomSampling (RS)** — Uniform random configuration selection
   - Simple, unbiased sampling
   - Good baseline for benchmarking

2. **FeatureFrequency (FF)** — Weight by feature occurrence patterns
   - Prioritize configurations exploring all features
   - Better coverage than RS

3. **TwoCoverage (2-COV)** — Ensure feature pairs appear together
   - Stronger coverage guarantee
   - More configurations needed for same coverage

**Data Flow**:
```
Feature Model ──→ Oracle (FM validator)
                     ↓
                 Valid config space
                     ↓
            Sampling Strategy (RS/FF/2-COV)
                     ↓
            E+ (valid), E- (invalid) examples
                     ↓
                 JSON files (training data)
```

#### acqmss/eval/ — Evaluation Framework

**Purpose**: Measure accuracy of learned constraints against ground truth.

**Components**:
- `cross_validation.py` — n-fold CV orchestration
- `accuracy.py` — Calculate accuracy, precision, recall, F1
- `report.py` — Generate CSV/JSON/LaTeX/Markdown reports
- `evaluator.py` — High-level evaluation orchestrator
- `interactive_metrics.py` — QuAcq-specific metrics (query counts, convergence)

**Metrics**:
```
Accuracy  = (TP + TN) / (TP + TN + FP + FN)   [Primary]
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * P * R / (P + R)
```

**Comparison Strategies**:
- **description** — Compare constraint natural language descriptions
- **clause** — Compare CNF clauses exactly

### explanation/ — SAT Solver Infrastructure

**Purpose**: Provide diagnosis algorithms and solver abstractions for constraint acquisition.

#### explanation/models/ — Diagnosis Model Abstraction

**Key Classes**:
```python
class DiagnosisModel:
    """SAT representation of a system."""
    def __init__(self, feature_model, solver_name='glucose4'):
        self.clauses: list[list[int]]    # CNF clauses
        self.variable_map: dict          # Feature → var ID
        self.assumptions: list[int]      # Unit assumptions
        self.solver: Solver              # PySAT solver instance

class CONGENTask:
    """Task representation for CONGEN."""
    def __init__(self, diagnosis_model, bias, examples):
        self.set_kb: DiagnosisModel      # Set KB (bias)
        self.positive_examples: list     # E+
        self.negative_examples: list     # E-
        self.split_diff_utils: dict      # CNF diff utilities

class InteractiveTask:
    """Task state for QuAcq interactive learning."""
    def __init__(self, bias, learned_kb, background):
        self.bias: Set[str]              # Remaining bias (set for O(1) removal)
        self.learned_kb: List[str]       # Learned constraint IDs (KB)
        self.background: List[int]       # Background assumptions (BG)
        self.constraint_map: dict        # Constraint ID → CNF clauses
        self.feature_ids: dict           # Feature name → SAT variable ID
        self.n_queries: int              # Query count

    def __post_init__(self):
        """Auto-convert list→set for backward compatibility."""
        if not isinstance(self.bias, set):
            self.bias = set(self.bias)

    def remove_from_bias(self, constraint_ids: List[str]):
        """Remove constraints using set subtraction (O(1) per item)."""
        self.bias -= set(constraint_ids)
```

**Construction**:
```python
from explanation.models import DiagnosisModelBuilder, TaskPreparation

# Builder pattern
model = (DiagnosisModelBuilder()
         .with_feature_model(fm)
         .with_solver('glucose4')
         .build())

# Task preparation
prep = IncrementalCONGENTaskPreparation()
task = prep.prepare(model).task
```

#### explanation/operations/ — Diagnosis Algorithms

**Solver Abstraction Layer**:

```python
class ConsistencyChecker(ABC):
    """Abstract SAT checker interface."""

    @abstractmethod
    def is_consistent(self, clauses) -> bool:
        """Check satisfiability."""
        pass

class IncrementalPySATChecker(ConsistencyChecker):
    """Persistent solver with assumptions.

    - Reuses solver instance across calls
    - Fast hypothesis testing via assumptions
    - ~50x faster than non-incremental
    """
    def is_consistent(self, clauses):
        self.solver.add_clause(clause)
        return self.solver.solve()

class NonIncrementalPySATChecker(ConsistencyChecker):
    """Fresh solver per call.

    - Create new solver instance each time
    - Memory-light, baseline for comparison
    - Slower but clearer isolation
    """
    def is_consistent(self, clauses):
        solver = Solver()  # New instance
        for clause in clauses:
            solver.add_clause(clause)
        return solver.solve()

class SAT4JChecker(ConsistencyChecker):
    """External Java SAT4J solver.

    - Via subprocess (slower overhead)
    - Useful for verification/comparison
    - Supports SAT4J-specific options
    """
    def is_consistent(self, clauses):
        result = subprocess.run(['java', '-jar', 'sat4j.jar', ...])
        return result.returncode == 0
```

**Diagnosis Algorithm Implementations**:

1. **FastDiag** — Breadth-first minimal diagnosis
   ```
   FastDiag(KB, Background) → [D1, D2, ...]

   - Iteratively remove constraints from KB
   - Check consistency of KB \ {constraints}
   - Minimal diagnosis: cannot remove any single constraint
   - Multiple diagnoses via HSDAG tree
   ```

2. **QuickXPlain** — Minimal conflict explanation
   ```
   QuickXPlain(KB, Background) → [C1, C2, ...]

   - Find minimal subset of KB causing inconsistency
   - Divide-and-conquer search
   - Output: Minimal conflict (cannot add any constraint)
   ```

3. **KBDiag** — Kernel-based diagnosis
   ```
   KBDiag(KB, Background) → Diagnosis

   - Like FastDiag but kernel-based approach
   - More efficient for certain KB structures
   ```

4. **WipeOutR Variants**:
   - **WipeOutR_FM** — Feature model specific
   - **WipeOutR_T** — Test case specific

5. **HSDAG** — Hierarchical Search DAG
   ```
   HSDAG(FastDiag) → [D1, D2, ..., Dn]

   - Tree search optimization
   - Reuses computation across diagnosis instances
   - ~10x fewer solver calls
   - Single or multiple diagnoses
   ```

**Profiling Infrastructure**:

```python
class Profiler:
    """Measure execution time and solver call counts."""

    @measure('operation_name')
    def my_algorithm():
        pass  # Automatically timed

    def get_timing(name) -> float:
        """Get execution time in seconds."""
        pass

    def get_count(event) -> int:
        """Get event counter (e.g., SAT solver calls)."""
        pass
```

Profiler exports to CSV/JSON for analysis.

#### explanation/transformations/ — Model Converters

**FM to SAT Conversion**:
```python
def feature_model_to_diagnosis_model(fm: FeatureModel) -> DiagnosisModel:
    """Convert feature model to SAT instance.

    Steps:
    1. Extract features and constraints from FM
    2. Convert to propositional clauses (CNF)
    3. Create variable mapping (feature → var ID)
    4. Instantiate SAT solver
    5. Return DiagnosisModel with clauses + solver
    """
    pass
```

**DIMACS Format Support**:
- Read/write CNF files (standard SAT competition format)
- Convert between variable assignments and configurations

### apps/ — Standalone Applications

**Purpose**: Provide CLI interfaces for complete constraint acquisition pipelines.

**Application Architecture**:
```
apps/
├── generate_bias_config.py     ──→ Feature Model → YAML Bias Config
├── generate_bias_files.py      ──→ YAML Config → JSON/CNF Files
├── generate_examples.py        ──→ Feature Model → E+/E- Examples
├── run_congen.py               ──→ CONGEN Learning (Passive)
├── run_interactive.py          ──→ QuAcq Learning (Interactive)
├── run_evaluation.py           ──→ n-fold Cross-validation
├── evaluate_congen_results.py  ──→ Post-process Results
└── extract_results.py          ──→ Generate Reports
```

**Configuration-Driven Execution**:
```
TOML Config ──→ App ──→ Logger (console + file)
                          ↓
                      Algorithm (CONGEN/QuAcq/Eval)
                          ↓
                      Results (JSON/CSV/LaTeX)
                          ↓
                      Report (Markdown/LaTeX)
```

## Two Learning Paradigms

### 1. CONGEN (Passive/Batch Learning)
- Input: Pre-collected E+/E- examples
- No user interaction required
- Learns constraint KB in one pass
- Complexity: O(|B| * SAT checks)

### 2. QuAcq (Interactive/Active Learning)
- **Oracle mode**: Queries user for membership (interactive)
- **Example mode**: Uses pre-collected E+/E- (batch, no oracle)
- FindScope/FindC: O(|S| * log|X| + |Gamma|) queries per constraint
- Complexity: O(|C_T| * (log|X| + |Gamma|)) total queries

### Shared Infrastructure
Both paradigms use:
- Same FM representation and CNF conversion
- Same SAT solvers (Incremental/NonIncremental/SAT4J)
- Same bias generation pipeline
- Same evaluation framework (cross-validation, accuracy metrics)
- Shared CV folds for fair comparison (fold_io.py)

## Data Flow Diagrams

### CONGEN Learning Flow

```
Feature Model (UVL)
    ↓
    ├─→ BiasGenerator ──→ Bias Constraints (JSON)
    │                     ├─ Hierarchical
    │                     └─ Cross-tree
    │
    ├─→ ExampleGenerator (RS/FF/2-COV) ──→ E+ (valid), E- (invalid)
    │
    └─→ CONGEN Algorithm
        ├─ GenerateNE: E- → NE (negated examples)
        │   └─ Goal: Create conflicts for MSS finding
        │
        ├─ ACQMSS: Bias → MSS
        │   ├─ Input: Bias constraints, E+, E-, NE
        │   ├─ Process: KBDiag (divide-and-conquer)
        │   └─ Output: Maximum satisfiable subset
        │
        └─ REDUCE: MSS → KB (clean result)
            ├─ Iterate over MSS
            ├─ Check necessity of each constraint
            └─ Output: Minimal KB (no redundancy)

Result: Learned constraint set (KB)
        └─ Compare against ground truth (Bias)
            └─ Accuracy/Precision/Recall metrics
```

### QuAcq Interactive/Batch Flow

**Oracle-Based Mode (Original)**:
```
Feature Model + Bias
    ↓
    └─→ QuAcq Algorithm (loop)
        ├─ GenerateQuery: Create discriminative configuration
        │   └─ Goal: Distinguish between KB and remaining bias
        │
        ├─ Oracle: Validate configuration
        │   ├─ Automated: Check against FM + known constraints
        │   └─ Manual: Ask user "Is this valid?"
        │
        ├─ Update KB:
        │   ├─ If valid: Prune constraints rejecting query
        │   └─ If invalid: Find conflict, add to KB
        │
        └─ Termination: Bias fully explored or query limit reached
```

**Example-Based Mode (New — IJCAI13 FindScope/FindC)**:
```
Feature Model + Bias + E+/E- Examples
    ↓
    └─→ QuAcq.learn_from_examples() (loop)
        ├─ For each e in E-:
        │   ├─ FindScope: Binary search on scope via partial queries
        │   │   └─ O(|S| * log|X|) queries (ConsistencyChecker against FM)
        │   │
        │   ├─ FindC: Discriminate candidates with matching scope
        │   │   ├─ Exact scope match (c_vars == scope) preferred
        │   │   ├─ Fallback to subset match (c_vars ⊆ scope)
        │   │   ├─ Use pool examples (ExampleProvider)
        │   │   └─ Generate SAT queries if needed (query_mode=example_first)
        │   │
        │   └─ Add found constraint to KB
        │
        └─ Termination: All E- processed or bias exhausted

Result: Learned KB + query statistics
        └─ Convergence metrics
            └─ Query count, per-constraint precision, example pool usage
```

## Integration Points

### Between acqmss/ and explanation/

```python
# CONGEN imports diagnosis operations
from explanation.operations.algorithms import KBDiag, QuickXPlain
from explanation.operations import Profiler

class ACQMSS:
    def __init__(self, checker, profiler=None):
        self.checker = checker  # ConsistencyChecker from explanation/
        self.profiler = profiler or NullProfiler()

    def acquire(self, bias, examples):
        # Use KBDiag internally for MSS finding
        mss = kbdiag(self.model, self.checker)
        return mss
```

### Shared Infrastructure

**Profiling**:
- Global profiler pattern allows optional profiling
- Minimal overhead when disabled (NullProfiler)
- Used across acqmss, explanation, and apps

**Consistency Checking**:
- All algorithms accept pluggable ConsistencyChecker
- Easy to swap solver implementations
- Enables testing with mock checkers

**Model Representation**:
- Unified CNF clause format (list[list[int]])
- Variable mapping (feature → literal ID)
- Shared across generation, acquisition, and diagnosis

## Solver Architecture

### Solver Modes

#### Incremental Mode (Default)

```python
checker = IncrementalPySATChecker(solver, profiler=None)

# Persistent solver
solver = Solver('glucose4')
solver.add_clause([1, -2])  # Add clause
result = solver.solve()     # Solve
result = solver.solve()     # Reuse solver (fast)

# With assumptions
result = solver.solve([3])  # Add temporary unit clause
result = solver.solve([4])  # Reuse, different assumption (fast)
```

**Advantages**:
- ~50x faster for repeated SAT checks
- Persistent state across calls
- Assumptions enable efficient hypothesis testing

**Use Case**: CONGEN with many consistency checks

#### Non-Incremental Mode

```python
checker = NonIncrementalPySATChecker(solver_factory, profiler=None)

# Fresh solver per call
for hypothesis in hypotheses:
    solver = Solver('glucose4')  # New instance
    solver.add_clause([1, -2])
    result = solver.solve()  # Check hypothesis
```

**Advantages**:
- Memory-light (no persistent state)
- Clear isolation between checks
- Good for verification

**Use Case**: Baseline comparison, memory-constrained environments

#### SAT4J Mode (Optional)

```python
checker = SAT4JChecker(
    command=['java', '-jar', 'sat4j.jar'],
    timeout=60
)

# Subprocess-based (slower)
result = checker.is_consistent(clauses)
```

**Advantages**:
- Independent solver (Java-based)
- Useful for cross-validation
- SAT4J-specific tuning options

**Disadvantages**:
- Subprocess overhead (~100-500ms per call)
- Not incremental

## Performance Characteristics

### Algorithm Complexity

| Operation | Bias Size | Time | Solver Calls |
|-----------|-----------|------|--------------|
| FastDiag | 100 | <1 sec | 5-15 |
| QuickXPlain | 100 | <1 sec | 10-30 |
| KBDiag | 100 | 1-3 sec | 20-50 |
| ACQMSS (CONGEN) | 100 | 5-10 sec | 50-200 |
| REDUCE | 100 | 1-5 sec | 10-50 |
| CONGEN (arcade-game, 65 features) | 65 | 10-30 sec | 100-300 |
| CONGEN (linux, 6,467 features) | 6,467 | 30-60 min | 5K-20K |

### Optimization Techniques

1. **HSDAG Tree Search** — ~10x fewer solver calls
2. **Incremental Solver** — ~50x faster SAT checks
3. **Assumption-based Hypothesis Testing** — Reuse solver state
4. **Divide-and-Conquer** — ACQMSS reduces problem size
5. **Set-Based Bias Storage** — O(1) constraint removal vs O(n) for lists (QuAcq)
6. **Exact Scope Matching** — Prefers exact scope match before subset fallback (FindC)

Combined effect: 500-1000x speedup over naive approach for large models.

## Testing Architecture

### Test Organization

```
tests/
├── test_diagnosis.py        # FastDiag, QuickXPlain, KBDiag, WipeOutR, HSDAG
├── test_congen.py           # CONGEN, ACQMSS, REDUCE, GenerateNE
├── test_interactive.py      # QuAcq, InteractiveLearner, QueryGenerator
├── test_evaluation.py       # CrossValidation, AccuracyCalculator, Report
├── test_profiler.py         # Profiling infrastructure
└── test_*.py                # Other component tests
```

### Parameterized Testing

```python
@parameterized.expand([
    ('incremental', IncrementalPySATChecker),
    ('non_incremental', NonIncrementalPySATChecker),
])
def test_algorithm(self, name, checker_class):
    # Test runs with both checker implementations
    pass
```

### Test Control

```python
ENABLED_TESTS = {
    'fastdiag_basic': True,         # Always run
    'fastdiag_large': False,        # Skip (long-running)
    'quacq_interactive': False,     # Requires user input
}

ENABLED_PARAMS = {
    'incremental': True,
    'non_incremental': True,
    'sat4j': False,                 # Skip (requires Java)
}
```

## Documentation & Metadata

### Configuration Metadata

Each TOML file includes:
- Input paths (feature model, bias, examples)
- Algorithm settings (solver, timeout, mode)
- Output paths (results, profiling data)

### Result Metadata

Learning results include:
- Timestamp, version, configuration hash
- Ground truth (bias constraints)
- Learned KB
- Performance metrics
- Profiling data (timing, memory, solver calls)

### Report Generation

```python
from acqmss.eval.report import generate_reports

reports = generate_reports(
    results,
    formats=['csv', 'json', 'latex', 'markdown']
)
```

Output:
- Accuracy/precision/recall table
- Per-model performance summary
- Solver efficiency metrics
- Convergence plots (for QuAcq)

## Dependencies & External Interfaces

### Required
- **pysat** — SAT solver interface
- **flamapy** — Feature model parsing

### Optional
- **sat4j** — External Java solver
- **pytest + parameterized** — Testing
- **pyyaml, tomllib** — Configuration

### No Direct Dependencies
- Direct SAT solver (via PySAT abstraction)
- External constraint solvers
- Machine learning frameworks

## Security & Robustness

### Input Validation
- Feature models validated by flamapy
- Constraints validated in CNF format
- Configuration schema validated (TOML)

### Resource Limits
- Solver timeout (configurable)
- Maximum solver calls limit
- Memory limits (OS-level)

### Error Handling
- Graceful timeouts
- Clear error messages
- Fallback behaviors (NullProfiler, etc.)

## Future Architecture Enhancements

1. **Parallel HSDAG** — FastDiagP integration
2. **Distributed Solver** — Multiple machines
3. **Caching Layer** — Solver result memoization
4. **Incremental Learning** — Adapt KB to FM changes
5. **Alternative FM Formats** — fide, XSD support
6. **GPU Acceleration** — SAT solving on GPU

