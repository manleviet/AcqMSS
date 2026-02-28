# AcqMSS Codebase Summary

**Total Python Code**: ~21,300 lines across ~99 files (consolidated from ~104 files after QuAcq file mergers)
**Main Packages**: conacq (~9,700 LOC) + explanation (~4,600 LOC) + apps (~3,025 LOC) + tests (~3,745 LOC)
**Last Updated**: 2026-02-28 (QuAcqTask cleanup: pure data container, DescriptionProvider removed from learn())

## Package Structure

### conacq/ — Constraint Acquisition Algorithms (~9,900 LOC)

Core acquisition logic organized into seven sub-packages:

#### conacq/algorithms/ — Acquisition Algorithms (~2,845 LOC, 16 files)

Primary constraint discovery algorithms:

| File | LOC | Purpose |
|------|-----|---------|
| `congen.py` | 228 | ConGen orchestration (direct params, no task object) |
| `acqmss.py` | 104 | ACQMSS: divide-and-conquer MSS finding |
| `reduce.py` | 155 | REDUCE: redundancy elimination via consistency checking |
| `generate_ne.py` | 193 | GenerateNE: negated example generation (internal to ConGenModel.prepare()) |
| `task_preparation.py` | 435 | Task hierarchy (DiagnosisTask → TestCaseTask → ConGenTask) + unified prep |
| `congen_model.py` | 186 | ConGenModel - pure data container (bias + solver config), oracle-agnostic. Stores negated_constraint_map + next_available_id (computed at build time). Call prepare(oracle) before use. |
| `congen_model_builder.py` | 157 | ConGenModelBuilder - fluent builder pattern. Requires oracle. build() computes negation (idempotent), auto-prepares when oracle+examples set. Returns unprepared model otherwise. |
| (Total: 1,331 LOC for main algorithms) |
| (Subtotal: 1,439 LOC including both paradigm-specific builders) |

**QuAcq Sub-package** (`quacq/`, 10 files, ~2,000 LOC):

**Assumption-Based Learning (Unified with ConGen, Paper-Aligned Queries, DI Pattern)**:

| File | LOC | Purpose |
|------|-----|---------|
| `quacq.py` | 439 | QuAcq algorithm + QuAcqResult (DI pattern, mode dispatch, direct param learn()) |
| `sat_utils.py` | 93 | Standalone SAT utilities: config_to_assumptions, violates_clauses, get_kb_clauses — NEW |
| `quacq_model.py` | ~93 | QuAcqModel: dual to ConGenModel for interactive learning. Stores negated_constraint_map + next_available_id (computed at build time). |
| `quacq_model_builder.py` | ~74 | QuAcqModelBuilder: fluent builder, requires oracle. build() computes negation (idempotent), auto-prepares on build(). |
| `task_preparation.py` | ~123 | QuAcqTask + QuAcqTaskPreparation: pure data container + preparation |
| `_task_compat.py` | ~39 | Shared duck-typing helpers: get_clause_map(), get_negated_clauses(), get_bg_clauses() |
| `findc.py` | 208 | FindC (IJCAI13 Algorithm 3): oracle.is_valid() + DiscriminatingGenerator(C_L[Y]) |
| `findscope.py` | 134 | FindScope (IJCAI13 Algorithm 2): oracle.is_valid() partial queries, no SAT |
| `discriminating_generator.py` | 66 | DiscriminatingGenerator: Paper Algorithm 3 line 5, C_L[Y] + BG, not FM |
| `__init__.py` | ~60 | Package exports |

**Changes (This Session - QuAcqTask Cleanup + DI Refactor - commits 260228-e2b68c8)**:
- ✅ **Cleaned QuAcqTask** — Removed 7 dead methods (~80 LOC), now pure data container (fields only)
- ✅ **Moved behavior to sat_utils.py** — Standalone functions: config_to_assumptions, violates_clauses, get_kb_clauses
- ✅ **Removed DescriptionProvider** from QuAcq.learn() — Moved to runner layer (QuAcqRunner.resolve_kb())
- ✅ Refactored `QuAcq.__init__()` — DI pattern (oracle, query_provider, discriminating_generator, profiler)
- ✅ Added `QuAcq.for_oracle()` factory — discrim_gen required
- ✅ Added `QuAcq.for_examples()` factory — query_provider required
- ✅ Refactored `QuAcq.learn()` — Direct parameter signature (set_c, set_b, ..., mode, max_queries); runner resolves names
- ✅ learn() supports 3 modes: 'oracle', 'example_only', 'example_first' via single parameter

