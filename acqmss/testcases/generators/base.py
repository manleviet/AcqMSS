"""
Base class for example generators.
"""

from abc import ABC, abstractmethod
from ..data_structures import Example, ExampleSet
from ..oracle import Oracle


class ExampleGenerator(ABC):
    """
    Abstract base class for example generators.

    Generators use an Oracle to classify generated configurations
    as positive or negative examples.

    Attributes:
        oracle: Oracle for classifying examples
        features: Set of all feature names
        feature_ids: Mapping from feature names to SAT variable IDs
    """

    def __init__(self, oracle: Oracle):
        """
        Initialize generator with an oracle.

        Args:
            oracle: Oracle for classifying examples
        """
        self.oracle = oracle
        self.features = oracle.get_features()
        self.feature_ids = oracle.get_feature_ids()

    @abstractmethod
    def generate(self, **kwargs) -> ExampleSet:
        """
        Generate examples.

        Returns:
            ExampleSet with classified positive and negative examples
        """
        pass

    def _classify_and_add(self, example: Example, example_set: ExampleSet):
        """
        Classify example using oracle and add to example set.

        Args:
            example: Example to classify
            example_set: ExampleSet to add to
        """
        example.example_type = self.oracle.classify(example)
        example_set.add(example)
