# AcqMSS Code Standards & Guidelines

**Last Updated**: 2026-06-19 (Phase R refactor: immutable KB, pure Task, ConsistencyExecutor Protocol, operation-level solver mode, VariableCodec single source of truth)

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

High-level interfaces hiding complexity. QuAcqRunner demonstrates the pattern with name resolution:

```python
from conacq.algorithms.quacq import QuAcqModelBuilder, QuAcq, DiscriminatingGenerator
from conacq.example_generators import QueryProvider
from conacq.oracle import FeatureModelOracle

class QuAcqRunner:
    """High-level interface for QuAcq learning (DI-based, returns resolved KB)."""

    def run(self, positive_examples=None, negative_examples=None, mode='oracle'):
        """Learn constraints interactively, resolve names."""
        from explanation.operations.algorithms.checker import CheckerFactory
        
        # Prepare task (fresh per run)
        task = self.model.prepare_task(TaskInput(), self.oracle)
        
        # Create checker from Task (operation-level control)
        checker = CheckerFactory.create_from_task(task, solver_name='glucose4', use_incremental=True)
        
        # Inject checker + task into collaborators
        query_prov = QueryProvider(checker=checker, task=task, codec=task.codec)
        discrim_gen = DiscriminatingGenerator(checker, task, task.set_b[0])
        
        quacq = QuAcq.for_oracle(checker, self.oracle, query_prov, discrim_gen)

        # Algorithm returns raw assumption IDs
        result = quacq.learn(
            set_c=self.model.task.set_c, set_b=self.model.task.set_b,
            set_kb=self.model.task.set_kb, negation_map=self.model.task.negation_map,
            assumptions=self.model.task.assumptions,
            background_clauses=self.model.task.background_clauses,
            feature_ids=self.model.task.feature_ids, id_to_feature=self.model.task.id_to_feature,
            constraint_clauses=self.model.task.constraint_clauses,
            negated_clauses=self.model.task.negated_clauses,
            mode=mode, max_queries=self.max_queries)

        # Runner resolves names (matches ConGen pattern)
        kb_names, kb_clauses = self.model.resolve_kb(result.kb_assumption_ids)
        return QuAcqRunResult(
            kb_constraints=kb_names, kb_clauses=kb_clauses,
            n_kb=result.n_kb, n_queries=result.n_queries, ...)

# Usage
oracle = FeatureModelOracle('model.uvl')
model = QuAcqModelBuilder.from_bias('bias.json').with_oracle(oracle).build()
runner = QuAcqRunner(bias_path, fm_path)
result = runner.run(mode='oracle')
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

### 5. Dependency Injection & Executor Pattern (Phase R)

Pass dependencies as constructor parameters and via factories. **Key change**: solver mode is operation-level, not KB-level.

**Immutable KB + Pure Task Pattern**:
```python
# Build once (immutable KB)
model = ConGenModelBuilder.from_bias('bias.json').with_oracle(oracle).build()

# Prepare per fold (pure function; fresh Task each call)
task_input = TaskInput(positive_examples=fold_pos, negative_examples=fold_neg)
task = model.prepare_task(task_input)  # Returns fresh ConGenTask; no mutation

# Create checker from Task (operation-level control)
checker = CheckerFactory.create_from_task(
    task,
    solver_name='glucose4',
    use_incremental=True,    # Control at operation, not KB
    profiler_instance=profiler
)

# Inject executor (serial or parallel)
congen = ConGen(checker=checker, profiler=profiler)
result = congen.acquire(set_b=task.set_b, set_bg=task.set_c, ...)
```

**ConsistencyExecutor Protocol** (algorithms depend on this abstraction):
```python
from typing import Protocol, Future

class ConsistencyExecutor(Protocol):
    """Service for running consistency checks (serial or parallel)."""
    def is_consistent(set_c: List[int]) -> bool
    def is_consistent_test_cases(set_c, set_tc, stop) -> List
    def solve(set_c) -> Tuple[bool, Optional[List[int]]]  # Returns (sat, model)
    def submit(set_c) -> Future[bool]  # Async lookahead (FastDiagP)

# Serial executor (ConsistencyChecker itself)
checker = CheckerFactory.create_from_task(task, use_incremental=True)
# checker is a ConsistencyChecker (which implements ConsistencyExecutor)

