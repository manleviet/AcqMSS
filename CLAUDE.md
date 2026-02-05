# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AcqMSS (Constraint Acquisition With Maximum Satisfiable Subsets) is a Python-based system for constraint acquisition from feature models. It implements:
- **Diagnosis algorithms**: FastDiag, QuickXPlain, KBDiag, WipeOutR with HSDAG tree search
- **CONGEN**: Passive/batch constraint acquisition using ACQMSS, REDUCE, and GenerateNE
- **QuAcq**: Interactive constraint acquisition via membership queries
- **Evaluation framework**: Cross-validation, accuracy metrics, performance benchmarking

## Build and Test Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
PYTHONPATH=. pytest tests/ -v

# Run specific test files
PYTHONPATH=. pytest tests/test_diagnosis.py -v
PYTHONPATH=. pytest tests/test_congen.py -v
PYTHONPATH=. pytest tests/test_interactive.py -v

# Run a single test by name
PYTHONPATH=. pytest tests/test_diagnosis.py::test_fastdiag_1diag_0_incremental_with_profiling -v

# Run tests matching a pattern
PYTHONPATH=. pytest tests/test_diagnosis.py -k "fastdiag" -v
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

# Evaluate results
PYTHONPATH=. python apps/run_evaluation.py apps/conf/run_evaluation_config.toml -v
```

## Architecture

### Package Structure

```
acqmss/
├── algorithms/           # Constraint acquisition algorithms
│   ├── acqmss.py        # ACQMSS: divide-and-conquer MSS finder
│   ├── reduce.py        # REDUCE: redundancy elimination
│   ├── generate_ne.py   # GenerateNE: negated examples via QuickXPlain
│   ├── congen.py        # CONGEN: main passive learning algorithm
│   └── interactive/     # QuAcq interactive learning
│       ├── quacq.py     # QuAcq algorithm
│       ├── learner.py   # InteractiveLearner high-level interface
│       └── query_generator.py  # SAT-based query generation
├── bias/                # Bias generation for constraint acquisition
├── testcases/           # Example generation (E+/E-)
│   └── generators/      # Sampling strategies (rs, 2cov, ff)
└── eval/                # Evaluation framework
    ├── accuracy.py      # Accuracy calculation
    ├── cross_validation.py  # n-fold cross-validation
    └── evaluator.py     # Main evaluation entry point

explanation/
├── models/              # DiagnosisModel, DiagnosisModelBuilder
├── operations/          # HSDAG-based operations
│   └── algorithms/      # FastDiag, QuickXPlain, KBDiag, WipeOutR, HSDAG
└── transformations/     # Feature model → DiagnosisModel converters
```

### Two Learning Paradigms

**CONGEN (Passive/Batch Learning)**:
```
CONGEN(E+, E-, B, BG) → KB
1: NE ← GENERATENE(E⁻)      # Create negated examples
2: B′ ← ACQMSS(∅, B, NE, E⁺, BG)  # Find MSS of bias
3: return REDUCE(B′, NE, BG)  # Remove redundant constraints
```

**QuAcq (Interactive Learning)**:
```
QuAcq(B, BG, Oracle) → KB
while B is not empty:
  1. q ← GenerateQuery(KB, B, BG)
  2. answer ← Oracle.is_valid(q)
  3. if answer: prune constraints rejecting q
     else: find conflict, add to KB
return REDUCE(KB, BG)
```

### Solver Modes

- **Incremental**: Persistent solver with assumptions (default, efficient for repeated SAT checks)
- **Non-incremental**: Fresh solver instance per check
- **SAT4J**: External Java solver via subprocess

### Evaluation Metrics (from Paper Formula 1)

- **Accuracy** = (TP + TN) / (TP + TN + FP + FN) — primary metric
- **Precision** = TP / (TP + FP)
- **Recall** = TP / (TP + FN)
- **F1** = 2 * P * R / (P + R)

Evaluation strategies: `description` (compare constraint descriptions) or `clause` (compare CNF clauses)

## Test Configuration

Tests use `@parameterized.expand` with combinations of incremental/non-incremental modes and with/without profiling. Toggle specific tests via `ENABLED_TESTS` and `ENABLED_PARAMS` dictionaries at the top of test files.

## Key API Patterns

**CONGEN usage**:
```python
from acqmss.algorithms import CONGEN, CONGENModel, IncrementalCONGENTaskPreparation
from explanation.operations.algorithms.checker import IncrementalPySATChecker

model = CONGENModel.from_bias_and_examples(bias_constraints, pos_examples, neg_examples, feature_ids)
preparation = IncrementalCONGENTaskPreparation()
task = preparation.prepare(model).task
checker = IncrementalPySATChecker(task.set_kb, task.assumptions, 'glucose4', profiler)
congen = CONGEN(checker, profiler)
result = congen.acquire(task)
```

**QuAcq usage**:
```python
from acqmss.algorithms.interactive import InteractiveLearner

learner = InteractiveLearner.from_files(fm_path='model.uvl', bias_path='bias.json')
result = learner.learn(mode='automated', max_queries=1000)
evaluation = learner.evaluate(result)
```

**Diagnosis operations**:
```python
from explanation.operations import PySATDiagnosisBuilder, PySATTestcaseBuilder

# FastDiag
operation = PySATDiagnosisBuilder.for_diagnosis().with_max_diagnoses(5).build()

# QuickXPlain
operation = PySATDiagnosisBuilder.for_conflict().with_max_conflicts(3).build()

# KBDiag
operation = PySATTestcaseBuilder.for_debugging().with_max_diagnoses(1).build()
```

## Data Directories

- `data/fms/` — Feature models (.uvl, .fide)
- `data/bias-config/` — Bias YAML configurations
- `data/bias/` — Generated bias files (JSON/CNF)
- `data/examples/` — Generated test examples (E+/E-)
- `data/results/` — CONGEN results and evaluations
- `apps/conf/` — TOML configuration files for apps