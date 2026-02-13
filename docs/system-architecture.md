# AcqMSS System Architecture

**Last Updated**: 2026-02-13

## High-Level Overview

AcqMSS is organized in a **two-layer architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│ Application Layer (apps/)                                   │
│ generate_bias_config.py, generate_examples.py,              │
│ run_congen.py, run_interactive_eval.py, run_congen_eval.py  │
└─────────────────┬───────────────────────────────────────────┘
                  │ TOML Configuration Files
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Core Acquisition Algorithms (acqmss/)                       │
│ ├─ CONGEN: GenerateNE → ACQMSS → REDUCE (caller-invoked NE)│
│ ├─ QuAcq: GenerateQuery → Oracle → Update KB                │
│ ├─ Bias generation from feature models                      │
│ ├─ Example generation (RS, FF, 2-COV strategies)            │
│ ├─ Oracle implementations (FeatureModelOracle, etc.)        │
│ └─ Evaluation framework (CV, accuracy metrics, profiling)    │
└─────────────────┬───────────────────────────────────────────┘
                  │ Dependencies
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ SAT Infrastructure (explanation/)                           │
│ ├─ Diagnosis Algorithms (FastDiag, QuickXPlain, etc.)       │
│ ├─ HSDAG: Tree search optimization (10x speedup)            │
│ ├─ Solver Abstraction (Incremental, NonIncremental, SAT4J)  │
│ └─ Model Transformation (FM → SAT, DIMACS conversion)       │
└─────────────────┬───────────────────────────────────────────┘
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
preparation = CONGENTaskPreparation()  # mode_name defaults to "congen"
task = preparation.prepare(model).task
checker = IncrementalPySATChecker(task.set_kb, task.assumptions, 'glucose4')
congen = CONGEN(checker, profiler)
result = congen.acquire(task)  # → KB + metadata

# Interactive learning
learner = InteractiveLearner.from_files(fm_path='model.uvl', bias_path='bias.json')
result = learner.learn(mode='automated')  # → KB + query history
```

**Key Algorithms**:
1. **CONGEN** — Passive constraint acquisition
   - Input: Bias (candidate constraints), E+ (valid configs), pre-computed NE
   - Process: GenerateNE invoked by caller, merged via `merge_ne_into_task()`, then ACQMSS → REDUCE
   - Output: KB (learned constraint set)

2. **GenerateNE** — Create negated examples (caller-invoked, immutable)
   - Convert E- to logical negation for conflict detection
   - Called BEFORE CONGEN; results merged into task via `merge_ne_into_task()`
   - Checkers immutable after construction (no mutations)

3. **ACQMSS** — Divide-and-conquer maximum satisfiable subset finding
   - Recursively partition bias constraints
   - Find MSS via KBDiag (kernel-based diagnosis)

4. **REDUCE** — Remove redundant constraints
   - Iterate over learned KB
   - Check if each constraint is necessary via consistency check

5. **QuAcq** — Interactive and batch learning (two modes)
   - **Oracle mode** (original): GenerateQuery → Oracle → Update KB
   - **Example mode** (new): learn_from_examples() with FindScope/FindC
   - FindScope: O(|S| * log|X|) queries per call
   - FindC: O(|Gamma|) queries per call

#### acqmss/bias/ — Bias Generation

**Purpose**: Extract constraints from feature models for use as bias in learning.

**Components**:
- `bias_generator.py` — Extract hierarchical + cross-tree constraints from FM
- `clause_generator.py` — Convert constraints to CNF clauses
- `bias_io.py` — Load/save bias in JSON/YAML formats
- `config_loader.py` — TOML configuration for bias generation

#### acqmss/testcases/ — Example Generation

**Purpose**: Generate diverse positive/negative configurations for training.

**Strategies**:
1. **RandomSampling (RS)** — Uniform random configuration selection
2. **FeatureFrequency (FF)** — Weight by feature occurrence patterns
3. **TwoCoverage (2-COV)** — Ensure feature pairs appear together

#### acqmss/oracle/ — Oracle Implementations

**Purpose**: Unified oracle interface for configuration validation and example generation.

**Architecture**:
- `Oracle` (base.py) — Unified abstract base class for all oracle implementations
  - Implements: `is_valid()`, `get_features()`, `get_feature_ids()`, `ask()` (alias)
  - No separate oracle hierarchies (AutomatedOracle merged into implementations)

**Concrete Implementations**:
- `FeatureModelOracle` (fm_oracle.py) — Validates against SAT-based feature model ground truth
- `UserPromptOracle` (user_prompt.py) — Interactive human-in-the-loop oracle
- `CachedOracle` (cached.py) — Wrapper caching query results
- `ExampleProvider` (example_provider.py) — Batch example interface for learning
- `OracleData` (extractor.py) — Extracted oracle data for evaluation

**Critical Detail**: Feature ID consistency
- `FeatureModelOracle._build_feature_ids()` uses flamapy's variable mapping from `FmToPysat.variables`
- Ensures feature_ids match SAT variable IDs in CNF clauses
- Alphabetical sorting would cause critical mismatch with clause literals

#### acqmss/eval/ — Evaluation Framework

**Purpose**: Measure accuracy of learned constraints against ground truth.

**Components**:
- `cross_validation.py` — n-fold CV orchestration (CONGEN & Interactive modes)
- `congen_runner.py` — CONGEN pipeline runner with metrics
- `interactive_runner.py` — QuAcq pipeline runner (analogous to CONGENRunner)
- `accuracy.py` — Calculate accuracy, precision, recall, F1
- `report.py` — Generate CSV/JSON/LaTeX/Markdown reports
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
    clauses: list[list[int]]    # CNF clauses
    variable_map: dict          # Feature → var ID
    assumptions: list[int]      # Unit assumptions
    solver: Solver              # PySAT solver instance

class DiagnosisTask:
    """Base task with assumptions."""
    assumptions: list[int]      # Control literals
    set_kb: list[list[int]]     # CNF with assumption literals

class CONGENTask(TestCaseTask):
    """Task for CONGEN - unified assumption-based format."""
    set_c: list[int]            # Bias assumption IDs
    set_tc: list[int]           # E+ assumption IDs
    set_tv: list[int]           # E- assumption IDs
    set_ne: list[int]           # Negated example assumption IDs
    set_b: list[int]            # Background assumption IDs
    neg_c_map: Dict[int, int]   # Negation map: assumption_id → negated_id
```

