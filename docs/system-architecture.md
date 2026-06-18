# AcqMSS System Architecture

**Last Updated**: 2026-02-28 (QueryProvider + ConsistencyChecker refactor: injected checker/model, unified SAT interface, get_model() extraction)

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

**Core API**:

```python
from conacq.algorithms import ConGen, ConGenModelBuilder
from conacq.algorithms.quacq import QuAcqModelBuilder, QuAcq
from conacq.oracle import FeatureModelOracle
from conacq.example_generators import QueryProvider
from explanation.operations.algorithms.checker import CheckerFactory

# Passive learning — Pattern 1: auto-prepare (oracle + examples at build time)
oracle = FeatureModelOracle('data/fms/model.uvl')
model = (ConGenModelBuilder.from_bias('data/bias/model.json')
         .with_oracle(oracle).with_examples('data/examples/model.json').build())

# Passive learning — Pattern 2: manual prepare (CV reuse)
model = ConGenModelBuilder.from_bias('data/bias/model.json').build()  # unprepared
model.prepare(oracle, positive_examples=pos, negative_examples=neg)  # Calls GenerateNE internally

checker = CheckerFactory.create_from_model(model, profiler)
congen = ConGen(checker, profiler)
result = congen.acquire(
    set_b=model.task.set_c,
    set_bg=model.task.set_b,
    set_tc=model.task.set_tc,
    set_neg_tv=model.task.set_neg_tv,
    negation_map=model.task.negation_map  # Maps assumption ID → negated ID for REDUCE
)

# For cross-validation: build once, prepare per fold
model = ConGenModelBuilder.from_bias('data/bias/model.json').build()
oracle = FeatureModelOracle('data/fms/model.uvl')
for fold_pos, fold_neg in folds:
    model.prepare(oracle, positive_examples=fold_pos, negative_examples=fold_neg)
    # Use model.task for this fold

# Interactive learning — QuAcq (DI pattern, commit 260228)
from conacq.example_generators import QueryProvider
from conacq.algorithms.quacq import DiscriminatingGenerator, QuAcq
from explanation.operations.algorithms.checker import CheckerFactory

oracle = FeatureModelOracle('data/fms/model.uvl')
model = (QuAcqModelBuilder.from_bias('data/bias/model.json')
         .with_oracle(oracle)
         .build())  # Returns prepared model, task ready

# Build checker (injected dependency) — NEW pattern
checker = CheckerFactory.create_from_model(model)

# QueryProvider with injected checker + model — NEW: no solver_name parameter
query_prov = QueryProvider(
    checker=checker,    # Injected ConsistencyChecker
    model=model         # For config_to_assumptions()
)

# DiscriminatingGenerator with injected checker + model (NEW - commit 260228)
discrim_gen = DiscriminatingGenerator(checker, model, model.task.set_b[0])

# QuAcq with checker parameter (NEW)
quacq = QuAcq.for_oracle(checker, oracle, query_prov, discrim_gen)

# Run learning (simplified signature, no background_clauses/negated_clauses params)
result = quacq.learn(
    set_c=model.task.set_c, set_b=model.task.set_b,
    set_kb=model.task.set_kb, negation_map=model.task.negation_map,
    assumptions=model.task.assumptions,
    background_clauses=model.task.background_clauses,
    feature_ids=model.task.feature_ids, id_to_feature=model.task.id_to_feature,
    constraint_clauses=model.task.constraint_clauses,
    negated_clauses=model.task.negated_clauses,
    mode='oracle', max_queries=1000)  # → QuAcqResult with KB assumption IDs only
# Runner resolves names: kb_names, kb_clauses = model.resolve_kb(result.kb_assumption_ids)

# Query generation (instance methods on QueryProvider instance)
config, c_id = query_prov.generate_from_sat(remaining_bias, learned_kb, set_b, negation_map, id_to_feature)
config, c_id = query_prov.generate_from_pool(remaining_bias, learned_kb, set_b)
config, c_id = query_prov.generate(remaining_bias, learned_kb, set_b, negation_map, id_to_feature)
```

**Key Algorithms**:
1. **ConGen** — Passive constraint acquisition
   - Input: Bias (B), E+ (set_tc), NE (set_neg_tv), BG (set_bg) as assumption IDs
   - Process: Check consistency → ACQMSS → REDUCE
   - Output: CONGENResult with KB constraint names and assumption IDs
   - **GenerateNE now called internally by `ConGenModel.prepare()`** (callers no longer invoke directly)
   - Can be reused across CV folds: Call `model.prepare(oracle, fold_pos, fold_neg)` per fold (oracle reused)

