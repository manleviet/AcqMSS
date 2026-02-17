"""
Feature model oracle using SAT solver for validation.

Loads a feature model from .uvl file, converts to CNF, and validates
configurations via persistent PySAT solver.
"""

from typing import Dict, Optional, Set, List

from pysat.solvers import Solver

from conacq.oracle.base import Oracle
from conacq.oracle.fm_data import FMData
from conacq.oracle.fm_oracle_model import FMOracleModel
from explanation.operations.algorithms.checker import CheckerFactory
from explanation.operations.algorithms.profiler import get_global_profiler, AbstractProfiler


class FeatureModelOracle(Oracle):
    """Oracle using feature model as ground truth.

    Loads a feature model, converts it to CNF, and uses a SAT solver
    to validate configurations.

    Extends Oracle ABC with FM-specific methods:
    get_fm_data(), complete_configuration(), get_features(), etc.

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

        # Lazy-loaded for description extraction (most callers never need this)
        self._fm = None
        self._constraint_descriptions_cache: Optional[Set[str]] = None

    @property
    def fm(self):
        """Lazy-load FM for description extraction."""
        if self._fm is None:
            from flamapy.metamodels.fm_metamodel.transformations import UVLReader
            self._fm = UVLReader(self.fm_path).transform()
        return self._fm

    # --- Oracle ABC implementation ---

    def is_valid(self, assignments: Dict[str, bool]) -> bool:
        """Check if configuration is valid (satisfies FM constraints).

        Args:
            assignments: Feature assignments {feature_name: True/False}

        Returns:
            True if configuration is valid
        """
        if any(name not in self._oracle_model.variables for name in assignments):
            raise KeyError(f"Unknown features in assignment: {set(assignments) - set(self._oracle_model.variables)}")

        self._oracle_model.with_configuration(assignments)

        return self._checker.is_consistent(self._oracle_model.get_c())

    # --- FM-specific extensions (not part of Oracle ABC) ---

    def get_fm_data(self) -> FMData:
        """Create FMData snapshot from current oracle state.

        Returns:
            Frozen FMData with all FM metadata
        """
        return FMData(
            features=self.get_features(),
            feature_ids=self.get_feature_ids(),
            root_feature=self.get_root_feature(),
            num_constraints=self.get_num_constraints(),
            next_tseitin_var=self.get_next_tseitin_var(),
        )

    def get_features(self) -> Set[str]:
        """Get all feature names."""
        return set(self._oracle_model.variables.keys())

    def get_feature_ids(self) -> Dict[str, int]:
        """Get feature name to SAT variable ID mapping."""
        return dict(self._oracle_model.variables)

    def complete_configuration(self, partial: Dict[str, bool]) -> Optional[Dict[str, bool]]:
        """Complete a partial configuration to a full valid one via SAT solving.

        If no valid completion exists for the given partial, falls back to
        returning any valid configuration (ignoring partial constraints).
        Returns None only if no valid configuration exists at all.

        Args:
            partial: Partial assignment {feature_name: True/False} for subset of features

        Returns:
            Full valid configuration dict, or None if no valid completion exists
        """
        assumptions = []
        for name, value in partial.items():
            fid = self._oracle_model.variables[name]
            assumptions.append(fid if value else -fid)

        solver = Solver(name=self.solver_name)
        for clause in self._oracle_model.get_raw_fm_clauses():
            solver.add_clause(clause)

        try:
            if solver.solve(assumptions=assumptions):
                return self._model_to_config(solver.get_model())
            # Fallback: try without assumptions
            if solver.solve():
                return self._model_to_config(solver.get_model())
        finally:
            solver.delete()

        return None

    def _model_to_config(self, model: List[int]) -> Dict[str, bool]:
        """Convert SAT model to feature config dict."""
        return {name: fid in model
                for name, fid in self._oracle_model.variables.items()}

    # Convenience getters (delegate to model)
    def get_kb(self) -> List[List[int]]:
        """Get the full knowledge base with assumptions."""
        return self._oracle_model.task.set_kb

    def get_assumptions(self) -> List[int]:
        """Get the list of assumption literals."""
        return self._oracle_model.task.assumptions

    def get_c(self) -> List[int]:
        """Get the set of constraint assumptions (FM constraints only, excluding feature assignments)."""
        return self._oracle_model.get_c()

    def get_root_feature(self) -> str:
        """Get root feature name."""
        return self.fm.root.name

    def get_cnf_clauses(self) -> List[List[int]]:
        """Get the raw ground truth CNF clauses (without assumption guards)."""
        return self._oracle_model.get_raw_fm_clauses()

    def get_num_constraints(self) -> int:
        """Get number of FM constraints in ground truth."""
        return len(self._oracle_model.constraint_map)

    def get_next_tseitin_var(self) -> int:
        """Get starting Tseitin variable ID from FM model."""
        return self._oracle_model.next_tseitin_var

    def get_constraint_descriptions(self) -> Set[str]:
        """Extract constraint descriptions from FM (cached).

        Returns:
            Set of constraint descriptions
        """
        if self._constraint_descriptions_cache is None:
            from conacq.oracle.constraint_description import extract_constraint_descriptions
            self._constraint_descriptions_cache = extract_constraint_descriptions(self.fm)
        return self._constraint_descriptions_cache

    def __repr__(self):
        return f"FeatureModelOracle(features={len(self._oracle_model.variables)})"

    def cleanup(self):
        """Release checker resources."""
        if hasattr(self, '_checker') and self._checker is not None:
            self._checker.cleanup()
            self._checker = None

    def __del__(self):
        self.cleanup()
