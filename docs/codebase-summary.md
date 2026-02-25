# AcqMSS Codebase Summary

**Total Python Code**: ~20,900 lines across ~101 files
**Main Packages**: conacq (~9,272 LOC) + explanation (~4,600 LOC) + apps (~3,300 LOC) + tests (~3,745 LOC)
**Last Updated**: 2026-02-18

## Package Structure

### conacq/ — Constraint Acquisition Algorithms (~9,900 LOC)

Core acquisition logic organized into seven sub-packages:

#### conacq/algorithms/ — Acquisition Algorithms (~2,771 LOC, 15 files)

Primary constraint discovery algorithms:

| File | LOC | Purpose |
|------|-----|---------|
| `congen.py` | 228 | ConGen orchestration (direct params, no task object) |
| `acqmss.py` | 104 | ACQMSS: divide-and-conquer MSS finding |
| `reduce.py` | 155 | REDUCE: redundancy elimination via consistency checking |
| `generate_ne.py` | 193 | GenerateNE: negated example generation (internal to ConGenModel.prepare()) |
| `task_preparation.py` | 435 | Task hierarchy (DiagnosisTask → TestCaseTask → ConGenTask) + unified prep |
| `congen_model.py` | 186 | ConGenModel - pure data container (bias + solver config), oracle-agnostic. Call prepare(oracle) before use |
| `congen_model_builder.py` | 157 | ConGenModelBuilder - fluent builder pattern. Auto-prepares when oracle+examples set; otherwise returns unprepared model |

**Interactive Sub-package** (`interactive/`, 7 files, ~1,543 LOC):

| File | LOC | Purpose |
|------|-----|---------|
| `quacq.py` | 439 | QuAcq: oracle-based + example-based learning modes |
| `learner.py` | 426 | InteractiveLearner: high-level facade (from_examples(), from_files()) |
| `findc.py` | 208 | FindC (IJCAI13 Algorithm 3): constraint discrimination from scope |
| `task.py` | 137 | Task state, scope helpers, shared utilities (violates_clauses) |
| `result.py` | 137 | InteractiveResult - outcome with metrics |
| `findscope.py` | 134 | FindScope (IJCAI13 Algorithm 2): scope identification via partial queries |
| `__init__.py` | ~60 | Package exports |

#### conacq/bias/ — Bias (Constraint) Generation (~1,176 LOC, 6 files)

Feature model to constraint conversion pipeline:

| File | LOC | Purpose |
|------|-----|---------|
| `bias_generator.py` | 275 | Extract constraints from feature model (hierarchical + cross-tree) |
| `bias_io.py` | 222 | JSON/YAML I/O for constraints and configurations |
| `config_loader.py` | 203 | TOML/YAML configuration loading for bias generation |
| `clause_generator.py` | 199 | Convert FM constraints to CNF clauses |
| `data_structures.py` | 160 | Constraint, BiasConfig, ConstraintType enumerations |

#### conacq/example_generators/ — Example & Query Generation (~1,097 LOC, 7 files)

Sampling strategies, example generation, and query generation for learning:

| File | LOC | Purpose |
|------|-----|---------|
| `query_generator.py` | 262 | QueryGenerator: discriminative query generation (moved from interactive/) |
| `base.py` | 245 | Base strategy class. Calls oracle.complete_configuration() (no pysat.solvers imports) |
| `random_sampling.py` | 245 | RS sampling: uniformly random configuration selection |
| `feature_frequency.py` | 197 | FF: feature frequency-based sampling. Calls oracle.complete_configuration() |
| `nwise_coverage.py` | 136 | 2-COV strategy: n-wise pairwise coverage |
| `example_provider.py` | ~120 | ExampleProvider: batch example interface (moved from oracle/) |
| `__init__.py` | ~1 | Package exports with lazy-loaded QueryGenerator |

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

10. **Builder Pattern**: ConGenModelBuilder encapsulates bias loading and configuration. `build()` auto-prepares when `with_oracle()` + `with_examples()` are set; returns unprepared model otherwise. Call `model.prepare(oracle, examples)` manually for CV reuse patterns.

11. **Oracle Separation**: Oracle created independently and passed to `model.prepare()`. Enables cross-validation reuse without rebuilding model.

#### conacq/runners/ — Execution Runners (~446 LOC, 3 files)

Pipeline runners for constraint acquisition algorithms (extracted from eval/):

| File | LOC | Purpose |
|------|-----|---------|
| `congen_runner.py` | 235 | CONGEN pipeline runner with profiling + bias shuffle seed support |
| `interactive_runner.py` | 197 | QuAcq pipeline runner with metrics collection |
| `__init__.py` | ~14 | Package exports |

#### conacq/eval/ — Evaluation Framework (~2,346 LOC, 11 files)

Cross-validation and accuracy metrics:

