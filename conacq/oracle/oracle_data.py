"""Frozen provisioning snapshot derived from the oracle model at build time.

An oracle does two unrelated jobs (ADR-0009): it *answers* questions about the
target (``is_valid``/``complete_configuration``), and it *provisions* the
algorithm's SAT inputs (``kb``/``assumptions``/``c``/``bg_data``/``root_clauses``).
The second job has no business living on a live actor whose state a query can
shift — that entanglement was the A6 bug.

``OracleData`` is job ② extracted into an immutable value: built once, eagerly, and
handed to the consumers (``GenerateNE``, the model builders, both task-preparation
strategies). Being frozen, nothing a membership query does can reach it, so "a
query corrupts the background" is not expressible. It satisfies ``BGProvider`` +
``KBProvider`` so the consumers depend on the same narrow contracts as before —
they simply receive a snapshot instead of the live oracle.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from conacq.oracle.bg_data import BGData
    from explanation.api import AssignmentAssumptionMap


@dataclass(frozen=True)
class OracleData:
    """Immutable snapshot of the oracle's provisioning surface (job ②).

    Fields:
        kb: Full knowledge base with assumption guards (oracle task's set_kb).
        assumptions: All assumption literals (oracle task's assumptions).
        c: FM constraint assumptions (oracle task's set_c) — the background the
           acquisition algorithm treats as always-true facts.
        bg_data: Root BG constraint pair + Part-4 assignment data for ConGen/QuAcq.
        root_clauses: Raw root-constraint CNF clauses (without assumption guards).
        assignment_map: Feature-assignment → assumption-id map (for query encoding).
        next_available_id: First free assumption id after the oracle's Parts 1-4.
    """

    kb: List[List[int]]
    assumptions: List[int]
    c: List[int]
    bg_data: "BGData"
    root_clauses: List[List[int]]
    assignment_map: "AssignmentAssumptionMap"
    next_available_id: int

    # --- KBProvider surface ---
    def get_kb(self) -> List[List[int]]:
        """Get the full knowledge base with assumptions."""
        return self.kb

    def get_assumptions(self) -> List[int]:
        """Get the list of assumption literals."""
        return self.assumptions

    def get_c(self) -> List[int]:
        """Get the FM constraint assumptions (background knowledge)."""
        return self.c

    # --- BGProvider surface ---
    def get_bg_data(self) -> "BGData":
        """Return root BG assumption data for ConGen/QuAcq."""
        return self.bg_data

    def get_root_clauses(self) -> List[List[int]]:
        """Get raw background-knowledge clauses (root constraint)."""
        return self.root_clauses
