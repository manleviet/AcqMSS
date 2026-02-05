"""
Task data structures for Interactive (QuAcq) constraint acquisition.

Defines the InteractiveTask that maintains state throughout the
interactive learning process.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any


def _to_hashable(item: Any) -> Any:
    """Convert item to hashable form for set operations."""
    if isinstance(item, list):
        return tuple(_to_hashable(x) for x in item)
    return item


@dataclass
class InteractiveTask:
    """
    Task state for interactive constraint acquisition.

    Maintains all state needed during the QuAcq learning loop:
    - Remaining bias constraints to test
    - Learned knowledge base
    - Background knowledge
    - Constraint mappings for SAT solving

    Attributes:
        bias: List of remaining constraint IDs in the bias
        learned_kb: List of constraint IDs that have been learned
        background: Background knowledge assumptions (BG)
        feature_ids: Mapping from feature names to SAT variable IDs
        constraint_map: Mapping from constraint ID to its CNF clauses
        negated_constraint_map: Mapping from constraint ID to negated CNF clauses
        n_queries: Count of membership queries asked
        query_history: History of (query, answer) pairs for analysis
    """
    # Remaining bias constraint IDs
    bias: List[str] = field(default_factory=list)

    # Learned constraint IDs (KB)
    learned_kb: List[str] = field(default_factory=list)

    # Background knowledge (BG) as assumption literals
    background: List[int] = field(default_factory=list)

    # Feature name to SAT variable ID mapping
    feature_ids: Dict[str, int] = field(default_factory=dict)

    # Reverse mapping: SAT variable ID to feature name
    id_to_feature: Dict[int, str] = field(default_factory=dict)

    # Constraint ID to CNF clauses mapping
    constraint_map: Dict[str, List[List[int]]] = field(default_factory=dict)

    # Constraint ID to negated CNF clauses mapping
    negated_constraint_map: Dict[str, List[List[int]]] = field(default_factory=dict)

    # Query statistics
    n_queries: int = 0

    # Query history: list of (configuration, oracle_answer) tuples
    query_history: List[Tuple[Dict[str, bool], bool]] = field(default_factory=list)

    def get_kb_clauses(self) -> List[List[int]]:
        """Get all CNF clauses from the learned KB."""
        clauses = []
        for c_id in self.learned_kb:
            if c_id in self.constraint_map:
                clauses.extend(self.constraint_map[c_id])
        return clauses

    def get_bias_clauses(self) -> Dict[str, List[List[int]]]:
        """Get CNF clauses for all remaining bias constraints."""
        return {c_id: self.constraint_map[c_id]
                for c_id in self.bias
                if c_id in self.constraint_map}

    def add_to_kb(self, constraint_id: str) -> None:
        """Add a constraint to the learned KB."""
        if constraint_id not in self.learned_kb:
            self.learned_kb.append(constraint_id)

    def remove_from_bias(self, constraint_ids: List[str]) -> None:
        """Remove constraints from the bias."""
        for c_id in constraint_ids:
            if c_id in self.bias:
                self.bias.remove(c_id)

    def record_query(self, config: Dict[str, bool], answer: bool) -> None:
        """Record a membership query and its answer."""
        self.n_queries += 1
        self.query_history.append((config.copy(), answer))

    def config_to_assumptions(self, config: Dict[str, bool]) -> List[int]:
        """Convert configuration dict to SAT assumption literals."""
        assumptions = []
        for name, value in config.items():
            if name in self.feature_ids:
                fid = self.feature_ids[name]
                assumptions.append(fid if value else -fid)
        return assumptions

    def model_to_config(self, model: List[int]) -> Dict[str, bool]:
        """Convert SAT model to configuration dict."""
        config = {}
        for lit in model:
            var = abs(lit)
            if var in self.id_to_feature:
                config[self.id_to_feature[var]] = lit > 0
        return config

    def get_constraint_name(self, constraint_id: str) -> str:
        """Get human-readable constraint name."""
        return constraint_id

    def clone(self) -> 'InteractiveTask':
        """Create a deep copy of this task."""
        return InteractiveTask(
            bias=self.bias.copy(),
            learned_kb=self.learned_kb.copy(),
            background=self.background.copy(),
            feature_ids=self.feature_ids.copy(),
            id_to_feature=self.id_to_feature.copy(),
            constraint_map={k: [c.copy() for c in v]
                            for k, v in self.constraint_map.items()},
            negated_constraint_map={k: [c.copy() for c in v]
                                    for k, v in self.negated_constraint_map.items()},
            n_queries=self.n_queries,
            query_history=[(c.copy(), a) for c, a in self.query_history]
        )
