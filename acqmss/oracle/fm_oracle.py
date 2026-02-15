"""
Feature model oracle using SAT solver for validation.

Loads a feature model from .uvl file, converts to CNF, and validates
configurations via persistent PySAT solver.
"""

from typing import Dict, Set, List, Optional

from flamapy.metamodels.fm_metamodel.models import FeatureModel
from pysat.solvers import Solver

from acqmss.oracle.base import Oracle
from acqmss.oracle.fm_oracle_model import FMOracleModel
from explanation.operations.algorithms.checker import CheckerFactory
from explanation.operations.algorithms.profiler import get_global_profiler, AbstractProfiler


# def _load_fm(fm_path: str) -> FeatureModel:
#     """Load feature model using flamapy."""
#     from flamapy.metamodels.fm_metamodel.transformations import UVLReader
#
#     if fm_path.endswith('.uvl'):
#         return UVLReader(fm_path).transform()
#     else:
#         raise ValueError(f"Unsupported feature model format: {fm_path}")


class FeatureModelOracle(Oracle):
    """Oracle using feature model as ground truth.

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

    def __init__(self, fm_path: str, solver_name: str = 'glucose4',
                 use_incremental: bool = True,
                 profiler: AbstractProfiler = None):
        """Initialize oracle from feature model file.

        Args:
            fm_path: Path to feature model (.uvl format)
            solver_name: SAT solver name for checker
            profiler: Profiler instance (uses global if None)
        """
        self.fm_path = fm_path

        self.solver_name = solver_name
        self.profiler = profiler if profiler is not None else get_global_profiler()

        # Prepares the model and checker
        self._oracle_model = FMOracleModel.from_fm(fm_path).set_incremental(use_incremental).build()
        self._checker = CheckerFactory.create_from_model(self._oracle_model, solver_name, self.profiler)

        # Load FM for constraint description extraction (used by evaluation)
        # from flamapy.metamodels.fm_metamodel.transformations import UVLReader
        # self.fm = UVLReader(fm_path).transform()
        #
        # # Build ground truth CNF (also extracts flamapy variable mapping)
        # self.cnf_clauses = self._build_cnf()
        # self.feature_ids = self._build_feature_ids()
        #
        # # Verify feature_ids covers contiguous 1..n range matching CNF variables
        # assert set(self.feature_ids.values()) == set(range(1, len(self.features) + 1)), \
        #     "feature_ids must cover variables 1..n matching CNF clause space"
        # 
        # # Build FMOracleModel + ConsistencyChecker for is_valid()
        # constraint_map = {"fm": self.cnf_clauses}
        # max_var = max(abs(lit) for clause in self.cnf_clauses for lit in clause)
        # self._oracle_model = FMOracleModel.from_fm_data(
        #     constraint_map=constraint_map,
        #     variables=self.feature_ids,
        #     next_tseitin_var=max_var
        # )
        # self.checker = CheckerFactory.create_from_model(
        #     self._oracle_model, solver_name, self.profiler
        # )

    # def _extract_features(self) -> Set[str]:
    #     """Extract all feature names from FM."""
    #     return {f.name for f in self.fm.get_features()}
    #
    # def _extract_leaf_features(self) -> Set[str]:
    #     """Extract leaf features (features with no children)."""
    #     return {f.name for f in self.fm.get_features() if f.is_leaf()}
    #
    # def _build_feature_ids(self) -> Dict[str, int]:
    #     """Build mapping from feature names to SAT variable IDs.
    #
    #     Uses flamapy's variable assignment (tree traversal order)
    #     to match CNF clause variable IDs.
    #     """
    #     return dict(self._flamapy_variables)
    #
    # def _build_cnf(self) -> List[List[int]]:
    #     """Build CNF clauses from feature model using flamapy.
    #
    #     Also stores flamapy's variable mapping as the authoritative
    #     source for feature-to-SAT-variable ID assignment.
    #
    #     Returns:
    #         List of CNF clauses (each clause is a list of literals)
    #     """
    #     from flamapy.metamodels.pysat_metamodel.transformations import FmToPysat
    #
    #     sat_model = FmToPysat(self.fm).transform()
    #
    #     # Store flamapy's variable mapping (authoritative source)
    #     self._flamapy_variables = dict(sat_model.variables)
    #
    #     # Extract clauses from the model
    #     clauses = []
    #     for clause in sat_model.get_all_clauses().clauses:
    #         clauses.append(list(clause))
    #
    #     return clauses

    # --- Oracle ABC implementation ---

    # Convenience getters (delegate to result)
    def get_c(self) -> List:
        """Get the set of potentially faulty constraints."""
        return self._oracle_model.task.set_c

    def get_kb(self) -> List[List[int]]:
        """Get the full knowledge base with assumptions."""
        return self._oracle_model.task.set_kb

    def get_assumptions(self) -> List[int]:
        """Get the list of assumption literals."""
        return self._oracle_model.task.assumptions

    def is_valid(self, assignments: Dict[str, bool]) -> bool:
        """Check if configuration is valid (satisfies FM constraints).

        Args:
            assignments: Feature assignments {feature_name: True/False}

        Returns:
            True if configuration is valid
        """
        # If any unknown features are assigned, we consider it invalid (backward compatibility)
        if any(name not in self._oracle_model.variables for name in assignments):
            raise KeyError(f"Unknown features in assignment: {set(assignments) - set(self._oracle_model.variables)}")

        self._oracle_model.with_configuration(assignments)

        return self._checker.is_consistent(self._oracle_model.get_c())

    def get_features(self) -> Set[str]:
        """Get all feature names."""
        return set(self._oracle_model.variables.keys())

    def get_feature_ids(self) -> Dict[str, int]:
        """Get feature name to SAT variable ID mapping."""
        return dict(self._oracle_model.variables)

    # --- FM-specific extensions ---

    def get_leaf_features(self) -> Set[str]:
        """Get leaf features (features with no children)."""
        return {f.name for f in self.fm.get_features() if f.is_leaf()}

    def get_root_feature(self) -> str:
        """Get root feature name."""
        return self.fm.root.name

    # def get_valid_configuration(self, assumptions: Optional[List[int]] = None) -> Optional[Dict[str, bool]]:
    #     """Get a valid configuration using SAT solver.
    #
    #     Uses raw Solver (needs get_model() for assignment extraction).
    #
    #     Args:
    #         assumptions: Optional list of literals to fix
    #
    #     Returns:
    #         Complete valid assignment {feature: True/False}, or None if UNSAT
    #     """
    #     solver = Solver(name=self.solver_name, bootstrap_with=self.cnf_clauses)
    #     try:
    #         if solver.solve(assumptions=assumptions or []):
    #             model = solver.get_model()
    #             config = {}
    #             for name, fid in self.feature_ids.items():
    #                 config[name] = fid in model
    #             return config
    #         return None
    #     finally:
    #         solver.delete()

    def get_cnf_clauses(self) -> List[List[int]]:
        """Get the raw ground truth CNF clauses (without assumption guards)."""
        return self._oracle_model.get_raw_fm_clauses()

    def get_num_constraints(self) -> int:
        """Get number of FM constraints in ground truth."""
        return len(self._oracle_model.constraint_map)

    def get_constraint_descriptions(self) -> Set[str]:
        """Extract constraint descriptions from FM.

        Returns descriptions in format matching bias:
        - "parent --mandatory--> child"
        - "parent --optional--> child"
        - "parent --alternative--> [child1, child2, ...]"
        - "parent --or--> [child1, child2, ...]"
        - "feature1 requires feature2"
        - "feature1 excludes feature2"

        Returns:
            Set of constraint descriptions
        """
        descriptions = set()

        # Extract hierarchical constraints from feature relationships
        for feature in self.fm.get_features():
            for relation in feature.get_relations():
                if relation.is_mandatory():
                    for child in relation.children:
                        descriptions.add(f"{feature.name} --mandatory--> {child.name}")
                elif relation.is_optional():
                    for child in relation.children:
                        descriptions.add(f"{feature.name} --optional--> {child.name}")
                elif relation.is_alternative():
                    children_names = [c.name for c in relation.children]
                    descriptions.add(f"{feature.name} --alternative--> {children_names}")
                elif relation.is_or():
                    children_names = [c.name for c in relation.children]
                    descriptions.add(f"{feature.name} --or--> {children_names}")

        # Extract cross-tree constraints
        for ctc in self.fm.get_constraints():
            desc = self._parse_ctc_to_description(ctc)
            if desc:
                descriptions.add(desc)

        return descriptions

    def _parse_ctc_to_description(self, ctc) -> Optional[str]:
        """Parse cross-tree constraint to description format.

        Supports requires and excludes constraints.
        """
        from flamapy.core.models.ast import ASTOperation

        ast = ctc.ast
        if ast is None:
            return None

        root = ast.root

        # Handle requires: A => B (same as !A | B)
        if root.data == ASTOperation.IMPLIES:
            left = root.left
            right = root.right
            if left and right:
                left_name = self._get_feature_name(left)
                right_name = self._get_feature_name(right)
                if left_name and right_name:
                    return f"{left_name} requires {right_name}"

        # Handle excludes: !(A & B) or A => !B
        if root.data == ASTOperation.NOT:
            inner = root.left
            if inner and inner.data == ASTOperation.AND:
                left = inner.left
                right = inner.right
                if left and right:
                    left_name = self._get_feature_name(left)
                    right_name = self._get_feature_name(right)
                    if left_name and right_name:
                        names = sorted([left_name, right_name])
                        return f"{names[0]} excludes {names[1]}"

        if root.data == ASTOperation.IMPLIES:
            left = root.left
            right = root.right
            if right and right.data == ASTOperation.NOT:
                left_name = self._get_feature_name(left)
                right_name = self._get_feature_name(right.left)
                if left_name and right_name:
                    names = sorted([left_name, right_name])
                    return f"{names[0]} excludes {names[1]}"

        # Handle OR patterns (flamapy UVL representation)
        if root.data == ASTOperation.OR:
            left = root.left
            right = root.right
            if left and right:
                # OR(NOT(A), NOT(B)) == !(A & B) == A excludes B
                if (left.data == ASTOperation.NOT and
                        right.data == ASTOperation.NOT):
                    left_name = self._get_feature_name(left.left)
                    right_name = self._get_feature_name(right.left)
                    if left_name and right_name:
                        names = sorted([left_name, right_name])
                        return f"{names[0]} excludes {names[1]}"

                # OR(NOT(A), B) == !A | B == A => B == A requires B
                if left.data == ASTOperation.NOT:
                    left_name = self._get_feature_name(left.left)
                    right_name = self._get_feature_name(right)
                    if left_name and right_name:
                        return f"{left_name} requires {right_name}"

        # Fallback: use constraint string representation
        return str(ctc)

    def _get_feature_name(self, node) -> Optional[str]:
        """Extract feature name from AST node."""
        from flamapy.core.models.ast import ASTOperation

        if node is None:
            return None

        # If it's a simple feature reference
        if node.data is None or not isinstance(node.data, ASTOperation):
            return str(node.data) if node.data else None

        return None

    def __repr__(self):
        return f"FeatureModelOracle(features={self.get_feature_count()})"

    def cleanup(self):
        """Release checker resources."""
        if hasattr(self, '_checker') and self._checker is not None:
            self._checker.cleanup()
            self._checker = None

    def __del__(self):
        self.cleanup()