**Previous Session Changes (FindScope/FindC Refactoring - commit 260227)**:
- ✅ Added `discriminating_generator.py` — DiscriminatingGenerator (Paper Algorithm 3 line 5)
- ✅ Updated `findscope.py` — oracle.is_valid() instead of SAT-based consistency check
- ✅ Updated `findc.py` — Pool-based narrowing via oracle.is_valid()

**Previous Session Changes**:
- ✅ Merged `QuAcqTaskPreparation` into `task_preparation.py` (was `quacq_task.py`, renamed)
- ✅ Merged `QuAcqResult` into `quacq.py` (deleted `result.py`)
- ✅ Deleted `task.py` (`InteractiveTask`) — use `QuAcqTask` (assumes int IDs)
- ✅ Deleted `learner.py` (`InteractiveLearner`) — use `QuAcqModelBuilder` path
- ✅ Simplified `_task_compat.py` (removed InteractiveTask fallback branches)

#### conacq/bias/ — Bias (Constraint) Generation (~1,176 LOC, 6 files)

Feature model to constraint conversion pipeline:

| File | LOC | Purpose |
|------|-----|---------|
| `bias_generator.py` | 275 | Extract constraints from feature model (hierarchical + cross-tree) |
| `bias_io.py` | 222 | JSON/YAML I/O for constraints and configurations |
| `config_loader.py` | 203 | TOML/YAML configuration loading for bias generation |
| `clause_generator.py` | 199 | Convert FM constraints to CNF clauses |
| `data_structures.py` | 160 | Constraint, BiasConfig, ConstraintType enumerations |

#### conacq/example_generators/ — Example & Query Generation (~850 LOC, 6 files)

Sampling strategies and query generation for learning:

| File | LOC | Purpose |
|------|-----|---------|
| `query_provider.py` | ~320 | QueryProvider: unified query/example provision (strategies: generate_from_pool, generate_from_sat, generate) |
| `base.py` | 245 | Base strategy class. Calls oracle.complete_configuration() (no pysat.solvers imports) |
| `random_sampling.py` | 245 | RS sampling: uniformly random configuration selection |
| `feature_frequency.py` | 197 | FF: feature frequency-based sampling. Calls oracle.complete_configuration() |
| `nwise_coverage.py` | 136 | 2-COV strategy: n-wise pairwise coverage |
| `__init__.py` | ~1 | Package exports with QueryProvider |

#### conacq/examples/ — Example and Query History Conversion (~120 LOC, 4 files)

Utilities for converting query histories and managing example formats:

| File | LOC | Purpose |
|------|-----|---------|
| `query_converter.py` | 64 | Convert QuAcqRunner query_history to ExampleSet or assignment lists for ConGen |
| `data_structures.py` | ~30 | Example, ExampleSet, ExampleType dataclasses |
| `io_utils.py` | ~25 | I/O utilities for example persistence |
| `__init__.py` | ~1 | Package exports |

**Oracle Sub-package** (`conacq/oracle/`, 10 files, ~1,000 LOC):

| File | LOC | Purpose |
|------|-----|---------|
| `base.py` | 47 | Oracle ABC: minimal interface. Only abstract: `is_valid(assignments)`. Concrete: `ask()` alias. |
| `fm_data.py` | 25 | FMData: frozen dataclass for FM metadata (features, feature_ids, root_feature, num_constraints, next_available_id). Decouples metadata from oracle. |
| `bg_data.py` | 27 | BGData: frozen dataclass for background knowledge root constraint + negation pair. Extracted post-preparation from Oracle for ConGen consumption. Enables assumption ID allocation without overlap. |
| `fm_oracle.py` | 200+ | FeatureModelOracle: FM oracle implementation. ABC methods: `is_valid()`, `ask()`. FM-specific: `get_fm_data()`, `get_features()`, `get_feature_ids()`, `get_root_feature()`, `get_num_constraints()`, `get_next_available_id()`, `complete_configuration()`, `get_cnf_clauses()`, `get_constraint_descriptions()`. |
| `fm_oracle_model.py` | 280+ | FMOracleModel: assumption-guarded FM clauses, CheckerModel protocol. Exposes `bg_data` property + `get_bg_data()` for ConGen to extract root BG constraint. |
| `constraint_description.py` | 120 | CTC description extraction from FM (requires/excludes/hierarchical) |
| `user_prompt.py` | 100+ | UserPromptOracle: interactive oracle. ABC methods: `is_valid()`, `ask()`. Raises NotImplementedError for FM-specific methods. |
| `cached.py` | 80+ | CachedOracle: transparent caching wrapper. Caches `is_valid()`, delegates FM methods to base oracle. |
| `extractor.py` | 100+ | OracleData / GroundTruthData: extracted oracle data for evaluation (FM reader, no solver) |
| `__init__.py` | 1 | Package exports |

