"""
Model classes for CONGEN algorithm.

Uses existing classes from explanation module:
- Assignment, TestCase, TestSuite from explanation.models.testsuite
- TaskInput from explanation.models.task_preparation

CONGENModel is a simplified model for CONGEN that doesn't require
the full DiagnosisModel infrastructure (no FM transformation needed).
"""

from dataclasses import dataclass, field
from typing import Dict, List

from explanation.models.testsuite import Assignment, TestCase, TestSuite
from explanation.models.task_preparation import TaskInput


@dataclass
class CONGENModel:
    """Model for CONGEN algorithm.

    This is a simplified model specifically for CONGEN, holding:
    - constraint_map: Bias constraints {name: clauses}
    - negated_constraint_map: Pre-computed negated constraints (optional)
    - variables: Feature name to variable ID mapping
    - task_input: Test cases configuration (uses TaskInput from explanation)
    - next_tseitin_var: Next available variable ID for Tseitin encoding

    Unlike DiagnosisModel from explanation module, this doesn't require
    a feature model and works directly with bias constraints.
    """
    constraint_map: Dict[str, List[List[int]]] = field(default_factory=dict)
    negated_constraint_map: Dict[str, List[List[int]]] = field(default_factory=dict)
    variables: Dict[str, int] = field(default_factory=dict)
    task_input: TaskInput = field(default_factory=TaskInput)
    next_tseitin_var: int = 1

    @classmethod
    def from_bias_and_examples(
            cls,
            bias_constraints: Dict[str, List[List[int]]],
            positive_examples: List[Dict[str, bool]],
            negative_examples: List[Dict[str, bool]],
            feature_ids: Dict[str, int]
    ) -> 'CONGENModel':
        """Create model from bias constraints and examples.

        Args:
            bias_constraints: {constraint_name: [clauses]} from bias
            positive_examples: List of valid configurations {feature: bool}
            negative_examples: List of invalid configurations {feature: bool}
            feature_ids: {feature_name: variable_id}

        Returns:
            CONGENModel ready for task preparation
        """
        # Find max variable ID for Tseitin allocation
        max_var = max(feature_ids.values()) if feature_ids else 0
        for clauses in bias_constraints.values():
            for clause in clauses:
                for lit in clause:
                    max_var = max(max_var, abs(lit))

        # Convert examples to test suites using explanation module classes
        positive_tc = cls._examples_to_testsuite(positive_examples)
        negative_tc = cls._examples_to_testsuite(negative_examples)

        return cls(
            constraint_map=bias_constraints,
            negated_constraint_map={},
            variables=feature_ids,
            task_input=TaskInput(
                positive_test_cases=positive_tc,
                negative_test_cases=negative_tc
            ),
            next_tseitin_var=max_var + 1
        )

    @staticmethod
    def _examples_to_testsuite(examples: List[Dict[str, bool]]) -> TestSuite:
        """Convert list of example dicts to TestSuite.

        Uses TestSuite, TestCase, Assignment from explanation.models.testsuite.
        """
        testcases = []
        for example in examples:
            assignments = [
                Assignment(feature=name, value=value)
                for name, value in example.items()
            ]
            testcases.append(TestCase(assignments=assignments))
        return TestSuite(testcases=testcases)
