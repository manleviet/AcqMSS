"""
QuAcqTask: assumption-ID-based task for QuAcq constraint acquisition.

Parallel to ConGenTask — uses integer assumption IDs instead of string IDs,
inherits DiagnosisTask for set_kb/assumptions/negation_map/set_b fields.
Also contains QuAcqTaskPreparation (co-located: creation logic next to data).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Dict

from explanation.models.task_preparation import (
    DescriptionProvider,
    DiagnosisTask,
    PreparationOutput,
    prepare_kb,
    _ASSUMPTION_PAIR_STRIDE,
)
if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle
    from .quacq_model import QuAcqModel


@dataclass
class QuAcqTask(DiagnosisTask):
    """Immutable task for QuAcq constraint acquisition.

    Inherits from DiagnosisTask:
        set_c:         Bias constraint assumption IDs (same role as ConGenTask)
        set_b:         BG assumption IDs (from BGData root constraint)
        set_kb:        Full KB with assumption guards
        negation_map:  {assumption_id -> negated_assumption_id}
        assumptions:   All assumption IDs

    QuAcq-specific immutable data:
        background_clauses:   Raw BG CNF clauses (no assumption guards)
        feature_ids:          Feature name -> SAT variable ID
        id_to_feature:        SAT variable ID -> feature name
        constraint_clauses:   assumption_id -> raw CNF clauses (no guards)
        negated_clauses:      assumption_id -> negated CNF clauses (raw, for QueryGenerator)

    Mutable state (remaining_bias, learned_kb, n_queries, query_history)
    lives in the QuAcq algorithm, not here.
    """
    # Raw BG CNF clauses (without assumption guards) for _find_conflict
    background_clauses: List[List[int]] = field(default_factory=list)

    # Feature name -> SAT variable ID
    feature_ids: Dict[str, int] = field(default_factory=dict)

    # SAT variable ID -> feature name
    id_to_feature: Dict[int, str] = field(default_factory=dict)

    # assumption_id -> raw clauses (WITHOUT assumption guards, for violation checking)
    constraint_clauses: Dict[int, List[List[int]]] = field(default_factory=dict)

    # assumption_id -> negated clauses (raw, for QueryGenerator and FindC)
    negated_clauses: Dict[int, List[List[int]]] = field(default_factory=dict)

    def get_kb_clauses(self, learned_kb: List[int]) -> List[List[int]]:
        """Get raw CNF clauses for given learned KB assumption IDs."""
        clauses = []
        for aid in learned_kb:
            clauses.extend(self.constraint_clauses.get(aid, []))
        return clauses

    def config_to_assumptions(self, config: Dict[str, bool]) -> List[int]:
        """Convert configuration dict to SAT assumption literals."""
        assumptions = []
        for name, value in config.items():
            if name in self.feature_ids:
                fid = self.feature_ids[name]
                assumptions.append(fid if value else -fid)
        return assumptions

    def partial_config_to_assumptions(self, config: Dict[str, bool],
                                      variables: set) -> List[int]:
        """Convert partial config (only variables in scope) to assumptions."""
        assumptions = []
        for name in variables:
            if name in config and name in self.feature_ids:
                fid = self.feature_ids[name]
                assumptions.append(fid if config[name] else -fid)
        return assumptions

    def model_to_config(self, model: List[int]) -> Dict[str, bool]:
        """Convert SAT model to configuration dict."""
        config = {}
        for lit in model:
            var = abs(lit)
            if var in self.id_to_feature:
                config[self.id_to_feature[var]] = lit > 0
        return config

    def get_constraints_with_scope(self, scope: set,
                                    remaining_bias: set) -> List[int]:
        """Get bias constraint assumption IDs whose variables match scope.

        Prefers exact scope match (c_vars == scope). Falls back to subset
        match (c_vars ⊆ scope) if no exact matches found.
        """
        exact = []
        subset = []
        for aid in remaining_bias:
            c_vars = self._get_constraint_vars(aid)
            if not c_vars:
                continue
            if c_vars == scope:
                exact.append(aid)
            elif c_vars.issubset(scope):
                subset.append(aid)
        return exact if exact else subset

    def _get_constraint_vars(self, assumption_id: int) -> set:
        """Get the set of feature-name variables for a constraint."""
        clauses = self.constraint_clauses.get(assumption_id, [])
        c_vars = set()
        for clause in clauses:
            for lit in clause:
                var = abs(lit)
                if var in self.id_to_feature:
                    c_vars.add(self.id_to_feature[var])
        return c_vars

    @staticmethod
    def violates_clauses(clauses: List[List[int]],
                         assignment: Dict[int, bool]) -> bool:
        """Check if assignment violates constraint clauses."""
        for clause in clauses:
            clause_satisfied = False
            for lit in clause:
                var = abs(lit)
                if var in assignment:
                    if (lit > 0 and assignment[var]) or (lit < 0 and not assignment[var]):
                        clause_satisfied = True
                        break
            if not clause_satisfied:
                return True
        return False


class QuAcqTaskPreparation:
    """Prepare QuAcqTask from bias + oracle. No E+/E-.

    Assumption ID layout (QuAcq owns Parts 5-6):
      Parts 1-4: Owned by Oracle (see OracleTaskPreparation)
      Part 5:    Tseitin vars (negated bias constraints)   <- This method
      Part 6:    Bias constraint assumptions (paired)      <- This method
    """

    def prepare(self, model: QuAcqModel,
                oracle: FeatureModelOracle) -> PreparationOutput:
        """Prepare QuAcqTask from model and oracle.

        Args:
            model: QuAcqModel with bias constraint_map
            oracle: FeatureModelOracle for BG data and feature IDs

        Returns:
            PreparationOutput with QuAcqTask and DescriptionProvider
        """
        result = QuAcqTask()
        provider = DescriptionProvider()

        # Step 0: Copy BG data from Oracle (root constraint pair)
        bg_data = oracle.get_bg_data()
        result.set_kb.extend(bg_data.set_kb)
        result.assumptions.extend(list(bg_data.assumptions))
        result.negation_map.update(bg_data.negation_map)
        for aid, desc in bg_data.descriptions.items():
            provider.add_constraint_description(aid, desc)
        result.set_b = list(bg_data.assumptions)

        # Store raw BG clauses (without assumption guards) for _find_conflict
        result.background_clauses = oracle.get_root_clauses()

        # Step 1: Assign assumption IDs (negated forms from builder)
        id_assumption = model.next_available_id
        bias_start_pos = len(result.assumptions)
        id_assumption = prepare_kb(
            result, provider, model.constraint_map,
            id_assumption, model.negated_constraint_map)

        # Step 3: Extract bias assumption IDs (stride=2: original, not negated)
        result.set_c = list(
            result.assumptions[bias_start_pos::_ASSUMPTION_PAIR_STRIDE])

        # Step 4: Build constraint_clauses and negated_clauses mappings
        for aid in result.set_c:
            name = provider.get_description(aid)
            if name in model.constraint_map:
                result.constraint_clauses[aid] = model.constraint_map[name]
            neg_key = f"NOT({name})"
            if neg_key in model.negated_constraint_map:
                result.negated_clauses[aid] = model.negated_constraint_map[neg_key]

        # Step 5: Populate feature_ids/id_to_feature from oracle
        fm_data = oracle.get_fm_data()
        result.feature_ids = fm_data.feature_ids
        result.id_to_feature = {v: k for k, v in fm_data.feature_ids.items()}

        return PreparationOutput(result, provider)