**Critical Implementation Details**:

1. **Oracle ABC**: Minimal interface with only `is_valid()` abstract method. FM-specific methods live on concrete implementations (e.g., `FeatureModelOracle.get_fm_data()`). Avoids coupling callers to FM-specific APIs.

2. **FMData Dataclass**: Frozen, immutable container for FM metadata created by `FeatureModelOracle.get_fm_data()`. Passed explicitly to callers to decouple FM metadata from oracle instance. Used by example generators, task preparation, etc.

3. **FeatureModelOracle Architecture**: 
   - ABC methods (all oracles): `is_valid()`, `ask()`
   - FM-specific extensions (FeatureModelOracle only): `get_fm_data()`, `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()`, `get_root_feature()`, `get_num_constraints()`, `get_next_available_id()`, `get_constraint_descriptions()`
   - Delegates to `FMOracleModel` for SAT-based consistency checking

4. **FMOracleModel Architecture**: FM clauses stored directly in `set_kb` (always active). Feature assignments become assumption-guarded unit clauses: `[-a_pos_i, fid]` and `[-a_neg_i, -fid]`. Satisfies `CheckerModel` protocol for `CheckerFactory` integration. Prepared via `OracleTaskPreparation` class. Exposes `bg_data` property (lazy-computed) and `get_bg_data()` method for ConGen to extract root background constraint pair post-preparation.

5. **Feature ID Consistency**: The `FMOracleModel.variables` uses flamapy's variable mapping (tree traversal order) stored in `FmToPysat.variables` as the authoritative source. This ensures feature_ids match SAT variable IDs in CNF clauses. Using alphabetical sorting would cause critical mismatch with clause variable references.

6. **Example Generator Refactoring**: Now typed as `FeatureModelOracle` (not generic `Oracle`). Use `oracle.complete_configuration()` for generating valid configs instead of direct SAT solver calls. Decouples generators from solver details.

7. **Assumption-Based Representation**: All checkers (Incremental and NonIncremental) use identical assumption-based data: `List[int]` for assumptions, used uniformly in algorithms (no `if is_incremental` branching).

8. **GenerateNE Design**: Now invoked internally by `ConGenModel.prepare()`. Results simplified to `NEResult(new_clauses, set_neg_tv, next_available_id)`. Merged via inline code in `ConGenModel.prepare()` (no longer caller-invoked).

9. **CheckerModel Protocol**: `FMOracleModel` and `ConGenModel` implement `get_kb()`, `get_assumptions()`, `use_incremental` for compatibility with `CheckerFactory`.

10. **Builder Pattern** (commit 260227): ConGenModelBuilder encapsulates bias loading and configuration. Requires oracle via `with_oracle()` (needed for build-time negation computation). `build()` computes negation (idempotent) and auto-prepares when `with_examples()` is also set; returns unprepared model otherwise. Call `model.prepare(oracle, examples)` manually for CV reuse patterns.

11. **Oracle Required at Build Time**: Oracle passed to `with_oracle()` for negation computation in `build()`. Same oracle can be passed to `model.prepare()` for example preparation. Enables cross-validation reuse without rebuilding model.

#### conacq/runners/ — Execution Runners (~480 LOC, 4 files)

Pipeline runners with unified lifecycle (build-once/run-many/cleanup-once):

| File | LOC | Purpose |
|------|-----|---------|
| `base_runner.py` | ~110 | BaseRunner ABC + BaseRunResult (9 shared fields for both runners) |
| `congen_runner.py` | 235 | ConGenRunner: CONGEN pipeline with profiling + bias shuffle seed support |
| `quacq_runner.py` | 197 | QuAcqRunner: QuAcq dual-mode (oracle + example modes) |
| `__init__.py` | ~18 | Package exports |

**BaseRunner Architecture** (NEW):
- ABC defining lifecycle: `__init__` (oracle + model built once) → `run()` (may be called multiple times) → `cleanup()` (release resources)
- Oracle and model created once in `__init__`, reused across all `run()` calls
- Enforces consistent initialization across ConGen and QuAcq runners
- `cleanup()` method releases oracle resources

**BaseRunResult** (NEW):
- 9 shared fields: `kb_constraints`, `kb_clauses`, `bg_clauses`, `n_bias`, `n_kb`, `runtime_ms`, `consistency_checks`, `memory_peak_mb`, `profiler_data`
- Both `ConGenRunResult` and `QuAcqRunResult` inherit from BaseRunResult
- Provides `get_performance_metrics()` (with `n_mss=None` default; override in ConGenRunResult for actual MSS count)

