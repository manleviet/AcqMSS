"""Consistency-checking package: the port (``protocols``) + the adapters (``backend``).

Internal facade — re-exports the public checker surface for convenience *within*
the framework. The framework's single public door remains ``explanation.api``;
this package's ``__init__`` is NOT a second public entry point.

Algorithms that only need the contract should import the clean port directly
(``from explanation.checker.protocols import ConsistencyChecker``) so a pure
consumer does not pull the solver adapters — and pysat/subprocess — through this
facade.
"""
from .protocols import ConsistencyChecker, TestCaseChecker, CopyableChecker
from .backend import SolverBackend, build_checker, SolverTimeoutError

__all__ = [
    'ConsistencyChecker',
    'TestCaseChecker',
    'CopyableChecker',
    'SolverBackend',
    'build_checker',
    'SolverTimeoutError',
]
