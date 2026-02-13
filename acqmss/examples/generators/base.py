"""
Base class for example generators.
"""

import random
from abc import ABC, abstractmethod
from typing import Optional, Dict

from pysat.solvers import Solver

from ..data_structures import Example, ExampleSet, ExampleType
from acqmss.oracle import Oracle


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
        # Shuffle to add randomness
        shuffled = list(features_list)
        random.shuffle(shuffled)

        # Pick random subset to fix
        n_fixed = random.randint(0, len(shuffled) // 2)
        assumptions = []

        for f in shuffled[:n_fixed]:
            fid = self.feature_ids[f]
            val = random.choice([True, False])
            assumptions.append(fid if val else -fid)

        # Create temporary solver
        solver = Solver(name='glucose4')
        for clause in self.oracle.get_cnf_clauses():
            solver.add_clause(clause)

        try:
            if solver.solve(assumptions=assumptions):
                model = solver.get_model()
                config = {}
                for name, fid in self.feature_ids.items():
                    config[name] = fid in model
                return config
            else:
                # Fallback: try without assumptions
                if solver.solve():
                    model = solver.get_model()
                    config = {}
                    for name, fid in self.feature_ids.items():
                        config[name] = fid in model
                    return config
        finally:
            solver.delete()

        return None