**ConGenRunner** (inherits BaseRunner):
- File-path-based constructor: `ConGenRunner(bias_path, fm_path, solver_name='glucose4')`
- `__init__`: Builds model once via ConGenModelBuilder (requires oracle for negation computation)
- `run(positive_examples, negative_examples, shuffle_seed=None)` returns `ConGenRunResult` with MSS count
  - Per-fold lifecycle: prepare() → shuffle set_c after prepare() → run ConGen
  - Supports bias shuffle seed for reproducibility
  - Oracle reused across folds (no rebuild)

**QuAcqRunner** (inherits BaseRunner):
- File-path-based constructor: `QuAcqRunner(bias_path, fm_path, ...)`
- `__init__`: Builds model once via QuAcqModelBuilder (requires oracle for negation computation, auto-prepares)
- Per-run lifecycle: re-prepare() → shuffle set_c after prepare() → dispatch to oracle/example mode
- Dual-mode `run(mode, ...)`: dispatches to oracle ('automated'/'interactive') or example ('example_only'/'example_first') paths
- Returns `QuAcqRunResult` with KB constraints, metrics, and profiler data

**Unified Shuffle Pattern** (NEW - commit 260228):
- Both runners now follow identical shuffle lifecycle: prepare() → shuffle set_c → run algorithm
- Shuffle seed controls bias iteration order after preparation (not before)
- Enables reproducible CV experiments without model rebuild

#### conacq/eval/ — Evaluation Framework (~2,760 LOC, 14 files)

Cross-validation, accuracy metrics, unified CV output, and QuAcq->ConGen progressive evaluation:

| File | LOC | Purpose |
|------|-----|---------|
| `cross_validation.py` | 504 | n-fold CV (CONGEN + Interactive) with pre-generated fold support |
| `interactive_metrics.py` | 391 | QuAcq-specific metrics (query count, convergence) |
| `kb_comparator.py` | 267 | Compare learned KB vs GroundTruth FM. Strategies: description, clause, semantic (SAT-based equivalence) |
| `report.py` | 281 | Generate CSV/JSON/LaTeX/Markdown reports; unified CV dict builder (`generate_unified_cv_dict`, `_enrich_constraints`) |
| `accuracy.py` | 170 | Accuracy/precision/recall/F1 calculation |
| `performance_metrics.py` | 140 | Runtime, SAT checks, memory metrics |
| `config.py` | ~120 | Shared pipeline config utilities (ModelConfig, load_pipeline_config, parse_models, find_kb_files, find_cv_files) |
| `folds.py` | 145 | Shared CV fold generation/save/load for fair comparison |
| `result_loader.py` | 84 | Load evaluation results; added `ConGenResultData.from_dict()` classmethod |
| `oracle_extractor.py` | 102 | Extract oracle data for interactive learning |
| `semantic_equivalence.py` | 111 | SAT-based bidirectional entailment checker (KB ≡ C_T equivalence) |
| `progressive_evaluation.py` | 212 | ProgressiveEvaluator engine: run ConGen at query-budget checkpoints, compare vs ground truth |

### explanation/ — SAT Solver Infrastructure (~6,100 LOC, ~35 files)

Diagnosis algorithms and SAT model abstraction:

#### explanation/models/ — Diagnosis Models (~1,403 LOC, 5 files)

SAT model representation and construction:

| File | LOC | Purpose |
|------|-----|---------|
| `task_preparation.py` | 750 | Unified DiagnosisTaskPreparation, TestCaseTaskPreparation, factory classes |
| `diagnosis_model_builder.py` | 300 | Builder pattern: construct DiagnosisModel with configuration |
| `pysat_diagnosis_model.py` | 255 | DiagnosisModel: SAT instance + metadata (clauses, assumptions) |
| `testsuite.py` | 75 | TestSuite: holds test cases + their configurations |

#### explanation/operations/ — SAT Operations (~4,405 LOC, ~25 files)

Diagnosis algorithm implementations and SAT abstractions:

**Core Algorithm Files**:

| File | LOC | Purpose |
|------|-----|---------|
| `profiler.py` | 800 | Profiling infrastructure: decorator-based timing, call counting |
| `checker.py` | 450 | ConsistencyChecker ABC + implementations (both use assumption-based data; immutable) |
| `hsdag.py` | 350 | HSDAG tree search: optimization for multiple diagnoses/conflicts |
| `pysat_explanation_builder.py` | 330 | Builder for diagnosis operations (FastDiag, QuickXPlain, KBDiag) |
| `pysat_abstract_explanation.py` | 250 | Template method base for diagnosis operations |

**Diagnosis Algorithm Implementations** (`algorithms/` subdirectory, ~2,000 LOC):

