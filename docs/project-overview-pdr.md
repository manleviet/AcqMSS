# AcqMSS Project Overview & Product Development Requirements (PDR)

## Executive Summary

AcqMSS (Constraint Acquisition With Maximum Satisfiable Subsets) is a Python research system for automatically discovering constraints in feature models through **two complementary learning paradigms**:

1. **CONGEN (Passive/Batch Learning)** — Learn from sets of valid/invalid example configurations
2. **QuAcq (Interactive Learning)** — Learn through dialog with a domain expert or oracle

The system combines state-of-the-art SAT solver algorithms (FastDiag, QuickXPlain, KBDiag, WipeOutR) with HSDAG tree search optimization to efficiently extract constraint knowledge from feature models.

**Target Users**: Researchers in automated constraint discovery, feature model engineers, software product line maintainers.

## Problem Statement

### Challenge
Feature models encode complex product variability through constraints. Discovering or verifying these constraints is labor-intensive and error-prone when done manually. This is especially critical for:
- **Legacy systems** where constraint documentation is incomplete
- **Evolved systems** where constraints have drifted from implementation
- **Large models** (100s to 1000s of features) where manual verification is infeasible

### Motivation
Automated constraint acquisition reduces engineering effort, improves consistency, and enables systematic feature model validation and maintenance.

## Product Vision

Build a **production-ready constraint acquisition framework** that:
- Scales to feature models with thousands of features
- Provides flexible learning paradigms (batch vs. interactive)
- Integrates with industry tools (flamapy for FM parsing)
- Offers comprehensive evaluation and profiling capabilities
- Prioritizes accuracy over speed (research system, not real-time)

## Core Functional Requirements

### FR-1: Passive Constraint Acquisition (CONGEN)

**Requirement**: System shall learn constraints from positive and negative example sets.

**Acceptance Criteria**:
- Given E+ (valid configs) and E- (invalid configs), produce KB (constraint set)
- Accuracy (TP+TN) / (TP+TN+FP+FN) ≥ 90% on validation sets
- Support incremental and non-incremental solver modes
- Complete 65-feature model in <30 seconds
- Handle up to 1,000 bias constraints per model

**Key Algorithms**:
1. GenerateNE — Create negated examples from E-
2. ACQMSS — Find maximum satisfiable subset of bias
3. REDUCE — Eliminate redundant constraints

### FR-2: Interactive Constraint Acquisition (QuAcq)

**Requirement**: System shall learn constraints through membership queries with an oracle.

**Acceptance Criteria**:
- Support both automated (FM-based) and manual (user-driven) oracles
- Query generation prioritizes discriminative queries
- Converge in <1,000 queries for models <300 features
- Accuracy ≥ 85% on learned constraint sets
- Support real-time query-answer cycles

**Key Features**:
- GenerateQuery — Create discriminative configurations
- Update KB — Prune constraints based on oracle feedback
- Convergence detection — Stop when bias is fully learned

### FR-3: Diagnosis Algorithms

**Requirement**: System shall support multiple SAT-based diagnosis operations.

**Acceptance Criteria**:
- Implement FastDiag (breadth-first minimal diagnosis)
- Implement QuickXPlain (minimal conflict finding)
- Implement KBDiag (kernel-based diagnosis)
- Support HSDAG tree search optimization (≥10x speedup)
- Support both PySAT and SAT4J solvers

**Key Algorithms**:
- FastDiag — Find all minimal diagnoses
- FastDiagP — Parallel variant
- QuickXPlain — Find minimal conflict explanations
- KBDiag — Kernel-based approach
- WipeOutR_FM, WipeOutR_T — Feature model and test case variants

### FR-4: Evaluation Framework

**Requirement**: System shall provide comprehensive evaluation metrics.

**Acceptance Criteria**:
- n-fold cross-validation (1-10 folds)
- Calculate accuracy, precision, recall, F1
- Support description and clause-level comparison strategies
- Generate CSV, JSON, LaTeX, Markdown reports
- Profile execution time and memory usage
- Count SAT solver calls

### FR-5: Feature Model Support

**Requirement**: System shall integrate with flamapy for FM parsing and constraint extraction.

**Acceptance Criteria**:
- Parse UVL feature models
- Extract hierarchical constraints (mandatory, optional, alternative, or)
- Extract cross-tree constraints (requires, excludes)
- Support 7+ reference models (14-6,467 features)
- Generate bias configurations in JSON and CNF formats

