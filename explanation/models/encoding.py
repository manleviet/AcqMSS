"""Free-function encoders between feature configs, SAT literals, and assumptions.

Single source of truth for the config↔literal and clause→name translations that
were previously duplicated across QuAcqModel, FMOracleModel, FMOracle
and Example. Pure functions: the name↔id catalog and the assignment-assumption
layer are passed in (owned by the KB / AssignmentAssumptionMap), never held here.
"""
from typing import Dict, List, Set

from explanation.models.assignment_assumption_map import AssignmentAssumptionMap


def _config_items(config):
    """Iterate (name, value) whether config is a plain dict or a Configuration."""
    return config.elements.items() if hasattr(config, 'elements') else config.items()


def config_to_variable_literals(config, name_to_id: Dict[str, int]) -> List[int]:
    """Encode a configuration as signed SAT variable literals.

    Positive value → +var, negative → -var. Features absent from ``name_to_id``
    are skipped. Sorted by feature name for deterministic ordering.
    """
    return [name_to_id[name] if value else -name_to_id[name]
            for name, value in sorted(_config_items(config))
            if name in name_to_id]


def variable_literals_to_config(lits: List[int], id_to_name: Dict[int, str]) -> Dict[str, bool]:
    """Decode SAT model literals to a feature configuration dict.

    Literals whose variable is not a feature (Tseitin/assumption vars) are skipped.
    """
    config: Dict[str, bool] = {}
    for lit in lits:
        var = abs(lit)
        if var in id_to_name:
            config[id_to_name[var]] = lit > 0
    return config


def config_to_assignment_assumptions(config, assignment_map: AssignmentAssumptionMap) -> List[int]:
    """Encode a configuration as assignment-assumption literals.

    Features absent from the assignment-assumption layer are skipped.
    """
    pos = assignment_map.pos_assignment_to_assumption
    neg = assignment_map.neg_assignment_to_assumption
    return [pos[name] if value else neg[name]
            for name, value in _config_items(config)
            if name in pos]


def get_constraint_vars(clauses: List[List[int]], id_to_name: Dict[int, str]) -> Set[str]:
    """Feature names referenced by the given constraint clauses."""
    return {id_to_name[abs(lit)]
            for clause in clauses for lit in clause
            if abs(lit) in id_to_name}