2. **GenerateNE** — Create negated examples (internal API, not caller-invoked)
   - **Invoked only internally by `ConGenModel.prepare()`**
   - Uses QuickXPlain to find minimal conflicts from E⁻
   - Simplified result: `NEResult(new_clauses, set_neg_tv, next_available_id)` (removed `assumption_ids`, `neg_map`)
   - Results merged in-place via inline code in `ConGenModel.prepare()`

3. **ACQMSS** — Divide-and-conquer maximum satisfiable subset finding
   - Recursively partition bias constraints
   - Find MSS via KBDiag (kernel-based diagnosis)

4. **REDUCE** — Remove redundant constraints
   - Iterate over learned KB
   - Check if each constraint is necessary via consistency check

5. **QuAcq** — Interactive and batch learning (two modes, paper-aligned)
   - **Oracle mode** (original): GenerateQuery → Oracle.ask() → Update KB
   - **Example mode** (paper-faithful): FindScope + FindC via oracle.is_valid() + DiscriminatingGenerator(C_L[Y])
   - FindScope: O(|S| * log|X|) queries per call (oracle.is_valid + SAT-based bias pruning)
   - FindC: O(|Gamma|) queries per call (oracle.is_valid + SAT-based rejection + DiscriminatingGenerator)

#### conacq/bias/ — Bias Generation

**Purpose**: Extract constraints from feature models for use as bias in learning.

**Components**:
- `bias_generator.py` — Extract hierarchical + cross-tree constraints from FM
- `clause_generator.py` — Convert constraints to CNF clauses
- `bias_io.py` — Load/save bias in JSON/YAML formats
- `config_loader.py` — TOML configuration for bias generation

#### conacq/example_generators/ — Example & Query Generation

**Purpose**: Generate diverse positive/negative configurations and discriminative queries for learning.

**Components**:

**Example Generation Strategies**:
1. **RandomSampling (RS)** — Uniform random configuration selection
2. **FeatureFrequency (FF)** — Weight by feature occurrence patterns
3. **TwoCoverage (2-COV)** — Ensure feature pairs appear together

**Query Generation & Selection** (commit 260228):
- **QueryProvider** — Unified query/example provision with injected ConsistencyChecker
  - Constructor: `QueryProvider(pool=None, seed=None, checker=ConsistencyChecker, model=QuAcqModel, profiler=None)`
  - All SAT checks delegated to injected `checker` (no ad-hoc solver creation)
  - Config-to-assumption conversion via injected `model.config_to_assumptions()`
  - Three strategies:
    1. `generate_from_pool(remaining_bias, learned_kb, set_b)` — Pool iteration with paper conditions
    2. `generate_from_sat(remaining_bias, learned_kb, set_b, negation_map, id_to_feature)` — SAT-based generation
    3. `generate(remaining_bias, learned_kb, set_b, negation_map, id_to_feature)` — Pool-first, SAT fallback
  - **Consistency checks**: Both pool filtering conditions use `checker.is_consistent()`
  - **SAT model extraction**: `checker.get_model()` returns assignment for config conversion

#### conacq/oracle/ — Oracle Implementations

**Purpose**: Unified oracle interface for configuration validation.

**Oracle ABC** (`base.py`):
- Minimal interface: `is_valid(assignments)` and `ask()` (alias) only
- FM-specific methods on concrete implementations

**Key Classes**:

1. **FMData** (`fm_data.py`): FM metadata (features, feature_ids, root, constraints, next_available_id)
   - Created once by `FeatureModelOracle.get_fm_data()`, passed to decouple callers
2. **FeatureModelOracle** (`fm_oracle.py`): FM-based oracle
   - **ABC methods**: `is_valid(assignments)`, `ask(query)` for configuration validation
   - **Extensions**: FM metadata access (FMData), SAT-based config completion, constraint descriptions
   - Delegates consistency checks to `FMOracleModel` (incremental solver by default)

3. **BGData** (`bg_data.py`): Root FM constraint as assumption-guarded clauses
   - Contains root constraint pair (original + negated form) and negation mapping
   - Extracted post-preparation via `FMOracleModel.bg_data` property
   - Enables ConGen to allocate assumption IDs without overlap

4. **FMOracleModel** (`fm_oracle_model.py`): SAT representation of FM for consistency checking
   - FM clauses in `set_kb`; feature assignments guarded by assumption literals
   - Implements `CheckerModel` protocol for `CheckerFactory` integration
   - Prepared via `OracleTaskPreparation`; exposes `bg_data` property for root constraint extraction

