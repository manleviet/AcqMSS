# AcqMSS Code Standards & Guidelines

**Last Updated**: 2026-02-18

## Language & Environment

- **Primary Language**: Python 3.13+
- **Type Hints**: Mandatory on all public functions
- **Docstring Style**: Google-style or NumPy (consistent per module)
- **Code Formatting**: ruff check/format
- **Type Checking**: mypy strict mode recommended
- **Testing**: pytest with @parameterized.expand
- **Module File Size**: ~200 lines (max ~300 for complex modules)

## Naming Conventions

### Modules & Files

- **Convention**: `snake_case` for all `.py` filenames
- **Rationale**: Python import convention, improves discoverability with tools (Glob, Grep)
- **Examples**:
  - ✓ `fastdiag.py`, `task_preparation.py`, `random_sampling.py`
  - ✗ `FastDiag.py`, `task-preparation.py` (breaks imports or conventions)

### Classes

- **Convention**: `PascalCase`
- **Examples**:
  ```python
  class FastDiag:          # Algorithm
  class DiagnosisModel:    # Data model
  class ConsistencyChecker: # Abstract base
  ```

### Functions & Methods

- **Convention**: `snake_case`
- **Private methods**: Prefix with `_`
- **Examples**:
  ```python
  def acquire(self, task):           # Public
  def _find_mss(self, bias, ne):     # Private
  def is_consistent(self, clauses):  # Query-like
  ```

### Constants & Enums

- **Convention**: `UPPER_SNAKE_CASE` for module-level constants
- **Examples**:
  ```python
  DEFAULT_SOLVER = 'glucose4'
  MAX_SOLVER_CALLS = 10000
  TIMEOUT_SECONDS = 300.0

  class ConstraintType(Enum):
      REQUIRES = 'requires'
      EXCLUDES = 'excludes'
  ```

### Variables

- **Convention**: `snake_case` (local, instance, class)
- **Boolean prefixes**: Prefer `is_`, `has_`, `should_`
- **Examples**:
  ```python
  self.learned_kb = []           # Instance
  is_consistent = checker(task)  # Local boolean
  has_conflict = len(diag) > 0   # Query result
  ```

## File Organization

### Module Structure

```python
"""
Module docstring: Brief description of module purpose.

Longer explanation if needed. May reference related modules.
"""

# Imports (grouped: stdlib → third-party → local)
from __future__ import annotations
from typing import Sequence, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from pysat.solvers import Solver
from flamapy.metamodels.fm_metamodel import FeatureModel

from explanation.models import DiagnosisModel
from .data_structures import Constraint

# Constants
DEFAULT_SOLVER = 'glucose4'
TIMEOUT_SECONDS = 300.0

# Classes
class MyAlgorithm(ABC):
    """Public class docstring."""
    pass

# Functions
def acquire(model: DiagnosisModel) -> list[Constraint]:
    """Function docstring with type hints."""
    pass

# Private functions
def _helper_function() -> None:
    """Private function."""
    pass
```

### Import Order

1. **Standard library** (abc, typing, pathlib, etc.)
2. **Third-party** (pysat, flamapy, pytest, etc.)
3. **Local relative** (from . or .. imports)

Use `from __future__ import annotations` for modern type syntax.

## Design Patterns

### 1. Abstract Base Classes (Strategy Pattern)

Used for pluggable solver implementations:

```python
from abc import ABC, abstractmethod

class ConsistencyChecker(ABC):
    """Abstract solver interface."""

    @abstractmethod
    def is_consistent(self, clauses: list[list[int]]) -> bool:
        """Check if clauses are satisfiable."""
        pass

class IncrementalPySATChecker(ConsistencyChecker):
    """Persistent solver with assumptions."""
    def is_consistent(self, clauses):
        # Persistent solver reuses state
        pass

class NonIncrementalPySATChecker(ConsistencyChecker):
    """Fresh solver per call."""
    def is_consistent(self, clauses):
        # Create new solver each time
        pass
```

