from abc import abstractmethod
from typing import List, Tuple, Optional

from flamapy.core.operations import Operation

from explanation.models.task_preparation import Task, DiagnosisFormatter
from explanation.operations.algorithms.checker import ConsistencyChecker, CheckerFactory
from explanation.operations.algorithms.hsdag.hsdag import HSDAG
from explanation.operations.algorithms.hsdag.labeler.labeler import IHSLabelable
from explanation.operations.algorithms.profiler import AbstractProfiler, get_global_profiler


def _format_results(singular: str, plural: str, items: List, task: Task) -> str:
    """Format a list of results (conflicts or diagnoses) for display.

    Args:
        singular: Singular form of the item type (e.g., "Conflict", "Diagnosis")
        plural: Plural form of the item type (e.g., "Conflicts", "Diagnoses")
        items: List of items to format
        task: Task instance carrying the description provider

    Returns:
        Formatted string representation of the results
    """
    if not items:
        return f'No {singular.lower()} found'

    label = singular if len(items) == 1 else plural
    formatted_items = DiagnosisFormatter.format(items, task.describe)
    return f'{label}: {formatted_items}'


def _execute_hsdag(task: Task, hsdag: HSDAG) -> Tuple[str, str]:
    """Execute HSDAG algorithm and format results.

    Args:
        task: The task carrying description provider for result formatting
        hsdag: Configured HSDAG instance to execute

    Returns:
        Tuple of (conflicts_message, diagnoses_message) formatted for display
    """
    hsdag.construct()

    diagnoses = hsdag.get_diagnoses()
    conflicts = hsdag.get_conflicts()

    conflicts_message = _format_results('Conflict', 'Conflicts', conflicts, task)
    diagnoses_message = _format_results('Diagnosis', 'Diagnoses', diagnoses, task)

    return conflicts_message, diagnoses_message


