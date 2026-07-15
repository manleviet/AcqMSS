"""
Feature model oracle using SAT solver for validation.

Loads a feature model from .uvl file, converts to CNF, and validates
configurations via persistent PySAT solver.
"""

from typing import Dict, Optional, Set, List

from pysat.solvers import Solver

from conacq.oracle.fm_data import FMData
from conacq.oracle.fm_oracle_model import FMOracleModel, FMOracleTaskPreparation
from conacq.oracle.protocols import (
    MembershipOracle,
    CompletableOracle,
    CatalogProvider,
)
from explanation.api import variable_literals_to_config, config_to_assignment_assumptions
from explanation.api import build_checker, SolverBackend
from profiling import get_global_profiler, AbstractProfiler, measure_time, count_calls


class FMOracle(MembershipOracle, CompletableOracle, CatalogProvider):
    """Oracle using feature model as ground truth.

    Loads a feature model, converts it to CNF, and uses a SAT solver
    to validate configurations.

    Declares its three answer roles (ADR-0009/0010) by inheriting the narrow
    protocols: MembershipOracle (is_valid), CompletableOracle (complete_configuration),
    CatalogProvider (get_variables/get_variable_ids). Provisioning (job ②) is NOT a
    role of the oracle — it lives on the frozen OracleData snapshot.
    FM-specific methods: get_fm_data(), get_features(), etc.

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

        # Build the immutable FM KB, then RECEIVE the frozen provisioning snapshot
        # (job ②, ADR-0009) — the preparation assembles OracleData; the oracle does
        # not build what it provides, it only holds it.
        self._oracle_model = FMOracleModel.from_fm(fm_path).build()
        self.oracle_data = FMOracleTaskPreparation.prepare(self._oracle_model)

        # The oracle builds its own membership checker (job ①) from the REAL task in
        # the snapshot (one source — no fabricated task). The oracle owns its solver
        # mode (use_incremental).
        self._checker = build_checker(
            self.oracle_data.task,
            SolverBackend.from_flags(use_incremental=use_incremental),
            solver_name, self.profiler)

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
        # Read the catalog view once (not once per feature inside the generator).
        name_to_id = self._oracle_model.name_to_id
        if any(name not in name_to_id for name in assignments):
            raise KeyError(f"Unknown features in assignment: {set(assignments) - set(name_to_id)}")

        # FM-constraint assumptions (the frozen task's set_c, always active) plus
        # this query's feature-assignment assumptions. Both come from the immutable
        # OracleData: a query reads a frozen value, never a live actor's shiftable
        # state, so the background it hands the checker cannot drift.
        set_c = self.oracle_data.task.set_c + config_to_assignment_assumptions(
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
        """Get all feature names. The oracle exposes the catalog (CatalogProvider);
        the model owns the raw name↔id data."""
        return set(self._oracle_model.name_to_id.keys())

    def get_variable_ids(self) -> Dict[str, int]:
        """Get feature name → SAT variable ID mapping, derived from the model's
        name↔id catalog."""
        return dict(self._oracle_model.name_to_id)

    def _fm_clauses(self) -> List[List[int]]:
        """Raw FM CNF clauses (no assumption guards), derived from the KB's
        constraint_map.

        NOTE: rebuilt on every call. ``complete_configuration`` is a hot path, so a
        persistent completion solver (issue #10) belongs here — deferred to T11.5;
        do NOT optimize it in this arc (behaviour must stay identical)."""
        return [clause for clauses in self._oracle_model.constraint_map.values()
                for clause in clauses]

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
        for clause in self._fm_clauses():
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
        return self._fm_clauses()

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