# Parallel executor (ProcessExecutor wrapping checker)
executor = ProcessExecutor(set_kb, assumptions, solver_name, use_incremental)
memo_executor = MemoizingExecutor(executor)  # Add caching

# Both have identical method signatures; algorithms work with either
```

**ConGen** (passive learning with executor):
```python
class ConGen:
    def __init__(self, checker: ConsistencyExecutor, profiler=None):
        self.checker = checker  # Can be serial or parallel
        self.profiler = profiler or NullProfiler()

    def acquire(self, set_b, set_bg, set_tc, set_neg_tv, negation_map) -> ConGenResult:
        """Learn constraints using injected executor."""
        # No awareness of executor type; works with either serial or parallel
        ...
```

**QuAcq** (interactive learning, Phase R):
```python
class QuAcq:
    """Interactive learning with Task-based DI."""
    def __init__(self, oracle: Oracle, query_provider: QueryProvider = None,
                 discriminating_generator: DiscriminatingGenerator = None,
                 profiler: AbstractProfiler = None):
        self.oracle = oracle
        self.query_provider = query_provider
        self.discriminating_generator = discriminating_generator

    def learn(self, set_c, set_b, set_kb, negation_map, assumptions,
              background_clauses, feature_ids, id_to_feature,
              constraint_clauses, negated_clauses,
              mode='oracle', max_queries=1000) -> QuAcqResult:
        """Run learning (Task-centric, returns raw IDs; runner resolves names).
        
        Modes: 'oracle'/'automated'/'interactive', 'example_only', 'example_first'
        """
        # Mode dispatch via single parameter; no mutating state on QuAcq
        ...
```


# Usage: Build once, prepare+shuffle per fold (cross-validation, Phase R)

oracle = FeatureModelOracle('data/fms/model.uvl')
model = (ConGenModelBuilder
         .from_bias('data/bias/model.json')
         .with_oracle(oracle)           # Required for build-time negation
         .build())                       # Returns immutable KB (negation computed)

# Pattern: Build once, prepare+shuffle per fold
import random
from conacq.algorithms import TaskInput
from conacq.runners import ConGenRunner

# Recommended: Use ConGenRunner facade
runner = ConGenRunner('data/bias/model.json', 'data/fms/model.uvl')
try:
    for fold_idx, (fold_pos, fold_neg) in enumerate(folds):
        # runner handles prepare(task_input, oracle) + shuffle + acquire
        result = runner.run(fold_pos, fold_neg, shuffle_seed=fold_idx + 42)
finally:
    runner.cleanup()

# Manual control (when needed):
from explanation.operations.algorithms.checker import CheckerFactory
from conacq.algorithms import ConGen

task_input = TaskInput(positive_examples=fold_pos, negative_examples=fold_neg)
task = model.prepare_task(task_input, oracle)  # Pure function → fresh Task
random.Random(seed).shuffle(task.set_c)         # Shuffle after prepare
checker = CheckerFactory.create_from_task(task, solver_name='glucose4', use_incremental=True)
congen = ConGen(checker=checker)
result = congen.acquire(set_b=task.set_b, set_bg=task.set_c, 
                       set_tc=task.set_tc, set_neg_tv=task.set_neg_tv, 
                       negation_map=task.negation_map)
```

**Benefits**:
- Easy to test (inject mock checker)
- Loose coupling
- **Mode-agnostic**: No `if is_incremental` branching in algorithms

### 6. Shared Utility Methods

Extract duplicated logic into static/class methods. Example: Violation checking logic centralized in `QuAcqTask` and reused by QuAcq, FindScope, and FindC.

### 7. Interactive Learning Patterns

`QuAcqRunner` provides high-level facade for QuAcq learning. QuAcq processes negative examples with FindScope/FindC to identify violated constraints in both oracle and example-based modes.

### 8. Task-as-Unit Pattern (Phase R)

Models are immutable KBs; Tasks are immutable units of work. Each `model.prepare_task(task_input, oracle)` call returns a fresh, independent Task with its own assumption ID lists. All Tasks from the same KB share the same VariableCodec (KB-level single source of truth).

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

4. **FMOracleModel**: Assumption-guarded FM model (Phase R)
   - FM clauses in `set_kb` (always active)
   - Feature assignments as assumption-guarded unit clauses: `[-a_pos_i, fid]`, `[-a_neg_i, -fid]`
   - Implements `ModelProtocol` (immutable KB + `get_codec()`)
   - Exposes `bg_data` property for root constraint extraction

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