#### explanation/operations/ — Diagnosis Algorithms

**Solver Abstraction Layer**:
```python
class ConsistencyChecker(ABC):
    """Abstract SAT checker interface (immutable after construction).

    Both incremental and non-incremental use assumption-based data representation:
    - set_c: List[int] - assumption IDs to enable
    - set_kb: CNF clauses with assumption literals
    - assumptions: List of all possible assumption IDs
    """

    @abstractmethod
    def is_consistent(self, set_c: List[int]) -> bool:
        """Check if set_c assumptions are consistent with KB."""
        pass

class IncrementalPySATChecker(ConsistencyChecker):
    """Persistent solver with assumption-based solving.
    - ~50x faster than non-incremental
    - Use case: CONGEN with many consistency checks
    """

class NonIncrementalPySATChecker(ConsistencyChecker):
    """Fresh solver per call with assumption-based data.
    - Memory-light baseline for comparison
    - Use case: Verification and comparison
    """
```

**Diagnosis Algorithm Implementations**:

1. **FastDiag** — Breadth-first minimal diagnosis
   - Find all minimal diagnoses via HSDAG tree search
   - ~10x speedup with tree optimization

2. **QuickXPlain** — Minimal conflict explanation
   - Find minimal subset of KB causing inconsistency
   - Divide-and-conquer search

3. **KBDiag** — Kernel-based diagnosis
   - More efficient for certain KB structures
   - Used internally by ACQMSS

4. **WipeOutR Variants** — Feature model and test case specific

5. **HSDAG** — Hierarchical Search DAG
   - Tree search optimization
   - Reuses computation across diagnosis instances

#### explanation/transformations/ — Model Converters

**FM to SAT Conversion**:
- Extract features and constraints from FM
- Convert to propositional clauses (CNF)
- Create variable mapping — MUST use flamapy's tree traversal order
- Instantiate SAT solver

**Critical**: The variable mapping MUST come from flamapy's variable assignment (tree traversal order), NOT alphabetical sorting. The Oracle uses flamapy's variable mapping as the authoritative source to ensure feature_ids match the SAT variable IDs in CNF clauses.

## Two Learning Paradigms

