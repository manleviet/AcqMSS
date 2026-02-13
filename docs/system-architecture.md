# AcqMSS System Architecture

## High-Level Overview

AcqMSS is organized in a **two-layer architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│ Application Layer (apps/)                                   │
│ generate_bias_config.py, generate_examples.py,              │
│ run_congen.py, run_interactive_eval.py, run_congen_eval.py        │
└─────────────────┬───────────────────────────────────────────┘
                  │ TOML Configuration Files
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Core Acquisition Algorithms (acqmss/)                       │
│ ├─ CONGEN: ACQMSS → REDUCE (GenerateNE pre-computed)        │
│ ├─ GenerateNE: Create negated examples (called by caller)   │
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
   - Input: Bias (candidate constraints), E+ (valid configs), pre-computed NE
   - Process: ACQMSS → REDUCE (NE pre-computed by caller)
   - Output: KB (learned constraint set)

2. **GenerateNE** — Create negated examples from negatives
   - Convert E- to their logical negation (for conflict detection)
   - Called by callers before CONGEN; results merged into task via `merge_ne_into_task()`
   - Immutable after caller runs it (no mutations on checker)

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
- `cross_validation.py` — n-fold CV orchestration (CONGEN & Interactive modes)
- `congen_runner.py` — CONGEN pipeline runner with metrics
- `interactive_runner.py` — QuAcq pipeline runner (analogous to CONGENRunner)
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

class DiagnosisTask:
    """Base task representation with assumptions.

    The root class now holds the assumptions field, eliminating redundant
    incremental/non-incremental subclasses.
    """
    def __init__(self, ...):
        self.assumptions: list[int]      # Control literals (moved from subclasses)
        self.set_kb: list[list[int]]     # CNF clauses with assumption literals

class TestCaseTask(DiagnosisTask):
    """Task with test case fields."""
    # Inherits assumptions from DiagnosisTask

class CONGENTask(TestCaseTask):
    """Task representation for CONGEN - unified assumption-based format."""
    def __init__(self, ...):
        self.set_c: list[int]            # Bias constraint assumption IDs
        self.set_tc: list[int]           # Positive example (E+) assumption IDs
        self.set_tv: list[int]           # Negative example (E-) assumption IDs
        self.set_ne: list[int]           # Negated example (NE) assumption IDs
        self.set_b: list[int]            # Background (BG) assumption IDs
        self.neg_c_map: Dict[int, int]   # Negation map: assumption_id → negated_id
        self.e_neg_literals: list[list[int]]  # Raw E- literals for GenerateNE

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

class InteractiveRunResult:
    """Result of running interactive learning (from InteractiveRunner.run())."""
    def __init__(self, kb_constraints, kb_clauses, n_bias, n_kb, n_queries,
                 convergence_reason, runtime_ms, consistency_checks, memory_peak_mb):
        self.kb_constraints: List[str]        # Constraint IDs in learned KB
        self.kb_clauses: List[List[int]]      # CNF clauses of KB
        self.n_bias: int                      # Original bias size
        self.n_kb: int                        # Final KB size
        self.n_queries: int                   # Membership queries asked
        self.convergence_reason: str          # Termination reason (bias_exhausted, max_queries, etc)
        self.runtime_ms: float                # Execution time
        self.consistency_checks: int          # SAT solver calls
        self.memory_peak_mb: float            # Peak memory usage
```

**Construction**:
```python
from explanation.models import DiagnosisModelBuilder, TaskPreparation
from acqmss.algorithms import CONGENTaskPreparation

# Builder pattern
model = (DiagnosisModelBuilder()
         .with_feature_model(fm)
         .with_solver('glucose4')
         .build())

# Task preparation (unified for both incremental/non-incremental)
prep = CONGENTaskPreparation()  # mode_name defaults to "congen"
task = prep.prepare(model).task
```

#### explanation/operations/ — Diagnosis Algorithms

**Solver Abstraction Layer**:

```python
class ConsistencyChecker(ABC):
    """Abstract SAT checker interface (immutable after construction).

    Checkers are read-only after creation. No add_clause/add_assumption mutations.
    GenerateNE runs separately before CONGEN, results merged via merge_ne_into_task().
    """

    @abstractmethod
    def is_consistent(self, set_c: List[int]) -> bool:
        """Check if set_c (assumption IDs) are consistent with KB.

        All checkers use unified assumption-based data representation:
        - set_c: List[int] - assumption IDs to enable
        - set_kb: CNF clauses with assumption literals
        - assumptions: List of all possible assumption IDs
        """
        pass

class IncrementalPySATChecker(ConsistencyChecker):
    """Persistent solver with assumption-based solving.

    - Reuses solver instance across calls
    - Fast hypothesis testing via assumptions
    - ~50x faster than non-incremental

    Note: The assumptions parameter comes from DiagnosisTask.assumptions
    (moved to root class from 6 former subclasses).
    """
    def __init__(self, set_kb: List[List[int]], assumptions: List[int], ...):
        self.solver = Solver()
        self.set_kb = set_kb
        self.assumptions = assumptions  # From DiagnosisTask.assumptions

    def is_consistent(self, set_c: List[int]):
        # set_c: assumption IDs to enable
        # Compute final assumptions: enable set_c, disable others
        return self.solver.solve(assumptions=final_assumptions)

