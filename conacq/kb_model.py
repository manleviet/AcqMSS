"""KBModel: generic base holding the shared KB fields + read-only name↔id catalog.

Domain-neutral: the base owns the fields every conacq KB shares (constraint maps,
next assumption id, and the two name↔id direction dicts under generic names) and
centralizes read-only exposure via ``MappingProxyType`` under the KB Protocol
names (``name_to_id`` / ``id_to_name``). Subclasses call ``super().__init__()``
then set only model-specific values; builders populate the fields at build time.
No feature-model terms in the base.
"""
from types import MappingProxyType
from typing import Dict, List, Mapping


class KBModel:
    """Base holding shared KB fields and surfacing name↔id read-only."""

    def __init__(self) -> None:
        # Constraint name -> raw CNF clauses
        self.constraint_map: Dict[str, List[List[int]]] = {}
        # Constraint NOT(name) -> negated CNF clauses (for redundancy detection)
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        # Starting id for assumption literals; 0 until the builder computes the
        # real value from the FM/oracle at build time.
        self.next_available_id: int = 0
        # name↔id catalog (populated at build); exposed read-only via properties
        self._name_to_id: Dict[str, int] = {}
        self._id_to_name: Dict[int, str] = {}

    @property
    def name_to_id(self) -> Mapping[str, int]:
        """Name → id (read-only view)."""
        return MappingProxyType(self._name_to_id)

    @property
    def id_to_name(self) -> Mapping[int, str]:
        """Id → name (read-only view)."""
        return MappingProxyType(self._id_to_name)
