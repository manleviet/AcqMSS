"""Solver backends — the concrete adapters that answer consistency questions by
talking to a real SAT solver, plus the single factory that builds one.

Each backend satisfies the ``ConsistencyChecker`` / ``TestCaseChecker`` port
(``protocols.py``) structurally. ``CheckerBase`` holds the shared
machinery (profiler, delta computation, the test-case loop, copy/pickling,
context-manager); the three concrete backends differ only in how they reach a
solver:

- ``IncrementalPySATChecker`` — persistent PySAT solver + assumptions.
- ``NonIncrementalPySATChecker`` — a fresh PySAT solver per check.
- ``SAT4JChecker`` — the external SAT4J solver via subprocess.

``build_checker(task, backend=…)`` is the ONE public construction door AND the
single place a concrete backend class is selected: it reads the task's KB +
assumptions and maps the ``SolverBackend`` token to a concrete class.
"""
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, List, Optional, Sequence

from pysat.formula import CNF
from pysat.solvers import Solver

from profiling import get_global_profiler, count_calls, AbstractProfiler

from .protocols import ConsistencyChecker

if TYPE_CHECKING:
    from explanation.models.task_preparation import Task

_DEFAULT_SAT4J_JAR = "solver_apps/org.sat4j.core.jar"


class SolverTimeoutError(Exception):
    """Raised when a solver backend exceeds its wall-clock timeout.

    Surfaced (not swallowed) so a timeout can never be mistaken for a real UNSAT
    answer. A caller that hits it must either raise the limit
    (``build_checker(sat4j_timeout=…)``) or switch to a PySAT backend.
    """


class CheckerBase(ABC):
    """Shared base for solver backends (structurally satisfies the checker port)."""

    def __init__(self, profiler_instance: AbstractProfiler = None):
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        # Every backend guards its checks against these assumption literals;
        # declared on the base so ``_compute_delta`` reads a real base attribute
        # (a subclass that forgets to set it starts empty rather than raising a
        # runtime AttributeError). Concrete backends overwrite it.
        self.assumptions: List[int] = []

    def _compute_delta(self, set_c: Sequence[int]) -> tuple:
        """Compute enabled/disabled assumption partition: delta = assumptions \\ set_c."""
        set_c_set = set(set_c)
        delta = [item for item in self.assumptions if item not in set_c_set]
        return set_c, delta

    @abstractmethod
    def is_consistent(self, set_c: Sequence[int]) -> bool:
        """Check if the given CNF formula is consistent."""
        pass

    @abstractmethod
    def find_model(self, set_c: Sequence[int]) -> Optional[List[int]]:
        """Solve KEEPING the disabled assumptions and return the pinned model, or None
        if UNSAT. is_consistent drops them (SAT/UNSAT is encoding-invariant); a model
        needs them (a free guard may flip true and force its literal). See ADR-0013."""
        pass

    @count_calls(key="is_consistent_test_cases_calls")
    def is_consistent_test_cases(self, set_c: Sequence[int], set_tc: Sequence[int], stop_at_first_violation: bool) -> List:
        """Check consistency against multiple test cases, returning inconsistent ones."""
        set_tcp = []
        # Accumulates test cases inconsistent with CNF formula
        for tc in set_tc:
            if not self.is_consistent(list(set_c) + [tc]):
                set_tcp.append(tc)
            if stop_at_first_violation and len(set_tcp) > 0:
                break
        return set_tcp

    @abstractmethod
    def copy(self):
        """Create a copy for multiprocessing."""
        pass

    def cleanup(self) -> None:
        """Release resources. Override in subclasses with persistent state."""
        pass

    def __getstate__(self):
        state = self.__dict__.copy()
        state['profiler'] = None
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        if self.profiler is None:
            self.profiler = get_global_profiler()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


