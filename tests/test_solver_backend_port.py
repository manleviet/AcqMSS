"""Port tests for the checker port protocols and the single backend factory.

Pins two things T7 establishes:
1. All three concrete backends satisfy the narrow ``ConsistencyChecker`` port and
   the broader ``TestCaseChecker`` port (the latter because
   ``is_consistent_test_cases`` lives on ``CheckerBase``).
2. ``build_checker`` (the task-based public door AND the single place a concrete
   backend class is selected) maps each ``SolverBackend`` token to the right
   class; ``from_flags`` maps the operation flags to the right token.
"""
import os

import pytest

from explanation.api import DiagnosisTask
from explanation.checker.protocols import (
    ConsistencyChecker,
    CopyableChecker,
    # Aliased: a leading-"Test" name trips pytest's class collector.
    TestCaseChecker as _TestCaseChecker,
)
from explanation.checker.backend import (
    CheckerBase,
    IncrementalPySATChecker,
    NonIncrementalPySATChecker,
    SAT4JChecker,
    SolverBackend,
    _DEFAULT_SAT4J_JAR,
    build_checker,
)

_BACKEND_CLASSES = [IncrementalPySATChecker, NonIncrementalPySATChecker, SAT4JChecker]


def _task(set_kb=None, assumptions=None):
    """A one-line real Task through the public door (build_checker reads set_kb/assumptions)."""
    return DiagnosisTask(set_kb=set_kb or [[1]], assumptions=assumptions or [])


@pytest.mark.parametrize("backend_cls", _BACKEND_CLASSES)
def test_backends_satisfy_consistency_checker_port(backend_cls):
    assert issubclass(backend_cls, ConsistencyChecker)
    assert issubclass(backend_cls, CheckerBase)


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


def test_build_checker_maps_tokens_to_classes():
    # build_checker is both the public door and the single class-selection site.
    inc = build_checker(_task(), SolverBackend.PYSAT_INCREMENTAL)
    non = build_checker(_task(), SolverBackend.PYSAT_NON_INCREMENTAL)
    try:
        assert isinstance(inc, IncrementalPySATChecker)
        assert isinstance(non, NonIncrementalPySATChecker)
    finally:
        inc.cleanup()
        non.cleanup()


@pytest.mark.skipif(not os.path.exists(_DEFAULT_SAT4J_JAR),
                    reason="SAT4J jar not installed")
def test_build_checker_maps_sat4j_token_to_class():
    checker = build_checker(_task(), SolverBackend.SAT4J)
    assert isinstance(checker, SAT4JChecker)
