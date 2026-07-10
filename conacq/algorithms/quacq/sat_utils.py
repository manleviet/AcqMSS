"""
Standalone SAT utility functions for QuAcq algorithm.

Pure functions extracted from QuAcqTask — shared by FindScope, FindC,
DiscriminatingGenerator, and QuAcq.learn().
"""

from profiling import count_calls, get_global_profiler


@count_calls('prune_calls')
def prune_rejecting(
        checker,
        model,
        remaining_bias: set,
        assignment: dict,
        root_assumption: int,
        profiler=None
) -> list:
    """Remove constraints from remaining_bias that reject the given assignment.

    A constraint is pruned if KB + root + assignment_assumptions + constraint is UNSAT.

    Returns list of pruned constraint assumption IDs.
    Mutates remaining_bias in-place.
    """
    if profiler is None:
        profiler = get_global_profiler()
    config_assumptions = model.config_to_assumptions(assignment)
    base = [root_assumption] + config_assumptions
    pruned = []
    for c_id in list(remaining_bias):
        profiler.increment('prune_is_consistent_calls')
        if not checker.is_consistent(base + [c_id]):
            pruned.append(c_id)
    remaining_bias -= set(pruned)
    return pruned
