# AcqMSS System Architecture

**Last Updated**: 2026-06-19 (Phase R task-as-unit refactor: immutable KB, pure Task, ConsistencyExecutor abstraction, ProcessExecutor + memo cache, FMOracle hot-path unified)

## High-Level Overview

AcqMSS is organized in a **two-layer architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│ Application Layer (apps/)                                   │
│ generate_bias_config.py, generate_bias_files.py,            │
│ generate_examples.py, generate_cv_folds.py,                 │
│ run_congen.py, run_cv.py, run_quacq.py,               │
│ run_compare.py, extract_results.py                          │
└─────────────────┬───────────────────────────────────────────┘
                  │ TOML Configuration Files
                  ▼
┌─────────────────────────────────────────────────────────────┐
│ Core Acquisition Algorithms (conacq/)                       │
│ ├─ CONGEN: GenerateNE → ACQMSS → REDUCE (internal NE gen)  │
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

### conacq/ — Constraint Acquisition Core

**Purpose**: Implement constraint discovery algorithms independent of SAT solver details.

#### conacq/algorithms/ — Acquisition Algorithms

**Core API (Phase R - task-as-unit)**:

```python
from conacq.algorithms import ConGen, ConGenModelBuilder
from conacq.algorithms.quacq import QuAcqModelBuilder, QuAcq
from conacq.oracle import FeatureModelOracle
from conacq.example_generators import QueryProvider
from explanation.operations.algorithms.checker import CheckerFactory
from explanation.operations.algorithms.executor import ProcessExecutor, MemoizingExecutor

# Passive learning — Pattern: build once, prepare+shuffle per fold (cross-validation)
oracle = FeatureModelOracle('data/fms/model.uvl')
model = (ConGenModelBuilder.from_bias('data/bias/model.json')
         .with_oracle(oracle)           # Required: oracle for build-time negation
         .build())                       # Returns immutable KB (negation computed)

# Build once, prepare per fold (each prepare_task call = fresh Task)
for fold_pos, fold_neg in folds:
    task_input = TaskInput(positive_examples=fold_pos, negative_examples=fold_neg)
    task = model.prepare_task(task_input, oracle)  # Pure function → fresh ConGenTask
    
    # Shuffle bias iteration order, create checker, run ConGen
    random.Random(seed).shuffle(task.set_c)
    checker = CheckerFactory.create_from_task(
        task, solver_name='glucose4', use_incremental=True, profiler_instance=profiler
    )
    congen = ConGen(checker, profiler=profiler)
    result = congen.acquire(
        set_b=task.set_b, set_bg=task.set_c, set_tc=task.set_tc,
        set_neg_tv=task.set_neg_tv, negation_map=task.negation_map
    )

# Interactive learning — QuAcq (Phase R: task-based, DI pattern)
from conacq.example_generators import QueryProvider
from conacq.algorithms.quacq import DiscriminatingGenerator, QuAcq
from explanation.operations.algorithms.checker import CheckerFactory

oracle = FeatureModelOracle('data/fms/model.uvl')
model = (QuAcqModelBuilder.from_bias('data/bias/model.json')
         .with_oracle(oracle)
         .build())

# Per-run: prepare fresh Task (pure function)
task = model.prepare_task(TaskInput(), oracle)
checker = CheckerFactory.create_from_task(
    task, solver_name='glucose4', use_incremental=True, profiler_instance=profiler
)

# Inject checker + Task into collaborators (no model dependency)
query_prov = QueryProvider(
    checker=checker,
    task=task,           # Injected Task (not model)
    codec=task.codec     # VariableCodec from KB
)

discrim_gen = DiscriminatingGenerator(checker, task, task.set_b[0])

# QuAcq with injected executor + oracle
quacq = QuAcq.for_oracle(checker, oracle, query_prov, discrim_gen)

# Run learning (Task-centric, returns raw assumption IDs)
result = quacq.learn(
    set_c=task.set_c, set_b=task.set_b,
    set_kb=task.set_kb, negation_map=task.negation_map,
    assumptions=task.assumptions,
    background_clauses=task.background_clauses,
    feature_ids=task.feature_ids, id_to_feature=task.id_to_feature,
    constraint_clauses=task.constraint_clauses,
    negated_clauses=task.negated_clauses,
    mode='oracle', max_queries=1000)
# Runner resolves names: kb_names, kb_clauses = model.resolve_kb(result.kb_assumption_ids)

# Query generation via codec (no model dependency)
config, c_id = query_prov.generate(remaining_bias, learned_kb, set_b, 
                                   negation_map, task.feature_ids, task.codec)
```

