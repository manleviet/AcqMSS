"""
FindC algorithm from IJCAI13 paper (Algorithm 3).

Given a scope (from FindScope), finds the specific constraint
that is violated by the negative example.

Uses oracle.is_valid() for membership queries and DiscriminatingGenerator
for SAT-based discriminating examples from C_L[Y] (learned KB).

Complexity: O(|Gamma|) queries where Gamma = candidate constraints with scope.
"""

import logging
from typing import Optional, Dict, List

from .sat_utils import (
    config_to_assumptions, get_constraints_with_scope, violates_clauses
)
from conacq.example_generators import ExampleProvider
from explanation.operations.algorithms.profiler import AbstractProfiler


def find_c(
        e: dict,
        scope: set,
        constraint_clauses: Dict[int, List[List[int]]],
        feature_ids: Dict[str, int],
        id_to_feature: Dict[int, str],
        remaining_bias: set,
        record_query,
        oracle,
        learned_kb: list,
        generator,
        example_provider: Optional[ExampleProvider] = None,
        query_mode: str = 'example_only',
        profiler: AbstractProfiler = None
):
    """
    Find constraint with given scope violated by e.

    Uses discriminating examples (from pool or DiscriminatingGenerator)
    to narrow down which constraint in the scope is the one in the target.

    Args:
        e: Negative example
        scope: Variable scope from FindScope (set of feature names)
        constraint_clauses: assumption_id -> raw CNF clauses
        feature_ids: Feature name -> SAT variable ID
        id_to_feature: SAT variable ID -> feature name
        remaining_bias: Mutable set of remaining bias assumption IDs
        record_query: Callback(config, answer, source) to record queries
        oracle: Oracle with is_valid(Dict[str, bool]) -> bool
        learned_kb: Currently learned constraint IDs (for DiscriminatingGenerator)
        generator: DiscriminatingGenerator instance
        example_provider: ExampleProvider for pool-based discriminating examples
        query_mode: 'example_only' or 'example_first'
        profiler: Optional profiler

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

    # Use discriminating examples to narrow down
    remaining = list(rejecting)

    # Pool-first hybrid (validated: keep pool narrowing with oracle.is_valid)
    if example_provider is not None and not example_provider.is_exhausted():
        result = _narrow_with_pool(
            remaining, constraint_clauses, feature_ids,
            remaining_bias, record_query, oracle, example_provider)
        if result is not None:
            return result

    if query_mode == 'example_first':
        result = _narrow_with_generator(
            remaining, remaining_bias, record_query, oracle,
            learned_kb, generator, scope)
        if result is not None:
            return result

    # If we can't discriminate further, return first remaining candidate
    logging.debug('FindC: returning first of %d candidates', len(remaining))
    return remaining[0]


def _narrow_with_pool(
        candidates: list,
        constraint_clauses: Dict[int, List[List[int]]],
        feature_ids: Dict[str, int],
        remaining_bias: set,
        record_query,
        oracle,
        example_provider: ExampleProvider
):
    """Try to narrow candidates using examples from pool + oracle.is_valid()."""
    while not example_provider.is_exhausted() and len(candidates) > 1:
        disc_e = example_provider.next_example()
        if disc_e is None:
            break

        disc_assumptions = config_to_assumptions(disc_e, feature_ids)
        disc_assignment = {abs(lit): lit > 0 for lit in disc_assumptions}

        # Check which candidates this example violates
        violating = [c for c in candidates
                     if violates_clauses(constraint_clauses.get(c, []), disc_assignment)]

        # Check validity via oracle (not SAT)
        is_valid = oracle.is_valid(disc_e)
        record_query(disc_e, is_valid, 'findc')

        if is_valid:
            # Valid example: constraints that reject it are NOT in target
            if violating:
                for c_id in violating:
                    remaining_bias.discard(c_id)
                candidates = [c for c in candidates if c not in violating]
        else:
            # Invalid example: at least one violating constraint IS in target
            if violating:
                candidates = violating

    if len(candidates) == 1:
        return candidates[0]
    return None


def _narrow_with_generator(
        candidates: list,
        remaining_bias: set,
        record_query,
        oracle,
        learned_kb: list,
        generator,
        scope: set
):
    """Try to narrow candidates using DiscriminatingGenerator (C_L[Y])."""
    i = 0
    while i < len(candidates) and len(candidates) > 1:
        c_i = candidates[i]
        j = i + 1
        while j < len(candidates):
            c_j = candidates[j]
            disc_e = generator.generate(c_i, c_j, learned_kb, scope)
            if disc_e is None:
                j += 1
                continue

            is_valid = oracle.is_valid(disc_e)
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
