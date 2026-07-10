"""KB Protocol: the read-only name↔id catalog every knowledge base exposes.

Structural contract shared by ``DiagnosisModel`` (explanation) and the conacq
``KBModel`` subclasses. name↔id lives in ONE place — the KB — and is exposed
read-only; the ``encoding`` free functions consume these maps as parameters
rather than duplicating them.
"""
from typing import Dict, List, Mapping, Protocol, runtime_checkable


@runtime_checkable
class KBProtocol(Protocol):
    """A knowledge base's read-only catalog of names, ids, and constraints."""

    @property
    def id_to_name(self) -> Mapping[int, str]:
        """SAT variable id → feature name (read-only view)."""
        ...

    @property
    def name_to_id(self) -> Mapping[str, int]:
        """Feature name → SAT variable id (read-only view)."""
        ...

    constraint_map: Dict[str, List[List[int]]]
    negated_constraint_map: Dict[str, List[List[int]]]
    next_available_id: int