5. **UserPromptOracle** (`user_prompt.py`): Interactive human-in-the-loop oracle
   - Raises `NotImplementedError` for `complete_configuration()` and `get_cnf_clauses()`
   - Suitable for interactive learning only

6. **CachedOracle** (`cached.py`): Transparent result caching wrapper
   - Caches `is_valid()` results
   - Delegates `complete_configuration()`, `get_cnf_clauses()` to base oracle

7. **OracleData** (`extractor.py`): Extracted oracle data for evaluation
   - Backward-compatible alias: `GroundTruthData`
   - Reads FM directly (no solver)

**Architecture Notes**:
- Unified `Oracle` ABC with FM-specific extensions in concrete classes
- FM metadata decoupled via `FMData` (explicit passing)

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
- `__init__(bias_path, fm_path, solver_name, use_incremental=True)` — Build once: load bias, create oracle with configured solver mode, build model
- `run(**kwargs)` (abstract) — Run many: execute acquisition algorithm (prepare → shuffle → acquire)
- `cleanup()` — Cleanup once: release oracle resources
- `feature_ids` property — Get feature→SAT variable mapping

**BaseRunResult** (9 shared fields):
- KB output: `kb_constraints` (str names), `kb_clauses` (CNF), `bg_clauses` (root constraint)
- Size metrics: `n_bias` (original), `n_kb` (learned)
- Performance: `runtime_ms`, `consistency_checks` (SAT calls), `memory_peak_mb`
- Profiling: `profiler_data` (full profiler snapshot)
- Method: `get_performance_metrics()` returns PerformanceMetrics (with `n_mss=None` for interactive, actual value for ConGen)

**ConGenRunner** (inherits BaseRunner):
- `__init__`: Builds ConGenModel via ConGenModelBuilder (requires oracle for negation at build time)
- `run(positive_examples, negative_examples, shuffle_seed=None)` → `ConGenRunResult`
  - Per-fold: `model.prepare(oracle, E+, E-)`
  - Shuffle: `random.Random(shuffle_seed).shuffle(task.set_c)` after prepare
  - Run ConGen with shuffled bias iteration order
- Calls `cleanup()` in CV wrapper functions via try/finally

**QuAcqRunner** (inherits BaseRunner):
- `__init__`: Builds QuAcqModel via QuAcqModelBuilder (requires oracle for negation at build time, auto-prepares)
- `run(positive_examples=None, negative_examples=None, mode='example_only', shuffle_seed=None)` → `QuAcqRunResult`
  - Per-run: `model.prepare(oracle)` (fresh task, reuses built negation)
  - Shuffle: `random.Random(shuffle_seed).shuffle(task.set_c)` after prepare
  - Dispatch to oracle or example path based on mode
- Modes: 'automated'/'interactive' (oracle), 'example_only'/'example_first' (examples)

**Runners re-exported from `conacq.eval`** (for backward compat):
- `BaseRunner`, `BaseRunResult` exported from `conacq/runners/__init__.py`
- Then re-exported from `conacq/eval/__init__.py`

#### conacq/eval/ — Evaluation Framework

**Purpose**: Measure accuracy of learned constraints against ground truth; unified CV output pipeline.

**Components**:
- `cross_validation.py` — n-fold CV orchestration (CONGEN & Interactive modes); calls `runner.cleanup()` via try/finally
- `accuracy.py` — Calculate accuracy, precision, recall, F1
- `kb_comparator.py` — Strategy-based comparison (description/clause) against oracle FM + `ComparationResult.to_enriched_dict()`
- `config.py` — Pipeline config (ModelConfig, find_cv_files, find_kb_files)
- `result_loader.py` — Load evaluation results + `ConGenResultData.from_dict()`
- `report.py` — Generate CSV/JSON/LaTeX/Markdown reports; unified CV dict builder (`generate_unified_cv_dict`, `_enrich_constraints`)


**Metrics**:
```
Accuracy  = (TP + TN) / (TP + TN + FP + FN)   [Primary]
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * P * R / (P + R)
```

**Comparison Strategies** (in `kb_comparator.py`):
- **description** — Compare constraint natural language descriptions (recommended)
- **clause** — Compare CNF clauses exactly (structural)
- **semantic** — SAT-based bidirectional entailment (KB ≡ C_T equivalence)

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
    """Base task with assumptions (inherited by TestCaseTask and QuAcqTask)."""
    assumptions: list[int]      # Control literals
    set_kb: list[list[int]]     # CNF with assumption literals
    set_b: list[int]            # Background assumption IDs
    set_c: list[int]            # Bias assumption IDs
    negation_map: Dict[int, int]   # Negation map: assumption_id → negated_id

