"""PySATAbstractExplanation — the thin shared base for PySAT-backed operations.

Owns only what every PySAT operation needs: the profiler, the solver-selection
flags, the result-message buffer, the single checker-construction seam
(``_create_checker``), and ``get_result``. It deliberately holds NO HSDAG
machinery.

- HSDAG-based operations (diagnosis / conflict / test-case) extend
  ``PySATAbstractHSDAGExplanation`` (which adds the labeler + HSDAG template).
- Redundancy operations (WipeOutR_FM / WipeOutR_T) extend THIS directly, so they
  are first-class — their ``execute()`` is the real API, not an override that
  disables an inherited HSDAG path. This is what lets them drop the old
  inherit-``PySATDiagnosis``-then-stub-two-methods hack.

``execute`` stays abstract (inherited from flamapy's ``Operation``); every
concrete operation implements it.
"""
from typing import List

from flamapy.core.operations import Operation

from explanation.models.task_preparation import Task
from explanation.checker.protocols import ConsistencyChecker
from explanation.checker.backend import SolverBackend, build_checker
from profiling import AbstractProfiler, get_global_profiler


class PySATAbstractExplanation(Operation):
    """Shared base: checker seam + result accessor, no HSDAG."""

    def __init__(self, profiler_instance: AbstractProfiler = None,
                 use_sat4j: bool = False) -> None:
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()
        self.solver_name: str = 'glucose3'
        # Solver selection: operation-level concerns (not a property of the task).
        self.use_incremental: bool = True
        self.use_sat4j: bool = use_sat4j
        self.result_messages: List[str] = []

    def _create_checker(self, task: Task) -> ConsistencyChecker:
        """Build the solver backend for *task* via the single construction door.

        The ``use_sat4j`` / ``use_incremental`` flags fold into one backend token;
        ``build_checker`` picks the concrete backend. Reads the task's KB + assumptions.
        """
        config = SolverBackend.from_flags(
            use_incremental=self.use_incremental, use_sat4j=self.use_sat4j)
        return build_checker(task, config, self.solver_name, self.profiler)

    def get_result(self) -> List[str]:
        """Return the formatted result messages."""
        return self.result_messages
