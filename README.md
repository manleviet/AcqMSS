# AcqMSS: Constraint Acquisition With Maximum Satisfiable Subsets

A research system for automatically acquiring constraints from feature models through **passive/batch learning (CONGEN)** and **interactive learning (QuAcq)** paradigms. Leverages advanced SAT solver algorithms (FastDiag, QuickXPlain, KBDiag, WipeOutR) with HSDAG tree search optimization.

## Quick Start

### Installation

```bash
git clone https://github.com/manleviet/AcqMSS.git
cd AcqMSS

python3.13 -m venv .venv
source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### Run Tests

```bash
PYTHONPATH=. pytest tests/ -v                        # All tests
PYTHONPATH=. pytest tests/test_congen.py -v          # Specific file
PYTHONPATH=. pytest tests/ -k "fastdiag" -v          # Pattern match
```

### Basic Workflow

```bash
# 1. Generate bias from feature model
python -m apps.generate_bias_config data/fms/arcade-game.uvl -v
python -m apps.generate_bias_files data/bias-config/arcade-game.yaml

# 2. Generate test examples (E+/E-)
python -m apps.generate_examples apps/conf/generate_examples_config.toml -v

# 3. Learn constraints (ConGen passive learning)
python -m apps.run_congen apps/conf/run_congen_config.toml -v

# 4. Compare learned KB against oracle
python -m apps.run_compare apps/conf/run_compare_config.toml -v
```

## Two Learning Paradigms

### CONGEN: Passive/Batch Learning

Learn constraints from positive (valid) and negative (invalid) example configurations:

```python
from conacq.algorithms import ConGen, ConGenModelBuilder
from conacq.oracle import FeatureModelOracle
from explanation.operations.algorithms.checker import CheckerFactory

# Build model (no FM dependency)
model = ConGenModelBuilder.from_bias('data/bias/model.json').build()

# Create oracle
oracle = FeatureModelOracle('data/fms/model.uvl')

# Prepare with examples (calls GenerateNE internally)
model.prepare(oracle, positive_examples=pos_examples, negative_examples=neg_examples)

# Create checker and run ConGen
checker = CheckerFactory.create_from_model(model, profiler)
congen = ConGen(checker, profiler)
result = congen.acquire(
    set_b=model.task.set_c,
    set_bg=model.task.set_b,
    set_tc=model.task.set_tc,
    set_neg_tv=model.task.set_neg_tv,
    negation_map=model.task.negation_map
)
```

**Process**: GenerateNE → ACQMSS (MSS finding) → REDUCE (redundancy elimination)

### QuAcq: Interactive Learning

Learn constraints through interaction with an oracle (user or model):

```python
from conacq.algorithms.interactive import InteractiveLearner

learner = InteractiveLearner.from_files(
    fm_path='data/fms/arcade-game.uvl',
    bias_path='data/bias/arcade-game.json'
)
result = learner.learn(mode='automated', max_queries=1000)
```

**Process**: GenerateQuery → Oracle → Update KB → Repeat → REDUCE

## Key Features

- **CONGEN**: Passive acquisition from examples (divide-and-conquer MSS finding)
- **QuAcq**: Interactive acquisition via membership queries
- **Diagnosis Algorithms**: FastDiag, QuickXPlain, KBDiag, WipeOutR with HSDAG tree search
- **SAT Solvers**: Incremental PySAT (~50x faster), non-incremental, SAT4J
- **Evaluation**: n-fold cross-validation, accuracy/precision/recall/F1, CSV/JSON/LaTeX export

## Feature Models

Seven reference models of increasing complexity:

| Model | Features | Constraints | Cross-tree |
|-------|----------|-------------|------------|
| REAL-FM-7 IDE | 14 | ~20 | 2 |
| arcade-game | 65 | ~60 | 34 |
| fqa | 179 | ~100 | 9 |
| REAL-FM-4 eshop | 291 | ~150 | 21 |
| busybox-1.18.0 | 854 | ~500 | 67 |
| ea2468 | 1,408 | ~800 | 1,281 |
| linux-2.6.33.3 | 6,467 | ~10,000 | 7,650 |

## Project Structure

```
AcqMSS/
├── conacq/                    # Core constraint acquisition package
│   ├── algorithms/            # ACQMSS, CONGEN, REDUCE, GenerateNE
│   │   └── interactive/       # QuAcq, learner, FindScope, FindC
│   ├── bias/                  # Bias generation from feature models
│   ├── example_generators/    # RS, 2-COV, FF + QueryGenerator, ExampleProvider
│   ├── examples/              # Example data structures + I/O utilities
│   ├── oracle/                # Oracle ABC, FeatureModelOracle, FMData, cached
│   ├── runners/               # ConGenRunner, InteractiveRunner (moved from eval/)
│   └── eval/                  # Accuracy, cross-validation, evaluator
├── explanation/               # SAT solver infrastructure
│   ├── models/                # DiagnosisModel, builder, task preparation
│   ├── operations/            # FastDiag, QuickXPlain, KBDiag, WipeOutR, HSDAG
│   └── transformations/       # FM → SAT converters
├── apps/                      # CLI applications + TOML configs
├── data/                      # Feature models, bias, examples, results
├── tests/                     # Parameterized test suite
└── docs/                      # Comprehensive documentation
```

## Configuration

All applications use TOML configuration files in `apps/conf/`. See [docs/codebase-summary.md](docs/codebase-summary.md) for details.

## Documentation

| Document | Focus |
|----------|-------|
| [docs/README.md](docs/README.md) | Documentation index and navigation |
| [docs/project-overview-pdr.md](docs/project-overview-pdr.md) | Goals, requirements, success criteria |
| [docs/codebase-summary.md](docs/codebase-summary.md) | Package structure, file inventory, dependencies |
| [docs/code-standards.md](docs/code-standards.md) | Naming, patterns, testing, style guide |
| [docs/system-architecture.md](docs/system-architecture.md) | Components, data flow, design patterns |
| [docs/project-roadmap.md](docs/project-roadmap.md) | Phase progress, timeline, milestones |
| [docs/quacq.md](docs/quacq.md) | QuAcq algorithm documentation (IJCAI 2013) |
| [docs/congen.md](docs/congen.md) | ConGen algorithm documentation (MSS-based acquisition) |

## Contributing

1. Follow code standards in `docs/code-standards.md`
2. Add tests for new features
3. Ensure all tests pass: `PYTHONPATH=. pytest tests/ -v`
4. Update documentation in `docs/` if applicable

## License

MIT License. See LICENSE file for details.

## Citation

If you use AcqMSS in your research, please cite:

```bibtex
@software{acqmss2026,
  author = {Leviet, Man},
  title = {AcqMSS: Constraint Acquisition With Maximum Satisfiable Subsets},
  year = {2026},
  url = {https://github.com/manleviet/AcqMSS}
}
```

---

**Version**: 1.0 | **Python**: 3.13+ | **Status**: Production research system | **Last Updated**: 2026-02-17
