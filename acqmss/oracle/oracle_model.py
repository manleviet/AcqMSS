"""
Oracle models for ConsistencyChecker integration.

OracleModel: Assumption-guarded FM validation (incremental checker).
OneShotModel: Baked unit clauses for one-shot SAT checks (non-incremental).

Both satisfy CheckerModel Protocol for use with CheckerFactory.create_from_model().
"""

from typing import Dict, List


class OracleModel:
    """Model for Oracle FM validation via ConsistencyChecker.

    Uses constraint_map + variables pattern (same as DiagnosisModel/ConGenModel).
    Satisfies CheckerModel Protocol after prepare().

    FM clauses go directly into set_kb (always active).
    Feature assignments become assumption-guarded unit clauses:
      [-a_pos_i, fid]  → if a_pos_i active, feature must be true
      [-a_neg_i, -fid] → if a_neg_i active, feature must be false
    """

    def __init__(self):
        # Same data structure as ConGenModel/DiagnosisModel
        self.constraint_map: Dict[str, List[List[int]]] = {}
        self.variables: Dict[str, int] = {}
        self.next_tseitin_var: int = 0
        self.use_incremental: bool = True

        # Populated after prepare()
        self._set_kb: List[List[int]] = []
        self._assumptions: List[int] = []
        self._feature_to_pos_assumption: Dict[str, int] = {}
        self._feature_to_neg_assumption: Dict[str, int] = {}

    def get_kb(self) -> List[List[int]]:
        return self._set_kb

    def get_assumptions(self) -> List[int]:
        return self._assumptions

    def config_to_active_assumptions(self, config: Dict[str, bool]) -> List[int]:
        """Convert feature config to list of assumption IDs to activate."""
        active = []
        for name, value in config.items():
            if value:
                active.append(self._feature_to_pos_assumption[name])
            else:
                active.append(self._feature_to_neg_assumption[name])
        return active

    def prepare(self) -> 'OracleModel':
        """Build set_kb + assumptions from constraint_map and variables."""
        OracleTaskPreparation.prepare(self)
        return self

    @classmethod
    def from_fm(cls, constraint_map: Dict[str, List[List[int]]],
                variables: Dict[str, int],
                next_tseitin_var: int) -> 'OracleModel':
        """Factory: create from FM data and prepare."""
        model = cls()
        model.constraint_map = constraint_map
        model.variables = variables
        model.next_tseitin_var = next_tseitin_var
        return model.prepare()


class OracleTaskPreparation:
    """Prepare assumption-guarded clauses for Oracle FM validation.

    FM constraints → direct in set_kb (always active).
    Feature assignments → assumption-guarded unit clauses.
    """

    @staticmethod
    def prepare(model: 'OracleModel') -> None:
        set_kb = []
        assumptions = []

        # Step 1: FM constraints from constraint_map → direct in set_kb
        for clauses in model.constraint_map.values():
            set_kb.extend(clauses)

        # Step 2: Feature assignments → assumption-guarded
        id_assumption = model.next_tseitin_var + 1
        feature_to_pos = {}
        feature_to_neg = {}

        for name, fid in model.variables.items():
            # a_pos: if active → feature must be true
            a_pos = id_assumption
            set_kb.append([-a_pos, fid])
            assumptions.append(a_pos)
            feature_to_pos[name] = a_pos
            id_assumption += 1

            # a_neg: if active → feature must be false
            a_neg = id_assumption
            set_kb.append([-a_neg, -fid])
            assumptions.append(a_neg)
            feature_to_neg[name] = a_neg
            id_assumption += 1

        model._set_kb = set_kb
        model._assumptions = assumptions
        model._feature_to_pos_assumption = feature_to_pos
        model._feature_to_neg_assumption = feature_to_neg


class OneShotModel:
    """Minimal CheckerModel for one-shot SAT checks.

    Bakes all clauses + unit assumptions into set_kb.
    Satisfies CheckerModel Protocol for CheckerFactory.
    """
    use_incremental = False

    def __init__(self, clauses: List[List[int]], unit_assumptions: List[int] = None):
        self._set_kb = list(clauses)
        if unit_assumptions:
            self._set_kb.extend([lit] for lit in unit_assumptions)

    def get_kb(self) -> List[List[int]]:
        return self._set_kb

    def get_assumptions(self) -> List[int]:
        return []