**Benefits**:
- Testable with mock solvers
- Easy to swap implementations
- Clear contract for new solvers

### 2. Builder Pattern

For complex object construction:

```python
class DiagnosisModelBuilder:
    """Fluent builder for DiagnosisModel."""

    def __init__(self):
        self._feature_model = None
        self._solver_name = 'glucose4'

    def with_feature_model(self, fm: FeatureModel) -> DiagnosisModelBuilder:
        self._feature_model = fm
        return self

    def with_solver(self, name: str) -> DiagnosisModelBuilder:
        self._solver_name = name
        return self

    def build(self) -> DiagnosisModel:
        return DiagnosisModel(self._feature_model, self._solver_name)

# Usage
model = (DiagnosisModelBuilder()
         .with_feature_model(fm)
         .with_solver('glucose4')
         .build())
```

### 3. Facade Pattern

High-level interfaces hiding complexity:

```python
class InteractiveLearner:
    """High-level interface for QuAcq."""

    @classmethod
    def from_files(cls, fm_path: str, bias_path: str) -> InteractiveLearner:
        """Convenience constructor."""
        fm = load_feature_model(fm_path)
        bias = load_bias(bias_path)
        return cls(fm, bias)

    def learn(self, mode: str = 'automated', max_queries: int = 1000):
        """Learn constraints interactively."""
        pass

# Usage
learner = InteractiveLearner.from_files('model.uvl', 'bias.json')
result = learner.learn()
```

### 4. Template Method Pattern

Base class defines algorithm skeleton, subclasses fill steps:

```python
from abc import abstractmethod

class PySATAbstractExplanation(ABC):
    """Template for diagnosis operations."""

    def execute(self) -> list[Diagnosis]:
        """Execute diagnosis algorithm (template method)."""
        solver_instance = self._prepare_solver()
        result = self._diagnose(solver_instance)
        self._finalize(solver_instance)
        return result

    @abstractmethod
    def _diagnose(self, solver) -> list[Diagnosis]:
        """Subclass implements specific algorithm."""
        pass

class FastDiag(PySATAbstractExplanation):
    def _diagnose(self, solver):
        # FastDiag-specific implementation
        pass
```

### 5. Dependency Injection

Pass dependencies as constructor parameters:

```python
class ConGen:
    """Constraint acquisition via AcqMSS (mode-agnostic)."""

    def __init__(
            self,
            checker: ConsistencyChecker,
            profiler: Optional[Profiler] = None
    ):
        self.checker = checker  # Injected (Incremental or NonIncremental)
        self.profiler = profiler or NullProfiler()

    def acquire(
            self,
            set_b: List[int],  # Bias assumption IDs
            set_bg: List[int],  # Background assumption IDs
            set_tc: List[int],  # E+ assumption IDs
            set_neg_tv: List[int],  # NE assumption IDs
            negation_map: Dict[int, int]  # Maps assumption ID → negated ID for REDUCE
    ) -> CONGENResult:
        """Learn constraints using injected checker.

        Works identically with both checker types (no is_incremental branching).
        """
        with self.profiler.measure('acqmss'):
            mss = self._acqmss(set_b, set_neg_tv, set_tc, set_bg)
        return Result(mss)


# Usage with ConGenModelBuilder (fluent pattern)

# Pattern 1: Auto-prepare (oracle + examples set at build time)
oracle = FeatureModelOracle('data/fms/model.uvl')
model = (ConGenModelBuilder
         .from_bias('data/bias/model.json')
         .with_oracle(oracle)
         .with_examples('data/examples/model.json')
         .build())  # Returns prepared model (ready to use)

# Pattern 2: Manual prepare (cross-validation reuse)
model = ConGenModelBuilder.from_bias('data/bias/model.json').build()  # Unprepared
oracle = FeatureModelOracle('data/fms/model.uvl')
model.prepare(oracle, positive_examples=pos, negative_examples=neg)  # GenerateNE called internally

# Create checker and run ConGen
from explanation.operations.algorithms.checker import CheckerFactory, CheckerModel

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
    checker = CheckerFactory.create_from_model(model, profiler)
    # Use model.task for this fold
```

