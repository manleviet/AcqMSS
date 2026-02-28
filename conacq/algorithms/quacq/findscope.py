"""
FindScope algorithm from IJCAI13 paper (Algorithm 2).

Finds scope of violated constraint using partial membership queries
checked via oracle.is_valid(). Prunes bias via SAT-based consistency
checking with ConsistencyChecker.

Complexity: O(|S| * log|X|) queries where S=scope size, X=total variables.
"""

import logging
from typing import List

from explanation.operations.algorithms.checker import ConsistencyChecker


class FindScope:
    """Finds scope of violated constraint via partial membership queries.

    Oracle, checker, and model injected at construction; per-call data passed to run().
    """

    def __init__(self, oracle, checker: ConsistencyChecker, model):
        self.oracle = oracle
        self.checker = checker
        self.model = model

    def run(
            self,
            e: dict,
            R: set,
            Y: set,
            ask_query: bool,
            remaining_bias: set,
            record_query,
            root_assumption: int,
    ) -> List[str]:
        """
        Find scope of violated constraint via partial membership queries.

        Args:
            e: Complete negative example (config dict)
            R: Already-determined scope variables (feature names)
            Y: Remaining variables to search
            ask_query: Whether to query oracle with e[R]
            remaining_bias: Mutable set of remaining bias assumption IDs
            record_query: Callback(config, answer, source) to record queries
            root_assumption: Root BG assumption ID for SAT checking

        Returns:
            Scope variables (feature names) as list
        """
        if ask_query:
            partial = {k: e[k] for k in R if k in e}
            is_consistent = self.oracle.is_valid(partial)
            record_query(partial, is_consistent, 'findscope')

            if is_consistent:
                self._prune_rejecting_partial(
                    remaining_bias, e, R, root_assumption)
            else:
                return []

        if len(Y) <= 1:
            return list(Y)

        # Binary split
        Y_list = sorted(Y)
        mid = len(Y_list) // 2
        Y1 = set(Y_list[:mid])
        Y2 = set(Y_list[mid:])

        S1 = self.run(e, R | Y1, Y2, True,
                      remaining_bias, record_query, root_assumption)
        S2 = self.run(e, R | set(S1), Y1, len(S1) > 0,
                      remaining_bias, record_query, root_assumption)

        return S1 + S2

    def _prune_rejecting_partial(
            self,
            remaining_bias: set,
            e: dict,
            R: set,
            root_assumption: int,
    ) -> None:
        """Prune bias constraints that reject partial assignment e[R].

        Uses SAT-based consistency checking: a constraint is pruned if
        KB + root + partial_assignment + constraint is UNSAT.
        """
        partial = {k: e[k] for k in R if k in e}
        if not partial:
            return

        config_assumptions = self.model.config_to_assumptions(partial)
        base = [root_assumption] + config_assumptions

        pruned = []
        for c_id in list(remaining_bias):
            if not self.checker.is_consistent(base + [c_id]):
                pruned.append(c_id)

        if pruned:
            remaining_bias -= set(pruned)
            logging.debug('FindScope pruned %d constraints from partial query', len(pruned))
