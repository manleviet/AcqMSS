# AcqMSS Codebase Summary

**Total Python Code**: 126,878 lines across 524 files
**Main Packages**: acqmss (7,931 LOC) + explanation (7,234 LOC) + apps (3,639 LOC) + tests (3,405 LOC)

## Package Structure

### acqmss/ — Constraint Acquisition Algorithms (7,931 LOC)

Core acquisition logic organized into four sub-packages:

#### acqmss/algorithms/ — Acquisition Algorithms (2,980 LOC, 15 files)

Primary constraint discovery algorithms:

| File | LOC | Purpose |
|------|-----|---------|
| `congen.py` | 176 | CONGEN orchestration (GenerateNE → ACQMSS → REDUCE) |
| `acqmss.py` | 268 | ACQMSS: divide-and-conquer MSS finding |
| `reduce.py` | 152 | REDUCE: redundancy elimination via consistency checking |
| `generate_ne.py` | 181 | GenerateNE: negated example generation from negative examples |
| `__init__.py` | 23 | Package initialization, exports CONGENModel, CONGEN, ACQMSS, REDUCE |

**Interactive Sub-package** (`interactive/`, 9 files, ~1,900 LOC):

| File | LOC | Purpose |
|------|-----|---------|
| `quacq.py` | 439 | QuAcq algorithm: incremental KB refinement (oracle-based + example-based modes) |
| `learner.py` | 406 | InteractiveLearner: high-level facade, supports from_examples() for batch learning |
| `query_generator.py` | 262 | GenerateQuery: creates discriminative queries from bias constraints |
| `user_interface.py` | 248 | ManualOracle, AutomatedOracle, ExampleProvider: oracle + batch example interfaces |
| `findscope.py` | 134 | FindScope (IJCAI13 Algorithm 2): identify violated constraint scope via partial queries |
| `findc.py` | 208 | FindC (IJCAI13 Algorithm 3): identify specific constraint from scope |
| `task.py` | 194 | Task state management, scope helpers, shared utilities (violates_clauses) |

#### acqmss/bias/ — Bias (Constraint) Generation (1,097 LOC, 6 files)

Feature model to constraint conversion pipeline:

| File | LOC | Purpose |
|------|-----|---------|
| `bias_generator.py` | 275 | Extract constraints from feature model (hierarchical + cross-tree) |
| `bias_io.py` | 222 | JSON/YAML I/O for constraints and configurations |
| `config_loader.py` | 203 | TOML/YAML configuration loading for bias generation |
| `clause_generator.py` | 199 | Convert FM constraints to CNF clauses |
| `data_structures.py` | 160 | Constraint, BiasConfig, ConstraintType enumerations |

#### acqmss/testcases/ — Example Generation (1,609 LOC, 9 files)

Positive/negative example generation strategies:

| File | LOC | Purpose |
|------|-----|---------|
| `random_sampling.py` | 389 | RS sampling: uniformly random configuration selection |
| `oracle.py` | 326 | FeatureModelOracle: validate configurations against FM |
| `feature_frequency.py` | 308 | FF/2-COV: feature frequency and 2-coverage strategies |
| `data_structures.py` | 217 | Configuration, Example, ExampleSet datastructures |
| `io_utils.py` | 155 | Load/save examples in JSON format |

#### acqmss/eval/ — Evaluation Framework (2,725 LOC, 14 files)

Cross-validation and accuracy metrics:

| File | LOC | Purpose |
|------|-----|---------|
| `interactive_metrics.py` | 391 | QuAcq-specific metrics (query count, convergence) |
| `cross_validation.py` | 440 | n-fold CV (CONGEN + Interactive) with pre-generated fold support |
| `report.py` | 281 | Generate CSV/JSON/LaTeX/Markdown reports |
| `evaluator.py` | 267 | Evaluation orchestrator for CONGEN/QuAcq results |
| `accuracy.py` | 179 | Accuracy/precision/recall/F1 calculation |
| `congen_runner.py` | 217 | CONGEN pipeline runner with profiling + bias shuffle seed support |
| `interactive_runner.py` | 198 | QuAcq pipeline runner with metrics collection (analogous to CONGENRunner) |
| `fold_io.py` | 146 | Shared CV fold generation/save/load for fair comparison |

### explanation/ — SAT Solver Infrastructure (7,234 LOC)

Diagnosis algorithms and SAT model abstraction:

#### explanation/models/ — Diagnosis Models (1,809 LOC, 5 files)

SAT model representation and construction:

| File | LOC | Purpose |
|------|-----|---------|
| `task_preparation.py` | 952 | Task preparation: convert FM to SAT, set up solver |
| `diagnosis_model_builder.py` | 437 | Builder pattern: construct DiagnosisModel with configuration |
| `pysat_diagnosis_model.py` | 290 | DiagnosisModel: SAT instance + metadata (clauses, assumptions, split/diff) |
| `testsuite.py` | 93 | TestSuite: holds test cases + their configurations |

#### explanation/operations/ — SAT Operations (5,130 LOC, 31 files)

Diagnosis algorithm implementations and SAT abstractions:

**Core Algorithm Files**:

| File | LOC | Purpose |
|------|-----|---------|
| `profiler.py` | 1192 | Profiling infrastructure: decorator-based execution timing, call counting |
| `checker.py` | 494 | ConsistencyChecker ABC + implementations (Incremental, NonIncremental, SAT4J) |
| `hsdag.py` | 353 | HSDAG tree search: optimization for multiple diagnoses/conflicts |
| `pysat_explanation_builder.py` | 418 | Builder for diagnosis operations (FastDiag, QuickXPlain, KBDiag) |
| `pysat_abstract_explanation.py` | 277 | Template method base for diagnosis operations |

