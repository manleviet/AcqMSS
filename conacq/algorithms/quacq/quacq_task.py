"""
QuAcqTask: assumption-ID-based task for QuAcq constraint acquisition.

Parallel to ConGenTask — uses integer assumption IDs instead of string IDs,
inherits DiagnosisTask for set_kb/assumptions/negation_map/set_b fields.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional

from explanation.models.task_preparation import DiagnosisTask


@dataclass
class QuAcqTask(DiagnosisTask):
    """Assumption-based task for QuAcq, parallel to ConGenTask.

    Inherits from DiagnosisTask:
        set_c:         Unused by QuAcq (empty list)
        set_b:         BG assumption IDs (from BGData root constraint)
        set_kb:        Full KB with assumption guards
        negation_map:  {assumption_id -> negated_assumption_id}
        assumptions:   All assumption IDs

    QuAcq-specific fields:
        bias:                 Set of bias constraint assumption IDs (O(1) removal)
        learned_kb:           List of learned KB assumption IDs
        background_clauses:   Raw BG CNF clauses (no assumption guards)
        feature_ids:          Feature name -> SAT variable ID
        id_to_feature:        SAT variable ID -> feature name
        constraint_clauses:   assumption_id -> raw CNF clauses (no guards)
        negated_clauses:      assumption_id -> negated CNF clauses (raw, for QueryGenerator)
        n_queries:            Number of membership queries asked
        query_history:        List of (config, answer, source) triples
    """
    # Bias constraint assumption IDs (set for O(1) removal)
    bias: Set[int] = field(default_factory=set)

    # Learned KB assumption IDs
    learned_kb: List[int] = field(default_factory=list)

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

    # Query statistics
    n_queries: int = 0

    # Query history: (config, oracle_answer, source) triples
    query_history: List[Tuple[Dict[str, bool], bool, str]] = field(default_factory=list)

    def get_kb_clauses(self) -> List[List[int]]:
        """Get raw CNF clauses from learned KB assumption IDs."""
        clauses = []
        for aid in self.learned_kb:
            clauses.extend(self.constraint_clauses.get(aid, []))
        return clauses

    def add_to_kb(self, assumption_id: int) -> None:
        """Add a constraint assumption ID to the learned KB."""
        if assumption_id not in self.learned_kb:
            self.learned_kb.append(assumption_id)

    def remove_from_bias(self, assumption_ids: List[int]) -> None:
        """Remove constraint assumption IDs from the bias set."""
        self.bias -= set(assumption_ids)

    def record_query(self, config: Dict[str, bool], answer: bool,
                     source: str = 'main') -> None:
        """Record a membership query and its answer."""
        self.n_queries += 1
        self.query_history.append((config.copy(), answer, source))

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

    def get_constraints_with_scope(self, scope: set) -> List[int]:
        """Get bias constraint assumption IDs whose variables match scope.

        Prefers exact scope match (c_vars == scope). Falls back to subset
        match (c_vars ⊆ scope) if no exact matches found.
        """
        exact = []
        subset = []
        for aid in self.bias:
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

    def clone(self) -> 'QuAcqTask':
        """Create a deep copy of this task."""
        return QuAcqTask(
            # DiagnosisTask fields
            set_b=self.set_b.copy(),
            set_kb=[c.copy() for c in self.set_kb],
            assumptions=self.assumptions.copy(),
            negation_map=dict(self.negation_map),
            # QuAcqTask fields
            bias=set(self.bias),
            learned_kb=self.learned_kb.copy(),
            background_clauses=[c.copy() for c in self.background_clauses],
            feature_ids=dict(self.feature_ids),
            id_to_feature=dict(self.id_to_feature),
            constraint_clauses={k: [c.copy() for c in v]
                                for k, v in self.constraint_clauses.items()},
            negated_clauses={k: [c.copy() for c in v]
                             for k, v in self.negated_clauses.items()},
            n_queries=self.n_queries,
            query_history=[(c.copy(), a, s) for c, a, s in self.query_history]
        )