**Key Algorithms**:
1. **ConGen** — Passive constraint acquisition
   - Input: Bias (B), E+ (set_tc), NE (set_neg_tv), BG (set_b) as assumption IDs
   - Process: Check consistency → ACQMSS → REDUCE
   - Output: CONGENResult with KB constraint names and assumption IDs
   - GenerateNE integrated into `ConGenTaskPreparation` (called by `model.prepare_task()`)

2. **GenerateNE** — Create negated examples (pure internal function)
   - Invoked by `ConGenTaskPreparation.prepare()` during task preparation
   - Uses QuickXPlain to find minimal conflicts from E⁻
   - Pure: `generate()` returns `NEPerTestcase` list; does NOT mutate caller's KB
   - Caller (strategy) extends its own KB copy from returned clauses

3. **ACQMSS** — Divide-and-conquer maximum satisfiable subset finding
   - Recursively partition bias constraints
   - Find MSS via KBDiag (kernel-based diagnosis)

4. **REDUCE** — Remove redundant constraints
   - Iterate over learned KB
   - Check if each constraint is necessary via consistency check

5. **QuAcq** — Interactive and batch learning (two modes)
   - Oracle mode: GenerateQuery → Oracle.ask() → Update KB
   - Example mode: FindScope + FindC via oracle.is_valid()

#### conacq/bias/ — Bias Generation

**Purpose**: Extract constraints from feature models for use as bias in learning.

**Components**:
- `bias_generator.py` — Extract hierarchical + cross-tree constraints from FM
- `clause_generator.py` — Convert constraints to CNF clauses
- `bias_io.py` — Load/save bias in JSON/YAML formats
- `config_loader.py` — TOML configuration for bias generation

#### conacq/example_generators/ — Example & Query Generation

**Purpose**: Generate diverse configurations and discriminative queries.

**Components**:

**Example Generation Strategies**:
1. **RandomSampling (RS)** — Uniform random configuration selection
2. **FeatureFrequency (FF)** — Weight by feature occurrence patterns
3. **TwoCoverage (2-COV)** — Ensure feature pairs appear together

**Query Generation** (Phase R):
- **QueryProvider** — Unified query/example provision with injected checker
  - All SAT checks delegated to `checker.is_consistent()` (no ad-hoc solver creation)
  - Three strategies: pool-first, SAT-based, or pool+SAT fallback

#### conacq/oracle/ — Oracle Implementations

**Purpose**: Unified oracle interface for configuration validation.

**Oracle ABC** (`base.py`):
- Minimal interface: `is_valid(assignments)` and `ask()` (alias) only
- FM-specific methods on concrete implementations

**Key Classes**:

- **FeatureModelOracle** — FM-based oracle with incremental solver
- **FMOracleModel** — SAT representation of FM (Phase R) with assumption-guarded assignments
- **UserPromptOracle** — Interactive human oracle
- **CachedOracle** — Transparent result caching wrapper
- **OracleData** — Extracted oracle data for evaluation

**Critical Detail**: Feature ID consistency
- `FMOracleModel.variables` uses flamapy's variable mapping (tree traversal order)
- Ensures feature_ids match SAT variable IDs in CNF clauses
- Alphabetical sorting would cause critical mismatch with clause literals
- Source of truth: `FmToPysat.variables` from FM→SAT conversion

#### conacq/runners/ — Execution Runners

**Purpose**: Unified lifecycle for running constraint acquisition algorithms with resource management.

**Unified Lifecycle Pattern** (commit 260228):
```
# ConGenRunner: build once, prepare+shuffle per fold, cleanup once
runner = ConGenRunner(bias_path, fm_path)  # __init__: build model+oracle
try:
    result1 = runner.run(pos_fold_1, neg_fold_1, shuffle_seed=42)  # prepare → shuffle → run
    result2 = runner.run(pos_fold_2, neg_fold_2, shuffle_seed=43)  # prepare → shuffle → run
finally:
    runner.cleanup()  # cleanup once

# QuAcqRunner: same pattern
runner = QuAcqRunner(bias_path, fm_path)  # __init__: build model+oracle
try:
    result1 = runner.run(pos_fold_1, neg_fold_1, mode='example_only', shuffle_seed=42)
    result2 = runner.run(pos_fold_2, neg_fold_2, mode='example_only', shuffle_seed=43)
finally:
    runner.cleanup()
```