| File | LOC | Purpose |
|------|-----|---------|
| `algorithms/fastdiag.py` | 85 | FastDiag: breadth-first minimal diagnosis finding |
| `algorithms/fastdiagp.py` | 150 | FastDiagP: parallel FastDiag variant |
| `algorithms/quickxplain.py` | 80 | QuickXPlain: minimal conflict finding |
| `algorithms/kbdiag.py` | 100 | KBDiag: kernel-based diagnosis |
| `algorithms/wipeoutr_fm.py` | 90 | WipeOutR_FM: feature model variant |
| `algorithms/wipeoutr_t.py` | 110 | WipeOutR_T: test case variant |
| `algorithms/utils.py` | 120 | split, diff, negate_cnf_tseitin utilities |

**Operation Wrappers** (pysat_*_*.py files, 10 files, ~1,800 LOC):

Each wraps diagnosis algorithms for specific use cases (diagnosis vs conflict, PySAT vs SAT4J, various test modes).

#### explanation/transformations/ — Model Converters (~292 LOC, 5 files)

Feature model to SAT conversion:

| File | LOC | Purpose |
|------|-----|---------|
| `fm_to_diag_pysat.py` | 113 | Feature model → DiagnosisModel (PySAT) |
| `dimacs_to_diag_pysat.py` | 81 | DIMACS CNF → DiagnosisModel |
| `dimacs_to_configuration.py` | 59 | DIMACS variable assignments → Configuration |
| `testsuite_reader.py` | 42 | Read test suites from files |

### apps/ — Standalone Applications (~3,025 LOC, 11 files)

CLI applications for constraint acquisition pipeline. Uses `python -m apps.X` invocation pattern.

| File | LOC | Purpose |
|-----|-----|---------|
| `__init__.py` | ~1 | Package marker (enables python -m invocation) |
| `extract_results.py` | 621 | Post-process results, generate Markdown/LaTeX reports (reads embedded evaluation from unified CV format or falls back to external eval files) |
| `generate_bias_config.py` | 536 | Feature model → YAML bias configuration |
| `generate_examples.py` | 325 | Generate E+/E- examples with sampling strategies |
| `generate_bias_files.py` | 302 | YAML bias config → JSON/CNF files |
| `run_congen.py` | 217 | Execute CONGEN learning pipeline (dev/debug tool) |
| `run_cv.py` | ~420 | Unified n-fold CV for ConGen and Interactive; outputs single JSON per (model x strategy x mode) |
| `run_quacq.py` | ~350 | Pure QuAcq learning → KB files (no CV, no evaluation) |
| `run_compare.py` | ~270 | Config mode: reads/enriches unified CV JSONs (idempotent write-back); KB mode: compare learned KB vs GroundTruth FM |
| `run_evaluation.py` | 243 | QuAcq → ConGen pipeline: run QuAcq, feed progressive query subsets to ConGen, compare both KBs vs ground truth |
| `generate_cv_folds.py` | 68 | CLI to pre-generate CV folds for reproducible evaluation |

**Config Files** (`conf/`, 11 TOML files):
- `generate_bias_config.toml` — Bias config generation settings
- `generate_bias_files_config.toml` — Bias JSON/CNF generation settings
- `generate_examples_config.toml` — Example generation settings
- `generate_cv_folds_config.toml` — CV fold generation settings
- `run_congen_config.toml` — Single ConGen run settings
- `run_cv_config.toml` — Unified CV settings (ConGen + Interactive)
- `run_quacq_config.toml` — Interactive-only learning settings
- `run_compare_config.toml` — KB comparison settings
- `run_evaluation_config.toml` — QuAcq → ConGen evaluation pipeline settings
- `extract_results_config.toml` — Results extraction settings
- `test_eval_config.toml` — Test evaluation settings

### tests/ — Test Suite (~3,500+ LOC, 8 files)

Comprehensive test coverage using pytest + @parameterized.expand:

| File | LOC | Purpose |
|------|-----|---------|
| `test_diagnosis.py` | 1,416 | Diagnosis algorithms (FastDiag, QuickXPlain, KBDiag, WipeOutR, HSDAG) |
| `test_quacq.py` | 603 | QuAcq interactive learning (oracle and example modes) |
| `test_evaluation.py` | 474 | Cross-validation and accuracy metric tests |
| `test_profiler.py` | 536 | Profiling infrastructure tests |
| `test_congen.py` | 349 | CONGEN learning tests (passive acquisition) |
| `test_bias_module.py` | 117 | Bias module tests |
| `test_utils.py` | 35 | Utility function tests |

