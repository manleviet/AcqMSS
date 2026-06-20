"""Variable codec: the single source of truth for translating between feature
names, SAT variable IDs, and assignment-assumption literals for one KB.

Replaces the per-model duplication previously scattered across QuAcqModel
(``features`` / ``config_to_assumptions`` / ``model_to_config``), FMOracleModel
and FMOracle. Built once at the KB level and referenced by every Task derived
from that KB.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class VariableCodec:
    """Bidirectional codec between feature names, variable IDs, and assumptions.

    Attributes:
        id_to_name: SAT variable ID -> feature name. Always present; enables
            ``model_to_config`` (decoding a SAT model back to a configuration).
        pos_assignment_to_assumption: feature name -> assumption ID asserting the
            feature is selected. Optional — only populated when the KB carries an
            assignment-assumption layer (QuAcq Part 4 / FMOracle membership queries).
        neg_assignment_to_assumption: feature name -> assumption ID asserting the
            feature is deselected. Optional, paired with the positive map.
    """
    id_to_name: Dict[int, str]
    pos_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
    neg_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)

    def config_to_assumptions(self, config: Dict[str, bool]) -> List[int]:
        """Encode a feature configuration as assignment-assumption literals.

        Features absent from the assignment-assumption layer are skipped.
        """
        return [self.pos_assignment_to_assumption[feat] if val
                else self.neg_assignment_to_assumption[feat]
                for feat, val in config.items()
                if feat in self.pos_assignment_to_assumption]

    def model_to_config(self, model_lits: List[int]) -> Dict[str, bool]:
        """Decode a SAT model (list of signed literals) to a configuration dict."""
        config: Dict[str, bool] = {}
        for lit in model_lits:
            var = abs(lit)
            if var in self.id_to_name:
                config[self.id_to_name[var]] = lit > 0
        return config

    def get_constraint_vars(self, clauses: List[List[int]]) -> set:
        """Feature names referenced by the given constraint clauses.

        Takes the raw clauses (held per-Task) rather than an assumption ID, since
        the clause→ID mapping is task state, while name resolution is codec state.
        """
        return {self.id_to_name[abs(lit)]
                for clause in clauses for lit in clause
                if abs(lit) in self.id_to_name}