**BaseRunner ABC**:
- `__init__(bias_path, fm_path, solver_name, use_incremental=True)` — Build: load bias, create oracle, build model
- `run(**kwargs)` (abstract) — Execute: prepare_task → shuffle → acquire
- `cleanup()` — Release oracle resources
- `feature_ids` property — Get feature→SAT variable mapping

**BaseRunResult** (9 shared fields):
- KB output: `kb_constraints` (str names), `kb_clauses` (CNF), `bg_clauses` (root constraint)
- Size metrics: `n_bias` (original), `n_kb` (learned)
- Performance: `runtime_ms`, `consistency_checks` (SAT calls), `memory_peak_mb`
- Profiling: `profiler_data` (full profiler snapshot)
- Method: `get_performance_metrics()` returns PerformanceMetrics (with `n_mss=None` for interactive, actual value for ConGen)

**ConGenRunner** (inherits BaseRunner):
- `__init__`: Builds ConGenModel via ConGenModelBuilder (requires oracle for build-time negation)
- `run(positive_examples, negative_examples, shuffle_seed=None)` → `ConGenRunResult`
  - Prepare: `task = model.prepare_task(TaskInput(...), oracle)`
  - Shuffle: `random.Random(shuffle_seed).shuffle(task.set_c)` after prepare
  - Acquire: Run ConGen with shuffled bias iteration order
- `cleanup()` called in CV wrapper functions via try/finally

**QuAcqRunner** (inherits BaseRunner):
- `__init__`: Builds QuAcqModel via QuAcqModelBuilder (requires oracle for build-time negation)
- `run(positive_examples=None, negative_examples=None, mode='example_only', shuffle_seed=None)` → `QuAcqRunResult`
  - Prepare: `task = model.prepare_task(TaskInput(), oracle)` (fresh task per run)
  - Shuffle & dispatch based on mode
- Modes: 'automated'/'interactive' (oracle), 'example_only'/'example_first' (examples)

#### conacq/eval/ — Evaluation Framework

**Purpose**: Measure accuracy and generate CV reports.

**Components**:
- `cross_validation.py` — n-fold CV orchestration (CONGEN & Interactive modes); calls `runner.cleanup()` via try/finally
- `accuracy.py` — Calculate accuracy, precision, recall, F1
- `kb_comparator.py` — Strategy-based comparison (description/clause) against oracle FM + `ComparationResult.to_enriched_dict()`
- `config.py` — Pipeline config (ModelConfig, find_cv_files, find_kb_files)
- `result_loader.py` — Load evaluation results + `ConGenResultData.from_dict()`
- `report.py` — Generate CSV/JSON/LaTeX/Markdown reports; unified CV dict builder (`generate_unified_cv_dict`, `_enrich_constraints`)


**Metrics**: Accuracy, precision, recall, F1 (against ground truth FM)

**Comparison Strategies** (in `kb_comparator.py`):
- **description** — Compare constraint natural language descriptions (recommended)
- **clause** — Compare CNF clauses exactly (structural)
- **semantic** — SAT-based bidirectional entailment (KB ≡ C_T equivalence)

### explanation/ — SAT Solver Infrastructure

**Purpose**: Provide diagnosis algorithms and solver abstractions for constraint acquisition.

#### explanation/models/ — Diagnosis Task & Codec (Phase R)

