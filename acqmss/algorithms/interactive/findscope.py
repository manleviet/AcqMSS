"""
FindScope algorithm from IJCAI13 paper (Algorithm 2).

Finds the scope (set of variables) of a violated constraint
using partial queries checked via ConsistencyChecker against FM.

Complexity: O(|S| * log|X|) queries where S=scope size, X=total variables.
"""

import logging
from typing import List, Set

from pysat.solvers import Solver

from .task import InteractiveTask


def find_scope(
        e: dict,
        R: set,
        Y: set,
        ask_query: bool,
        fm_clauses: List[List[int]],
        task: InteractiveTask,
        solver_name: str = 'glucose4'
) -> List[str]:
    """
    Find scope of violated constraint via partial queries.

    Uses SAT-based consistency checking against target FM for partial queries
    (same infrastructure as CONGEN — no oracle needed).

    Args:
        e: Complete negative example (config dict)
        R: Already-determined scope variables (feature names)
        Y: Remaining variables to search
        ask_query: Whether to check e[R] against FM
        fm_clauses: Target FM CNF clauses
        task: InteractiveTask state
        solver_name: SAT solver name

    Returns:
        Scope variables (feature names) as list
    """
    if ask_query:
        # Check partial assignment e[R] against FM
        partial_assumptions = task.partial_config_to_assumptions(e, R)
        is_consistent = _check_partial_consistency(
            fm_clauses, partial_assumptions, solver_name
        )

        if is_consistent:
            # e[R] is consistent with FM → R alone doesn't violate anything
            # Prune bias constraints that reject this partial assignment
            _prune_rejecting_partial(task, e, R)
        else:
            # e[R] is inconsistent → R already contains the scope
            return []

    if len(Y) <= 1:
        return list(Y)

    # Binary split
    Y_list = sorted(Y)
    mid = len(Y_list) // 2
    Y1 = set(Y_list[:mid])
    Y2 = set(Y_list[mid:])

    S1 = find_scope(e, R | Y1, Y2, True, fm_clauses, task, solver_name)
    S2 = find_scope(e, R | set(S1), Y1, len(S1) > 0, fm_clauses, task, solver_name)

    return S1 + S2


def _check_partial_consistency(
        fm_clauses: List[List[int]],
        partial_assumptions: List[int],
        solver_name: str
) -> bool:
    """Check if partial assignment is consistent with FM."""
    all_clauses = list(fm_clauses)
    for lit in partial_assumptions:
        all_clauses.append([lit])

    solver = Solver(name=solver_name, bootstrap_with=all_clauses)
    try:
        return solver.solve()
    finally:
        solver.delete()


def _prune_rejecting_partial(task: InteractiveTask, e: dict, R: set) -> None:
    """Prune bias constraints that reject partial assignment e[R]."""
    assumptions = task.partial_config_to_assumptions(e, R)
    if not assumptions:
        return

    assignment = {abs(lit): lit > 0 for lit in assumptions}

    pruned = []
    for c_id in list(task.bias):
        clauses = task.constraint_map.get(c_id, [])
        # Only check constraints whose variables are all in R
        c_vars = task._get_constraint_vars(c_id)
        if not c_vars.issubset(R):
            continue

        if task.violates_clauses(clauses, assignment):
            pruned.append(c_id)

    if pruned:
        task.remove_from_bias(pruned)
        logging.debug('FindScope pruned %d constraints from partial query', len(pruned))
