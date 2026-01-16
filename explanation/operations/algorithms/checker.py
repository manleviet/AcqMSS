"""
Consistency Checker implementations for Consistency-Based Algorithms

This module provides different strategies for checking consistency of CNF formulas
in constraint-based systems. All checkers implement a common interface
and support multiprocessing through pickling.

Available Implementations
-------------------------
1. **IncrementalPySATChecker**: Uses PySAT with incremental solving
   - Maintains persistent solver instance
   - Uses assumptions to enable/disable constraints
   - Most efficient for multiple checks on same knowledge base
   - Supports pickling for multiprocessing

2. **NonIncrementalPySATChecker**: Uses PySAT with fresh solver for each check
   - Creates new solver for each consistency check
   - Simpler but less efficient than incremental mode
   - Supports pickling for multiprocessing

3. **SAT4JChecker**: Uses external SAT4J solver via subprocess
   - Calls Java-based SAT4J solver
   - Slower due to I/O overhead
   - Useful for cross-validation or SAT4J-specific features
   - Supports pickling for multiprocessing

Factory Pattern
---------------
Use `CheckerFactory` to create checker instances:
- `create_from_model()`: Create checker based on DiagnosisModel configuration
- `create_sat4jchecker()`: Create SAT4J checker directly

Usage Examples
--------------
Basic usage with context manager::

    from .checker import CheckerFactory
    from .pysat_diagnosis_model import DiagnosisModel

    # Create checker from model
    model = DiagnosisModel(...)
    model.is_incremental = True
    model.prepare_diagnosis_task()

    with CheckerFactory.create_from_model('glucose3', model) as checker:
        result = checker.is_consistent(model.get_c())
        print(f"Consistent: {result}")
    # Cleanup happens automatically

Multiprocessing support (e.g., with FastDiagP):

    from multiprocessing import Pool

    # Create checker
    checker = CheckerFactory.create_from_model('glucose3', model)

    # Use in parallel
    with Pool(4) as pool:
        results = pool.map(some_function, [checker.copy() for _ in range(4)])

SAT4J usage::

    # Create SAT4J checker
    checker = CheckerFactory.create_sat4jchecker(
        sat4j_jar_path="solver_apps/org.sat4j.core.jar"
    )

    # Use like any other checker
    result = checker.is_consistent(clauses)

Pickling Protocol
-----------------
All checkers implement `__getstate__` and `__setstate__` for serialization:
- Profiler instances are excluded (contain thread locks)
- Solver instances are excluded (C extensions, not picklable)
- On unpickling, profiler and solvers are recreated

Thread Safety
-------------
- Checkers are NOT thread-safe (use separate instances per thread)
- For multiprocessing, use `checker.copy()` to create independent instances

References
----------
Java implementation reference:
https://github.com/HiConfiT/hiconfit-core/blob/main/ca-cdr-package/src/main/java/at/tugraz/ist/ase/cacdr/checker/ChocoConsistencyChecker.java
"""
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from typing import List

from pysat.formula import CNF
from pysat.solvers import Solver

from .profiler import get_global_profiler, count_calls, AbstractProfiler
from ...models.pysat_diagnosis_model import DiagnosisModel


class ConsistencyChecker(ABC):
    """
    Abstract base class for consistency checkers.

    All implementations must support:
    - Checking consistency of CNF formulas
    - Creating copies for multiprocessing
    - Resource cleanup
    - Context manager protocol
    """

    def __init__(self, profiler_instance: AbstractProfiler = None):
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        self.result = False

    @abstractmethod
    def is_consistent(self, set_c: List) -> bool:
        """
        Check if the given CNF formula is consistent.

        :param set_c: a list of assumptions or clauses
        :return: True if consistent, False otherwise
        """
        pass

    @count_calls(key="is_consistent_test_cases_calls")
    def is_consistent_test_cases(self, set_c: List, set_tc: List, stop_at_first_violation: bool) -> List:
        """
        Check consistency with multiple test cases.

        :param set_c: constraints to check with
        :param set_tc: list of test case assumptions
        :param stop_at_first_violation: if True, return after first inconsistent test case
        :return: list of inconsistent test cases
        """
        set_tcp = []
        # Accumulates inconsistent test cases, stopping if `only_one`
        for tc in set_tc:
            if not self.is_consistent(set_c + [tc]):
                set_tcp.append(tc)
            if stop_at_first_violation and len(set_tcp) > 0:
                break

        return set_tcp

    @abstractmethod
    def copy(self):
        """
        Create a copy of this checker for use in multiprocessing.

        :return: a new instance with the same configuration
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Release any resources held by this checker.
        """
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


