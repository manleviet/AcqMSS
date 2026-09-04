# Phase 1: Modify Checker Interface + Implementations

## Context Links
- Source: `explanation/operations/algorithms/checker.py`
- [Plan](plan.md)

## Overview
- **Priority**: High (unblocks all other phases)
- **Status**: COMPLETE
- **Description**: Add `add_clause()`/`add_assumption()` to base class.
  Modify `NonIncrementalPySATChecker` and `SAT4JChecker` to accept
  `set_kb` + `assumptions` and use assumption-based solving.

## Key Insights
- `IncrementalPySATChecker` already works with assumptions. No change needed.
- `NonIncrementalPySATChecker` currently takes no `set_kb`/`assumptions`.
  `is_consistent(set_c)` receives clause lists and creates fresh solver with them.
- `SAT4JChecker` writes clauses to temp CNF file, runs java subprocess.
  Has no assumption support at all.
- PySAT's `Solver.solve(assumptions=[...])` is the incremental mechanism.
  For non-incremental: create fresh solver with same `set_kb`, solve with same
  assumption list, delete solver.
- SAT4J: assumptions encoded as unit clauses `[a]`/`[-a]` appended to CNF.
  Semantically identical to PySAT assumptions.

## Requirements
1. `ConsistencyChecker` gets `add_clause()` and `add_assumption()` methods
2. `NonIncrementalPySATChecker.__init__` accepts `set_kb`, `assumptions`
3. `NonIncrementalPySATChecker.is_consistent(set_c: List[int])` uses
   assumption-based solving with fresh solver
4. `SAT4JChecker.__init__` accepts `set_kb`, `assumptions`
5. `SAT4JChecker.is_consistent(set_c: List[int])` uses unit clauses for
   assumptions
6. `CheckerFactory.create_from_model()` passes `set_kb`/`assumptions` to
   non-incremental checker too

## Related Code Files
- **Modify**: `explanation/operations/algorithms/checker.py`
  - `ConsistencyChecker` (line 100): add `add_clause()`, `add_assumption()`
  - `NonIncrementalPySATChecker` (line 278): new init + is_consistent
  - `SAT4JChecker` (line 362): new init + is_consistent
  - `CheckerFactory` (line 452): update `create_from_model()`

## Implementation Steps

### Step 1: Add methods to `ConsistencyChecker` base class

```python
def add_clause(self, clause: List[int]) -> None:
    """Add a clause to the knowledge base.
    Incremental: adds to live solver + set_kb.
    Non-incremental: adds to set_kb only (next fresh solver gets it).
    """
    pass  # Default no-op; subclasses override

def add_assumption(self, assumption_id: int) -> None:
    """Register a new assumption ID."""
    pass  # Default no-op; subclasses override
```

### Step 2: Implement in `IncrementalPySATChecker`

```python
def add_clause(self, clause: List[int]) -> None:
    self.solver.add_clause(clause)
    self.set_kb.append(clause)

def add_assumption(self, assumption_id: int) -> None:
    self.assumptions.append(assumption_id)
```

### Step 3: Modify `NonIncrementalPySATChecker`

New init:
```python
def __init__(self, set_kb: List[List[int]], assumptions: List[int],
             solver_name: str = 'glucose3',
             profiler_instance: AbstractProfiler = None) -> None:
    super().__init__(profiler_instance)
    self.solver_name = solver_name
    self.set_kb = set_kb
    self.assumptions = assumptions
```

New `is_consistent`:
```python
def is_consistent(self, set_c: List[int]) -> bool:
    # Same assumption logic as incremental
    delta = [a for a in self.assumptions if a not in set_c]
    final_assumptions = set_c + [-a for a in delta]

    solver = Solver(self.solver_name, bootstrap_with=self.set_kb,
                    use_timer=True)
    self.result = solver.solve(assumptions=final_assumptions)
    self.profiler.record_time("solver_time", solver.time())
    solver.delete()
    return self.result
```

