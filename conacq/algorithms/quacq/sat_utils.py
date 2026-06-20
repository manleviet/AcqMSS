"""
Standalone SAT utility functions for QuAcq algorithm.

Pure functions extracted from QuAcqTask — shared by FindScope, FindC,
DiscriminatingGenerator, and QuAcq.learn().
"""

from explanation.operations.algorithms.profiler import count_calls, get_global_profiler


@count_calls('prune_calls')
def prune_rejecting(
        checker,
        codec,
        remaining_bias: set,
        assignment: dict,
        root_assumption: int,
        profiler=None
) -> list:
    """Remove constraints from remaining_bias that reject the given assignment.

    A constraint is pruned if KB + root + assignment_assumptions + constraint is UNSAT.

    Args:
        checker: ConsistencyChecker instance
        codec: VariableCodec for config_to_assumptions encoding
        remaining_bias: Mutable set of remaining bias assumption IDs (mutated in-place)
        assignment: Feature config dict {feature_name: bool}
        root_assumption: Root BG assumption ID
        profiler: Optional profiler instance

    Returns:
        List of pruned constraint assumption IDs.
    """
    if profiler is None:
        profiler = get_global_profiler()
    config_assumptions = codec.config_to_assumptions(assignment)
    base = [root_assumption] + config_assumptions
    pruned = []
    for c_id in list(remaining_bias):
        profiler.increment('prune_is_consistent_calls')
        if not checker.is_consistent(base + [c_id]):
            pruned.append(c_id)
    remaining_bias -= set(pruned)
    return pruned
