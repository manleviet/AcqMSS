"""
FindScope algorithm from IJCAI13 paper (Algorithm 2).

Finds scope of violated constraint using partial membership queries
checked via oracle.is_valid().

Complexity: O(|S| * log|X|) queries where S=scope size, X=total variables.
"""

import logging
from typing import List

from ._task_compat import get_clause_map
from explanation.operations.algorithms.profiler import AbstractProfiler


def find_scope(
        e: dict,
        R: set,
        Y: set,
        ask_query: bool,
        oracle,
        task,
        remaining_bias: set,
        record_query,
        profiler: AbstractProfiler = None
) -> List[str]:
    """
    Find scope of violated constraint via partial membership queries.

    Args:
        e: Complete negative example (config dict)
        R: Already-determined scope variables (feature names)
        Y: Remaining variables to search
        ask_query: Whether to query oracle with e[R]
        oracle: Oracle with is_valid(Dict[str, bool]) -> bool
        task: QuAcqTask state (immutable)
        remaining_bias: Mutable set of remaining bias assumption IDs
        record_query: Callback(config, answer, source) to record queries
        profiler: Optional profiler

    Returns:
        Scope variables (feature names) as list
    """
    if ask_query:
        partial = {k: e[k] for k in R if k in e}
        is_consistent = oracle.is_valid(partial)
        record_query(partial, is_consistent, 'findscope')

        if is_consistent:
            _prune_rejecting_partial(task, remaining_bias, e, R)
        else:
            return []

    if len(Y) <= 1:
        return list(Y)

    # Binary split
    Y_list = sorted(Y)
    mid = len(Y_list) // 2
    Y1 = set(Y_list[:mid])
    Y2 = set(Y_list[mid:])

    S1 = find_scope(e, R | Y1, Y2, True, oracle, task, remaining_bias, record_query, profiler)
    S2 = find_scope(e, R | set(S1), Y1, len(S1) > 0, oracle, task, remaining_bias, record_query, profiler)

    return S1 + S2


def _prune_rejecting_partial(task, remaining_bias: set, e: dict, R: set) -> None:
    """Prune bias constraints that reject partial assignment e[R].

    Mutates remaining_bias in place.
    """
    assumptions = task.partial_config_to_assumptions(e, R)
    if not assumptions:
        return

    assignment = {abs(lit): lit > 0 for lit in assumptions}
    clause_map = get_clause_map(task)

    pruned = []
    for c_id in list(remaining_bias):
        clauses = clause_map.get(c_id, [])
        c_vars = task._get_constraint_vars(c_id)
        if not c_vars.issubset(R):
            continue

        if task.violates_clauses(clauses, assignment):
            pruned.append(c_id)

    if pruned:
        remaining_bias -= set(pruned)
        logging.debug('FindScope pruned %d constraints from partial query', len(pruned))