**Benefits**:
- Easy to test (inject mock checker)
- Loose coupling
- **Mode-agnostic**: No `if is_incremental` branching in algorithms

### 6. Shared Utility Methods

Extract duplicated logic into static/class methods. Example: `InteractiveTask.violates_clauses()` used by QuAcq, FindScope, and FindC centralizes violation checking logic in one place.

### 7. Interactive Learning Patterns

`InteractiveLearner` provides high-level facade for QuAcq learning modes (oracle-based or example-based). QuAcq processes negative examples with FindScope/FindC to identify violated constraints.

### 8. CheckerModel Protocol (Duck Typing)

Classes implementing `CheckerModel` must provide:
- `get_kb() -> List[List[int]]` — Return CNF clauses
- `get_assumptions() -> List[int]` — Return all possible assumptions
- `use_incremental: bool` — Flag for solver mode preference

Both `ConGenModel` and `FMOracleModel` implement this protocol for integration with `CheckerFactory`.

## Oracle Module Conventions

**Package**: `conacq/oracle/` — Minimal, focused oracle abstraction

**Oracle ABC**: Minimal interface — only `is_valid(assignments)` abstract; `ask()` concrete alias.

**Key Classes**:

1. **FMData** (`@dataclass(frozen=True)`): Immutable FM metadata container
   - Fields: `features`, `feature_ids`, `root_feature`, `num_constraints`, `next_available_id`, `feature_count` property
   - Created by `FeatureModelOracle.get_fm_data()`, passed explicitly to decouple callers

2. **BGData** (`@dataclass(frozen=True)`): Root background knowledge constraint data
   - Fields: `set_kb` (assumption-guarded clauses), `assumptions` (tuple of root and negated IDs), `negation_map`, `descriptions`, `next_available_id`
   - Created by `FMOracleModel.get_bg_data()` after task preparation
   - Enables ConGen to cleanly allocate assumption IDs without overlap with oracle assumptions

3. **FeatureModelOracle**: Main FM oracle
   - ABC methods: `is_valid()`, `ask()`
   - FM extensions: `get_fm_data()`, `get_features()`, `get_feature_ids()`, `get_root_feature()`, `get_num_constraints()`, `get_next_available_id()`, `complete_configuration()`, `get_cnf_clauses()`, `get_constraint_descriptions()`
   - Delegates to `FMOracleModel` for consistency checking
   - Uses incremental solver by default

4. **FMOracleModel**: Assumption-guarded FM model
   - FM clauses in `set_kb` (always active)
   - Feature assignments as assumption-guarded unit clauses: `[-a_pos_i, fid]`, `[-a_neg_i, -fid]`
   - Satisfies `CheckerModel` protocol for `CheckerFactory`
   - Exposes `bg_data` property and `get_bg_data()` method to extract root constraint

5. **UserPromptOracle**: Interactive human oracle (implements `is_valid()` only)

6. **CachedOracle**: Transparent caching wrapper (caches `is_valid()`, delegates FM methods)

**Design Principles**:
- Minimal ABC (only `is_valid()`)
- FM metadata via `FMData` (decoupled)
- FM-specific methods on `FeatureModelOracle` (not ABC)
- Example generators typed as `FeatureModelOracle` (not generic `Oracle`)

**Critical**: Feature ID consistency — `FMOracleModel.variables` uses flamapy's tree traversal order (source: `FmToPysat.variables`). **Never** sort alphabetically — breaks SAT clause literal mapping.

## Testing Strategy

### Test Structure

Use `@parameterized.expand` for testing across solver modes:

