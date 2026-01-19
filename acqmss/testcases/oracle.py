"""
Oracle implementations for constraint acquisition.

The Oracle provides ground truth for classifying configurations as valid or invalid.
FeatureModelOracle uses a feature model as the ground truth.
"""

from abc import ABC, abstractmethod
from typing import Dict, Set, List, Optional
from pysat.solvers import Solver

from .data_structures import Example, ExampleType


class Oracle(ABC):
    """
    Abstract oracle interface for classifying examples.

    An oracle answers membership queries: is this configuration valid?
    """

    @abstractmethod
    def classify(self, example: Example) -> ExampleType:
        """
        Classify example as positive or negative.

        Args:
            example: Example to classify

        Returns:
            ExampleType.POSITIVE if valid, ExampleType.NEGATIVE if invalid
        """
        pass

    @abstractmethod
    def is_valid(self, assignments: Dict[str, bool]) -> bool:
        """
        Check if configuration is valid.

        Args:
            assignments: Feature assignments {feature_name: True/False}

        Returns:
            True if configuration satisfies the ground truth
        """
        pass

    @abstractmethod
    def get_features(self) -> Set[str]:
        """Get all feature names in the model"""
        pass

    @abstractmethod
    def get_feature_ids(self) -> Dict[str, int]:
        """Get mapping from feature names to SAT variable IDs"""
        pass


class FeatureModelOracle(Oracle):
    """
    Oracle using feature model as ground truth.

    Loads a feature model, converts it to CNF, and uses a SAT solver
    to validate configurations.

    Attributes:
        fm_path: Path to the feature model file
        fm: Loaded feature model object
        features: Set of all feature names
        feature_ids: Mapping {feature_name: SAT_variable_id}
        cnf_clauses: Ground truth CNF clauses
        solver: Persistent SAT solver for queries

    Example:
        >>> oracle = FeatureModelOracle('data/fms/model.uvl')
        >>> oracle.is_valid({'root': True, 'child': True})
        True
    """

    def __init__(self, fm_path: str):
        """
        Initialize oracle from feature model file.

        Args:
            fm_path: Path to feature model (.uvl format)
        """
        self.fm_path = fm_path
        self.fm = self._load_fm(fm_path)
        self.features = self._extract_features()
        self.feature_ids = self._build_feature_ids()
        self.leaf_features = self._extract_leaf_features()

        # Build ground truth CNF
        self.cnf_clauses = self._build_cnf()

        # Initialize persistent SAT solver
        self.solver = Solver(name='glucose4')
        for clause in self.cnf_clauses:
            self.solver.add_clause(clause)

    def _load_fm(self, fm_path: str):
        """Load feature model using flamapy"""
        from flamapy.metamodels.fm_metamodel.transformations import UVLReader

        if fm_path.endswith('.uvl'):
            return UVLReader(fm_path).transform()
        else:
            raise ValueError(f"Unsupported feature model format: {fm_path}")

    def _extract_features(self) -> Set[str]:
        """Extract all feature names from FM"""
        return {f.name for f in self.fm.get_features()}

    def _extract_leaf_features(self) -> Set[str]:
        """Extract leaf features (features with no children)"""
        return {f.name for f in self.fm.get_features() if f.is_leaf()}

    def _build_feature_ids(self) -> Dict[str, int]:
        """Build mapping from feature names to SAT variable IDs"""
        return {f: i + 1 for i, f in enumerate(sorted(self.features))}

    def _build_cnf(self) -> List[List[int]]:
        """
        Build CNF clauses from feature model using flamapy.

        Returns:
            List of CNF clauses (each clause is a list of literals)
        """
        from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat

        sat_model = FmToPysat(self.fm).transform()

        # Extract clauses from the model
        # The clauses are stored in sat_model.cnf
        clauses = []
        for clause in sat_model.get_all_clauses().clauses:
            clauses.append(list(clause))

        return clauses

    def classify(self, example: Example) -> ExampleType:
        """
        Classify example using SAT solver.

        Args:
            example: Example to classify

        Returns:
            ExampleType.POSITIVE if valid, ExampleType.NEGATIVE if invalid
        """
        is_valid = self.is_valid(example.assignments)
        return ExampleType.POSITIVE if is_valid else ExampleType.NEGATIVE

    def is_valid(self, assignments: Dict[str, bool]) -> bool:
        """
        Check if configuration is valid (satisfies FM constraints).

        Args:
            assignments: Feature assignments {feature_name: True/False}

        Returns:
            True if configuration is valid
        """
        assumptions = []
        for name, value in assignments.items():
            if name in self.feature_ids:
                fid = self.feature_ids[name]
                assumptions.append(fid if value else -fid)

        return self.solver.solve(assumptions=assumptions)

    def get_features(self) -> Set[str]:
        """Get all feature names"""
        return self.features

    def get_feature_ids(self) -> Dict[str, int]:
        """Get feature name to SAT variable ID mapping"""
        return self.feature_ids

    def get_leaf_features(self) -> Set[str]:
        """Get leaf features (features with no children)"""
        return self.leaf_features

    def get_root_feature(self) -> str:
        """Get root feature name"""
        return self.fm.root.name

    def get_valid_configuration(self, assumptions: Optional[List[int]] = None) -> Optional[Dict[str, bool]]:
        """
        Get a valid configuration using SAT solver.

        Args:
            assumptions: Optional list of literals to fix

        Returns:
            Complete valid assignment {feature: True/False}, or None if UNSAT
        """
        if assumptions is None:
            assumptions = []

        if self.solver.solve(assumptions=assumptions):
            model = self.solver.get_model()
            config = {}
            for name, fid in self.feature_ids.items():
                config[name] = fid in model
            return config
        return None

    def get_cnf_clauses(self) -> List[List[int]]:
        """Get the ground truth CNF clauses"""
        return self.cnf_clauses

    def get_num_constraints(self) -> int:
        """Get number of CNF clauses in ground truth"""
        return len(self.cnf_clauses)

    def __repr__(self):
        return f"FeatureModelOracle(features={len(self.features)}, " \
               f"clauses={len(self.cnf_clauses)})"

    def __del__(self):
        """Clean up SAT solver"""
        if hasattr(self, 'solver') and self.solver is not None:
            self.solver.delete()