**Key Testing Patterns**:
- **Parameterization**: `@parameterized.expand()` combinations of incremental/non-incremental modes
- **Test Control**: `ENABLED_TESTS` and `ENABLED_PARAMS` dictionaries for selective test execution
- **Profiling Tests**: Measure execution time and solver call counts
- **Mode Coverage**: Tests run in both incremental (persistent solver) and non-incremental (fresh solver) modes

## Data Directories

### data/fms/ — Feature Models (7 models)

Reference UVL feature models for testing and evaluation:

| Model | Features | Constraints | Files |
|-------|----------|-------------|-------|
| REAL-FM-7 IDE | 14 | ~20 | 1 |
| arcade-game | 65 | ~60 | 1 |
| fqa | 179 | ~100 | 1 |
| REAL-FM-4 eshop | 291 | ~150 | 1 |
| busybox-1.18.0 | 854 | ~500 | 1 |
| ea2468 | 1,408 | ~800 | 1 |
| linux-2.6.33.3 | 6,467 | ~10,000 | 1 |

### data/bias-config/ — Bias Configurations

YAML-formatted bias configurations (one per model), generated by `generate_bias_config.py`.

### data/bias/ — Generated Bias Files

Generated constraint files in JSON and CNF formats:
- `{model}.json` — JSON constraint representation
- `{model}.cnf` — DIMACS CNF format
- `{model}_stats.json` — Constraint statistics

### data/examples/ — Generated Examples

Positive/negative example sets (naming: `{model}_{strategy}_{multiplier}.json`):
- Strategies: `RS` (random sampling), `FF` (feature frequency), `2COV` (2-coverage)
- Multipliers: 25, 50, 75, 100, 150 (percentage of valid configurations to sample)

### data/results/ — Evaluation Results

CONGEN and QuAcq learning results:
- `{model}_CONGEN.json` — CONGEN result
- `{model}_CV_{fold}.json` — Cross-validation folds
- `{model}_interactive.json` — QuAcq result
- `{model}_profile.json` — Execution profiling data

## Dependencies

### Core Runtime
- **python-sat** (PySAT) — SAT solver interface (glucose4, minisat, lingeling)
- **flamapy** — Feature model parsing and manipulation (UVL format)

### Development & Testing
- **pytest** — Test framework
- **parameterized** — Test parameterization decorator

### Utilities
- **pyyaml** — YAML configuration parsing
- **tomllib** (Python 3.11+) — TOML configuration parsing

### Optional
- **sat4j** — External Java SAT solver (subprocess invocation)

## Key Architectural Patterns

### 1. Builder Pattern
- `DiagnosisModelBuilder` — Construct diagnosis models with configuration
- `PySATExplanationBuilder` — Build diagnosis operations

### 2. Strategy Pattern
- `ConsistencyChecker` ABC with implementations (Incremental, NonIncremental, SAT4J)
- Sampling strategies: `RandomSampling`, `FeatureFrequency`, `TwoCoverage`
- Evaluation strategies: `description`, `clause`

### 3. Template Method
- `PySATAbstractExplanation` — Base for diagnosis algorithms
- Subclasses implement specific algorithms

### 4. Dependency Injection
- Algorithms accept `ConsistencyChecker` as dependency
- Profiler optionally injected for timing/counting
- Mode-agnostic: No `if is_incremental` branching

### 5. Facade Pattern
- `InteractiveLearner` — High-level QuAcq interface
- `CONGENRunner` — High-level CONGEN pipeline
- `Evaluator` — High-level evaluation orchestration

### 6. Builder Pattern
- `ConGenModelBuilder.from_bias()` — Builder-pattern model construction
- Solver instantiation via consistent factories

## Codebase Statistics

| Component | LOC | Files | Avg File Size | Status |
|-----------|-----|-------|---------------|--------|
| conacq/ | ~10,170 | ~53 | ~192 | ✅ Core algorithms (QuAcq unified + eval pipeline + builder) |
| explanation/ | ~4,600 | ~35 | ~131 | ✅ SAT infrastructure |
| apps/ | ~3,300 | 12 | ~275 | ✅ CLI applications (+ run_evaluation.py) |
| tests/ | ~3,745 | 8 | ~468 | ✅ Comprehensive coverage |
| **Total** | **~21,970** | **~108** | **~203** | ✅ **Production ready** |

**Recent Changes** (QuAcqTask Inheritance Refactoring - commit 260227):

**Task Hierarchy Refactoring**:
- **DiagnosisTask** → Base class for both TestCaseTask and QuAcqTask
  - Holds common assumption-based fields: `set_kb`, `assumptions`, `set_b`, `set_c`, `negation_map`
