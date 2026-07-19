"""Assumption-id allocator: hand out ids, and emit paired (original, negated) ids
as a unit so the caller never re-derives which is which by stride (the magic ``2``).

The old code threaded a bare ``int`` through every preparation hop and, at read-back,
sliced ``assumptions[start:stop:2]`` to recover the originals — a stride that is only
correct when every entry in the range is a pair, plus a ``start`` offset the caller
had to snapshot before allocating. Two ID-mismatch bugs shipped from those two
implicit batons (the stride and the offset).

This allocator removes both. ``allocate_pair`` returns ``(original, negated)`` so the
emitting function has the original in hand and returns it directly — no stride, no
offset, no name to look it up by. The allocator carries only the running counter;
across a stage boundary the handoff is the plain int ``next_id`` (never this object —
``OracleData`` stays a frozen value, ADR-0009).
"""
from __future__ import annotations

from typing import Tuple


class AssumptionIdAllocator:
    """Hands out contiguous assumption ids; emits pairs as a unit."""

    def __init__(self, start: int = 1) -> None:
        self._next = start

    def allocate(self) -> int:
        """Emit one id (a single, un-negated assumption)."""
        i = self._next
        self._next += 1
        return i

    def allocate_pair(self) -> Tuple[int, int]:
        """Emit two contiguous ids ``(original, negated)`` — the emitting function
        gets the original directly, so there is nothing left to infer by stride."""
        orig = self._next
        neg = self._next + 1
        self._next += 2
        return orig, neg

    @property
    def next_id(self) -> int:
        """The next free id — the int handed to the next stage / to ``OracleData``."""
        return self._next