### FR-6: Example Generation

**Requirement**: System shall generate diverse example sets from feature models.

**Acceptance Criteria**:
- Implement Random Sampling (RS) strategy
- Implement Feature Frequency (FF) strategy
- Implement 2-Coverage (2-COV) strategy
- Support sampling at 25%, 50%, 75%, 100%, 150% of valid configs
- Validate generated examples against FM

### FR-7: Configuration Management

**Requirement**: System shall use external configuration (no hard-coded values).

**Acceptance Criteria**:
- All applications read TOML configuration files
- Support per-task configuration (bias generation, example generation, CONGEN, QuAcq, evaluation)
- Configuration includes input/output paths, solver settings, algorithm parameters

## Non-Functional Requirements

### NFR-1: Performance

**Requirement**: System performance shall scale to realistic feature model sizes.

| Constraint | Value | Rationale |
|-----------|-------|-----------|
| Arcade-game (65 features) | <30 sec CONGEN | Development feedback loop |
| linux (6,467 features) | <60 min CONGEN | Research overnight runs |
| Solver call overhead | <1% per call | Incremental solver efficiency |
| Memory per solver instance | <500 MB | Practical constraint |

### NFR-2: Accuracy

**Requirement**: Learned constraints shall match ground truth with high fidelity.

| Metric | Target | Rationale |
|--------|--------|-----------|
| Accuracy (weighted) | ≥90% | Primary research metric |
| Precision | ≥85% | Minimize false positives |
| Recall | ≥80% | Minimize false negatives |
| F1-score | ≥0.82 | Balanced performance |

### NFR-3: Code Quality

**Requirement**: Code shall follow Python best practices.

**Standards**:
- Type hints on all public functions
- Docstrings on all public modules, classes, functions
- Test coverage ≥80% for core algorithms
- No hard-coded magic numbers (use configuration)
- Snake_case for modules, PascalCase for classes

### NFR-4: Testability

**Requirement**: System shall support comprehensive testing across solver modes.

**Test Coverage**:
- Parameterized tests (incremental vs. non-incremental)
- Profile-enabled tests (optional timing/counting)
- Selective test execution via ENABLED_TESTS dict
- Unit tests for all algorithms
- Integration tests for end-to-end pipelines

### NFR-5: Compatibility

**Requirement**: System shall support multiple Python versions and solvers.

| Component | Requirement |
|-----------|-------------|
| Python | 3.13+ |
| PySAT solvers | glucose4, minisat, lingeling |
| Optional SAT solvers | SAT4J (external Java) |
| Feature model tools | flamapy |
| OS | Linux, macOS, Windows |

### NFR-6: Reproducibility

**Requirement**: Results shall be reproducible across runs.

**Mechanisms**:
- Configurable random seeds
- Deterministic example generation
- Profiling data export (CSV/JSON)
- Result archiving with metadata (date, version, config)

## System Architecture Highlights

### Two-Layer Architecture

```
Application Layer (apps/)
  ├── generate_bias_config.py
  ├── generate_examples.py
  ├── run_congen.py
  ├── run_interactive_eval.py
  └── run_congen_eval.py
       ↓
Core Algorithms (acqmss/)
  ├── CONGEN (GenerateNE → ACQMSS → REDUCE)
  ├── QuAcq (GenerateQuery → Oracle → Update KB)
  ├── Bias generation
  ├── Example generation
  └── Evaluation
       ↓
SAT Infrastructure (explanation/)
  ├── Diagnosis algorithms (FastDiag, QuickXPlain, KBDiag, WipeOutR)
  ├── HSDAG tree search
  ├── Solver abstraction (Incremental, NonIncremental, SAT4J)
  └── Model transformation (FM → SAT)
```

### Key Design Patterns

1. **Dependency Injection** — Algorithms accept ConsistencyChecker
2. **Strategy Pattern** — Multiple solver implementations
3. **Builder Pattern** — DiagnosisModelBuilder configuration
4. **Facade Pattern** — InteractiveLearner, CONGENRunner high-level interfaces
5. **Template Method** — PySATAbstractExplanation algorithm base

## Success Criteria

