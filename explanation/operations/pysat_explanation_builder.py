"""Builder for configuring diagnosis/debugging operations.

This module provides a fluent builder interface for creating and configuring
diagnosis/debugging operations.

The builder hierarchy:
- PySATExplanationBuilder: Abstract base class with common methods
- PySATDiagnosisBuilder: For diagnosis/conflict operations (FastDiag, QuickXPlain)
- PySATDebuggingBuilder: For debugging operations with test cases (KBDiag)
"""
from abc import ABC
from typing import Optional, TypeVar

from flamapy.metamodels.configuration_metamodel.models import Configuration

from explanation.models.testsuite import TestSuite
from explanation.operations.pysat_abstract_explanation import PySATAbstractExplanation
from explanation.operations.pysat_conflict import PySATConflict
from explanation.operations.pysat_conflict_sat4j import PySATConflictSAT4J
from explanation.operations.pysat_debugging import PySATDebugging
from explanation.operations.pysat_diagnosis import PySATDiagnosis
from explanation.operations.pysat_diagnosis_sat4j import PySATDiagnosisSAT4J

# Type variable for method chaining with correct return types
T = TypeVar('T', bound='PySATExplanationBuilder')


class PySATExplanationBuilder(ABC):
    """Abstract base builder for configuring diagnosis/debugging operations.

    This builder provides a fluent interface for setting up diagnosis/debugging operations
    with various configuration options. It supports method chaining for convenient
    configuration.

    Subclasses:
        - PySATDiagnosisBuilder: For diagnosis/conflict operations
        - PySATDebuggingBuilder: For debugging operations with test cases

    Example:
        >>> builder = PySATDiagnosisBuilder.for_diagnosis()
        >>> operation = (builder
        ...     .with_configuration(my_config)
        ...     .with_max_diagnoses(10)
        ...     .with_max_depth(5)
        ...     .build())
        >>> result = operation.execute(diagnosis_model)
    """

    def __init__(self, operation: PySATAbstractExplanation):
        """Initialize builder with a specific operation type.

        Args:
            operation: The operation instance to configure
        """
        self._operation = operation

    def with_max_conflicts(self: T, max_conflicts: Optional[int]) -> T:
        """Set maximum number of conflicts to find.

        Args:
            max_conflicts: Maximum number of conflicts (None for no limit,
                         must be positive if specified)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If max_conflicts is not positive
        """
        self._operation.max_conflicts = max_conflicts
        return self

    def with_max_diagnoses(self: T, max_diagnoses: Optional[int]) -> T:
        """Set maximum number of diagnoses to find.

        Args:
            max_diagnoses: Maximum number of diagnoses (None for no limit,
                          must be positive if specified)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If max_diagnoses is not positive
        """
        self._operation.max_diagnoses = max_diagnoses
        return self

    def with_max_depth(self: T, max_depth: Optional[int]) -> T:
        """Set maximum depth of HSDAG tree.

        Args:
            max_depth: Maximum depth (None for no limit,
                      must be positive if specified)

        Returns:
            Self for method chaining

        Raises:
            ValueError: If max_depth is not positive
        """
        self._operation.max_depth = max_depth
        return self

    def with_depth_first_search(self: T, enabled: bool = True) -> T:
        """Enable or disable depth-first search in HSDAG.

        Args:
            enabled: Whether to use depth-first search (default: True)

        Returns:
            Self for method chaining
        """
        self._operation.depth_first_search = enabled
        return self

    def with_solver(self: T, solver_name: str) -> T:
        """Set the SAT solver to use.

        Args:
            solver_name: Name of the SAT solver (e.g., 'glucose3', 'sat4j')

        Returns:
            Self for method chaining
        """
        self._operation.solver_name = solver_name
        return self

    def build(self) -> PySATAbstractExplanation:
        """Build and return the configured operation.

        Returns:
            Configured PySATAbstractExplanation instance ready for execution
        """
        return self._operation


