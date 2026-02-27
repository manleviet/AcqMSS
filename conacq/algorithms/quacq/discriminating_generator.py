"""
DiscriminatingGenerator: Paper Algorithm 3 line 5.

Generates discriminating examples from C_L[Y] (learned KB restricted to scope)
+ BG clauses, NOT from FM clauses (ground truth).
"""

from typing import Dict, List, Optional, Set

from pysat.solvers import Solver

from .task_preparation import QuAcqTask


class DiscriminatingGenerator:
    """Generate discriminating examples from learned KB restricted to scope.

    Paper Algorithm 3 line 5: choose e' in sol(C_L[Y]) s.t. e' |= c_i, e' |/= c_j.
    SAT formula: BG + C_L[Y] + c_i + neg(c_j).

    Args:
        task: QuAcqTask with constraint/negated clause maps and BG clauses
        solver_name: PySAT solver name
    """

    def __init__(self, task: QuAcqTask, solver_name: str = 'glucose4') -> None:
        self._task = task
        self._solver_name = solver_name

    def generate(self, c_i: int, c_j: int,
                 learned_kb: List[int], scope: Set[str]) -> Optional[Dict[str, bool]]:
        """Find e' s.t. e' in sol(BG + C_L[Y]) and e' |= c_i and e' |/= c_j.

        Args:
            c_i: Constraint ID that e' must satisfy
            c_j: Constraint ID that e' must violate
            learned_kb: Currently learned constraint IDs
            scope: Variable scope Y (feature names)

        Returns:
            Config dict if SAT, None if UNSAT
        """
        cl_y = self._get_learned_clauses_in_scope(learned_kb, scope)
        bg = list(self._task.background_clauses)
        clauses_i = self._task.constraint_clauses.get(c_i, [])
        neg_j = self._task.negated_clauses.get(c_j, [])

        solver = Solver(name=self._solver_name,
                        bootstrap_with=bg + cl_y + clauses_i + neg_j)
        try:
            if solver.solve():
                return self._task.model_to_config(solver.get_model())
        finally:
            solver.delete()
        return None

    def _get_learned_clauses_in_scope(self, learned_kb: List[int],
                                       scope: Set[str]) -> List[List[int]]:
        """C_L[Y]: learned constraint clauses restricted to scope Y."""
        clauses: List[List[int]] = []
        for c_id in learned_kb:
            c_vars = self._task._get_constraint_vars(c_id)
            if c_vars.issubset(scope):
                clauses.extend(self._task.constraint_clauses.get(c_id, []))
        return clauses
