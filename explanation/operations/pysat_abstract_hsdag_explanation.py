from abc import abstractmethod
from typing import List, Tuple, Optional


from explanation.models.task_preparation import (
    PreparedTask, DescriptionProvider, format_diagnoses, Task,
)
from explanation.checker.protocols import ConsistencyChecker
from explanation.operations.algorithms.hsdag.hsdag import HSDAG
from explanation.operations.algorithms.hsdag.labeler.labeler import IHSLabelable
from explanation.operations.pysat_abstract_explanation import PySATAbstractExplanation
from profiling import AbstractProfiler


def _format_results(singular: str, plural: str, items: List,
                    describe: DescriptionProvider) -> str:
    """Format a list of results (conflicts or diagnoses) for display.

    Args:
        singular: Singular form of the item type (e.g., "Conflict", "Diagnosis")
        plural: Plural form of the item type (e.g., "Conflicts", "Diagnoses")
        items: List of items to format
        describe: DescriptionProvider for pretty printing

    Returns:
        Formatted string representation of the results
    """
    if not items:
        return f'No {singular.lower()} found'

    label = singular if len(items) == 1 else plural
    formatted_items = format_diagnoses(items, describe)
    return f'{label}: {formatted_items}'


def _execute_hsdag(prepared: PreparedTask, hsdag: HSDAG) -> Tuple[str, str]:
    """Execute HSDAG algorithm and format results.

    Args:
        prepared: The prepared task carrying the DescriptionProvider (describe)
        hsdag: Configured HSDAG instance to execute

    Returns:
        Tuple of (conflicts_message, diagnoses_message) formatted for display
    """
    hsdag.construct()

    diagnoses = hsdag.get_diagnoses()
    conflicts = hsdag.get_conflicts()

    describe = prepared.describe
    conflicts_message = _format_results('Conflict', 'Conflicts', conflicts, describe)
    diagnoses_message = _format_results('Diagnosis', 'Diagnoses', diagnoses, describe)

    return conflicts_message, diagnoses_message


class PySATAbstractHSDAGExplanation(PySATAbstractExplanation):
    """Abstract operation for computing conflicts or diagnoses using HSDAG.

    This class provides a template method pattern for different diagnosis operations.
    Subclasses implement specific labeler strategies while reusing common infrastructure.

    Attributes:
        solver_name: SAT solver to use (default: 'glucose3')
        max_conflicts: Maximum number of conflicts to find (None means no limit)
        max_diagnoses: Maximum number of diagnoses to find (None means no limit)
        max_depth: Maximum depth of HSDAG tree (None means no limit)
        depth_first_search: Whether to use depth-first search in HSDAG
        result_messages: List of formatted result messages
    """

    def __init__(self, profiler_instance: AbstractProfiler = None,
                 use_sat4j: bool = False) -> None:
        """Initialize the abstract identifier with default values.

        Args:
            profiler_instance: Optional profiler; falls back to global profiler.
            use_sat4j: Whether to run consistency checks via the SAT4J checker
                (else the PySAT checker selected by ``use_incremental``).
        """
        super().__init__(profiler_instance, use_sat4j)

        self.result = False
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

        This method applies the standard configuration parameters to an HSDAG instance.
        Subclasses can override this if they need custom configuration logic.

        Args:
            hsdag: HSDAG instance to configure

        Returns:
            Configured HSDAG instance
        """
        hsdag = HSDAG(labeler, self.profiler)
        hsdag.max_number_conflicts = self.max_conflicts if self.max_conflicts is not None else -1
        hsdag.max_number_diagnoses = self.max_diagnoses if self.max_diagnoses is not None else -1
        hsdag.depth_first_search = self.depth_first_search
        hsdag.max_depth = self.max_depth if self.max_depth is not None else 0
        return hsdag

    def execute(self, prepared: PreparedTask) -> 'PySATAbstractHSDAGExplanation':
        """Execute the diagnosis operation.

        This is the main entry point that orchestrates the diagnosis process:
        1. Prepare HSDAG with appropriate labeler
        2. Execute HSDAG to find conflicts and diagnoses
        3. Format and store results
        4. Clean up resources

        Args:
            prepared: PreparedTask carrying the task (KB/assumptions/constraint
                sets) and its DescriptionProvider (describe)

        Returns:
            Self for method chaining

        Note:
            Profiler integration tracks preparation time, execution time,
            and result counts (num_diagnoses, num_conflicts).
        """
        self.checker, self.hsdag = self.prepare_hsdag(prepared)

        try:
            cs_mess, diag_mess = _execute_hsdag(prepared, self.hsdag)
            self.set_result_messages(cs_mess, diag_mess)
        finally:
            if self.checker is not None:
                self.checker.cleanup()
                self.checker = None

        return self

    @abstractmethod
    def prepare_hsdag(self, prepared: PreparedTask) -> Tuple[ConsistencyChecker, HSDAG]:
        """Prepare HSDAG with appropriate labeler for specific operation type.

        This is the main extension point for different operation types
        (Conflict, Diagnosis, Repair, etc.). Each subclass implements its own
        labeler strategy while optionally reusing common helper methods.

        Args:
            prepared: PreparedTask carrying the task and description provider

        Returns:
            Tuple of (consistency_checker, configured_hsdag)

        Example:
            def prepare_hsdag(self, prepared):
                task = prepared.task
                checker = self._create_checker(task)
                labeler = self._create_labeler(checker, task)
                hsdag = HSDAG(labeler)
                return checker, self._create_hsdag(labeler)
        """
        pass

    @abstractmethod
    def set_result_messages(self, cs_mess: str, diag_mess: str) -> None:
        """Set result messages in appropriate order for this operation type.

        Different operation types may want to present results in different orders.
        For example, conflict operations show conflicts first, while diagnosis
        operations show diagnoses first.

        Args:
            cs_mess: Formatted conflicts message
            diag_mess: Formatted diagnoses message
        """
        pass
