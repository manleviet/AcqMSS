"""
Base class for example example_generators.
"""

import random
from abc import ABC, abstractmethod
from typing import Optional, Dict

from acqmss.examples.data_structures import Example, ExampleSet, ExampleType
from acqmss.oracle.fm_oracle import FeatureModelOracle


class ExampleGenerator(ABC):
    """
    Abstract base class for example example_generators.

    Generators use a FeatureModelOracle to classify generated configurations
    as positive or negative examples.

    Attributes:
        oracle: FeatureModelOracle for classifying and completing examples
        features: Set of all feature names
        feature_ids: Mapping from feature names to SAT variable IDs
    """

    def __init__(self, oracle: FeatureModelOracle):
        """
        Initialize generator with a FeatureModelOracle.

        Args:
            oracle: FeatureModelOracle for classifying examples
        """
        self.oracle = oracle
        fm_data = oracle.get_fm_data()
        self.features = fm_data.features
        self.feature_ids = fm_data.feature_ids

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
        is_valid = self.oracle.is_valid(example.assignments)
        example.example_type = ExampleType.POSITIVE if is_valid else ExampleType.NEGATIVE
        example_set.add(example)

    def _generate_valid_config(self, features_list: list) -> Optional[Dict[str, bool]]:
        """
        Generate a valid configuration with randomness.

        Uses partial random assumptions to get diverse valid configs.

        Args:
            features_list: List of feature names

        Returns:
            Valid configuration dict, or None if failed
        """
        shuffled = list(features_list)
        random.shuffle(shuffled)

        n_fixed = random.randint(0, len(shuffled) // 2)
        partial = {f: random.choice([True, False]) for f in shuffled[:n_fixed]}

        return self.oracle.complete_configuration(partial)
