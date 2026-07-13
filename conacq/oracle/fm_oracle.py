"""
Feature model oracle using SAT solver for validation.

Loads a feature model from .uvl file, converts to CNF, and validates
configurations via persistent PySAT solver.
"""

from typing import Dict, Optional, Set, List

from pysat.solvers import Solver

from conacq.oracle.base import Oracle
from conacq.oracle.fm_data import FMData
from conacq.oracle.oracle_data import OracleData
from conacq.oracle.fm_oracle_model import FMOracleModel
from explanation.api import variable_literals_to_config, config_to_assignment_assumptions
from explanation.api import build_checker, SolverBackend
from profiling import get_global_profiler, AbstractProfiler, measure_time, count_calls


class FMOracle(Oracle):
    """Oracle using feature model as ground truth.

    Loads a feature model, converts it to CNF, and uses a SAT solver
    to validate configurations.

    Extends Oracle ABC with FM-specific methods:
    get_fm_data(), complete_configuration(), get_features(), etc.

    Example:
        >>> oracle = FMOracle('data/fms/model.uvl')
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
        self._checker = build_checker(
            self._oracle_model.task,
            SolverBackend.from_flags(use_incremental=self._oracle_model.use_incremental),
            solver_name, self.profiler)

        # Lazy-loaded for description extraction (most callers never need this)
        self._fm = None

        # Job ② (ADR-0009): freeze the provisioning surface once, at build time.
        # The oracle answers queries; this snapshot provisions the algorithm.
        # Being immutable, nothing a membership query does can reach it.
        self.oracle_data = self._build_oracle_data()

    def _build_oracle_data(self) -> OracleData:
        """Snapshot the oracle model's provisioning surface into a frozen value."""
        model = self._oracle_model
        # Raw root-constraint clauses, keyed by the root feature name (unchanged
        # from the former get_root_clauses computation).
        root_clauses = list(model.constraint_map[self.get_root_feature()])
        return OracleData(
            kb=model.get_kb(),
            assumptions=model.get_assumptions(),
            c=model.get_c(),
            bg_data=model.bg_data,
            root_clauses=root_clauses,
            assignment_map=model.assignment_map,
            next_available_id=model.next_available_id,
        )

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
        # Read the catalog view once (not once per feature inside the generator).
        name_to_id = self._oracle_model.name_to_id
        if any(name not in name_to_id for name in assignments):
            raise KeyError(f"Unknown features in assignment: {set(assignments) - set(name_to_id)}")

        # FM-constraint assumptions (the frozen snapshot's set_c, always active)
        # plus this query's feature-assignment assumptions. Both come from the
        # immutable OracleData: a query reads a frozen value, never a live actor's
        # shiftable state, so the background it hands the checker cannot drift.
        set_c = self.oracle_data.c + config_to_assignment_assumptions(
            assignments, self.oracle_data.assignment_map)

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
            feature_ids=self.get_variable_ids(),
            root_feature=self.get_root_feature(),
            num_constraints=self.get_num_constraints(),
            next_available_id=self.get_next_available_id(),
        )

    def get_variables(self) -> Set[str]:
        """Get all feature names (delegated to the catalog owner)."""
        return self._oracle_model.get_variables()

    def get_variable_ids(self) -> Dict[str, int]:
        """Get feature name to SAT variable ID mapping (delegated to the model)."""
        return self._oracle_model.get_variable_ids()

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

    # TODO: need check
    def get_root_feature(self) -> str:
        """Get root feature name."""
        return self.fm.root.name

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
        return f"FMOracle(features={len(self._oracle_model.name_to_id)})"

    # TODO: need update
    def cleanup(self):
        """Release checker resources."""
        if hasattr(self, '_checker') and self._checker is not None:
            self._checker.cleanup()
            self._checker = None

    def __del__(self):
        self.cleanup()