**Task Hierarchy** (immutable unit-of-work):
```python
class Task(ABC):
    """Immutable unit of work: KB + operation-specific state.
    
    Shared across all tasks: the KB (clauses + assumptions + negation map) + codec.
    """
    set_kb: list[list[int]]     # CNF with assumption literals
    set_b: list[int]            # Background assumption IDs
    set_c: list[int]            # Bias assumption IDs
    assumptions: list[int]      # All assumption literals
    negation_map: dict[int, int] # assumption_id → negated_id
    describe: Optional[DescriptionProvider]  # Formatting (KB name resolution)
    codec: Optional[VariableCodec]          # Variable name ↔ ID + config ↔ assumptions

class DiagnosisTask(Task):
    """Base task with assumptions (shared fields only)."""
    pass

class TestCaseTask(Task):
    """Task for test case scenarios (test-specific fields)."""
    set_tc: list[int]           # E+ assumption IDs
    set_tv: list[int]           # E- assumption IDs

class ConGenTask(TestCaseTask):
    """Task for ConGen passive learning."""
    set_neg_tv: list[int]       # Negated example assumption IDs from GenerateNE

class QuAcqTask(DiagnosisTask):
    """Task for QuAcq interactive learning.
    
    Adds interactive-specific state (no inheritance change; sibling to TestCaseTask).
    """
    bias: set[int]              # Remaining bias assumption IDs
    learned_kb: list[int]       # Learned constraint assumption IDs
    background_clauses: list[list[int]]  # Raw BG CNF (no guards)
    feature_ids: dict[str, int] # Feature name → SAT var ID
    id_to_feature: dict[int, str] # SAT var ID → feature name
    constraint_clauses: dict[int, list[list[int]]]  # constraint_id → raw clauses
    negated_clauses: dict[int, list[list[int]]]  # constraint_id → negated clauses

class VariableCodec:
    """Codec for variable/assumption/config translation (Phase R).
    
    Single source of truth for translating between feature names, SAT variable IDs,
    and assumption literals for one KB. Built once at KB level; referenced by all Tasks.
    
    Attributes:
        id_to_name: SAT var ID → feature name (always present)
        pos_assignment_to_assumption: feature → assumption ID asserting True (optional)
        neg_assignment_to_assumption: feature → assumption ID asserting False (optional)
    """
    id_to_name: dict[int, str]
    pos_assignment_to_assumption: dict[str, int]  # optional
    neg_assignment_to_assumption: dict[str, int]  # optional
    
    def config_to_assumptions(config: dict[str, bool]) -> list[int]
    def model_to_config(model_lits: list[int]) -> dict[str, bool]
```

#### explanation/operations/ — Diagnosis Algorithms & Executor Layer (Phase R)

**ConsistencyExecutor Protocol** (L2/L3 abstraction):
```python
class ConsistencyExecutor(Protocol):
    """Service contract for running consistency checks.
    
    The single abstraction algorithms depend on. Serial implementation is
    ConsistencyChecker itself (inline); parallel is ProcessExecutor (shared pool).
    Both MUST give identical results — only timing differs.
    """
    def is_consistent(set_c: List[int]) -> bool
    def is_consistent_test_cases(set_c, set_tc, stop_at_first_violation) -> List
    def solve(set_c) -> Tuple[bool, Optional[List[int]]]  # Returns (sat, model)
    def submit(set_c) -> Future[bool]  # Async lookahead (FastDiagP)
```

**Serial Executor** (`ConsistencyChecker` implementing `ConsistencyExecutor`):
- `IncrementalPySATChecker` — Persistent solver (~50x faster, ideal for ConGen)
  - Computes delta: disabled assumptions = all_assumptions \ set_c
  - Calls solver with negated disabled assumptions
  - `solve()` returns (sat, model); `submit()` returns immediate future
- `NonIncrementalPySATChecker` — Fresh solver per call (baseline)
  - Builds CNF from set_kb and set_c clauses each time
  - `solve()` returns (sat, None)
- `SAT4JChecker` — External Java solver via subprocess
- All support `is_consistent_test_cases()` for batch CC (used by KBDiag, ConGen)

**Parallel Executor** (`ProcessExecutor`, NEW in Phase R):
- Shared multiprocess pool: each worker builds checker ONCE from KB (sent once via initializer)
- Per call: only assumptions (picklable ints) shipped; bool or (bool, model) returned
- Profiler (option B): workers use NullProfiler; main process counts at call boundary
  - Result: serial ConsistencyChecker and ProcessExecutor report identical metrics
- Used by FastDiagP for speculative lookahead (`submit()`)

**Memoizing Cache** (`MemoizingExecutor`, NEW):
- Decorator over any executor (serial or parallel)
- Thread-safe hash map: assumptions-hash → resolved bool (never futures)
- HIT does NOT count as a consistency check (no counter increment)
- MISS delegates to inner executor, which increments boundary counter

**Checker Factory** (Phase R):
```python
CheckerFactory.create_from_task(task, *, solver_name, use_incremental, profiler)
# Returns ConsistencyChecker (serial executor) or ProcessExecutor (via wrapper)
# Solver mode controlled at operation level, not KB level
```

**Diagnosis Algorithms**: FastDiag (minimal diagnosis via HSDAG), QuickXPlain (minimal conflicts), KBDiag (kernel-based, used by ACQMSS), WipeOutR (domain-specific), FastDiagP (parallel lookahead via executor)

#### explanation/transformations/ — Model Converters