class PySATDiagnosisBuilder(PySATExplanationBuilder):
    """Builder for diagnosis and conflict detection operations.

    This builder is used for operations that work with:
    - Feature model diagnosis (finding faulty constraints)
    - Configuration diagnosis (finding conflicting selections)
    - Test case diagnosis (finding constraints violating test cases)

    Uses FastDiag (for diagnoses) or QuickXPlain (for conflicts) algorithms.

    Example:
        >>> operation = (PySATDiagnosisBuilder.for_diagnosis()
        ...     .with_configuration(my_config)
        ...     .with_max_diagnoses(5)
        ...     .build())
        >>> result = operation.execute(model)

    Example with SAT4J solver:
        >>> operation = (PySATDiagnosisBuilder.for_diagnosis_sat4j()
        ...     .with_test_case(test_case)
        ...     .build())
    """

    @classmethod
    def for_conflict(cls) -> 'PySATDiagnosisBuilder':
        """Create a builder for conflict detection operations.

        Returns:
            PySATDiagnosisBuilder configured for PySATConflict
        """
        return cls(PySATConflict())

    @classmethod
    def for_diagnosis(cls) -> 'PySATDiagnosisBuilder':
        """Create a builder for diagnosis operations.

        Returns:
            PySATDiagnosisBuilder configured for PySATDiagnosis
        """
        return cls(PySATDiagnosis())

    @classmethod
    def for_diagnosis_sat4j(cls) -> 'PySATDiagnosisBuilder':
        """Create a builder for diagnosis operations using SAT4J solver.

        Returns:
            PySATDiagnosisBuilder configured for PySATDiagnosis with SAT4J
        """
        return cls(PySATDiagnosisSAT4J())

    @classmethod
    def for_conflict_sat4j(cls) -> 'PySATDiagnosisBuilder':
        """Create a builder for conflict detection operations using SAT4J solver.

        Returns:
            PySATDiagnosisBuilder configured for PySATConflict with SAT4J
        """
        return cls(PySATConflictSAT4J())

    def with_configuration(self, configuration: Configuration) -> 'PySATDiagnosisBuilder':
        """Set the configuration to be diagnosed.

        Args:
            configuration: Configuration instance to diagnose

        Returns:
            Self for method chaining
        """
        self._operation.set_configuration(configuration)
        return self

    def with_test_case(self, test_case: Configuration) -> 'PySATDiagnosisBuilder':
        """Set the test case for diagnosis.

        Args:
            test_case: Test case configuration

        Returns:
            Self for method chaining
        """
        self._operation.set_test_case(test_case)
        return self


class PySATDebuggingBuilder(PySATExplanationBuilder):
    """Builder for debugging operations with test cases.

    This builder is used for operations that work with positive and negative
    test cases using the KBDiag algorithm.

    Example:
        >>> operation = (PySATDebuggingBuilder.for_debugging()
        ...     .with_positive_test_cases(positive_tests)
        ...     .with_negative_test_cases(negative_tests)
        ...     .with_max_diagnoses(5)
        ...     .with_m(2)
        ...     .build())
        >>> result = operation.execute(model)
    """

    def __init__(self, operation: PySATDebugging):
        """Initialize builder with a PySATDebugging operation.

        Args:
            operation: The PySATDebugging instance to configure
        """
        super().__init__(operation)
        self._debugging_operation = operation

    @classmethod
    def for_debugging(cls) -> 'PySATDebuggingBuilder':
        """Create a builder for debugging operations with test cases.

        Uses KBDiag algorithm to find diagnoses based on positive/negative test cases.

        Returns:
            PySATDebuggingBuilder configured for PySATDebugging

        Example:
            >>> operation = (PySATDebuggingBuilder.for_debugging()
            ...     .with_positive_test_cases(test_suite)
            ...     .with_max_diagnoses(1)
            ...     .build())
        """
        return cls(PySATDebugging())

    def with_positive_test_cases(self, test_cases: TestSuite) -> 'PySATDebuggingBuilder':
        """Set positive test cases for debugging operations.

        Positive test cases represent configurations that SHOULD be valid
        but are currently rejected by the feature model.

        Args:
            test_cases: TestSuite of positive test cases

        Returns:
            Self for method chaining
        """
        self._debugging_operation.set_positive_test_cases(test_cases)
        return self

    def with_negative_test_cases(self, test_cases: TestSuite) -> 'PySATDebuggingBuilder':
        """Set negative test cases for debugging operations.

        Negative test cases represent configurations that SHOULD be invalid
        but are currently accepted by the feature model.

        Args:
            test_cases: TestSuite of negative test cases

        Returns:
            Self for method chaining
        """
        self._debugging_operation.set_negative_test_cases(test_cases)
        return self

    def with_m(self, m: int) -> 'PySATDebuggingBuilder':
        """Set m parameter for KBDiag algorithm.

        The m parameter controls how many test cases are considered at once
        during the diagnosis process.

        Args:
            m: Parameter value (default: 1)

        Returns:
            Self for method chaining
        """
        self._debugging_operation.set_m(m)
        return self