class IncrementalPySATChecker(ConsistencyChecker):
    """
    Incremental consistency checker using PySAT.

    This implementation maintains a persistent solver instance and uses
    assumptions to enable/disable constraints. More efficient for multiple
    consistency checks on the same knowledge base.

    The solver is bootstrapped with set_kb and uses assumptions to control
    which constraints are active.
    """

    def __init__(self, set_kb: List[List[int]], assumptions: List[int],
                 solver_name: str = 'glucose3', profiler_instance: AbstractProfiler = None) -> None:
        """
        Initialize incremental checker.

        :param set_kb: Knowledge base as CNF clauses with assumption literals
        :param assumptions: List of assumption literals that control constraints
        :param solver_name: Name of PySAT solver (e.g., 'glucose3', 'minisat22')
        :param profiler_instance: Optional profiler for metrics tracking
        """
        super().__init__(profiler_instance)
        self.solver_name = solver_name
        self.set_kb = set_kb
        self.assumptions = assumptions
        self.solver = Solver(solver_name, bootstrap_with=set_kb, use_timer=True)

    @count_calls(key="is_consistent_calls")
    def is_consistent(self, set_c: List) -> bool:
        """
        Check consistency using incremental solving with assumptions.

        :param set_c: list of assumption literals to enable
        :return: True if B ∪ C is consistent
        """
        # Calculate which assumptions to disable (delta)
        # delta = assumptions \ set_c
        delta = [item for item in self.assumptions if item not in set_c]

        # Build final assumptions: enable set_c, disable delta
        # assumptions = set_c + ¬delta
        final_assumptions = set_c + [-1 * item for item in delta]

        # Solve with assumptions
        self.result = self.solver.solve(assumptions=final_assumptions)

        # Track solver time
        self.profiler.record_time("solver_time", self.solver.time())
        if self.solver.time_accum() is not None:
            self.profiler.set_gauge("solver_time_accum", self.solver.time_accum())

        return self.result

    # @count_calls(key="is_consistent_test_cases_calls")
    # def is_consistent_test_cases(self, set_c: List, set_tc: List, only_one: bool) -> List:
    #     """
    #     Check consistency with multiple test cases.
    #
    #     :param set_c: constraints to check with
    #     :param set_tc: list of test case assumptions
    #     :param only_one: if True, return after first inconsistent test case
    #     :return: list of inconsistent test cases
    #     """
    #     set_tcp = []
    #     # Accumulates inconsistent test cases, stopping if `only_one`
    #     for tc in set_tc:
    #         if not self.is_consistent(set_c + [tc]):
    #             set_tcp.append(tc)
    #         if only_one and len(set_tcp) > 0:
    #             break
    #
    #     return set_tcp

    def copy(self):
        """Create a new instance with the same configuration for multiprocessing."""
        return IncrementalPySATChecker(
            self.set_kb,
            self.assumptions,
            self.solver_name,
            self.profiler
        )

    def cleanup(self) -> None:
        """Delete the PySAT solver instance."""
        if hasattr(self, 'solver') and self.solver is not None:
            self.solver.delete()
            self.solver = None

    def __getstate__(self):
        """Prepare object for pickling - exclude profiler."""
        state = self.__dict__.copy()
        # Remove the unpicklable profiler
        state['profiler'] = None
        # Remove the solver object as it cannot be pickled
        if 'solver' in state:
            state['solver'] = None
        return state

    def __setstate__(self, state):
        """Restore object from pickle."""
        self.__dict__.update(state)
        # Restore default profiler
        if self.profiler is None:
            self.profiler = get_global_profiler()
        # Recreate solver with stored config
        if hasattr(self, 'solver_name') and hasattr(self, 'set_kb'):
            self.solver = Solver(self.solver_name, bootstrap_with=self.set_kb, use_timer=True)