```python
from parameterized import parameterized

class TestFastDiag(unittest.TestCase):

    ENABLED_TESTS = {
        'fastdiag_basic': True,
        'fastdiag_hsdag': True,
        'fastdiag_large': False,  # Disabled for quick runs
    }

    ENABLED_PARAMS = {
        'incremental': True,
        'non_incremental': True,
        'sat4j': False,  # Optional Java solver
    }

    @parameterized.expand([
        ('incremental', IncrementalPySATChecker),
        ('non_incremental', NonIncrementalPySATChecker),
    ])
    def test_fastdiag_basic(self, name, checker_class):
        if not self.ENABLED_PARAMS[name]:
            self.skipTest(f'{name} disabled')

        result = fastdiag(self.model, checker=checker_class(self.solver))
        self.assertGreater(len(result), 0)
```

### Test Naming Conventions

- `test_<algorithm>_<scenario>` — Algorithm tests
- `test_<class>_<method>` — Class method tests
- `test_<feature>` — Feature tests
- Use descriptive names over generic `test_1`, `test_2`

### Coverage Requirements

- Core algorithms: ≥90%
- SAT operations: ≥85%
- Data structures: ≥80%
- I/O utilities: ≥70% (less critical)
- CLI applications: ≥60% (tested via integration)

## Documentation Standards

### Module Docstrings

```python
"""
constraint_acquisition.py

Constraint acquisition algorithms for learning from examples.

This module implements ConGen (passive learning) and QuAcq (interactive learning)
paradigms for discovering constraints from feature models using SAT solvers.

Classes:
    ConGen: Divide-and-conquer constraint acquisition
    QuAcq: Interactive query-based learning

Functions:
    acquire_constraints(): High-level acquisition function

Dependencies:
    - explanation.operations.algorithms: Diagnosis algorithms
    - acqmss.bias: Bias constraint handling
"""
```

### Class Docstrings

```python
class CONGEN:
    """Learn constraints via divide-and-conquer MSS finding.

    ConGen (Constraint Generalization) acquires constraints from positive and
    negative example sets by:
    1. Generating negated examples from negative examples
    2. Finding maximum satisfiable subset of bias constraints
    3. Removing redundant constraints

    Args:
        checker: Consistency checker (incremental or non-incremental)
        profiler: Optional profiler for timing/counting (default: NullProfiler)

    Attributes:
        checker (ConsistencyChecker): Solver interface
        profiler (Profiler): Execution profiler

    Example:
        >>> checker = IncrementalPySATChecker(solver)
        >>> congen_root = ConGen(checker, profiler=None)
        >>> result = congen_root.acquire(task)
        >>> print(len(result.kb))
    """
```

### Function/Method Docstrings

```python
def is_consistent(
    self,
    clauses: list[list[int]],
    assumptions: Optional[list[int]] = None
) -> bool:
    """Check if clauses are satisfiable under assumptions.

    Evaluates SAT consistency using the configured solver.

    Args:
        clauses: List of clauses (list of integer literals)
        assumptions: Optional list of unit assumptions (int literals)

    Returns:
        True if satisfiable, False if unsatisfiable

    Raises:
        ValueError: If clauses not in valid CNF format
        TimeoutError: If solver exceeds timeout

    Example:
        >>> checker = IncrementalPySATChecker(solver)
        >>> clauses = [[1, -2], [-1, 3]]
        >>> checker.is_consistent(clauses)
        True
    """
```

## Type Hints

### Requirements

- **All public functions/methods**: Type hints on parameters and return
- **Private functions**: Type hints recommended
- **Complex types**: Use `from __future__ import annotations`

### Examples

```python
from typing import Optional, Sequence, Callable
from pathlib import Path

def load_feature_model(path: Path) -> FeatureModel:
    """Load FM from file."""
    pass

def acquire(
    bias: list[Constraint],
    examples: tuple[list[Configuration], list[Configuration]],
    checker: ConsistencyChecker,
    timeout: Optional[float] = None
) -> Result:
    """Acquire constraints."""
    pass

def create_checker(
    solver_factory: Callable[[], Solver],
    name: str = 'glucose4'
) -> ConsistencyChecker:
    """Create solver checker."""
    pass
```