class IncrementalPySATChecker(CheckerBase):
    """Incremental backend using PySAT with a persistent solver and assumptions."""

    def __init__(self, set_kb: Sequence[Sequence[int]], assumptions: Sequence[int],
                 solver_name: str = 'glucose3', profiler_instance: AbstractProfiler = None) -> None:
        super().__init__(profiler_instance)
        self.solver_name = solver_name
        self.set_kb = set_kb
        self.assumptions = assumptions
        self.solver = Solver(solver_name, bootstrap_with=set_kb, use_timer=True)

    @count_calls(key="is_consistent_calls")
    def is_consistent(self, set_c: Sequence[int]) -> bool:
        # SAT/UNSAT only — drop the disabled (negated) assumptions. The one-way guard
        # encoding lets the solver deactivate a clause by setting its guard false, so
        # the answer is identical (ADR-0013). This is the hot path (thousands of calls).
        enabled, _ = self._compute_delta(set_c)
        result = self.solver.solve(assumptions=list(enabled))

        self.profiler.record_time("solver_time", self.solver.time())
        if self.solver.time_accum() is not None:
            self.profiler.set_gauge("solver_time_accum", self.solver.time_accum())

        return result

    def find_model(self, set_c: Sequence[int]) -> Optional[List[int]]:
        # Model path — KEEP the disabled negatives so every guard is pinned; a free
        # guard could flip true and force its literal, giving a divergent model.
        enabled, disabled = self._compute_delta(set_c)
        final_assumptions = list(enabled) + [-1 * item for item in disabled]
        result = self.solver.solve(assumptions=final_assumptions)
        self.profiler.record_time("solver_time", self.solver.time())
        return self.solver.get_model() if result else None

    def copy(self):
        return IncrementalPySATChecker(
            self.set_kb, self.assumptions, self.solver_name, self.profiler
        )

    def cleanup(self) -> None:
        if hasattr(self, 'solver') and self.solver is not None:
            self.solver.delete()
            self.solver = None

    def __getstate__(self):
        state = super().__getstate__()
        if 'solver' in state:
            state['solver'] = None
        return state

    def __setstate__(self, state):
        super().__setstate__(state)
        if hasattr(self, 'solver_name') and hasattr(self, 'set_kb'):
            self.solver = Solver(self.solver_name, bootstrap_with=self.set_kb, use_timer=True)


class NonIncrementalPySATChecker(CheckerBase):
    """Non-incremental backend using PySAT — a fresh solver per check."""

    def __init__(self, set_kb: Sequence[Sequence[int]], assumptions: Sequence[int],
                 solver_name: str = 'glucose3', profiler_instance: AbstractProfiler = None) -> None:
        super().__init__(profiler_instance)
        self.solver_name = solver_name
        self.set_kb = set_kb
        self.assumptions = assumptions

    @count_calls(key="is_consistent_calls")
    def is_consistent(self, set_c: Sequence[int]) -> bool:
        # SAT/UNSAT only — drop the disabled negatives (ADR-0013). Hot path.
        enabled, _ = self._compute_delta(set_c)
        solver = Solver(self.solver_name, bootstrap_with=self.set_kb, use_timer=True)
        result = solver.solve(assumptions=list(enabled))
        self.profiler.record_time("solver_time", solver.time())
        solver.delete()
        return result

    def find_model(self, set_c: Sequence[int]) -> Optional[List[int]]:
        # Model path — KEEP the disabled negatives so the model is fully pinned.
        enabled, disabled = self._compute_delta(set_c)
        final_assumptions = list(enabled) + [-1 * item for item in disabled]
        solver = Solver(self.solver_name, bootstrap_with=self.set_kb, use_timer=True)
        result = solver.solve(assumptions=final_assumptions)
        self.profiler.record_time("solver_time", solver.time())
        model = solver.get_model() if result else None
        solver.delete()
        return model

    def copy(self):
        return NonIncrementalPySATChecker(
            list(self.set_kb), list(self.assumptions),
            self.solver_name, self.profiler
        )


