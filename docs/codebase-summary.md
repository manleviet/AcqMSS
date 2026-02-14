# AcqMSS Codebase Summary

**Total Python Code**: ~22,000+ lines across ~106 files
**Main Packages**: acqmss (8,695 LOC) + explanation (6,580 LOC) + apps (3,765 LOC) + tests (~3,000+ LOC)
**Last Updated**: 2026-02-13

## Package Structure

### acqmss/ — Constraint Acquisition Algorithms (8,695 LOC)

Core acquisition logic organized into six sub-packages:

#### acqmss/algorithms/ — Acquisition Algorithms (~1,455 LOC, 7 files)

Primary constraint discovery algorithms:

| File | LOC | Purpose |
|------|-----|---------|
| `congen.py` | 228 | ConGen orchestration (direct params, no task object) |
| `acqmss.py` | 104 | ACQMSS: divide-and-conquer MSS finding |
| `reduce.py` | 155 | REDUCE: redundancy elimination via consistency checking |
| `generate_ne.py` | 193 | GenerateNE: negated example generation (called by ConGenModel.prepare()) |
| `task_preparation.py` | 435 | Task hierarchy (DiagnosisTask → TestCaseTask → ConGenTask) + unified prep |
| `congen_model.py` | 186 | ConGenModel - CheckerModel protocol, self-preparing with prepare() |
| `congen_model_builder.py` | 157 | ConGenModelBuilder - fluent builder pattern (mirrors DiagnosisModelBuilder) |

**Interactive Sub-package** (`interactive/`, 6 files, ~1,950 LOC):

| File | LOC | Purpose |
|------|-----|---------|
| `quacq.py` | 439 | QuAcq: oracle-based + example-based learning modes |
| `learner.py` | 426 | InteractiveLearner: high-level facade (from_examples(), from_files()) |
| `findscope.py` | 134 | FindScope (IJCAI13 Algorithm 2): scope identification via partial queries |
| `findc.py` | 208 | FindC (IJCAI13 Algorithm 3): constraint discrimination from scope |
| `task.py` | 137 | Task state, scope helpers, shared utilities (violates_clauses) |
| `result.py` | 137 | InteractiveResult - outcome with metrics |

#### acqmss/bias/ — Bias (Constraint) Generation (~1,250 LOC, 6 files)

Feature model to constraint conversion pipeline:

| File | LOC | Purpose |
|------|-----|---------|
| `bias_generator.py` | 275 | Extract constraints from feature model (hierarchical + cross-tree) |
| `bias_io.py` | 222 | JSON/YAML I/O for constraints and configurations |
| `config_loader.py` | 203 | TOML/YAML configuration loading for bias generation |
| `clause_generator.py` | 199 | Convert FM constraints to CNF clauses |
| `data_structures.py` | 160 | Constraint, BiasConfig, ConstraintType enumerations |

#### acqmss/example_generators/ — Example & Query Generation (~1,285 LOC, 7 files)

Sampling strategies, example generation, and query generation for learning:

| File | LOC | Purpose |
|------|-----|---------|
| `base.py` | 245 | Base strategy class for example generation |
| `random_sampling.py` | 245 | RS sampling: uniformly random configuration selection |
| `feature_frequency.py` | 197 | FF strategy: feature frequency-based sampling |
| `nwise_coverage.py` | 136 | 2-COV strategy: n-wise pairwise coverage |
| `query_generator.py` | 262 | QueryGenerator: discriminative query generation (moved from interactive/) |
| `example_provider.py` | 120+ | ExampleProvider: batch example interface for learning (moved from oracle/) |
| `__init__.py` | 1 | Package exports with lazy-loaded QueryGenerator |

**Oracle Sub-package** (`acqmss/oracle/`, 6 files, ~630 LOC):

| File | LOC | Purpose |
|------|-----|---------|
| `base.py` | 47 | Oracle ABC: unified oracle interface for membership queries |
| `fm_oracle.py` | 150+ | FeatureModelOracle: ground truth validation via SAT solver |
| `user_prompt.py` | 100+ | UserPromptOracle: interactive human-in-the-loop oracle |
| `cached.py` | 80+ | CachedOracle: wrapper with query result caching |
| `extractor.py` | 100+ | OracleData: extract oracle data for evaluation |
| `__init__.py` | 1 | Package exports |

**Critical Implementation Details**:

1. **Feature ID Consistency**: The `FeatureModelOracle`'s `_build_feature_ids()` method uses flamapy's variable mapping (tree traversal order) stored in `FmToPysat.variables` as the authoritative source. This ensures feature_ids match SAT variable IDs in CNF clauses. Using alphabetical sorting would cause critical mismatch with clause variable references.

2. **Assumption-Based Representation**: All checkers (Incremental and NonIncremental) use identical assumption-based data: `Dict[int, int]` mapping assumption IDs to their negation counterparts, used uniformly in REDUCE and other algorithms.

3. **GenerateNE Design**: GenerateNE is invoked internally by `ConGenModel.prepare()`. Results are merged into task via `merge_ne_into_task()`. Checkers are immutable after construction.

4. **CheckerModel Protocol**: ConGenModel implements `get_kb()`, `get_assumptions()`, `use_incremental`, `solver_name` for compatibility with CheckerFactory.

5. **Builder Pattern**: ConGenModelBuilder encapsulates file loading, model construction, and prepare() invocation (mirrors DiagnosisModelBuilder).

#### acqmss/eval/ — Evaluation Framework (~3,700 LOC, 13 files)

Cross-validation and accuracy metrics:

