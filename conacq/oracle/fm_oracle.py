"""
Feature model oracle using SAT solver for validation.

Loads a feature model from .uvl file, converts to CNF, and validates
configurations via a persistent PySAT checker built once from the base task.
"""

from typing import Dict, Optional, Set, List

from pysat.solvers import Solver

from conacq.oracle.base import Oracle
from conacq.oracle.bg_data import BGData
from conacq.oracle.fm_data import FMData
from conacq.oracle.fm_oracle_model import FMOracleModel
from explanation.models.task_preparation import DiagnosisTask
from explanation.operations.algorithms.checker import CheckerFactory
from explanation.operations.algorithms.profiler import get_global_profiler, AbstractProfiler, measure_time, count_calls


class FeatureModelOracle(Oracle):
    """Oracle using feature model as ground truth.

    Loads a feature model, converts it to CNF, and uses a SAT solver
    to validate configurations.

    The checker is built ONCE from the base task (prepare_task with no
    configuration).  Per-query, we extend set_c with the codec-encoded
    assignment assumptions rather than mutating the model.

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
            use_incremental: Whether to use incremental solver for membership queries
            profiler: Profiler instance (uses global if None)
        """
        self.fm_path = fm_path
        self.solver_name = solver_name
        self.profiler = profiler if profiler is not None else get_global_profiler()

        # Build model (loads FM, populates constraint_map/variables, calls prepare_task)
        self._oracle_model = FMOracleModel.from_fm(fm_path).build()

        # Obtain the base task (no configuration applied) and its codec
        self._base_task: DiagnosisTask = self._oracle_model.prepare_task()

        # Build checker ONCE from the base task
        self._checker = CheckerFactory.create_from_task(
            self._base_task,
            solver_name=solver_name,
            use_incremental=use_incremental,
            profiler_instance=self.profiler,
        )

        # Lazy-loaded for description extraction (most callers never need this)
        self._fm = None

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

        Builds the set_c for this query as:
            base_set_c + codec.config_to_assumptions(assignments)

        No model mutation — pure per-query computation.

        Args:
            assignments: Feature assignments {feature_name: True/False}

        Returns:
            True if configuration is valid
        """
        if any(name not in self._oracle_model.variables for name in assignments):
            raise KeyError(
                f"Unknown features in assignment: "
                f"{set(assignments) - set(self._oracle_model.variables)}"
            )

        codec = self._base_task.codec
        # base_set_c: FM constraint assumptions only (no feature assignments)
        base_set_c = self._oracle_model._base_set_c
        config_assumptions = codec.config_to_assumptions(assignments)
        set_c = base_set_c + config_assumptions

        return self._checker.is_consistent(set_c)

    # --- FM-specific extensions (not part of Oracle ABC) ---

    def get_fm_data(self) -> FMData:
        """Create FMData snapshot from current oracle state."""
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
        return set(self._oracle_model.variables.keys())

    def get_feature_ids(self) -> Dict[str, int]:
        """Get feature name to SAT variable ID mapping."""
        return dict(self._oracle_model.variables)

    def complete_configuration(self, partial: Dict[str, bool]) -> Optional[Dict[str, bool]]:
        """Complete a partial configuration to a full valid one via SAT solving.

        Uses a one-shot local Solver (not the persistent checker) because we
        need get_model() from a fresh solve, and this path is not a hot-path.
        Falls back to any valid configuration if partial constraints are
        unsatisfiable.  Returns None only if no valid configuration exists.

        Args:
            partial: Partial assignment {feature_name: True/False}

        Returns:
            Full valid configuration dict, or None if no valid completion exists
        """
        assumptions = []
        for name, value in partial.items():
            fid = self._oracle_model.variables[name]
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
        return {name: fid in model
                for name, fid in self._oracle_model.variables.items()}

    # Convenience getters (delegate to base task / model)

    def get_kb(self) -> List[List[int]]:
        """Get the full knowledge base with assumptions (from base task)."""
        return self._base_task.set_kb

    def get_assumptions(self) -> List[int]:
        """Get the list of assumption literals (from base task)."""
        return self._base_task.assumptions

    def get_c(self) -> List[int]:
        """Get the set of constraint assumptions (FM constraints only, excluding feature assignments)."""
        return list(self._oracle_model._base_set_c)

    def get_root_feature(self) -> str:
        """Get root feature name."""
        return self.fm.root.name

    def get_root_clauses(self) -> List[List[int]]:
        """Get raw background knowledge clauses (root constraint)."""
        root = self.get_root_feature()
        return list(self._oracle_model.constraint_map[root])

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
        return f"FeatureModelOracle(features={len(self._oracle_model.variables)})"

    def cleanup(self):
        """Release checker resources."""
        if hasattr(self, '_checker') and self._checker is not None:
            self._checker.cleanup()
            self._checker = None

    def __del__(self):
        self.cleanup()
