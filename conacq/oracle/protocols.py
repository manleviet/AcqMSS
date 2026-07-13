"""Narrow, role-based oracle protocols — the contracts consumers depend on.

The concrete ``FMOracle`` exposes 14 public methods, but no consumer
needs all of them. These ``@runtime_checkable`` protocols carve that surface into
the roles consumers actually use (measured, not guessed), so a consumer depends
on a 1-3 method contract rather than the concrete class — which makes alternative
oracles (``UserPromptOracle``, ``CachedOracle``) substitutable.

Critically, the KB-reading surface (``get_kb``/``get_assumptions``/``get_c``) is
named as its own role, ``KBProvider``. That is exactly the surface through which
the last-query pollution of ``get_c`` leaks, and its sole consumer is
``GenerateNE``. Giving it a name makes that blast radius visible in the type
system instead of hiding it inside a 14-method class.

The ``Oracle`` ABC stays as the implementation base (it supplies the ``ask``
default); consumers type against these protocols, not the ABC or the concrete
class. A couple of consumers span several roles — they type against the composite
protocols (``GeneratorOracle``, ``PreparationOracle``), which are unions of the
atomic roles, not new roles.
"""
from __future__ import annotations

from typing import (
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    TYPE_CHECKING,
    runtime_checkable,
)

if TYPE_CHECKING:
    from conacq.oracle.bg_data import BGData


@runtime_checkable
class MembershipOracle(Protocol):
    """Answer membership queries: is this configuration valid?"""

    def is_valid(self, assignments: Dict[str, bool]) -> bool: ...


@runtime_checkable
class CompletableOracle(Protocol):
    """Complete a partial configuration to a full valid one."""

    def complete_configuration(
        self, partial: Dict[str, bool]
    ) -> Optional[Dict[str, bool]]: ...


@runtime_checkable
class CatalogProvider(Protocol):
    """Expose the variable-name <-> SAT-variable-id catalog."""

    def get_variables(self) -> Set[str]: ...

    def get_variable_ids(self) -> Dict[str, int]: ...


@runtime_checkable
class BGProvider(Protocol):
    """Provide the root background-knowledge surface for task preparation."""

    def get_bg_data(self) -> "BGData": ...

    def get_root_clauses(self) -> List[List[int]]: ...


@runtime_checkable
class KBProvider(Protocol):
    """Read the knowledge base + assumption surface.

    This is the surface the last-query pollution leaks through (``get_c``), and
    its only consumer is ``GenerateNE``. Kept as its own role so that blast
    radius is visible in the type system, not buried in a 14-method class.
    """

    def get_kb(self) -> List[List[int]]: ...

    def get_assumptions(self) -> List[int]: ...

    def get_c(self) -> List[int]: ...


@runtime_checkable
class GeneratorOracle(MembershipOracle, CompletableOracle, CatalogProvider, Protocol):
    """Composite: what example generators need — classify + complete + catalog."""


@runtime_checkable
class PreparationOracle(BGProvider, KBProvider, Protocol):
    """Composite: what the ConGen preparation chain needs — background + KB."""
