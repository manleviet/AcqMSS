from typing import Tuple

from explanation.models.task_preparation import PreparedTask, Task
from explanation.checker.protocols import ConsistencyChecker
from explanation.operations.algorithms.hsdag.hsdag import HSDAG
from explanation.operations.algorithms.hsdag.labeler.quickxplain_labeler import QuickXPlainLabeler, \
    QuickXPlainParameters
from profiling import AbstractProfiler
from explanation.operations.pysat_abstract_hsdag_explanation import PySATAbstractHSDAGExplanation


class PySATConflict(PySATAbstractHSDAGExplanation):
    """Operation that computes conflicts and diagnoses using HSDAG and QuickXPlain.

    This operation identifies conflicts (sets of constraints that are inconsistent)
    and diagnoses (minimal sets of constraints whose removal makes the system consistent)
    using the combination of HSDAG tree search and QuickXPlain conflict labeling.

    Attributes:
        max_conflicts: Maximum number of conflicts to find (None for no limit)
        max_diagnoses: Maximum number of diagnoses to find (None for no limit)
        max_depth: Maximum depth of HSDAG tree (None for no limit)
        depth_first_search: Whether to use depth-first search
        solver_name: SAT solver to use (default: 'glucose3')
        use_sat4j: Whether to run consistency checks via the SAT4J checker

    Example:
        >>> operation = PySATConflict()
        >>> operation.max_conflicts = 10
        >>> result = operation.execute(prepared_task)
        >>> messages = result.get_result()
    """

    def __init__(self, profiler_instance: AbstractProfiler = None,
                 use_sat4j: bool = False) -> None:
        """Initialize PySATConflict operation with default values."""
        super().__init__(profiler_instance, use_sat4j)

    def _create_labeler(self, checker: ConsistencyChecker, task: Task) -> QuickXPlainLabeler:
        """Create QuickXPlain labeler for conflict detection.

        Args:
            checker: Consistency checker instance
            task: Task carrying set_c and set_b

        Returns:
            Configured QuickXPlainLabeler instance
        """
        parameters = QuickXPlainParameters(task.set_c, task.set_b)
        return QuickXPlainLabeler(checker, parameters)

    def prepare_hsdag(self, prepared: PreparedTask) -> Tuple[ConsistencyChecker, HSDAG]:
        """Prepare HSDAG with QuickXPlain labeler for conflict detection.

        Args:
            prepared: PreparedTask to use

        Returns:
            Tuple of (consistency_checker, configured_hsdag)
        """
        task = prepared.task
        checker = self._create_checker(task)
        labeler = self._create_labeler(checker, task)

        return checker, self._create_hsdag(labeler)

    def set_result_messages(self, cs_mess: str, diag_mess: str) -> None:
        """Set result messages with conflicts first, then diagnoses.

        Args:
            cs_mess: Formatted conflicts message
            diag_mess: Formatted diagnoses message
        """
        self.result_messages.extend([cs_mess, diag_mess])