| File | LOC | Purpose |
|------|-----|---------|
| `cross_validation.py` | 504 | n-fold CV (CONGEN + Interactive) with pre-generated fold support |
| `interactive_metrics.py` | 391 | QuAcq-specific metrics (query count, convergence) |
| `evaluator.py` | 267 | Evaluation orchestrator for CONGEN/QuAcq results |
| `report.py` | 281 | Generate CSV/JSON/LaTeX/Markdown reports |
| `accuracy.py` | 170 | Accuracy/precision/recall/F1 calculation |
| `performance_metrics.py` | 140 | Runtime, SAT checks, memory metrics |
| `fold_io.py` | 145 | Shared CV fold generation/save/load for fair comparison |
| `bias_loader.py` | 112 | Load bias constraints from files |
| `result_loader.py` | 84 | Load evaluation results |
| `oracle_extractor.py` | 102 | Extract oracle data for interactive learning |

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

### apps/ — Standalone Applications (~3,100 LOC, 8 files)

CLI applications for constraint acquisition pipeline:

| File | LOC | Purpose |
|-----|-----|---------|
| `extract_results.py` | 621 | Post-process results, generate Markdown/LaTeX reports (with fold metrics: precision/recall/F1/specificity mean±std) |
| `generate_bias_config.py` | 536 | Feature model → YAML bias configuration |
| `generate_examples.py` | 325 | Generate E+/E- examples with sampling strategies |
| `generate_bias_files.py` | 302 | YAML bias config → JSON/CNF files |
| `run_congen.py` | 217 | Execute CONGEN learning pipeline (dev/debug tool) |
| `run_interactive_eval.py` | 337 | Execute QuAcq interactive learning with CV support |
| `run_congen_eval.py` | ~370 | Execute n-fold CV + strategy evaluation (description/clause) against oracle FM |
| `generate_cv_folds.py` | 68 | CLI to pre-generate CV folds for reproducible evaluation |

**Config Files** (`conf/`, 7 TOML files):
- `generate_examples_config.toml` — Example generation settings
- `run_congen_config.toml` — CONGEN execution settings
- `run_interactive_eval_config.toml` — QuAcq execution settings
- `run_congen_eval_config.toml` — Cross-validation settings
- Plus 3 additional task-specific configs

### tests/ — Test Suite (~3,500+ LOC, 8 files)

Comprehensive test coverage using pytest + @parameterized.expand:

| File | LOC | Purpose |
|------|-----|---------|
| `test_diagnosis.py` | 1,416 | Diagnosis algorithms (FastDiag, QuickXPlain, KBDiag, WipeOutR, HSDAG) |
| `test_interactive.py` | 603 | QuAcq interactive learning (oracle and example modes) |
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
- `ConGenModelBuilder.from_bias_and_fm_uvl()` / `from_bias_and_fm_fide()` — Builder-pattern model construction
- Solver instantiation via consistent factories

## Codebase Statistics

| Component | LOC | Files | Avg File Size | Status |
|-----------|-----|-------|---------------|--------|
| conacq/ | ~9,272 | ~50 | ~185 | ✅ Core algorithms |
| explanation/ | ~4,600 | ~35 | ~131 | ✅ SAT infrastructure |
| apps/ | ~3,100 | 8 | ~388 | ✅ CLI applications |
| tests/ | ~3,745 | 8 | ~468 | ✅ Comprehensive coverage |
| **Total** | **~20,900** | **~101** | **~207** | ✅ **Production ready** |

**Recent Changes** (Oracle Interface Refactoring - commit c978d66):

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

**Earlier Changes** (still in place):
- ConGenModel pure data container (bias + solver config only)
- ConGenModel.prepare(oracle, pos_examples, neg_examples)
- ConGenModelBuilder.from_bias(path): returns unprepared model by default; auto-prepares if oracle+examples set via with_oracle()/with_examples()
- GenerateNE internalized to ConGenModel.prepare()
- FMOracleModel with assumption-guarded clauses
- Cross-validation reuse pattern

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

**Pipeline**: `run_congen_eval.py` (CV + strategy evaluation) → `extract_results.py` (reports + eval tables). `run_congen.py` is a dev/debug tool.

```bash
# Generate bias files from feature model
python -m apps.generate_bias_config data/fms/model.uvl -v
python -m apps.generate_bias_files data/bias-config/model.yaml

# Generate test examples
python -m apps.generate_examples apps/conf/generate_examples_config.toml

# Run unified cross-validation (ConGen + Interactive)
python -m apps.run_cv apps/conf/run_cv_config.toml -v

# Run pure QuAcq learning (no CV, no evaluation)
python -m apps.run_interactive apps/conf/run_interactive_config.toml -v
python -m apps.run_interactive apps/conf/run_interactive_config.toml --interactive

# Compare learned KB against oracle FM
python -m apps.run_compare --kb data/results/model_kb.json --bias data/bias/model-bias.json --oracle data/fms/model.uvl -v

# Describe KB constraints
python -m apps.describe_kb --kb data/results/model_kb.json --bias data/bias/model-bias.json

# Single-run ConGen (debug tool)
python -m apps.run_congen apps/conf/run_congen_config.toml -v
python -m apps.run_congen apps/conf/run_congen_config.toml --non-incremental

# Extract and generate final reports (includes fold metrics)
python -m apps.extract_results <results_dir> -v
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