**FM to SAT Conversion**: Extract FM features/constraints → propositional CNF clauses. **CRITICAL**: Variable mapping MUST use flamapy's tree traversal order (not alphabetical) to match feature_ids with SAT variable IDs.

## QuAcq → ConGen Evaluation Pipeline (NEW)

**Purpose**: Compare QuAcq (interactive) and ConGen (passive) via progressive query budgets to understand when ConGen reaches QuAcq KB quality.

**Architecture**:
```
QuAcq (automated)
    ├─ Run oracle-based learning
    ├─ Record query history with source tags ('main', 'findc')
    ├─ Final KB and metrics
    └─ Query history → assignment lists

Converter (query_converter.py)
    ├─ queries_to_assignment_lists() — Extract E+/E- from history
    └─ queries_to_examples() — Convert to ExampleSet format

Progressive Evaluator (progressive_evaluation.py)
    ├─ For each checkpoint [10%, 25%, 50%, 75%, 100%]:
    │   ├─ Slice query history to N% of total queries
    │   ├─ ConGen.run(E+_N%, E-_N%)
    │   ├─ Three comparisons (KB vs C_T):
    │   │   ├─ Description strategy (constraint names)
    │   │   ├─ Clause strategy (CNF matching)
    │   │   └─ Semantic strategy (SAT-based equivalence)
    │   └─ Metrics: accuracy, precision, recall, F1, KB size
    └─ Collect CheckpointResult for each % level

Final Comparison
    ├─ QuAcq final KB (all queries)
    ├─ ConGen final KB (100% checkpoint)
    └─ Semantic equivalence: KB ≡ C_T via bidirectional entailment
```

**Key Strategies**:

1. **Description-Based** (recommended): Compare constraint text descriptions
   - Pros: Human-readable, tolerant of syntactic variations
   - Cons: Requires constraint descriptions in bias

2. **Clause-Based**: Compare CNF clauses structurally
   - Pros: Syntactically precise
   - Cons: Semantically identical but reordered clauses count as mismatches

3. **Semantic-Based** (NEW): SAT-based bidirectional entailment
   - KB ⊨ C_T: For each c in C_T, (KB + BG + ¬c) is UNSAT
   - C_T ⊨ KB: For each c in KB, (C_T + ¬c) is UNSAT
   - Equivalence: Both directions hold → KB ≡ C_T
   - Implementation: `SemanticEquivalenceChecker` uses pysat directly

**Execution** (`run_evaluation.py`):
```bash
python -m apps.run_evaluation apps/conf/run_evaluation_config.toml -v
```

**Output** (`{model}_evaluation.json`):
```json
{
  "metadata": {"model": "arcade-game", "timestamp": "...", "checkpoints_pct": [10, 25, 50, 75, 100]},
  "quacq": {"n_queries": 150, "n_kb": 32, "convergence_reason": "bias_exhausted", "runtime_ms": 5230},
  "progressive": [
    {
      "checkpoint_pct": 10,
      "n_queries": 15,
      "n_kb": 8,
      "comparison": {
        "description": {"metrics": {"accuracy": 0.75, ...}, "matched_constraints": [...], ...},
        "clause": {...},
        "semantic": {"is_equivalent": false, "kb_entails_ct": true, "ct_entails_kb": false}
      }
    },
    ...
  ],
  "quacq": {
    "comparison": {
      "description": {...},
      "semantic": {"is_equivalent": true}
    }
  }
}
```

## Unified CV Output Pipeline

**Architecture** (commit 260226): CV pipeline now produces single JSON file per experiment (not 45+ files).

### Unified CV JSON Structure

**Filename format**:
- ConGen: `{model}_{strategy}_{mode}_cv.json` (no algorithm suffix, algorithm is determined from directory)
- Interactive: `{model}_{strategy}_{mode}_cv_{query_mode}.json` (includes query_mode: example_only, example_first, etc.)

**Examples**:
- ConGen: `arcade-game_RS_incremental_cv.json`
- Interactive: `arcade-game_RS_incremental_cv_example_only.json`

**Contents**:
```json
{
  "metadata": {
    "model": "arcade-game",
    "algorithm": "CONGEN",
    "strategy": "RS",
    "mode": "incremental",
    "num_folds": 10,
    "timestamp": "2026-02-26T13:27:00"
  },
  "folds": [
    {
      "fold_index": 0,
      "metrics": {
        "accuracy": 0.95,
        "precision": 0.92,
        "recall": 0.98,
        "f1_score": 0.95
      },
      "learned_kb": [
        {"id": 1, "clause": [1, 2, -3], "description": "..."},
        ...
      ],
      "evaluation": {
        "true_positives": 45,
        "false_positives": 2,
        "true_negatives": 200,
        "false_negatives": 1
      }
    },
    ...
  ],
  "summary": {
    "mean_accuracy": 0.93,
    "std_accuracy": 0.02,
    "mean_kb_size": 42,
    "std_kb_size": 3.5
  }
}
```