class SAT4JChecker(CheckerBase):
    """Backend using the external SAT4J solver via subprocess. Assumptions encoded as unit clauses."""

    def __init__(self, set_kb: Optional[Sequence[Sequence[int]]] = None,
                 assumptions: Optional[Sequence[int]] = None,
                 jar_path: str = _DEFAULT_SAT4J_JAR,
                 profiler_instance: AbstractProfiler = None, timeout: int = 300) -> None:
        super().__init__(profiler_instance)
        self.jar_path = jar_path
        self.timeout = timeout
        self.set_kb = set_kb or []
        self.assumptions = assumptions or []

        if not os.path.exists(jar_path):
            raise FileNotFoundError(
                f"SAT4J jar not found at: {jar_path}\n"
                f"Please ensure the solver is installed."
            )

    def _solve(self, assumption_clauses: List[List[int]]) -> str:
        """Run SAT4J on set_kb + the given assumption unit-clauses; return stdout."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cnf', delete=True) as f:
            cnf = CNF()
            cnf.extend(list(self.set_kb) + assumption_clauses)
            cnf.to_file(f.name)

            with self.profiler.timer("solver_time"):
                try:
                    result = subprocess.run(
                        ["java", "-jar", self.jar_path, f.name],
                        capture_output=True,
                        text=True,
                        timeout=self.timeout,
                        check=False
                    )
                    return result.stdout
                except subprocess.TimeoutExpired as e:
                    # Never coerce a timeout into a silent UNSAT: doing so recorded
                    # wrong (in)consistency answers with no signal. Surface it so the
                    # caller raises the limit or switches backend.
                    num_clauses = len(self.set_kb) + len(assumption_clauses)
                    raise SolverTimeoutError(
                        f"SAT4J exceeded its {self.timeout}s timeout on a "
                        f"{num_clauses}-clause formula. Raise the limit via "
                        f"build_checker(sat4j_timeout=…) or use a PySAT backend "
                        f"(SolverBackend.PYSAT_INCREMENTAL)."
                    ) from e
                except (OSError, subprocess.SubprocessError) as e:
                    raise RuntimeError(f"Failed to run SAT4J: {e}") from e

    @count_calls(key="is_consistent_calls")
    def is_consistent(self, set_c: Sequence[int]) -> bool:
        # SAT/UNSAT only — enabled unit clauses, drop the disabled negatives (ADR-0013).
        enabled, _ = self._compute_delta(set_c)
        output = self._solve([[a] for a in enabled])
        return "SATISFIABLE" in output and "UNSATISFIABLE" not in output

    def find_model(self, set_c: Sequence[int]) -> Optional[List[int]]:
        # Model path — KEEP the disabled negatives as unit clauses so the model is pinned.
        enabled, disabled = self._compute_delta(set_c)
        output = self._solve([[a] for a in enabled] + [[-a] for a in disabled])
        is_sat = "SATISFIABLE" in output and "UNSATISFIABLE" not in output
        return self._parse_model(output) if is_sat else None

    def _parse_model(self, output: str) -> Optional[List[int]]:
        """Parse SAT model from SAT4J output (v lines)."""
        model = []
        for line in output.splitlines():
            if line.startswith('v '):
                model.extend(int(x) for x in line[2:].split() if x != '0')
        return model if model else None

    def copy(self):
        return SAT4JChecker(
            list(self.set_kb), list(self.assumptions),
            self.jar_path, self.profiler, self.timeout
        )


class SolverBackend(Enum):
    """Which concrete backend ``build_checker`` should construct."""

    PYSAT_INCREMENTAL = auto()
    PYSAT_NON_INCREMENTAL = auto()
    SAT4J = auto()

    @classmethod
    def from_flags(cls, use_incremental: bool = True, use_sat4j: bool = False) -> 'SolverBackend':
        """Map the operation-level solver flags to a single backend token."""
        if use_sat4j:
            return cls.SAT4J
        return cls.PYSAT_INCREMENTAL if use_incremental else cls.PYSAT_NON_INCREMENTAL


def build_checker(task: 'Task',
                  backend: SolverBackend = SolverBackend.PYSAT_INCREMENTAL,
                  solver_name: str = 'glucose3',
                  profiler: AbstractProfiler = None,
                  sat4j_jar_path: str = _DEFAULT_SAT4J_JAR,
                  sat4j_timeout: int = 300) -> ConsistencyChecker:
    """Build a checker for *task* — the single public door AND the single place a
    concrete backend class is chosen.

    Reads ``task.set_kb`` / ``task.assumptions`` and maps the ``SolverBackend``
    token to a concrete class. Every checker in the system is built from a Task
    through here, so the choice of concrete backend lives in exactly one place.

    ``sat4j_timeout`` (seconds) bounds each SAT4J subprocess call; exceeding it
    raises ``SolverTimeoutError`` rather than returning a silent UNSAT. Ignored
    by the PySAT backends. The default preserves prior behavior.
    """
    set_kb, assumptions = task.set_kb, task.assumptions
    if backend is SolverBackend.SAT4J:
        return SAT4JChecker(set_kb=set_kb, assumptions=assumptions,
                            jar_path=sat4j_jar_path, profiler_instance=profiler,
                            timeout=sat4j_timeout)
    if backend is SolverBackend.PYSAT_NON_INCREMENTAL:
        return NonIncrementalPySATChecker(set_kb, assumptions, solver_name, profiler)
    return IncrementalPySATChecker(set_kb, assumptions, solver_name, profiler)
