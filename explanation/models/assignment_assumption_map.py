"""AssignmentAssumptionMap: the feature-assignment → assumption-ID layer.

Immutable holder owning the ``pos``/``neg`` assignment-assumption maps produced
during preparation (QuAcq Part 4 / FMOracle membership guards). Kept separate
from the name↔id catalog (which lives on the KB): this map is prep-derived
per-task state, whereas name↔id is a property of the KB.
"""
from dataclasses import dataclass, field

from explanation.models.frozen_dict import FrozenDict


@dataclass(frozen=True)
class AssignmentAssumptionMap:
    """Feature name → assumption ID, for asserting a feature selected/deselected.

    - ``pos_assignment_to_assumption[name]``: assumption asserting name = True
    - ``neg_assignment_to_assumption[name]``: assumption asserting name = False

    Deeply frozen: ``__post_init__`` coerces both maps to ``FrozenDict`` so the
    ``frozen=True`` label is honest (the maps are read-only after construction).
    """
    pos_assignment_to_assumption: "FrozenDict[str, int]" = field(default_factory=dict)
    neg_assignment_to_assumption: "FrozenDict[str, int]" = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, 'pos_assignment_to_assumption', FrozenDict(self.pos_assignment_to_assumption))
        object.__setattr__(self, 'neg_assignment_to_assumption', FrozenDict(self.neg_assignment_to_assumption))