class PySATAbstractExplanation(Operation):
    """Abstract operation for computing conflicts or diagnoses using HSDAG.

    This class provides a template method pattern for different diagnosis operations.
    Subclasses implement specific labeler strategies while reusing common infrastructure.

    Attributes:
        solver_name: SAT solver to use (default: 'glucose3')
        use_incremental: Whether to use incremental SAT solving (default: True)
        max_conflicts: Maximum number of conflicts to find (None means no limit)
        max_diagnoses: Maximum number of diagnoses to find (None means no limit)
        max_depth: Maximum depth of HSDAG tree (None means no limit)
        depth_first_search: Whether to use depth-first search in HSDAG
        result_messages: List of formatted result messages
    """

    def __init__(self, profiler_instance: AbstractProfiler = None) -> None:
        """Initialize the abstract identifier with default values."""
        self.profiler = profiler_instance if profiler_instance is not None else get_global_profiler()

        self.result = False
        self.solver_name: str = 'glucose3'
        self.use_incremental: bool = True
        self.result_messages: List[str] = []

        self.checker: Optional[ConsistencyChecker] = None
        self.hsdag: Optional[HSDAG] = None
        self._max_conflicts: Optional[int] = None  # None means no limit
        self._max_diagnoses: Optional[int] = None  # None means no limit
        self.depth_first_search: bool = False
        self._max_depth: Optional[int] = None  # None means no limit

    @property
    def max_conflicts(self) -> Optional[int]:
        """Get maximum number of conflicts to find."""
        return self._max_conflicts

    @max_conflicts.setter
    def max_conflicts(self, value: Optional[int]) -> None:
        """Set maximum number of conflicts with validation.

        Args:
            value: Maximum number of conflicts (must be positive or None for no limit)

        Raises:
            ValueError: If value is not positive
        """
        if value is not None and value < 1:
            raise ValueError(f"max_conflicts must be positive, got {value}")
        self._max_conflicts = value

    @property
    def max_diagnoses(self) -> Optional[int]:
        """Get maximum number of diagnoses to find."""
        return self._max_diagnoses

    @max_diagnoses.setter
    def max_diagnoses(self, value: Optional[int]) -> None:
        """Set maximum number of diagnoses with validation.

        Args:
            value: Maximum number of diagnoses (must be positive or None for no limit)

        Raises:
            ValueError: If value is not positive
        """
        if value is not None and value < 1:
            raise ValueError(f"max_diagnoses must be positive, got {value}")
        self._max_diagnoses = value

    @property
    def max_depth(self) -> Optional[int]:
        """Get maximum depth of HSDAG tree."""
        return self._max_depth

    @max_depth.setter
    def max_depth(self, value: Optional[int]) -> None:
        """Set maximum depth of HSDAG tree with validation.

        Args:
            value: Maximum depth (must be positive or None for no limit)

        Raises:
            ValueError: If value is not positive
        """
        if value is not None and value < 1:
            raise ValueError(f"max_depth must be positive, got {value}")
        self._max_depth = value

    def get_result(self) -> List[str]:
        """Get the formatted result messages.

        Returns:
            List of result message strings
        """
        return self.result_messages

    def get_diagnoses(self) -> List[List]:
        """Get raw diagnosis constraint sets from HSDAG.

        Returns:
            List of diagnoses (each a list of constraints), or empty if HSDAG not executed.
        """
        return self.hsdag.get_diagnoses() if self.hsdag else []

    def get_conflicts(self) -> List[List]:
        """Get raw conflict sets from HSDAG.

        Returns:
            List of conflicts (each a list of constraints), or empty if HSDAG not executed.
        """
        return self.hsdag.get_conflicts() if self.hsdag else []

    def _create_checker(self, task: Task) -> ConsistencyChecker:
        """Create consistency checker from task.

        Subclasses can override this to use different solvers or configurations.

        Args:
            task: Task carrying set_kb and assumptions

        Returns:
            Configured consistency checker instance
        """
        return CheckerFactory.create_from_task(
            task, solver_name=self.solver_name,
            use_incremental=self.use_incremental,
            profiler_instance=self.profiler)

    @abstractmethod
    def _create_labeler(self, checker: ConsistencyChecker, task: Task) -> IHSLabelable:
        """Create appropriate labeler for this operation type.

        This is the key extension point - each operation type creates its own labeler.

        Args:
            checker: Consistency checker instance
            task: Task carrying set_c, set_b, set_tc, etc.

        Returns:
            Configured labeler instance (QuickXPlainLabeler, FastDiagLabeler, etc.)
        """
        pass

    def _create_hsdag(self, labeler: IHSLabelable) -> HSDAG:
        """Configure HSDAG with common parameters.

        Args:
            labeler: Labeler instance to use

        Returns:
            Configured HSDAG instance
        """
        hsdag = HSDAG(labeler, self.profiler)
        hsdag.max_number_conflicts = self.max_conflicts if self.max_conflicts is not None else -1
        hsdag.max_number_diagnoses = self.max_diagnoses if self.max_diagnoses is not None else -1
        hsdag.depth_first_search = self.depth_first_search
        hsdag.max_depth = self.max_depth if self.max_depth is not None else 0
        return hsdag

    def execute(self, task: Task) -> 'PySATAbstractExplanation':
        """Execute the diagnosis operation.

        This is the main entry point that orchestrates the diagnosis process:
        1. Prepare HSDAG with appropriate labeler
        2. Execute HSDAG to find conflicts and diagnoses
        3. Format and store results
        4. Clean up resources

        Args:
            task: Task carrying the KB, assumptions, and description provider

        Returns:
            Self for method chaining
        """
        self.checker, self.hsdag = self.prepare_hsdag(task)

        try:
            cs_mess, diag_mess = _execute_hsdag(task, self.hsdag)
            self.set_result_messages(cs_mess, diag_mess)
        finally:
            if self.checker is not None:
                self.checker.cleanup()
                self.checker = None

        return self

    @abstractmethod
    def prepare_hsdag(self, task: Task) -> Tuple[ConsistencyChecker, HSDAG]:
        """Prepare HSDAG with appropriate labeler for specific operation type.

        This is the main extension point for different operation types.

        Args:
            task: Task carrying KB, assumptions, and constraint sets

        Returns:
            Tuple of (consistency_checker, configured_hsdag)
        """
        pass

    @abstractmethod
    def set_result_messages(self, cs_mess: str, diag_mess: str) -> None:
        """Set result messages in appropriate order for this operation type.

        Args:
            cs_mess: Formatted conflicts message
            diag_mess: Formatted diagnoses message
        """
        pass