- **TestCaseTask(DiagnosisTask)** → For test case scenarios (used by ConGen preparation)
  - Adds: `set_tc` (E+ assumption IDs), `set_tv` (E- assumption IDs)
- **ConGenTask(TestCaseTask)** → For passive constraint acquisition
  - Adds: `set_neg_tv` (negated example assumption IDs from GenerateNE)
- **QuAcqTask(DiagnosisTask)** → For interactive constraint acquisition (NEW inheritance)
  - Inherits: `set_kb`, `assumptions`, `set_b`, `set_c`, `negation_map` from DiagnosisTask
  - Adds: `bias` (remaining constraint IDs), `learned_kb` (discovered constraints)
  - Adds: `background_clauses` (raw BG CNF for violation checking), `feature_ids`, `id_to_feature`
  - Adds: `constraint_clauses`, `negated_clauses` (raw clause maps by ID)

**Benefits**:
- Eliminates duplicate field definitions across task types
- Clear inheritance hierarchy: DiagnosisTask is single source of truth for shared fields
- QuAcqTask focused on interactive-specific state (bias, learned_kb)
- Consistent field naming: `set_b` (assumption IDs) inherited from DiagnosisTask

**Shared Duck-Typing Helpers** (`_task_compat.py`):
- `get_clause_map(task)` — Normalize constraint→clauses mapping
- `get_negated_clauses(task, c_id)` — Normalize negated clause lookup
- `get_bg_clauses(task)` — Extract raw BG clauses from either task type

**Architecture Unification** (earlier):
- QuAcq now uses **int assumption IDs** (identical to ConGen)
- `QuAcqRunner` dispatches to oracle or example modes via `run(mode)`
- `QuAcqResult` has dual representation: kb_constraints (str names) + kb_assumption_ids (int IDs)
- Both QuAcqTask and ConGenTask use same negation_map and assumption layout
- Shared REDUCE algorithm reuse — no more `_reduce_kb()` conversion layer

**Deprecated Classes** (Backward compatible):
- `InteractiveTask` → Use `QuAcqTask` (string-based names replaced by assumption IDs)
- `InteractiveLearner` → Use `QuAcqModel` + `QuAcq` (clearer architecture)

**Earlier Changes** (Oracle Interface Refactoring - commit c978d66):

**Oracle ABC Slimmed**:
- Removed `get_features()`, `get_feature_ids()`, `complete_configuration()`, `get_cnf_clauses()` from Oracle ABC
- Only abstract methods: `is_valid(assignments)` (membership query)
- Concrete method: `ask()` (alias for `is_valid()`)
- All FM-specific methods moved to `FeatureModelOracle` implementation

**FMData Introduced**:
- New frozen dataclass `acqmss/oracle/fm_data.py` — FM metadata container
- Fields: `features`, `feature_ids`, `root_feature`, `num_constraints`, `next_available_id`
- Created by `FeatureModelOracle.get_fm_data()`, passed explicitly to decouple callers

**FeatureModelOracle Extended**:
- New method: `get_fm_data() -> FMData` — Create frozen metadata snapshot
- Concrete methods: `get_features()`, `get_feature_ids()`, `get_root_feature()`, `get_num_constraints()`, `get_next_available_id()`, `complete_configuration()`, `get_cnf_clauses()`, `get_constraint_descriptions()`
- `complete_configuration()` implements SAT-based config completion with fallback
- `get_cnf_clauses()` returns raw FM CNF (no assumption guards)

**Example Generators Refactored**:
- Typed as `FeatureModelOracle` (not generic `Oracle`)
- Use `oracle.complete_configuration()` instead of direct SAT solver calls
- Removed pysat.solvers imports from `base.py` and `feature_frequency.py`
- Decoupled from solver implementation details

**UserPromptOracle & CachedOracle Updated**:
- Simplified to implement only Oracle ABC (`is_valid()`, `ask()`)
- Raise `NotImplementedError` for FM-specific methods (or delegate to base)
- `CachedOracle` caches `is_valid()` results, delegates FM methods to base oracle

**OracleData Renamed**:
- Old name: `OracleData`
- New name: `GroundTruthData` (reflects FM-reading behavior)
- Backward-compatible alias: `OracleData` still available

**InteractiveLearner Updated**:
- `_build_task_from_bias()` now takes `fm_data: FMData` instead of oracle
- Receives FM metadata explicitly, not tied to oracle instance

**ConGenTaskPreparation Updated**:
- `prepare()` now takes `(model, fm_data, oracle)` signature
- `fm_data` for metadata (FMData), `oracle` for `GenerateNE` and config completion
- Separates concerns: metadata vs. SAT queries
- No longer uses `_prepare_bg()` method (refactored to use BG data extraction)