### Processing Pipeline

**Stage 1**: `run_cv.py`
- Loads config (models, strategies, modes)
- Runs n-fold CV for each combination
- Generates unified JSON per experiment
- No external KB files written

**Stage 2**: `run_compare.py` (config mode, optional)
- Reads unified CV JSON files
- Enriches with constraint descriptions via `_enrich_constraints()`
- Compares learned KBs across folds via `ComparationResult.to_enriched_dict()`
- Writes enriched evaluation back (idempotent, same filename)
- Fallback: Reads legacy external eval files if unified JSON not found

**Stage 3**: `extract_results.py`
- Reads unified CV JSON files via `ConGenResultData.from_dict()`
- Aggregates fold metrics (mean, std, min, max)
- Generates final reports (Markdown, LaTeX)
- Embeds fold-level accuracy/precision/recall/F1 in output

### Key Functions

| Function | Module | Purpose |
|----------|--------|---------|
| `generate_unified_cv_dict()` | report.py | Build unified CV output dict from CV results |
| `_enrich_constraints()` | report.py | Add constraint descriptions to KB within CV dict |
| `ComparationResult.to_enriched_dict()` | kb_comparator.py | Serialize comparison with full constraint details |
| `ConGenResultData.from_dict()` | result_loader.py | Deserialize CV result from dict (for extract_results.py) |
| `find_cv_files()` | config.py | Locate unified CV JSON files (`*_cv_*.json` pattern) |

### Backward Compatibility

- `extract_results.py` reads embedded evaluation first (preferred)
- Falls back to external eval files if unified JSON unavailable
- Legacy CV result files still supported
- Old `run_compare.py` mode (KB comparison) unchanged

## Two Learning Paradigms (Unified via Assumption IDs)

### 1. ConGen (Passive/Batch Learning)
- Input: Pre-collected E+/E- examples
- No user interaction required
- Learns constraint KB in one pass (GenerateNE → ACQMSS → REDUCE)
- **ConGenModel**: Immutable KB container (bias + negation map). Oracle injected at prepare_task() time.
- **Task Factory**: `model.prepare_task(task_input, oracle)` returns fresh ConGenTask with E+/E-/NE
- **CV Pattern**: Build once, prepare multiple times per fold without rebuilding
- **Task Representation**: `ConGenTask` with assumption IDs (set_c, set_tc, set_neg_tv, negation_map)
- Complexity: O(|B| * SAT checks)

### 2. QuAcq (Interactive/Active Learning) — NOW UNIFIED WITH ASSUMPTION IDs
- **Architecture**: `QuAcqModel` (dual to ConGenModel) + `QuAcqTask` (dual to ConGenTask)
- **Both use int assumption IDs** for constraint identification (matching ConGen semantics)
- **Oracle mode**: Queries user for membership via `QuAcq.learn(oracle_mode='automated'/'interactive')`
- **Example mode**: Uses pre-collected E+/E- via `QuAcq.learn_from_examples(positive_examples, negative_examples)`
- **CV support**: `n_fold_cross_validation_interactive()` with `QuAcqRunner(bias_path, fm_path, ...)`
- **Dual-mode runner**: `QuAcqRunner.run(mode)` dispatches to oracle or example paths
- **Task Representation**: `QuAcqTask` with assumption IDs (bias: Set[int], learned_kb: List[int])
- **Result Representation**: `QuAcqResult` with dual fields (kb_constraints: str names, kb_assumption_ids: int IDs)
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

### ConGen Learning Flow
```
Bias (JSON) + Feature Model (UVL) + Examples
    ├─→ [__init__] ConGenModelBuilder.from_bias(bias_path).with_oracle(oracle).build()
    │   └─ Computes negation at build time (immutable KB)
    │
    ├─→ [run] task = model.prepare_task(TaskInput(E+, E-), oracle)
    │   ├─ GenerateNE: E- → NE (internal to ConGenTaskPreparation)
    │   └─ Returns fresh ConGenTask (independent per call, no state mutation)
    │
    ├─→ [run] Shuffle: random.Random(seed).shuffle(task.set_c) (after prepare)
    │
    ├─→ [run] checker = CheckerFactory.create_from_task(task, solver_name='...', use_incremental=...)
    │   └─ Operation-level solver control (not on model)
    │
    └─→ [run] ConGen Algorithm
        ├─ acquire(set_b, set_bg, set_tc, set_neg_tv, negation_map, ...)
        ├─ ACQMSS: Bias → MSS via KBDiag
        └─ REDUCE: MSS → KB
```

