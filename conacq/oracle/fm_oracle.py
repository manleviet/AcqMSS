"""
Feature model oracle using SAT solver for validation.

Loads a feature model from .uvl file, converts to CNF, and validates
configurations via persistent PySAT solver.
"""

from typing import Dict, Optional, Set, List

from pysat.solvers import Solver

from conacq.oracle.base import Oracle
from conacq.oracle.bg_data import BGData
from conacq.oracle.fm_data import FMData
from conacq.oracle.fm_oracle_model import FMOracleModel
from explanation.models.encoding import variable_literals_to_config
from explanation.operations.algorithms.checker import CheckerFactory
from profiling import get_global_profiler, AbstractProfiler, measure_time, count_calls


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

    # TODO: need check
    @property
    def fm(self):
        """Lazy-load FM for description extraction."""
        if self._fm is None:
            from flamapy.metamodels.fm_metamodel.transformations import UVLReader
            self._fm = UVLReader(self.fm_path).transform()
        return self._fm

    # --- Oracle ABC implementation ---

    @measure_time('oracle_is_valid')
    @count_calls('oracle_is_valid_calls')
    def is_valid(self, assignments: Dict[str, bool]) -> bool:
        """Check if configuration is valid (satisfies FM constraints).

        Args:
            assignments: Feature assignments {feature_name: True/False}

        Returns:
            True if configuration is valid
        """
        if any(name not in self._oracle_model.name_to_id for name in assignments):
            raise KeyError(f"Unknown features in assignment: {set(assignments) - set(self._oracle_model.name_to_id)}")

        set_c = self._oracle_model.with_configuration(assignments).get_c()

        return self._checker.is_consistent(set_c)

    # --- FM-specific extensions (not part of Oracle ABC) ---

    # TODO: need check
    def get_fm_data(self) -> FMData:
        """Create FMData snapshot from current oracle state.

        Returns:
            Frozen FMData with all FM metadata
        """
        return FMData(
            features=self.get_variables(),
            feature_ids=self.get_feature_ids(),
            root_feature=self.get_root_feature(),
            num_constraints=self.get_num_constraints(),
            next_available_id=self.get_next_available_id(),
        )

    def get_bg_data(self) -> BGData:
        """Return root BG assumption data for ConGen."""
        return self._oracle_model.bg_data

    def get_variables(self) -> Set[str]:
        """Get all feature names."""
        return set(self._oracle_model.name_to_id.keys())

    # TODO: need check
    def get_feature_ids(self) -> Dict[str, int]:
        """Get feature name to SAT variable ID mapping."""
        return dict(self._oracle_model.name_to_id)

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
            fid = self._oracle_model.name_to_id[name]
            assumptions.append(fid if value else -fid)

        solver = Solver(name=self.solver_name)
        for clause in self._oracle_model.get_fm_clauses():
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
        return variable_literals_to_config(model, self._oracle_model.id_to_name)

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

    # TODO: need check
    def get_root_feature(self) -> str:
        """Get root feature name."""
        return self.fm.root.name

    def get_root_clauses(self) -> List[List[int]]:
        """Get raw background knowledge clauses (root constraint)."""
        root = self.get_root_feature()
        return list(self._oracle_model.constraint_map[root])

    # TODO: need check
    def get_cnf_clauses(self) -> List[List[int]]:
        """Get the raw ground truth CNF clauses (without assumption guards)."""
        return self._oracle_model.get_fm_clauses()

    def get_num_constraints(self) -> int:
        """Get number of FM constraints in ground truth."""
        return len(self._oracle_model.constraint_map)

    def get_next_available_id(self) -> int:
        """Get starting Tseitin variable ID from FM model."""
        return self._oracle_model.next_available_id

    def __repr__(self):
        return f"FeatureModelOracle(features={len(self._oracle_model.name_to_id)})"

    # TODO: need update
    def cleanup(self):
        """Release checker resources."""
        if hasattr(self, '_checker') and self._checker is not None:
            self._checker.cleanup()
            self._checker = None

    def __del__(self):
        self.cleanup()