class TestCaseTask(DiagnosisTask):
    """Task for test case scenarios (inherits from DiagnosisTask)."""
    set_tc: list[int]           # E+ assumption IDs
    set_tv: list[int]           # E- assumption IDs

class ConGenTask(TestCaseTask):
    """Task for ConGen - unified assumption-based format (inherits from TestCaseTask)."""
    set_neg_tv: list[int]       # Negated example assumption IDs

class QuAcqTask(DiagnosisTask):
    """Task for QuAcq interactive learning (inherits from DiagnosisTask).

    Inheritance pattern:
    - Inherits: set_kb, assumptions, set_b, set_c, negation_map from DiagnosisTask
    - Adds: bias, learned_kb (interactive learning state)
    - Adds: background_clauses (raw BG CNF for violation checking)
    - Adds: constraint_clauses, negated_clauses (raw CNF per assumption ID)
    - Adds: feature_ids, id_to_feature (feature mapping)
    """
    bias: set[int]              # Remaining bias assumption IDs
    learned_kb: list[int]       # Learned constraint assumption IDs
    background_clauses: list[list[int]]  # Raw BG CNF (no guards) - extracted from Oracle
    feature_ids: dict[str, int] # Feature name → SAT var ID
    id_to_feature: dict[int, str] # SAT var ID → feature name
    constraint_clauses: dict[int, list[list[int]]]  # constraint_id → raw clauses
    negated_clauses: dict[int, list[list[int]]]  # constraint_id → negated clauses
```

#### explanation/operations/ — Diagnosis Algorithms

**Solver Abstraction Layer** (commit 260228):
- `ConsistencyChecker(ABC)` — Abstract interface with two key methods:
  - `is_consistent(set_c: List[int]) -> bool` — Check CNF formula satisfiability
  - `get_model() -> Optional[List[int]]` — Extract SAT assignment after satisfiable check
  - Both implementations use assumption-based data (set_c as enabled assumptions)
- `IncrementalPySATChecker` — Persistent solver (~50x faster, ideal for ConGen)
  - Computes delta: disabled assumptions = all_assumptions \ set_c
  - Calls solver with negated disabled assumptions
  - `get_model()` returns solver's current model
- `NonIncrementalPySATChecker` — Fresh solver per call (baseline for comparison)
  - Builds CNF from set_kb and set_c clauses each time
  - `get_model()` returns None (no persistent state)
- `CheckerFactory.create_from_model(model)` — Factory for creating checker instances based on model's `use_incremental` flag

**Diagnosis Algorithms**: FastDiag (minimal diagnosis via HSDAG), QuickXPlain (minimal conflicts), KBDiag (kernel-based, used by ACQMSS), WipeOutR (domain-specific), HSDAG (tree optimization)

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
- Learns constraint KB in one pass (GenerateNE called by `ConGenModel.prepare()`, then ACQMSS → REDUCE)
- **ConGenModel**: Pure data container (bias + solver config). Oracle injected at `prepare()` time.
- **Preparation**: `model.prepare(oracle, positive_examples, negative_examples)` generates NE and populates `ConGenTask` (assumption-based).
- **Reusable**: Build once, prepare multiple times per fold for cross-validation without rebuilding.
- ConGenModel satisfies CheckerModel protocol (`get_kb()`, `get_assumptions()`, solver config)
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
    ├─→ [__init__] ConGenModelBuilder.from_bias(bias_path)
    │   ├─ .with_oracle(oracle)          # Required for build()
    │   ├─ .use_incremental(True/False)
    │   └─ .build() → ConGenModel
    │       ├─ [BUILD TIME] Compute negation: bias constraints → negated_constraint_map (Tseitin, idempotent)
    │       ├─ Store next_available_id (final tseitin var) in model
    │       └─ No auto-prepare (for CV reuse pattern)
    │
    ├─→ [__init__] FeatureModelOracle.from(fm_path)
    │   └─ Builds FMOracleModel with assumption-guarded FM clauses
    │
    ├─→ [run] ConGenModel.prepare(oracle, pos_examples, neg_examples)
    │   ├─ [PREPARE TIME] GenerateNE: E- → NE (assumption IDs) [internal to prepare()]
    │   ├─ [PREPARE TIME] Read negated_constraint_map (built at build time, idempotent read)
    │   └─ ConGenTaskPreparation: Create unified task from bias + NE
    │       ├─ Use model.next_available_id (from build time)
    │       └─ set_kb: CNF with assumption literals
    │       └─ set_c: Bias assumption IDs (will be shuffled after prepare)
    │       └─ set_tc: E+ assumption IDs
    │       └─ set_neg_tv: NE assumption IDs (populated by GenerateNE)
    │
    ├─→ [run] Shuffle bias iteration order (if shuffle_seed provided)
    │   └─ random.Random(seed).shuffle(task.set_c)
    │
    ├─→ [run] CheckerFactory.create_from_model(model)
    │   └─ Returns Incremental or NonIncremental checker
    │
    └─→ [run] ConGen Algorithm (mode-agnostic)
        ├─ acquire(set_b, set_bg, set_tc, set_neg_tv, negation_map, ...)
        ├─ ACQMSS: Bias (set_c) → MSS via KBDiag
        └─ REDUCE: MSS → KB (assumption IDs)

Result: CONGENResult (KB constraint names + assumption IDs)
    └─ Compare against ground truth (Bias)
        └─ Accuracy/Precision/Recall metrics
```