**Phase R Design**:
- **Immutable KB**: ConGenModel is pure data container; no mutation via prepare_task()
- **Pure Task Factory**: Each prepare_task() call returns fresh, independent Task
- **GenerateNE Pure**: Returns clauses; caller extends its own KB copy
- **Operation-Level Control**: use_incremental on CheckerFactory, not model builder
- **Oracle Injected**: Passed to prepare_task(), not stored in model

### QuAcq Interactive/Batch Flow (Paper-Aligned with oracle.is_valid())

```
Feature Model + Bias + Oracle
    ├─→ [__init__] QuAcqModelBuilder.from_bias(bias_path).with_oracle(oracle).build()
    │   └─ Computes negation at build time (immutable KB)
    │
    ├─→ [run] task = model.prepare_task(TaskInput(), oracle)
    │   └─ Fresh QuAcqTask per run (independent, no mutation)
    │
    ├─→ [run] Shuffle: random.Random(seed).shuffle(task.set_c)
    │
    ├─→ [run] checker = CheckerFactory.create_from_task(task, ...)
    │   └─ Operation-level solver control
    │
    └─→ [run] QuAcq Algorithm (oracle or example mode)
        ├─ GenerateQuery → oracle.is_valid() → Update KB
        │
        └─ Example mode: QuAcq.learn_from_examples(task, E+, E-)
            ├─ For each e in E-:
            │   ├─ FindScope: Binary search via oracle.is_valid() (O(|S| * log|X|))
            │   │   ├─ Partial query: oracle.is_valid({k: e[k] for k in R})
            │   │   ├─ SAT-based bias pruning: checker.is_consistent(base + [c_id]) per constraint
            │   │   │   └─ Prune constraints inconsistent with partial assignment
            │   │   └─ record_query(partial, answer, 'findscope')
            │   │
            │   ├─ FindC: Discriminate candidates via SAT-based filtering (O(|Gamma|))
            │   │   ├─ Scope matching: Find bias constraints with matching scope Y
            │   │   ├─ SAT-based rejection: checker.is_consistent(base + [c_id] + config_assumptions)
            │   │   │   └─ Reject constraints inconsistent with negative example e
            │   │   ├─ DiscriminatingGenerator (if provided): SAT formula BG + C_L[Y] + c_i + neg(c_j)
            │   │   │   ├─ Paper Algorithm 3 line 5 (not FM clauses)
            │   │   │   └─ oracle.is_valid(config) to validate discriminating example
            │   │   └─ record_query(disc_e, answer, 'findc')
            │   │
            │   └─ Add found constraint (assumption ID) to KB
            └─ Termination: All E- processed or bias exhausted

Result: QuAcqResult with assumption IDs + query history
    ├─ kb_assumption_ids: List[int] — Primary representation (raw from algorithm)
    ├─ query_history: List[(config, answer, source)] — Tagged queries ('main', 'findscope', 'findc')
    ├─ consistency_checks: int — Profiling data
    └─ kb_constraints: List[str] — Resolved by runner via model.resolve_kb()
```

**Phase R Design**:
- **Immutable KB**: QuAcqModel is pure data container
- **Per-run Prepare**: model.prepare_task(TaskInput(), oracle) returns fresh Task each run
- **Pure Task**: No state mutation across calls; independent Tasks for each run
- **Shuffle After Prepare**: Matches ConGen pattern (bias iteration randomization)
- **Operation-Level Control**: use_incremental on CheckerFactory, not model
- **Oracle Injected**: Passed to prepare_task(), not stored in model

**File Organization** (Consolidated in conacq/algorithms/quacq/):
- **task_preparation.py**: `QuAcqTask` class (inherits DiagnosisTask) + `QuAcqTaskPreparation`
- **quacq.py**: `QuAcq` algorithm + `QuAcqResult` (oracle.is_valid(), query history with tags)
- **findscope.py**: FindScope (Algorithm 2, DI pattern: oracle + ConsistencyChecker + model)
  - Bias pruning: SAT-based consistency checking via checker.is_consistent()