## Error Handling

### Exception Hierarchy

Create domain-specific exceptions:

```python
class AcqMSSException(Exception):
    """Base exception for AcqMSS."""
    pass

class SolverException(AcqMSSException):
    """Solver-related errors."""
    pass

class TimeoutException(SolverException):
    """Solver timeout exceeded."""
    pass

class InconsistentBiasException(AcqMSSException):
    """Bias constraints are unsatisfiable."""
    pass
```

### Usage

```python
def is_consistent(self, clauses):
    try:
        result = self.solver.solve(clauses)
    except TimeoutError as e:
        raise TimeoutException(f"Solver timeout after {self.timeout}s") from e
    except Exception as e:
        raise SolverException(f"Solver error: {e}") from e

    if result is None:
        raise InconsistentBiasException("Unsatisfiable formula")

    return result
```

## Configuration Management

### No Hard-Coded Values

All configuration via TOML files:

```python
# Bad
SOLVER_NAME = 'glucose4'
MAX_CALLS = 10000

# Good
config = load_config('apps/conf/run_congen_config.toml')
solver_name = config['settings']['solver']
max_calls = config['settings']['max_solver_calls']
```

### Configuration Structure

```toml
[input]
bias_file = "data/bias/arcade-game.json"
examples_file = "data/examples/arcade-game_RS_100.json"

[settings]
incremental = true
solver = "glucose4"
max_solver_calls = 10000
timeout_seconds = 300.0

[output]
result_file = "data/results/arcade-game_CONGEN.json"
profiling_file = "data/results/arcade-game_profile.json"
```

## Performance Considerations

### Solver Efficiency

1. **Incremental solver** (default):
   - Persistent solver instance
   - Reuse across calls with assumptions
   - ~50x faster for repeated checks

2. **Non-incremental mode**:
   - Fresh solver per call
   - Memory-light baseline
   - Use for verification/comparison

3. **HSDAG optimization**:
   - Tree search reduces solver calls
   - ~10x speedup typical
   - Automatic when available

### Profiling

Use decorator pattern for minimal overhead:

```python
from explanation.operations.profiler import Profiler

profiler = Profiler()

@profiler.measure('algorithm_name')
def run_algorithm(task):
    # Automatically timed
    pass

# Access results
timing = profiler.get_timing('algorithm_name')
call_count = profiler.get_count('sat_check')
```

## Security Considerations

### Input Validation

- Validate all external input (files, configs, command-line args)
- Type-check function parameters
- Reject malformed feature models early

### Resource Limits

- Set `timeout_seconds` for solver invocations
- Limit `max_solver_calls` to prevent infinite loops
- Monitor memory usage for large models

### File Handling

Use `pathlib.Path` for cross-platform safety:

```python
from pathlib import Path

# Good
config_path = Path('apps/conf/config.toml')
data_path = Path('data/results') / 'output.json'

# Less safe
config_path = 'apps/conf/config.toml'
```

## Code Review Checklist

Before submitting PR:
- [ ] Type hints on all public functions
- [ ] Docstrings on all public modules/classes/functions
- [ ] Error handling for all exception cases
- [ ] Tests for new code (≥80% coverage, pass both incremental/non-incremental modes)
- [ ] Code follows naming conventions
- [ ] No unused imports or variables
- [ ] Configuration externalized (not hard-coded)

## Style Guide Quick Reference

| Element | Convention | Example |
|---------|-----------|---------|
| Module | snake_case | `task_preparation.py` |
| Class | PascalCase | `class FastDiag` |
| Function | snake_case | `def acquire()` |
| Constant | UPPER_SNAKE_CASE | `MAX_CALLS = 10000` |
| Variable | snake_case | `learned_kb` |
| Boolean | is_/has_/should_ | `is_consistent` |
| Type hints | ✓ Required on public | `def acquire(task: Task)` |
| Docstrings | Google-style | Module, class, function |