class NonIncrementalPySATChecker(ConsistencyChecker):
    """Fresh solver per call with assumption-based data.

    - Create new solver instance each time
    - Uses same assumption-based representation as IncrementalPySATChecker
    - Memory-light baseline for comparison
    - Slower but clearer isolation

    Note: The assumptions parameter comes from DiagnosisTask.assumptions
    (moved to root class from 6 former subclasses).
    """
    def __init__(self, set_kb: List[List[int]], assumptions: List[int],
                 solver_name: str = 'glucose3'):
        self.set_kb = set_kb           # CNF clauses with assumption literals
        self.assumptions = assumptions  # From DiagnosisTask.assumptions

    def is_consistent(self, set_c):
        # set_c: assumptions to enable (List[int])
        # Compute delta: assumptions NOT in set_c
        # Create solver with KB, then check B ∪ C
        solver = Solver(self.solver_name, bootstrap_with=self.set_kb)
        return solver.solve(assumptions=final_assumptions)

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
    3. Create variable mapping (feature → var ID) — MUST use flamapy's tree traversal order
    4. Instantiate SAT solver
    5. Return DiagnosisModel with clauses + solver

    CRITICAL: The variable mapping MUST come from flamapy's variable assignment
    (tree traversal order), NOT from alphabetical sorting. The Oracle uses flamapy's
    variable mapping as the authoritative source to ensure feature_ids match the
    SAT variable IDs in CNF clauses.
    """
    pass
```

**DIMACS Format Support**:
- Read/write CNF files (standard SAT competition format)
- Convert between variable assignments and configurations

**Feature ID Resolution**:
- **Source of Truth**: Flamapy's variable mapping from `FmToPysat` transformation
- **Why**: Flamapy uses tree traversal order (depth-first) for variable numbering
- **Not**: Alphabetical sorting (incorrect mismatch between Oracle feature_ids and SAT variables)
- **Risk**: Mismatch causes SAT solver inconsistency, leading to incorrect Oracle validation

### Runner Pattern (for Evaluation Framework)

Similar to CONGENRunner, InteractiveRunner provides a high-level wrapper for running acquisition algorithms:

**CONGENRunner**:
```python
runner = CONGENRunner(bias_clauses, feature_ids, solver_name, is_incremental)
result = runner.run(positive_examples, negative_examples, shuffle_seed)
# → CONGENRunResult with KB + MSS info + metrics
```

**InteractiveRunner** (new, analogous):
```python
runner = InteractiveRunner(bias_clauses, feature_ids, fm_path, bias_path,
                           solver_name, max_queries, query_mode)
result = runner.run(positive_examples, negative_examples, shuffle_seed)
# → InteractiveRunResult with KB + query count + convergence reason + metrics
```

Both runners:
- Manage solver/profiling lifecycle
- Collect performance metrics (runtime, consistency_checks, memory)
- Support per-fold bias shuffling (shuffle_seed parameter)
- Return standardized result objects for CV aggregation

### apps/ — Standalone Applications

**Purpose**: Provide CLI interfaces for complete constraint acquisition pipelines.

**Application Architecture**:
```
apps/
├── generate_bias_config.py     ──→ Feature Model → YAML Bias Config
├── generate_bias_files.py      ──→ YAML Config → JSON/CNF Files
├── generate_examples.py        ──→ Feature Model → E+/E- Examples
├── run_congen.py               ──→ CONGEN Learning (Passive)
├── run_interactive_eval.py          ──→ QuAcq Learning (Interactive + CV)
├── run_congen_eval.py           ──→ n-fold Cross-validation
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
- **CV support**: `n_fold_cross_validation_interactive()` + `InteractiveRunner`
- FindScope/FindC: O(|S| * log|X| + |Gamma|) queries per constraint
- Complexity: O(|C_T| * (log|X| + |Gamma|)) total queries

### Shared Infrastructure
Both paradigms use:
- Same FM representation and CNF conversion
- Same SAT solvers (Incremental/NonIncremental/SAT4J)
- Same bias generation pipeline
- Same evaluation framework (cross-validation, accuracy metrics)
- Shared CV folds for fair comparison (fold_io.py)

### Interactive Cross-Validation

QuAcq now supports n-fold cross-validation, aligned with CONGEN's CV pipeline:

```
n_fold_cross_validation_interactive(
    E+, E-, n_folds, bias, feature_ids, fm_path, bias_path,
    seed, solver_name, max_queries, query_mode, fold_data, shuffle_bias
)
    ↓
InteractiveRunner (per fold)
    ├─ from_examples(): Load FM + bias + E+/E- pool
    ├─ learn_from_examples(): Run QuAcq with metric collection
    └─ Result: KB + queries + convergence_reason
    ↓
Per-fold metrics: Accuracy, precision, recall, query count
    ↓
CrossValidationResult: Mean accuracy ± std, per-fold KB, intersected KB
```

**Key Features**:
- Pre-generated fold support (for reproducible evaluation across CONGEN/Interactive)
- Per-fold bias shuffling (shuffle_seeds in FoldData)
- Query mode control: `example_only` or `example_first`
- Convergence tracking (query count, termination reason)

## Data Flow Diagrams

### CONGEN Learning Flow

```
Feature Model (UVL)
    ↓
    ├─→ BiasGenerator ──→ Bias Constraints (JSON, as assumption IDs)
    │                     ├─ Hierarchical
    │                     └─ Cross-tree
    │
    ├─→ ExampleGenerator (RS/FF/2-COV) ──→ E+ (valid), E- (invalid)
    │
    ├─→ TaskPreparation (mode-agnostic unified representation)
    │   └─ set_kb: CNF with assumption literals
    │   └─ set_c: Bias assumption IDs
    │   └─ set_tc: E+ assumption IDs
    │   └─ set_tv: E- assumption IDs
    │
    ├─→ GenerateNE: E- → NE (assumption IDs, called BEFORE CONGEN)
    │   └─ Output: Negated example assumption IDs
    │   └─ Merged into task via merge_ne_into_task()
    │
    └─→ CONGEN Algorithm (Incremental OR NonIncremental, same code)
        ├─ ACQMSS: Bias → MSS
        │   ├─ Input: Assumption IDs + ConsistencyChecker
        │   ├─ Process: KBDiag (divide-and-conquer)
        │   └─ Output: Assumption IDs of MSS
        │
        └─ REDUCE: MSS → KB (assumption IDs)
            ├─ Iterate over MSS
            ├─ Check necessity via is_consistent()
            └─ Output: Assumption IDs of minimal KB

Result: Learned constraint set (KB)
        └─ Compare against ground truth (Bias)
            └─ Accuracy/Precision/Recall metrics
```

**Mode-Agnostic Design**: CONGEN, ACQMSS, and REDUCE contain no
`if is_incremental` branching. All data is assumption-based (List[int]);
the ConsistencyChecker implementation determines solver lifecycle.
GenerateNE is called separately by callers before CONGEN.

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

**Feature ID Consistency (CRITICAL)**:

The Oracle and all SAT-based components must use the **same** feature_ids mapping:

```
Oracle (acqmss/testcases/oracle.py)
  ├─ _build_cnf(): Uses FmToPysat → generates CNF clauses with variable IDs
  └─ _build_feature_ids(): Must extract mapping from same FmToPysat transform

Result: feature_ids matches SAT variable IDs in CNF
```

- **Source of Truth**: Flamapy's variable mapping (tree traversal order)
- **In Oracle**: `self._flamapy_variables = dict(sat_model.variables)` from FmToPysat
- **Pattern**: All code using feature_ids must receive it from Oracle or same FM→SAT conversion
- **Failure Mode**: Alphabetical sorting breaks mismatch → incorrect Oracle validation

## Solver Architecture

### Solver Modes

#### Incremental Mode (Default)

```python
# Create checker with pre-built KB (immutable after construction)
set_kb = [[1, -2, 3], [-1, 4]]  # CNF clauses with assumption literals
assumptions = [5, 6, 7]          # Control literals for constraints
checker = IncrementalPySATChecker(set_kb, assumptions, profiler=None)

# Persistent solver reuses state across hypothesis tests
# Checkers are immutable: GenerateNE runs before CONGEN, results merged via merge_ne_into_task()
result = checker.is_consistent([5, 6])     # Consistent with assumptions 5,6
result = checker.is_consistent([5])        # Reuse solver, different assumption (fast)
```

**Advantages**:
- ~50x faster for repeated SAT checks
- Persistent state across calls
- Assumptions enable efficient hypothesis testing without solver re-initialization

**Note**: Checkers are read-only after construction. No `add_clause()` or `add_assumption()` mutations. GenerateNE output is merged into task before checker creation via `merge_ne_into_task()`.

**Use Case**: CONGEN with many consistency checks

#### Non-Incremental Mode

```python
# Prepare once (same KB + assumptions for all checks)
set_kb = [[1, -2, 3], [-1, 4]]  # CNF clauses with assumption literals
assumptions = [5, 6, 7]          # Assumption IDs that control constraints
checker = NonIncrementalPySATChecker(set_kb, assumptions, profiler=None)

# Fresh solver per call, but same assumption-based data
for hypothesis in hypotheses:
    result = checker.is_consistent(hypothesis)  # New solver, reuse KB
```

**Advantages**:
- Memory-light (no persistent solver state)
- Clear isolation between checks
- Same assumption-based representation as incremental
- Good for verification and baseline comparison

**Use Case**: Baseline comparison, memory-constrained environments, validation

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

