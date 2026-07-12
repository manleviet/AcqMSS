"""KBModel: generic base holding the shared KB fields + the name↔id catalog.

Domain-neutral: the base owns the fields every conacq KB shares (constraint maps,
next assumption id, and the two name↔id direction dicts). Subclasses call
``super().__init__()`` then set only model-specific values; builders populate the
fields at build time. No feature-model terms in the base.

The name↔id catalog is exposed as plain ``dict`` attributes — no runtime
read-only view (see ADR-0007). ``KBProtocol`` types it as ``Mapping``, so the
read-only guarantee stays at the type level, where it costs nothing.
"""
from typing import Dict, List


class KBModel:
    """Base holding shared KB fields and the name↔id catalog."""

    def __init__(self) -> None:
        # Constraint name -> raw CNF clauses
        self.constraint_map: Dict[str, List[List[int]]] = {}
        # Constraint NOT(name) -> negated CNF clauses (for redundancy detection)
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        # Starting id for assumption literals; 0 until the builder computes the
        # real value from the FM/oracle at build time.
        self.next_available_id: int = 0
        # name↔id catalog (plain dicts; populated at build).
        self.name_to_id: Dict[str, int] = {}
        self.id_to_name: Dict[int, str] = {}
