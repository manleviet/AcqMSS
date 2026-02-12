"""
FindC algorithm from IJCAI13 paper (Algorithm 3).

Given a scope (from FindScope), finds the specific constraint
that is violated by the negative example.

Complexity: O(|Gamma|) queries where Gamma = candidate constraints with scope.
"""

import logging
from typing import Optional, List

from pysat.solvers import Solver

from .task import InteractiveTask
from .user_interface import ExampleProvider


def find_c(
        e: dict,
        scope: set,
        task: InteractiveTask,
        fm_clauses: List[List[int]],
        example_provider: Optional[ExampleProvider],
        solver_name: str = 'glucose4',
        query_mode: str = 'example_only'
) -> Optional[str]:
    """
    Find constraint with given scope violated by e.

    Uses discriminating examples (from pool or SAT) to narrow down
    which constraint in the scope is the one in the target.

    Args:
        e: Negative example
        scope: Variable scope from FindScope (set of feature names)
        task: InteractiveTask state
        fm_clauses: Target FM CNF clauses
        example_provider: ExampleProvider for discriminating examples
        solver_name: SAT solver name
        query_mode: 'example_only' or 'example_first'

    Returns:
        Constraint ID or None if no constraint found
    """
    # Get candidate constraints: bias constraints whose scope matches
    candidates = task.get_constraints_with_scope(scope)

    if not candidates:
        logging.debug('FindC: no candidates with scope %s', scope)
        return None

    if len(candidates) == 1:
        return candidates[0]

    # Filter to constraints that actually reject e
    rejecting = []
    e_assumptions = task.config_to_assumptions(e)
    assignment = {abs(lit): lit > 0 for lit in e_assumptions}

    for c_id in candidates:
        clauses = task.constraint_map.get(c_id, [])
        if _violates(clauses, assignment):
            rejecting.append(c_id)

    if not rejecting:
        logging.debug('FindC: no rejecting constraint found')
        return None

    if len(rejecting) == 1:
        return rejecting[0]

    # Use discriminating examples to narrow down
    # Try to find an example that satisfies some candidates but not others
    remaining = list(rejecting)

    if example_provider is not None and not example_provider.is_exhausted():
        result = _narrow_with_pool(remaining, task, fm_clauses, example_provider, solver_name)
        if result is not None:
            return result

    if query_mode == 'example_first':
        result = _narrow_with_sat(remaining, task, fm_clauses, solver_name)
        if result is not None:
            return result

    # If we can't discriminate further, return first remaining candidate
    logging.debug('FindC: returning first of %d candidates', len(remaining))
    return remaining[0]


def _narrow_with_pool(
        candidates: List[str],
        task: InteractiveTask,
        fm_clauses: List[List[int]],
        example_provider: ExampleProvider,
        solver_name: str
) -> Optional[str]:
    """Try to narrow candidates using examples from pool."""
    # Check remaining pool examples as discriminating queries
    while not example_provider.is_exhausted() and len(candidates) > 1:
        disc_e = example_provider.next_example()
        if disc_e is None:
            break

        disc_assumptions = task.config_to_assumptions(disc_e)
        disc_assignment = {abs(lit): lit > 0 for lit in disc_assumptions}

        # Check which candidates this example violates
        violating = [c for c in candidates
                     if _violates(task.constraint_map.get(c, []), disc_assignment)]
        non_violating = [c for c in candidates if c not in violating]

        # Check if disc_e is consistent with FM
        is_valid = _check_fm_consistency(fm_clauses, disc_assumptions, solver_name)
        task.record_query(disc_e, is_valid)

        if is_valid:
            # Valid example: constraints that reject it are NOT in target
            # Remove violating constraints from candidates
            if violating:
                for c_id in violating:
                    if c_id in task.bias:
                        task.remove_from_bias([c_id])
                candidates = [c for c in candidates if c not in violating]
        else:
            # Invalid example: at least one violating constraint IS in target
            if violating:
                candidates = violating

    if len(candidates) == 1:
        return candidates[0]
    return None


def _narrow_with_sat(
        candidates: List[str],
        task: InteractiveTask,
        fm_clauses: List[List[int]],
        solver_name: str
) -> Optional[str]:
    """Try to narrow candidates using SAT-generated discriminating examples."""
    # Generate a query that distinguishes between candidate constraints
    # Try: SAT(KB ∪ BG ∪ c_i ∪ ¬c_j) for pairs of candidates
    for i, c_i in enumerate(candidates):
        for c_j in candidates[i+1:]:
            clauses_i = task.constraint_map.get(c_i, [])
            neg_j = task.negated_constraint_map.get(c_j, [])

            # Try to find example satisfying c_i but violating c_j
            all_clauses = list(fm_clauses) + clauses_i + neg_j
            solver = Solver(name=solver_name, bootstrap_with=all_clauses)
            try:
                if solver.solve():
                    model = solver.get_model()
                    disc_e = task.model_to_config(model)
                    disc_assumptions = task.config_to_assumptions(disc_e)
                    disc_assignment = {abs(lit): lit > 0 for lit in disc_assumptions}

                    is_valid = _check_fm_consistency(fm_clauses, disc_assumptions, solver_name)
                    task.record_query(disc_e, is_valid)

                    if is_valid:
                        # c_j rejects a valid example → c_j not in target
                        candidates = [c for c in candidates if c != c_j]
                    else:
                        # Invalid example violating c_j → c_j may be in target
                        pass

                    if len(candidates) == 1:
                        return candidates[0]
            finally:
                solver.delete()

    if len(candidates) == 1:
        return candidates[0]
    return candidates[0] if candidates else None


def _violates(clauses: List[List[int]], assignment: dict) -> bool:
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


def _check_fm_consistency(fm_clauses: List[List[int]],
                          assumptions: List[int],
                          solver_name: str) -> bool:
    """Check if example is consistent with FM."""
    all_clauses = list(fm_clauses)
    for lit in assumptions:
        all_clauses.append([lit])

    solver = Solver(name=solver_name, bootstrap_with=all_clauses)
    try:
        return solver.solve()
    finally:
        solver.delete()