class NonIncrementalPySATChecker(ConsistencyChecker):
    """
    Non-incremental consistency checker using PySAT.

    This implementation creates a fresh solver for each consistency check.
    Simpler than incremental mode but less efficient for repeated checks.

    The input set_c should be a list of lists (CNF clauses).
    """

    def __init__(self, solver_name: str = 'glucose3', profiler_instance: AbstractProfiler = None) -> None:
        """
        Initialize non-incremental checker.

        :param solver_name: Name of PySAT solver (e.g., 'glucose3', 'minisat22')
        :param profiler_instance: Optional profiler for metrics tracking
        """
        super().__init__(profiler_instance)
        self.solver_name = solver_name

    @count_calls(key="is_consistent_calls")
    def is_consistent(self, set_c: List) -> bool:
        """
        Check consistency by creating a fresh solver.

        :param set_c: list of lists representing CNF clauses
        :return: True if the formula is satisfiable
        """
        # Flatten set_c from list of lists to single list of clauses
        cnf = [clause for c in set_c for clause in c]

        # Create fresh solver
        solver = Solver(self.solver_name, bootstrap_with=cnf, use_timer=True)
        self.result = solver.solve()

        # Track solver time
        self.profiler.record_time("solver_time", solver.time())

        # Clean up immediately
        solver.delete()

        return self.result

    # @count_calls(key="is_consistent_test_cases_calls")
    # def is_consistent_test_cases(self, set_c: List, set_tc: List, only_one: bool) -> List:
    #     """
    #     Check consistency with multiple test cases.
    #
    #     :param set_c: constraints to check with
    #     :param set_tc: list of test case assumptions
    #     :param only_one: if True, return after first inconsistent test case
    #     :return: list of inconsistent test cases
    #     """
    #     set_tcp = []
    #     # Accumulates inconsistent test cases, stopping if `only_one`
    #     for tc in set_tc:
    #         if not self.is_consistent(set_c + [tc]):
    #             set_tcp.append(tc)
    #         if only_one and len(set_tcp) > 0:
    #             break
    #
    #     return set_tcp

    def copy(self):
        """Create a new instance with the same configuration for multiprocessing."""
        return NonIncrementalPySATChecker(self.solver_name, self.profiler)

    def cleanup(self) -> None:
        """No persistent resources to clean up."""
        pass

    def __getstate__(self):
        """Prepare object for pickling - exclude profiler."""
        state = self.__dict__.copy()
        state['profiler'] = None
        return state

    def __setstate__(self, state):
        """Restore object from pickle."""
        self.__dict__.update(state)
        if self.profiler is None:
            self.profiler = get_global_profiler()