New `add_clause` / `add_assumption`:
```python
def add_clause(self, clause: List[int]) -> None:
    self.set_kb.append(clause)

def add_assumption(self, assumption_id: int) -> None:
    self.assumptions.append(assumption_id)
```

Update `copy`:
```python
def copy(self):
    return NonIncrementalPySATChecker(
        list(self.set_kb), list(self.assumptions),
        self.solver_name, self.profiler
    )
```

### Step 4: Modify `SAT4JChecker`

New init:
```python
def __init__(self, set_kb: List[List[int]] = None,
             assumptions: List[int] = None,
             jar_path: str = "solver_apps/org.sat4j.core.jar",
             profiler_instance: AbstractProfiler = None,
             timeout: int = 300) -> None:
    super().__init__(profiler_instance)
    self.jar_path = jar_path
    self.timeout = timeout
    self.set_kb = set_kb or []
    self.assumptions = assumptions or []
    # Validate jar file exists
    if not os.path.exists(jar_path):
        raise FileNotFoundError(...)
```

New `is_consistent`:
```python
def is_consistent(self, set_c: List[int]) -> bool:
    # Encode assumptions as unit clauses
    delta = [a for a in self.assumptions if a not in set_c]
    assumption_clauses = [[a] for a in set_c] + [[-a] for a in delta]

    with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf',
                                     delete=True) as f:
        cnf = CNF()
        cnf.extend(self.set_kb + assumption_clauses)
        cnf.to_file(f.name)
        # ... subprocess call unchanged ...
```

New `add_clause` / `add_assumption`:
```python
def add_clause(self, clause: List[int]) -> None:
    self.set_kb.append(clause)

def add_assumption(self, assumption_id: int) -> None:
    self.assumptions.append(assumption_id)
```

### Step 5: Update `CheckerFactory.create_from_model()`

```python
@staticmethod
def create_from_model(model, solver_name='glucose3',
                      profiler_instance=None):
    if model.use_incremental:
        return IncrementalPySATChecker(
            model.get_kb(), model.get_assumptions(),
            solver_name, profiler_instance)
    else:
        return NonIncrementalPySATChecker(
            model.get_kb(), model.get_assumptions(),
            solver_name, profiler_instance)
```

### Step 6: Update `CheckerFactory.create_sat4jchecker()`

Add optional `set_kb`/`assumptions` params:
```python
@staticmethod
def create_sat4jchecker(profiler_instance=None,
                        sat4j_jar_path="solver_apps/org.sat4j.core.jar",
                        set_kb=None, assumptions=None):
    return SAT4JChecker(set_kb=set_kb, assumptions=assumptions,
                        jar_path=sat4j_jar_path,
                        profiler_instance=profiler_instance)
```

## Todo List
- [x] Add `add_clause()` + `add_assumption()` to `ConsistencyChecker`
- [x] Implement in `IncrementalPySATChecker`
- [x] Rewrite `NonIncrementalPySATChecker` with `set_kb`/`assumptions`
- [x] Rewrite `SAT4JChecker` with `set_kb`/`assumptions`
- [x] Update `CheckerFactory.create_from_model()`
- [x] Update `CheckerFactory.create_sat4jchecker()`
- [x] Verify imports compile: `python -c "from explanation.operations.algorithms.checker import *"`

## Success Criteria
- All 3 checkers accept `set_kb` + `assumptions`
- `is_consistent(set_c: List[int])` works uniformly for all checkers
- `add_clause()` / `add_assumption()` work for all checkers
- Existing incremental tests still pass (IncrementalPySATChecker unchanged)

## Risk Assessment
- **Breaking callers**: All code that instantiates `NonIncrementalPySATChecker()`
  or `SAT4JChecker()` without `set_kb`/`assumptions` will break.
  Must update callers (Phase 2 for CONGEN, Phase 4 for QuAcq, Phase 5 for
  diagnosis).
- **Mitigation**: Default `set_kb=[]`, `assumptions=[]` for backward compat
  during transition. Remove defaults after all callers updated.
