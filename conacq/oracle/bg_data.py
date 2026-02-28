"""Background knowledge data extracted from Oracle for ConGen consumption.

BGData captures the root BG constraint pair (first entry in Part 3 of the
shared assumption ID layout) plus the next available ID after Oracle's
Parts 3+4, allowing ConGen to start its own ID allocation cleanly.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class BGData:
    """Root BG constraint data extracted post-preparation from Oracle.

    Fields (Part 3 -- root constraint):
        set_kb: Assumption-guarded clauses for root constraint + negated form
        assumptions: (root_assumption_id, negated_root_assumption_id)
        negation_map: {root_id: negated_root_id}
        descriptions: {root_id: "desc", neg_id: "NOT(desc)"}
        next_available_id: First free ID after Oracle Parts 3+4

    Fields (Part 4 -- feature assignments):
        assignment_clauses: Assumption-guarded unit clauses ([-a_pos, fid], [-a_neg, -fid])
        assignment_assumptions: All Part 4 assumption IDs
        pos_assignment_to_assumption: {feature_name: pos_assumption_id}
        neg_assignment_to_assumption: {feature_name: neg_assumption_id}
    """
    set_kb: List[List[int]]
    assumptions: Tuple[int, int]
    negation_map: Dict[int, int]
    descriptions: Dict[int, str]
    next_available_id: int

    # Part 4: Feature assignment assumptions (for QuAcq pruning)
    assignment_clauses: List[List[int]] = field(default_factory=list)
    assignment_assumptions: List[int] = field(default_factory=list)
    pos_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
    neg_assignment_to_assumption: Dict[str, int] = field(default_factory=dict)