**BG Data Extraction** (new):
- New frozen dataclass `BGData` in `conacq/oracle/bg_data.py` — Root BG constraint pair + metadata
- Fields: `set_kb`, `assumptions` (root_id, negated_root_id), `negation_map`, `descriptions`, `next_available_id`
- FMOracleModel now exposes `bg_data` property (lazy-computed) and `get_bg_data()` method
- ConGenTaskPreparation calls `oracle.get_bg_data()` to extract root constraint post-preparation
- Enables clean separation: Oracle owns Parts 1-4 of assumption ID layout; ConGen starts allocation at `next_available_id`

**Build-Time Negation** (commit 260227):
- ConGenModelBuilder.build() now computes negation (idempotent) before prepare()
- ConGenModel stores negated_constraint_map + next_available_id (populated at build time)
- ConGenModel.prepare() is idempotent: reads negated_constraint_map, never writes to it
- QuAcqModelBuilder.build() follows same pattern: negation at build time

**Earlier Changes** (still in place):
- ConGenModel pure data container (bias + solver config only + negation maps)
- ConGenModel.prepare(oracle, pos_examples, neg_examples) - reads negation maps, doesn't write
- ConGenModelBuilder requires oracle (new requirement) for build-time negation
- GenerateNE internalized to ConGenModel.prepare()
- FMOracleModel with assumption-guarded clauses
- Cross-validation reuse pattern (build once, prepare multiple times)

## Build & Test Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests (both modes)
PYTHONPATH=. pytest tests/ -v

# Run specific test file
PYTHONPATH=. pytest tests/test_diagnosis.py -v

# Run tests matching pattern
PYTHONPATH=. pytest tests/ -k "fastdiag" -v

# Run single test with full profiling
PYTHONPATH=. pytest tests/test_diagnosis.py::test_fastdiag -v -s
```

## Main Applications

**Unified CV Pipeline** (replaces 45+ file outputs with single JSON per experiment):
1. `run_cv.py` — Unified n-fold CV for ConGen and/or Interactive → single JSON per (model x strategy x mode)
2. `run_compare.py` (config mode) — Reads unified CV JSONs, compares folds, writes enriched evaluation back
3. `extract_results.py` — Post-process unified CV JSONs, generate final reports with fold metrics
4. `run_congen.py` / `run_quacq.py` — Single-run tools for debugging
5. `run_compare.py` (KB mode) — Compare single learned KB vs GroundTruth FM

**QuAcq → ConGen Evaluation Pipeline** (NEW):
1. `run_evaluation.py` — Progressive evaluation: run QuAcq, feed query subsets to ConGen at checkpoints (10%, 25%, 50%, 75%, 100%), compare both KBs vs ground truth

```bash
# Generate bias files from feature model
python -m apps.generate_bias_config data/fms/model.uvl -v
python -m apps.generate_bias_files data/bias-config/model.yaml

# Generate test examples
python -m apps.generate_examples apps/conf/generate_examples_config.toml

# Run unified cross-validation (ConGen + Interactive)
python -m apps.run_cv apps/conf/run_cv_config.toml -v

# Run pure QuAcq learning (no CV, no evaluation)
python -m apps.run_quacq apps/conf/run_quacq_config.toml -v
python -m apps.run_quacq apps/conf/run_quacq_config.toml --interactive

# Compare learned KB against oracle FM
python -m apps.run_compare --kb data/results/model_kb.json --bias data/bias/model-bias.json --oracle data/fms/model.uvl -v

# Single-run ConGen (debug tool)
python -m apps.run_congen apps/conf/run_congen_config.toml -v
python -m apps.run_congen apps/conf/run_congen_config.toml --non-incremental

# Extract and generate final reports (includes fold metrics)
python -m apps.extract_results <results_dir> -v

# Run QuAcq -> ConGen evaluation pipeline (progressive checkpoints)
python -m apps.run_evaluation apps/conf/run_evaluation_config.toml -v
```

## File Size Analysis

Largest files (by line count):
- `explanation/operations/profiler.py` — 1,192 LOC (profiling infrastructure)
- `explanation/models/task_preparation.py` — 952 LOC (SAT task setup)
- `tests/test_diagnosis.py` — 1,416 LOC (diagnosis tests)
- `apps/extract_results.py` — 621 LOC (result processing, DRY-refactored from 1,139 LOC)

Most files keep to ~200 LOC for maintainability, except specialized components.

## Next Steps for Documentation

See:
- **project-overview-pdr.md** — Goals, requirements, success criteria
- **code-standards.md** — Naming, patterns, testing conventions
- **system-architecture.md** — Data flow, integration points, design decisions
- **project-roadmap.md** — Development phases and status