### Research Validation
- [ ] Reproduce published accuracy metrics (≥90% on benchmarks)
- [ ] Support 7+ reference feature models (14-6,467 features)
- [ ] Demonstrate HSDAG speedup (≥10x)
- [ ] Compare incremental vs. non-incremental solver modes

### Software Quality
- [ ] 80%+ test coverage on core algorithms
- [ ] All tests passing on Python 3.13+
- [ ] Type checking passes (mypy/pyright)
- [ ] Code follows style guidelines (ruff/black)

### User Experience
- [ ] Complete example pipeline in documentation
- [ ] All configuration files provided and documented
- [ ] CLI applications provide helpful error messages
- [ ] Results are exportable in multiple formats

### Engineering Scalability
- [ ] Modular package structure (acqmss, explanation, apps)
- [ ] Clear separation of concerns (algorithms vs. SAT vs. I/O)
- [ ] Extensible solver interface (pluggable checkers)
- [ ] Comprehensive documentation (API, architecture, usage)

## Development Phases

### Phase 1: Core Diagnosis Infrastructure (Completed)
- FastDiag, QuickXPlain, KBDiag, WipeOutR algorithms
- HSDAG tree search optimization
- SAT solver abstraction layer
- Incremental/non-incremental modes

### Phase 2: Constraint Acquisition (Completed)
- CONGEN (GenerateNE, ACQMSS, REDUCE)
- QuAcq interactive learning
- Bias generation from feature models
- Example generation with sampling strategies

### Phase 3: Evaluation Framework (Completed)
- n-fold cross-validation
- Accuracy/precision/recall/F1 metrics
- Profiling infrastructure (timing, memory, solver calls)
- Report generation (CSV, JSON, LaTeX)

### Phase 4: Applications & Integration (Completed)
- CLI applications for each pipeline stage
- TOML configuration system
- Reference feature models (7 models)
- End-to-end example workflows

### Phase 5: Documentation & Polish (Current/In Progress)
- Comprehensive API documentation
- Architecture guides
- Code standards and patterns
- Troubleshooting guides

## Key Metrics & Measurement

| Metric | Definition | Target | Measurement |
|--------|-----------|--------|-------------|
| **Accuracy** | (TP + TN) / (TP + TN + FP + FN) | ≥90% | Per-model evaluation |
| **Precision** | TP / (TP + FP) | ≥85% | False positive rate |
| **Recall** | TP / (TP + FN) | ≥80% | False negative rate |
| **Solver Efficiency** | Calls per CONGEN run | <10K (65-feat) | Profiling data |
| **Wall-clock Time** | Minutes to complete CONGEN | <0.5 (65-feat) | Profiler.py timing |
| **Convergence** | Queries for QuAcq completion | <1K | interactive_metrics.py |
| **Code Coverage** | % of algorithms with tests | ≥80% | pytest --cov |
| **Documentation** | Lines per 100 LOC | ≥15 | doc/code ratio |

## Stakeholder Communication

### Internal Research Team
- Weekly progress on algorithm tuning
- Monthly accuracy benchmarking results
- Quarterly feature model evaluation updates

### Academic Partners (if any)
- Quarterly status reports
- Method descriptions for publication
- Reproducibility packages with configurations

### External Users
- Release notes with improvements
- Configuration examples
- Troubleshooting guides

## Known Limitations & Future Work

### Current Limitations
1. No parallel solver support (sequential only)
2. FM parsing limited to UVL format
3. Oracle requires ground truth (not interactive with users)
4. No incremental learning across different FM versions

### Future Enhancements
1. FastDiagP parallel implementation (noted in code)
2. Additional FM formats (fide, XSD)
3. Interactive oracle with user confirmation
4. Caching of solver results across runs
5. GPU-accelerated SAT solving (if applicable)
6. Benchmark on industrial-scale models (10K+ features)

## Dependencies

### Runtime Critical
- **python-sat (PySAT)** — SAT solver interface (not replaceable)
- **flamapy** — FM parsing (core to FR-5)

### Development
- **pytest + parameterized** — Testing framework
- **pyyaml, tomllib** — Configuration parsing

### Optional (Research)
- **sat4j** — Verification solver
- **memory_profiler** — Advanced profiling
- **py-spy** — Sampling profiler

## Document Version Control

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-12 | Updated with accurate codebase metrics and file inventory |