class SAT4JChecker(ConsistencyChecker):
    """
    Consistency checker using external SAT4J solver.

    This implementation calls the SAT4J Java solver via subprocess.
    Slower than PySAT due to I/O overhead but can be useful for
    cross-validation or when SAT4J-specific features are needed.
    """

    def __init__(self, jar_path: str = "solver_apps/org.sat4j.core.jar",
                 profiler_instance: AbstractProfiler = None, timeout: int = 300) -> None:
        """
        Initialize SAT4J checker.

        :param jar_path: Path to SAT4J jar file
        :param profiler_instance: Optional profiler for metrics tracking
        :param timeout: Timeout in seconds for solver execution
        """
        super().__init__(profiler_instance)
        self.jar_path = jar_path
        self.timeout = timeout

        # Validate jar file exists
        if not os.path.exists(jar_path):
            raise FileNotFoundError(
                f"SAT4J jar not found at: {jar_path}\n"
                f"Please ensure the solver is installed."
            )

    @count_calls(key="is_consistent_calls")
    def is_consistent(self, set_c: List) -> bool:
        """
        Check consistency using SAT4J via subprocess.

        Creates a temporary CNF file, runs SAT4J solver, and parses the output.
        Handles timeouts gracefully by returning False (unsatisfiable).

        :param set_c: list of lists representing CNF clauses
        :return: True if the formula is satisfiable, False if unsatisfiable or timeout
        :raises RuntimeError: If solver execution fails for reasons other than timeout
        """
        # Create temporary file for CNF formula
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=True) as f:
            cnf = CNF()
            cnf.extend([clause for c in set_c for clause in c])
            cnf.to_file(f.name)

            # Run SAT4J solver
            with self.profiler.timer("solver_time"):
                try:
                    result = subprocess.run(
                        ["java", "-jar", self.jar_path, f.name],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        check=False
                    )
                    output = result.stdout
                except subprocess.TimeoutExpired:
                    # Timeout means we couldn't determine satisfiability
                    # Conservative approach: assume unsatisfiable
                    output = "TIMEOUT"
                except Exception as e:
                    raise RuntimeError(f"Failed to run SAT4J: {e}")

        # Parse result - SAT4J outputs "UNSATISFIABLE" or "SATISFIABLE"
        self.result = "SATISFIABLE" in output and "UNSATISFIABLE" not in output
        return self.result

    def copy(self):
        """Create a new instance with the same configuration for multiprocessing."""
        return SAT4JChecker(self.jar_path, self.profiler, self.timeout)

    def cleanup(self) -> None:
        """No persistent resources to clean up."""
        pass

    def __getstate__(self):
        """Prepare object for pickling - exclude profiler."""
        state = self.__dict__.copy()
        state['profiler'] = None
        return state

    def __setstate__(self, state):
        """Restore object from pickle."""
        self.__dict__.update(state)
        if self.profiler is None:
            self.profiler = get_global_profiler()


class CheckerFactory:
    """
    Factory for creating consistency checker instances.
    """

    @staticmethod
    def create_sat4jchecker(profiler_instance: AbstractProfiler = None,
                            sat4j_jar_path: str = "solver_apps/org.sat4j.core.jar") -> ConsistencyChecker:
        """
        Create a SAT4J consistency checker.

        :param profiler_instance: Optional profiler instance for metrics tracking
        :param sat4j_jar_path: Path to SAT4J jar file (default: "solver_apps/org.sat4j.core.jar")
        :return: SAT4JChecker instance
        :raises FileNotFoundError: If SAT4J jar file not found at specified path
        """
        return SAT4JChecker(jar_path=sat4j_jar_path, profiler_instance=profiler_instance)

    @staticmethod
    def create_from_model(model: DiagnosisModel,
                          solver_name: str = 'glucose3',
                          profiler_instance: AbstractProfiler = None) -> ConsistencyChecker:
        """
        Create a checker from a DiagnosisModel.

        Automatically selects between incremental and non-incremental modes
        based on the model's configuration.

        :param model: DiagnosisModel instance with prepared diagnosis task
        :param solver_name: Name of PySAT solver (e.g., 'glucose3', 'minisat22')
        :param profiler_instance: Optional profiler instance for metrics tracking
        :return: IncrementalPySATChecker if model.is_incremental=True, otherwise NonIncrementalPySATChecker
        """
        if model.is_incremental:
            return IncrementalPySATChecker(
                model.get_kb(),
                model.get_assumptions(),
                solver_name,
                profiler_instance
            )
        else:
            return NonIncrementalPySATChecker(solver_name, profiler_instance)
