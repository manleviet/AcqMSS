"""Background knowledge data extracted from Oracle for ConGen consumption.

BGData captures the root BG constraint pair (first entry in Part 3 of the
shared assumption ID layout) plus the next available ID after Oracle's
Parts 3+4, allowing ConGen to start its own ID allocation cleanly.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class BGData:
    """Root BG constraint data extracted post-preparation from Oracle.

    Fields:
        set_kb: Assumption-guarded clauses for root constraint + negated form
        assumptions: (root_assumption_id, negated_root_assumption_id)
        negation_map: {root_id: negated_root_id}
        descriptions: {root_id: "desc", neg_id: "NOT(desc)"}
        next_available_id: First free ID after Oracle Parts 3+4
    """
    set_kb: List[List[int]]
    assumptions: Tuple[int, int]
    negation_map: Dict[int, int]
    descriptions: Dict[int, str]
    next_available_id: int
