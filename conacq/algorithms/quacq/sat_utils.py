"""
Standalone SAT utility functions for QuAcq algorithm.

Pure functions extracted from QuAcqTask — shared by FindScope, FindC,
DiscriminatingGenerator, and QuAcq.learn().
"""

from typing import Dict, List, Set


def config_to_assumptions(config: Dict[str, bool],
                          feature_ids: Dict[str, int]) -> List[int]:
    """Convert configuration dict to SAT assumption literals."""
    assumptions = []
    for name, value in config.items():
        if name in feature_ids:
            fid = feature_ids[name]
            assumptions.append(fid if value else -fid)
    return assumptions


def partial_config_to_assumptions(config: Dict[str, bool],
                                   variables: set,
                                   feature_ids: Dict[str, int]) -> List[int]:
    """Convert partial config (only variables in scope) to assumptions."""
    assumptions = []
    for name in variables:
        if name in config and name in feature_ids:
            fid = feature_ids[name]
            assumptions.append(fid if config[name] else -fid)
    return assumptions


def get_constraint_vars(assumption_id: int,
                        constraint_clauses: Dict[int, List[List[int]]],
                        id_to_feature: Dict[int, str]) -> Set[str]:
    """Get the set of feature-name variables for a constraint."""
    clauses = constraint_clauses.get(assumption_id, [])
    c_vars: Set[str] = set()
    for clause in clauses:
        for lit in clause:
            var = abs(lit)
            if var in id_to_feature:
                c_vars.add(id_to_feature[var])
    return c_vars


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


def get_constraints_with_scope(scope: set,
                                remaining_bias: set,
                                constraint_clauses: Dict[int, List[List[int]]],
                                id_to_feature: Dict[int, str]) -> List[int]:
    """Get bias constraint IDs whose variables match scope.

    Prefers exact scope match (c_vars == scope). Falls back to subset
    match (c_vars ⊆ scope) if no exact matches found.
    """
    exact = []
    subset = []
    for aid in remaining_bias:
        c_vars = get_constraint_vars(aid, constraint_clauses, id_to_feature)
        if not c_vars:
            continue
        if c_vars == scope:
            exact.append(aid)
        elif c_vars.issubset(scope):
            subset.append(aid)
    return exact if exact else subset


def get_kb_clauses(learned_kb: List[int],
                   constraint_clauses: Dict[int, List[List[int]]]) -> List[List[int]]:
    """Get raw CNF clauses for given learned KB assumption IDs."""
    clauses = []
    for aid in learned_kb:
        clauses.extend(constraint_clauses.get(aid, []))
    return clauses