- **findc.py**: FindC (Algorithm 3, DI pattern: oracle + ConsistencyChecker + model + DiscriminatingGenerator)
  - Rejection filtering: SAT-based consistency checking before discriminating examples
- **discriminating_generator.py**: DiscriminatingGenerator (C_L[Y] + BG, not FM)
- **quacq_model.py**: QuAcqModel for interactive learning (includes config_to_assumptions)
- **quacq_model_builder.py**: Fluent builder pattern
- **sat_utils.py**: Shared SAT utilities (config/scope conversion, consistency pruning, constraint extraction)

## Integration Points

conacq/ uses explanation/ components:
- **ACQMSS**: Uses KBDiag from explanation.operations.algorithms
- **Consistency Checking**: Pluggable ConsistencyChecker abstraction (Incremental, NonIncremental, SAT4J)
- **Profiling**: Optional global profiler pattern (minimal overhead when disabled)
- **CNF Format**: Unified list[list[int]] representation across all components

**Feature ID Consistency (CRITICAL)**:

The Oracle and all SAT-based components must use the **same** feature_ids mapping:
```
Oracle (conacq/oracle/fm_oracle.py)
  ├─ _build_cnf(): Uses FmToPysat → generates CNF clauses with variable IDs
  └─ _build_feature_ids(): Must extract mapping from same FmToPysat transform

Result: feature_ids matches SAT variable IDs in CNF
```

- **Source of Truth**: Flamapy's variable mapping (tree traversal order)
- **Pattern**: All code using feature_ids must receive it from Oracle or same FM→SAT conversion
- **Failure Mode**: Alphabetical sorting breaks mismatch → incorrect Oracle validation

## Solver Architecture (Phase R)

**Immutable KB + Pure Task**:
- Model stores constraint_map, negated_constraint_map (read-only after build)
- `model.prepare_task(task_input) -> Task` is pure: fresh Task each call (no mutation)
- Checker built from Task, not model: `CheckerFactory.create_from_task(task, ...)`
- Solver mode (`use_incremental`) chosen at operation-level via `with_incremental()` builder or `create_from_task()` parameter

**Incremental Mode** (default):
- Persistent solver instance across calls
- ~50x faster for repeated SAT checks
- Checkers immutable after construction

**Non-Incremental Mode**:
- Fresh solver per call
- Memory-light, clear isolation
- Same assumption-based data representation as incremental
- Good for verification and comparison

**Parallel Mode (ProcessExecutor)** (Phase R):
- Shared multiprocess pool (L3); worker builds checker once from KB
- Option B profiler: main process counts at boundary, workers use NullProfiler
- Memo cache (KB-namespaced): deduplicates CC across concurrent submitters

## Performance Metrics

### PerformanceMetrics Updates

**PerformanceMetrics.n_mss** (NEW: `Optional[int] = None`):
- ConGenRunner: Sets actual MSS count from ACQMSS
- QuAcqRunner: None (no MSS concept in interactive learning)
- Enables unified metrics across both runners while supporting ConGen-specific measurements

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

- **HSDAG Tree Search** (~10x fewer calls)
- **Incremental Solver** (~50x faster)
- **Assumption-based Hypothesis Testing** (solver state reuse)
- **Divide-and-Conquer** (ACQMSS problem reduction)
- **Set-Based Bias Storage** (O(1) removals in QuAcq)

Combined: 500-1000x speedup over naive approaches.

## Testing Architecture

### Test Organization

```
tests/
├── test_diagnosis.py        # FastDiag, QuickXPlain, KBDiag, WipeOutR
├── test_congen.py           # CONGEN, ACQMSS, REDUCE, GenerateNE
├── test_quacq.py            # QuAcq, QuAcqTask, QueryGenerator, FindScope/FindC
├── test_evaluation.py       # CrossValidation, AccuracyCalculator
├── test_profiler.py         # Profiling infrastructure
└── test_*.py                # Other component tests
```

Tests run in both Incremental and NonIncremental modes. Control via `ENABLED_TESTS`/`ENABLED_PARAMS` dicts.

## Dependencies

**Required**: pysat (SAT solver), flamapy (FM parsing)
**Optional**: sat4j (Java solver), pytest
**Not used**: Direct SAT solvers, external constraint solvers, ML frameworks
**Security**: FM/CNF/TOML validation, configurable timeouts, graceful error handling