**Key Changes** (commit 260228 - unified shuffle-after-prepare):
- **Build-time Negation**: ConGenModelBuilder.build() computes negation at model construction (idempotent)
- **Prepare is Idempotent**: ConGenModel.prepare() no longer writes negated_constraint_map; only reads from model
- **Shuffle After Prepare**: Both runners shuffle task.set_c AFTER prepare(), not before (enables CV reuse)
- **next_available_id Stored**: Model stores tseitin var offset for reuse across multiple prepare() calls
- **ConGenModel**: Pure data container (no FM fields). Build once, prepare multiple times per fold.
- **Oracle**: Created once in __init__, passed to build() and prepare(). Enables CV reuse without rebuild.
- **GenerateNE**: Now internal to prepare() (callers no longer invoke directly).
- **Mode-Agnostic Design**: ConGen, ACQMSS, REDUCE contain no solver-mode branching.

### QuAcq Interactive/Batch Flow (Paper-Aligned with oracle.is_valid())

**Architecture** (commit 260228 - unified shuffle-after-prepare):
```
Feature Model + Bias + Oracle (required for both modes)
    ├─→ [__init__] QuAcqModelBuilder.from_bias(bias_path)
    │   ├─ .with_oracle(oracle)          # Required
    │   ├─ .use_incremental(True/False)  # Optional
    │   └─ .build()
    │       ├─ [BUILD TIME] Compute negation: bias constraints → negated_constraint_map (Tseitin)
    │       ├─ Store next_available_id (final tseitin var) in model
    │       └─ Auto-prepare with configured oracle (initial preparation at build time)
    │
    ├─→ [run] QuAcqModel.prepare(oracle) - fresh task per run
    │   └─ QuAcqTaskPreparation.prepare(model, oracle) creates QuAcqTask
    │       ├─ [PREPARE TIME] Read negated_constraint_map (built at build time, idempotent read)
    │       ├─ Inherits from DiagnosisTask: set_kb, assumptions, negation_map, set_b, set_c
    │       ├─ Copy BG data from Oracle (Parts 1-3) → set_b (assumption IDs)
    │       ├─ Store raw BG clauses (no guards) → background_clauses
    │       ├─ Use negated forms from model (not recomputing Tseitin)
    │       ├─ Assign assumption IDs (Part 5: paired original+negated)
    │       ├─ Store raw clauses per assumption ID
    │       │   ├─ constraint_clauses: assumption_id → raw CNF
    │       │   └─ negated_clauses: assumption_id → negated CNF (from model.negated_constraint_map)
    │       └─ QuAcqTask ready (bias: Set[int], learned_kb: List[int], inherited fields)
    │
    ├─→ [run] Shuffle bias iteration order (if shuffle_seed provided)
    │   └─ random.Random(seed).shuffle(task.set_c)
    │
    └─→ [run] QuAcq Algorithm (oracle or example mode, both use oracle.is_valid())
        ├─ Oracle mode: QuAcq.learn(task, oracle_mode='automated'/'interactive')
        │   └─ GenerateQuery → oracle.is_valid() → Update KB with assumption IDs
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

**Key Changes** (commit 260228 - unified shuffle-after-prepare):
- **Build-time Negation**: QuAcqModelBuilder.build() computes negation (idempotent, like ConGen)
- **Per-run Prepare**: model.prepare(oracle) refreshes task for each run (new assumption IDs per run)
- **Shuffle After Prepare**: Shuffle task.set_c AFTER prepare(), matching ConGen pattern
- **next_available_id Stored**: Model stores tseitin var offset for reuse across multiple prepare() calls
- **Idempotent Negation Maps**: Both prepare() calls read negated_constraint_map (never write to it)
- **Unified Pattern**: ConGen and QuAcq follow identical lifecycle (build-once → prepare+shuffle per run)

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