| File | LOC | Purpose |
|------|-----|---------|
| `cross_validation.py` | 504 | n-fold CV (CONGEN + Interactive) with pre-generated fold support |
| `congen_runner.py` | 228 | CONGEN pipeline runner with profiling + bias shuffle seed support |
| `interactive_runner.py` | 197 | QuAcq pipeline runner with metrics collection |
| `interactive_metrics.py` | 391 | QuAcq-specific metrics (query count, convergence) |
| `evaluator.py` | 267 | Evaluation orchestrator for CONGEN/QuAcq results |
| `report.py` | 281 | Generate CSV/JSON/LaTeX/Markdown reports |
| `accuracy.py` | 170 | Accuracy/precision/recall/F1 calculation |
| `performance_metrics.py` | 140 | Runtime, SAT checks, memory metrics |
| `fold_io.py` | 145 | Shared CV fold generation/save/load for fair comparison |
| `bias_loader.py` | 112 | Load bias constraints from files |
| `result_loader.py` | 84 | Load evaluation results |
| `oracle_extractor.py` | 102 | Extract oracle data for interactive learning |

### explanation/ — SAT Solver Infrastructure (~6,580 LOC, 42 files)

Diagnosis algorithms and SAT model abstraction:

#### explanation/models/ — Diagnosis Models (~1,000 LOC, 5 files)

SAT model representation and construction:

| File | LOC | Purpose |
|------|-----|---------|
| `task_preparation.py` | 750 | Unified DiagnosisTaskPreparation, TestCaseTaskPreparation, factory classes |
| `diagnosis_model_builder.py` | 300 | Builder pattern: construct DiagnosisModel with configuration |
| `pysat_diagnosis_model.py` | 255 | DiagnosisModel: SAT instance + metadata (clauses, assumptions) |
| `testsuite.py` | 75 | TestSuite: holds test cases + their configurations |

#### explanation/operations/ — SAT Operations (~5,200 LOC, 31 files)

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

#### explanation/transformations/ — Model Converters (~400 LOC, 5 files)

Feature model to SAT conversion:

| File | LOC | Purpose |
|------|-----|---------|
| `fm_to_diag_pysat.py` | 113 | Feature model → DiagnosisModel (PySAT) |
| `dimacs_to_diag_pysat.py` | 81 | DIMACS CNF → DiagnosisModel |
| `dimacs_to_configuration.py` | 59 | DIMACS variable assignments → Configuration |
| `testsuite_reader.py` | 42 | Read test suites from files |

### apps/ — Standalone Applications (~3,765 LOC, 9 files)

CLI applications for constraint acquisition pipeline:

| File | LOC | Purpose |
|-----|-----|---------|
| `extract_results.py` | 1,013 | Post-process results, generate reports |
| `generate_bias_config.py` | 536 | Feature model → YAML bias configuration |
| `generate_examples.py` | 325 | Generate E+/E- examples with sampling strategies |
| `generate_bias_files.py` | 302 | YAML bias config → JSON/CNF files |
| `run_congen.py` | 217 | Execute CONGEN learning pipeline |
| `run_interactive_eval.py` | 337 | Execute QuAcq interactive learning with CV support |
| `run_congen_eval.py` | 309 | Execute n-fold cross-validation |
| `generate_cv_folds.py` | 68 | CLI to pre-generate CV folds for reproducible evaluation |
| `evaluate_congen_results.py` | 524 | Post-process and analyze CONGEN results |

**Config Files** (`conf/`, 8 TOML files):
- `generate_examples_config.toml` — Example generation settings
- `run_congen_config.toml` — CONGEN execution settings
- `run_interactive_eval_config.toml` — QuAcq execution settings
- `run_congen_eval_config.toml` — Cross-validation settings
- Plus 4 additional task-specific configs

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
| acqmss/ | 8,695 | 47 | 185 | ✅ Core algorithms |
| explanation/ | 6,580 | 42 | 157 | ✅ SAT infrastructure |
| apps/ | 3,765 | 9 | 418 | ✅ CLI applications |
| tests/ | ~3,500+ | 8 | 437 | ✅ Comprehensive coverage |
| **Total** | **~22,540+** | **~106** | **~212** | ✅ **Production ready** |

**Recent Changes**:
- QueryGenerator moved from `acqmss/algorithms/interactive/` to `acqmss/example_generators/`
- ExampleProvider moved from `acqmss/oracle/` to `acqmss/example_generators/`
- Both classes now have canonical imports from `acqmss.example_generators`

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

```bash
# Generate bias files from feature model
PYTHONPATH=. python apps/generate_bias_config.py data/fms/model.uvl -v
PYTHONPATH=. python apps/generate_bias_files.py data/bias-config/model.yaml

# Generate test examples
PYTHONPATH=. python apps/generate_examples.py apps/conf/generate_examples_config.toml

# Run ConGen (passive learning)
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml --non-incremental

# Run QuAcq (interactive learning)
PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml -v
PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml --interactive

# Run QuAcq with cross-validation
PYTHONPATH=. python apps/run_interactive_eval.py apps/conf/run_interactive_eval_config.toml -v --cv

# Evaluate results
PYTHONPATH=. python apps/run_congen_eval.py apps/conf/run_congen_eval_config.toml -v
```

## File Size Analysis

Largest files (by line count):
- `explanation/operations/profiler.py` — 1,192 LOC (profiling infrastructure)
- `explanation/models/task_preparation.py` — 952 LOC (SAT task setup)
- `tests/test_diagnosis.py` — 1,416 LOC (diagnosis tests)
- `apps/extract_results.py` — 1,013 LOC (result processing)

Most files keep to ~200 LOC for maintainability, except specialized components.

## Next Steps for Documentation

See:
- **project-overview-pdr.md** — Goals, requirements, success criteria
- **code-standards.md** — Naming, patterns, testing conventions
- **system-architecture.md** — Data flow, integration points, design decisions
- **project-roadmap.md** — Development phases and status