**Diagnosis Algorithm Implementations**:

| File | LOC | Purpose |
|------|-----|---------|
| `algorithms/fastdiag.py` | 243 | FastDiag: breadth-first minimal diagnosis finding |
| `algorithms/fastdiagp.py` | 187 | FastDiagP: parallel FastDiag variant |
| `algorithms/quickxplain.py` | 198 | QuickXPlain: minimal conflict finding |
| `algorithms/kbdiag.py` | 127 | KBDiag: kernel-based diagnosis |
| `algorithms/wipeoutr_fm.py` | 194 | WipeOutR: feature model variant |
| `algorithms/wipeoutr_t.py` | 178 | WipeOutR_T: test case variant |

**Operation Wrappers** (pysat_*_*.py files, 10 files, ~1,800 LOC):

Each wraps diagnosis algorithms for specific use cases (diagnosis vs conflict, PySAT vs SAT4J, various test modes).

#### explanation/transformations/ — Model Converters (295 LOC, 5 files)

Feature model to SAT conversion:

| File | LOC | Purpose |
|------|-----|---------|
| `fm_to_diag_pysat.py` | 113 | Feature model → DiagnosisModel (PySAT) |
| `dimacs_to_diag_pysat.py` | 81 | DIMACS CNF → DiagnosisModel |
| `dimacs_to_configuration.py` | 59 | DIMACS variable assignments → Configuration |
| `testsuite_reader.py` | 42 | Read test suites from files |

### apps/ — Standalone Applications (3,769 LOC, 9 files)

CLI applications for constraint acquisition pipeline:

| File | LOC | Purpose |
|------|-----|---------|
| `extract_results.py` | 1015 | Post-process results, generate reports |
| `generate_bias_config.py` | 511 | Feature model → YAML bias configuration |
| `evaluate_congen_results.py` | 440 | Evaluate CONGEN learning results |
| `generate_examples.py` | 368 | Generate E+/E- examples with sampling strategies |
| `generate_bias_files.py` | 358 | YAML bias config → JSON/CNF files |
| `run_congen.py` | 253 | Execute CONGEN learning pipeline |
| `run_interactive.py` | 378 | Execute QuAcq interactive learning with CV support |
| `run_evaluation.py` | 316 | Execute n-fold cross-validation (fold_data + shuffle_bias support) |
| `generate_cv_folds.py` | 130 | CLI to pre-generate CV folds for reproducible evaluation |

**Config Files** (`conf/`, 8 TOML files):
- `generate_examples_config.toml` — Example generation settings
- `run_congen_config.toml` — CONGEN execution settings
- `run_interactive_config.toml` — QuAcq execution settings
- `run_evaluation_config.toml` — Cross-validation settings
- Plus 4 additional task-specific configs

### tests/ — Test Suite (3,405 LOC, 9 files)

Comprehensive test coverage using pytest + @parameterized.expand:

| File | LOC | Purpose |
|------|-----|---------|
| `test_diagnosis.py` | 1416 | Diagnosis algorithms (FastDiag, QuickXPlain, KBDiag, WipeOutR, HSDAG) |
| `test_interactive.py` | 563 | QuAcq interactive learning tests |
| `test_profiler.py` | 536 | Profiling infrastructure tests |
| `test_evaluation.py` | 443 | Cross-validation and accuracy metric tests |
| `test_congen.py` | 256 | CONGEN learning tests |

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

### 5. Facade Pattern
- `InteractiveLearner` — High-level QuAcq interface
- `CONGENRunner` — High-level CONGEN pipeline
- `Evaluator` — High-level evaluation orchestration

### 6. Factory Pattern
- `CONGENModel.from_bias_and_examples()` — Task preparation factory
- Solver instantiation via consistent factories

## Codebase Statistics

| Component | LOC | Files | Avg File Size |
|-----------|-----|-------|---------------|
| acqmss/ | 8,456 | 43 | 197 |
| explanation/ | 7,234 | 42 | 172 |
| apps/ | 3,769 | 9 | 419 |
| tests/ | 3,405 | 9 | 378 |
| **Total** | **22,864** | **103** | **222** |

(Excluding __pycache__, .pyc, __init__.py stubs)

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

# Run CONGEN (passive learning)
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml -v
PYTHONPATH=. python apps/run_congen.py apps/conf/run_congen_config.toml --non-incremental

# Run QuAcq (interactive learning)
PYTHONPATH=. python apps/run_interactive.py apps/conf/run_interactive_config.toml -v
PYTHONPATH=. python apps/run_interactive.py apps/conf/run_interactive_config.toml --interactive

# Run QuAcq with cross-validation
PYTHONPATH=. python apps/run_interactive.py apps/conf/run_interactive_config.toml -v --cv

# Evaluate results
PYTHONPATH=. python apps/run_evaluation.py apps/conf/run_evaluation_config.toml -v
```

## File Size Analysis

Largest files (by line count):
- `explanation/operations/profiler.py` — 1,192 LOC (profiling infrastructure)
- `explanation/models/task_preparation.py` — 952 LOC (SAT task setup)
- `tests/test_diagnosis.py` — 1,416 LOC (diagnosis tests)
- `apps/extract_results.py` — 1,015 LOC (result processing)

Most files keep to ~200-400 LOC for maintainability, except specialized components.

## Next Steps for Documentation

See:
- **project-overview-pdr.md** — Goals, requirements, success criteria
- **code-standards.md** — Naming, patterns, testing conventions
- **system-architecture.md** — Data flow, integration points, design decisions
- **project-roadmap.md** — Development phases and status
