"""
Standalone SAT utility functions for QuAcq algorithm.

Pure functions extracted from QuAcqTask — shared by FindScope, FindC,
DiscriminatingGenerator, and QuAcq.learn().
"""

from explanation.api import config_to_assignment_assumptions
from profiling import count_calls, get_global_profiler


@count_calls('prune_calls')
def prune_rejecting(
        checker,
        assignment_map,
        remaining_bias: dict,
        assignment: dict,
        root_assumption: int,
        profiler=None
) -> list:
    """Remove constraints from remaining_bias that reject the given assignment.

    A constraint is pruned if KB + root + assignment_assumptions + constraint is UNSAT.

    Stateless: the assignment→assumption map is passed in (from the prepared task),
    not read from a live model.

    Returns list of pruned constraint assumption IDs.
    Mutates remaining_bias in-place.
    """
    if profiler is None:
        profiler = get_global_profiler()
    config_assumptions = config_to_assignment_assumptions(assignment, assignment_map)
    base = [root_assumption] + config_assumptions
    pruned = []
    for c_id in list(remaining_bias):
        profiler.increment('prune_is_consistent_calls')
        if not checker.is_consistent(base + [c_id]):
            pruned.append(c_id)
    for c_id in pruned:
        remaining_bias.pop(c_id, None)
    return pruned
