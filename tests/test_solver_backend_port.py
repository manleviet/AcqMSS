"""Port tests for the checker port protocols and the single backend factory.

Pins two things T7 establishes:
1. All three concrete backends satisfy the narrow ``ConsistencyChecker`` port and
   the broader ``TestCaseChecker`` port (the latter because
   ``is_consistent_test_cases`` lives on ``SolverCheckerBase``).
2. ``build_checker`` (task-based public door) and the private ``_build_checker``
   — the single place a concrete backend class is selected — map each
   ``SolverBackend`` token to the right class; ``from_flags`` maps the operation
   flags to the right token.
"""
import os

import pytest

from explanation.operations.algorithms.checker import (
    ConsistencyChecker,
    CopyableChecker,
    # Aliased: a leading-"Test" name trips pytest's class collector.
    TestCaseChecker as _TestCaseChecker,
)
from explanation.operations.algorithms.solver_backend import (
    SolverCheckerBase,
    IncrementalPySATChecker,
    NonIncrementalPySATChecker,
    SAT4JChecker,
    SolverBackend,
    _DEFAULT_SAT4J_JAR,
    _build_checker,
    build_checker,
)

_BACKEND_CLASSES = [IncrementalPySATChecker, NonIncrementalPySATChecker, SAT4JChecker]


class _FakeTask:
    """Minimal task carrying only what build_checker reads."""

    def __init__(self, set_kb, assumptions):
        self.set_kb = set_kb
        self.assumptions = assumptions


@pytest.mark.parametrize("backend_cls", _BACKEND_CLASSES)
def test_backends_satisfy_consistency_checker_port(backend_cls):
    assert issubclass(backend_cls, ConsistencyChecker)
    assert issubclass(backend_cls, SolverCheckerBase)


@pytest.mark.parametrize("backend_cls", _BACKEND_CLASSES)
def test_backends_satisfy_testcase_checker_port(backend_cls):
    assert issubclass(backend_cls, _TestCaseChecker)


def test_copyable_is_a_separate_role_from_the_narrow_port():
    """A checker can satisfy ConsistencyChecker yet NOT be copyable.

    FastDiagP calls ``checker.copy()``, so it must depend on CopyableChecker, not
    the narrow port — otherwise a valid ConsistencyChecker would AttributeError.
    """
    class _MinimalChecker:
        def is_consistent(self, set_c):
            return True

        def get_model(self):
            return None

        def cleanup(self):
            pass

    minimal = _MinimalChecker()
    assert isinstance(minimal, ConsistencyChecker)      # satisfies the narrow port
    assert not isinstance(minimal, CopyableChecker)     # but cannot be cloned
    for backend_cls in _BACKEND_CLASSES:
        assert issubclass(backend_cls, CopyableChecker)  # real backends can


def test_pysat_backend_instances_satisfy_ports():
    inc = IncrementalPySATChecker([[1]], [])
    non = NonIncrementalPySATChecker([[1]], [])
    try:
        assert isinstance(inc, ConsistencyChecker)
        assert isinstance(inc, _TestCaseChecker)
        assert isinstance(non, ConsistencyChecker)
        assert isinstance(non, _TestCaseChecker)
    finally:
        inc.cleanup()
        non.cleanup()


def test_from_flags_maps_flags_to_token():
    assert SolverBackend.from_flags(use_incremental=True, use_sat4j=True) is SolverBackend.SAT4J
    assert SolverBackend.from_flags(use_incremental=False, use_sat4j=True) is SolverBackend.SAT4J
    assert SolverBackend.from_flags(use_incremental=True, use_sat4j=False) is SolverBackend.PYSAT_INCREMENTAL
    assert SolverBackend.from_flags(use_incremental=False, use_sat4j=False) is SolverBackend.PYSAT_NON_INCREMENTAL


def test_build_checker_maps_pysat_tokens_to_classes():
    task = _FakeTask([[1]], [])
    inc = build_checker(task, SolverBackend.PYSAT_INCREMENTAL)
    non = build_checker(task, SolverBackend.PYSAT_NON_INCREMENTAL)
    try:
        assert isinstance(inc, IncrementalPySATChecker)
        assert isinstance(non, NonIncrementalPySATChecker)
    finally:
        inc.cleanup()
        non.cleanup()


def test_build_checker_is_the_single_selection_site():
    inc = _build_checker(SolverBackend.PYSAT_INCREMENTAL, [[1]], [])
    non = _build_checker(SolverBackend.PYSAT_NON_INCREMENTAL, [[1]], [])
    try:
        assert isinstance(inc, IncrementalPySATChecker)
        assert isinstance(non, NonIncrementalPySATChecker)
    finally:
        inc.cleanup()
        non.cleanup()


@pytest.mark.skipif(not os.path.exists(_DEFAULT_SAT4J_JAR),
                    reason="SAT4J jar not installed")
def test_build_checker_maps_sat4j_token_to_class():
    checker = build_checker(_FakeTask([[1]], []), SolverBackend.SAT4J)
    assert isinstance(checker, SAT4JChecker)