### 1. CONGEN (Passive/Batch Learning)
- Input: Pre-collected E+/E- examples
- No user interaction required
- Learns constraint KB in one pass (GenerateNE called by caller, merged via merge_ne_into_task(), then ACQMSS → REDUCE)
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

## Data Flow Diagrams

### CONGEN Learning Flow
```
Feature Model (UVL)
    ├─→ BiasGenerator ──→ Bias Constraints
    ├─→ ExampleGenerator (RS/FF/2-COV) ──→ E+, E-
    └─→ TaskPreparation (unified representation)
        └─ set_kb: CNF with assumption literals
        └─ set_c: Bias assumption IDs
        └─ set_tc: E+ assumption IDs
        └─ set_tv: E- assumption IDs

    └─→ GenerateNE: E- → NE (assumption IDs, called BEFORE CONGEN)
        └─ Merged into task via merge_ne_into_task()

    └─→ CONGEN Algorithm (mode-agnostic, no is_incremental branching)
        ├─ ACQMSS: Bias → MSS via KBDiag
        └─ REDUCE: MSS → KB (assumption IDs)

Result: Learned constraint set (KB)
    └─ Compare against ground truth (Bias)
        └─ Accuracy/Precision/Recall metrics
```

**Mode-Agnostic Design**: CONGEN, ACQMSS, and REDUCE contain no `if is_incremental` branching. All data is assumption-based (List[int]); the ConsistencyChecker implementation determines solver lifecycle.

### QuAcq Interactive/Batch Flow

**Example-Based Mode (IJCAI13 FindScope/FindC)**:
```
Feature Model + Bias + E+/E- Examples
    └─→ QuAcq.learn_from_examples() (loop)
        ├─ For each e in E-:
        │   ├─ FindScope: Binary search via partial queries (O(|S| * log|X|))
        │   ├─ FindC: Discriminate candidates with scope (O(|Gamma|))
        │   └─ Add found constraint to KB
        └─ Termination: All E- processed or bias exhausted
```

## Integration Points

### Between acqmss/ and explanation/

```python
from explanation.operations.algorithms import KBDiag, QuickXPlain
from explanation.operations import Profiler

class ACQMSS:
    def __init__(self, checker, profiler=None):
        self.checker = checker  # ConsistencyChecker from explanation/
        self.profiler = profiler or NullProfiler()

    def acquire(self, bias, examples):
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
Oracle (acqmss/oracle/oracle.py)
  ├─ _build_cnf(): Uses FmToPysat → generates CNF clauses with variable IDs
  └─ _build_feature_ids(): Must extract mapping from same FmToPysat transform

Result: feature_ids matches SAT variable IDs in CNF
```

- **Source of Truth**: Flamapy's variable mapping (tree traversal order)
- **Pattern**: All code using feature_ids must receive it from Oracle or same FM→SAT conversion
- **Failure Mode**: Alphabetical sorting breaks mismatch → incorrect Oracle validation

## Solver Architecture

### Incremental Mode (Default)
- Persistent solver instance across calls
- ~50x faster for repeated SAT checks
- Checkers immutable after construction
- GenerateNE output merged before checker creation via `merge_ne_into_task()`

### Non-Incremental Mode
- Fresh solver per call
- Memory-light, clear isolation
- Same assumption-based data representation as incremental
- Good for verification and comparison

### SAT4J Mode (Optional)
- External Java solver via subprocess
- Good for cross-validation and solver comparison
- Subprocess overhead (~100-500ms per call)

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
5. **Set-Based Bias Storage** — O(1) constraint removal (QuAcq)
6. **Exact Scope Matching** — Prefers exact match before subset fallback (FindC)

Combined effect: 500-1000x speedup over naive approach for large models.

## Testing Architecture

### Test Organization

```
tests/
├── test_diagnosis.py        # FastDiag, QuickXPlain, KBDiag, WipeOutR
├── test_congen.py           # CONGEN, ACQMSS, REDUCE, GenerateNE
├── test_interactive.py      # QuAcq, InteractiveLearner, QueryGenerator
├── test_evaluation.py       # CrossValidation, AccuracyCalculator
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

## Dependencies & External Interfaces

### Required
- **pysat** — SAT solver interface
- **flamapy** — Feature model parsing

### Optional
- **sat4j** — External Java solver
- **pytest + parameterized** — Testing

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
