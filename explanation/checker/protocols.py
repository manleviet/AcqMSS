"""Consistency-checker port — the narrow contract diagnosis algorithms depend on.

This is a *port*: the abstract interface an algorithm needs from "something that
can answer consistency questions", with no knowledge of how the answer is
computed. The concrete adapters that actually talk to a SAT solver (PySAT,
SAT4J) live in ``backend.py`` and satisfy these Protocols structurally; this
module imports neither ``pysat`` nor ``subprocess`` and must stay that way.

- ``ConsistencyChecker`` — ``is_consistent`` / ``get_model`` / ``cleanup``. What
  the diagnosis path (PySATConflict / PySATDiagnosis and their labelers) needs.
- ``TestCaseChecker`` — a ``ConsistencyChecker`` that also offers
  ``is_consistent_test_cases``, needed by the test-case algorithms (KBDiag,
  QuickXPlainWithTestCases).
- ``CopyableChecker`` — a ``ConsistencyChecker`` that can ``copy()`` itself for
  parallel execution (FastDiagP).

Build a checker with ``build_checker(task, backend=…)`` (``backend.py``) — the
single construction door.
"""
from typing import List, Optional, Protocol, Sequence, runtime_checkable


@runtime_checkable
class ConsistencyChecker(Protocol):
    """The narrow consistency-checking contract algorithms depend on."""

    def is_consistent(self, set_c: Sequence[int]) -> bool:
        """Return whether the KB is satisfiable under the given active set.

        Answers SAT/UNSAT only — the one-way guard encoding (``¬a ∨ literal``) makes
        this invariant to the disabled assumptions, so they are dropped for speed.
        """
        ...

    def find_model(self, set_c: Sequence[int]) -> Optional[List[int]]:
        """Return a fully-pinned SAT model, or None if UNSAT.

        Unlike ``is_consistent`` this keeps the disabled (negated) assumptions: the
        one-way encoding leaves a guard free otherwise, and a solver may set it true
        and force its literal — so the model needs them pinned (ADR-0013).
        """
        ...

    def cleanup(self) -> None:
        """Release any solver resources held by this checker."""
        ...


@runtime_checkable
class TestCaseChecker(ConsistencyChecker, Protocol):
    """A ``ConsistencyChecker`` that can also test the KB against many test cases."""

    def is_consistent_test_cases(self, set_c: Sequence[int], set_tc: Sequence[int],
                                 stop_at_first_violation: bool) -> List:
        """Return the test cases inconsistent with the KB under ``set_c``."""
        ...


@runtime_checkable
class CopyableChecker(ConsistencyChecker, Protocol):
    """A ``ConsistencyChecker`` that can clone itself for parallel execution.

    The narrow ``ConsistencyChecker`` port does NOT promise ``copy()`` — a
    checker that only checks consistency is a valid ``ConsistencyChecker`` but
    would ``AttributeError`` on ``copy()``. Consumers that fan a checker out
    across workers (FastDiagP) must depend on this role instead.
    """

    def copy(self) -> 'CopyableChecker':
        """Return an independent clone (fresh solver) for use in another worker."""
        ...
