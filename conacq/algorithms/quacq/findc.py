"""
FindC algorithm from IJCAI13 paper (Algorithm 3).

Given a scope (from FindScope), finds the specific constraint
that is violated by the negative example.

Uses oracle.is_valid() for membership queries and DiscriminatingGenerator
for SAT-based discriminating examples from C_L[Y] (learned KB).

Complexity: O(|Gamma|) queries where Gamma = candidate constraints with scope.
"""

import logging
from typing import Dict, List

from .sat_utils import (
    config_to_assumptions, get_constraints_with_scope, violates_clauses
)
class FindC:
    """Finds constraint with given scope violated by example.

    Oracle and generator injected at construction; per-call data passed to run().
    """

    def __init__(self, oracle, generator=None):
        self.oracle = oracle
        self.generator = generator

    def run(
            self,
            e: dict,
            scope: set,
            constraint_clauses: Dict[int, List[List[int]]],
            feature_ids: Dict[str, int],
            id_to_feature: Dict[int, str],
            remaining_bias: set,
            record_query,
            learned_kb: list,
    ):
        """
        Find constraint with given scope violated by e.

        Uses DiscriminatingGenerator to narrow down which constraint
        in the scope is the one in the target (paper Algorithm 3).

        Args:
            e: Negative example
            scope: Variable scope from FindScope (set of feature names)
            constraint_clauses: assumption_id -> raw CNF clauses
            feature_ids: Feature name -> SAT variable ID
            id_to_feature: SAT variable ID -> feature name
            remaining_bias: Mutable set of remaining bias assumption IDs
            record_query: Callback(config, answer, source) to record queries
            learned_kb: Currently learned constraint IDs (for DiscriminatingGenerator)

        Returns:
            Constraint ID (int) or None
        """
        # Get candidate constraints: bias constraints whose scope matches
        candidates = get_constraints_with_scope(
            scope, remaining_bias, constraint_clauses, id_to_feature)

        if not candidates:
            logging.debug('FindC: no candidates with scope %s', scope)
            return None

        if len(candidates) == 1:
            return candidates[0]

        # Filter to constraints that actually reject e
        rejecting = []
        e_assumptions = config_to_assumptions(e, feature_ids)
        assignment = {abs(lit): lit > 0 for lit in e_assumptions}

        for c_id in candidates:
            clauses = constraint_clauses.get(c_id, [])
            if violates_clauses(clauses, assignment):
                rejecting.append(c_id)

        if not rejecting:
            logging.debug('FindC: no rejecting constraint found')
            return None

        if len(rejecting) == 1:
            return rejecting[0]

        # Use DiscriminatingGenerator to narrow down
        remaining = list(rejecting)

        if self.generator is not None:
            result = self._narrow_with_generator(
                remaining, remaining_bias, record_query,
                learned_kb, scope)
            if result is not None:
                return result

        # If we can't discriminate further, return first remaining candidate
        logging.debug('FindC: returning first of %d candidates', len(remaining))
        return remaining[0]

    def _narrow_with_generator(
            self,
            candidates: list,
            remaining_bias: set,
            record_query,
            learned_kb: list,
            scope: set
    ):
        """Try to narrow candidates using DiscriminatingGenerator (C_L[Y])."""
        i = 0
        while i < len(candidates) and len(candidates) > 1:
            c_i = candidates[i]
            j = i + 1
            while j < len(candidates):
                c_j = candidates[j]
                disc_e = self.generator.generate(c_i, c_j, learned_kb, scope)
                if disc_e is None:
                    j += 1
                    continue

                is_valid = self.oracle.is_valid(disc_e)
                record_query(disc_e, is_valid, 'findc')

                if is_valid:
                    # c_j rejects a valid example -> c_j not in target
                    candidates.remove(c_j)
                    remaining_bias.discard(c_j)
                    # don't increment j — next element shifted into position
                else:
                    j += 1

                if len(candidates) == 1:
                    return candidates[0]
            i += 1

        return candidates[0] if candidates else None
