"""
Adapter functions for working with QuAcqTask (int assumption IDs).

Used by QueryGenerator and FindScope/FindC helpers.
"""

from typing import List


def get_bg_clauses(task) -> List[List[int]]:
    """Get background clauses from QuAcqTask.

    Args:
        task: QuAcqTask instance

    Returns:
        List of background CNF clauses
    """
    return list(task.background_clauses)


def get_clause_map(task) -> dict:
    """Get constraint clause map from QuAcqTask.

    Args:
        task: QuAcqTask instance

    Returns:
        Dict[int, List[List[int]]] mapping assumption ID to raw CNF clauses
    """
    return task.constraint_clauses


def get_negated_clauses(task, c_id) -> List[List[int]]:
    """Get negated clauses for a constraint from QuAcqTask.

    Args:
        task: QuAcqTask instance
        c_id: Constraint assumption ID (int)

    Returns:
        List of negated CNF clauses, or empty list if not found
    """
    return task.negated_clauses.get(c_id, [])
