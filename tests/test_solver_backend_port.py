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
import subprocess

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
    SolverTimeoutError,
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

        def find_model(self, set_c):
            return None

        def cleanup(self):
            pass

    minimal = _MinimalChecker()
    assert isinstance(minimal, ConsistencyChecker)      # satisfies the narrow port
    assert not isinstance(minimal, CopyableChecker)     # but cannot be cloned
    for backend_cls in _BACKEND_CLASSES:
        assert issubclass(backend_cls, CopyableChecker)  # real backends can


@pytest.mark.parametrize("solver_name", ["glucose3", "cadical153"])
def test_find_model_keeps_guards_pinned_under_glucose_and_cadical(solver_name):
    """find_model must KEEP the disabled (negated) guard assumptions so inactive
    constraints stay OFF in the model — under BOTH solvers. is_consistent drops them
    (SAT/UNSAT is encoding-invariant), but a model needs them: without the pin, cadical
    may set a guard true and force its literal — a divergence glucose's default-false
    polarity HIDES. This is the net that only cadical can fail (ADR-0013)."""
    from pysat.solvers import Solver
    try:
        Solver(name=solver_name).delete()
    except Exception:
        pytest.skip(f"{solver_name} not available")
    # (a10 -> x1), (a11 -> not x1), plus a free clause; guard assumptions are 10, 11.
    kb = [[-10, 1], [-11, -1], [2, 3]]
    checker = IncrementalPySATChecker(set_kb=kb, assumptions=[10, 11], solver_name=solver_name)
    try:
        # Enable nothing -> both guards disabled -> both MUST be pinned false in the model.
        model = checker.find_model([])
        assert model is not None
        assert -10 in model and -11 in model, (
            f"{solver_name}: find_model left a guard free (model={model}) — pin dropped")
        # is_consistent stays SAT regardless of solver (answer is encoding-invariant).
        assert checker.is_consistent([]) is True
    finally:
        checker.cleanup()


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


def test_sat4j_timeout_raises_instead_of_silent_unsat(monkeypatch):
    """A SAT4J timeout must raise SolverTimeoutError — never a silent UNSAT.

    The old code set ``output = "TIMEOUT"`` on ``subprocess.TimeoutExpired`` so
    ``is_consistent`` returned ``False``: a timeout was indistinguishable from a
    real UNSAT and corrupted results with no signal. This pins the fixed
    contract. Deterministic and jar-independent — java is never launched:
    ``os.path.exists`` is stubbed for construction and ``subprocess.run`` is
    stubbed to raise the timeout.
    """
    import explanation.checker.backend as backend_mod
    monkeypatch.setattr(backend_mod.os.path, "exists", lambda _p: True)

    checker = build_checker(_task(), SolverBackend.SAT4J, sat4j_timeout=42)
    assert checker.timeout == 42  # build_checker forwards the timeout knob

    def _raise_timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["java"], timeout=42)
    monkeypatch.setattr(backend_mod.subprocess, "run", _raise_timeout)

    # pytest.raises fails with "DID NOT RAISE" if it silently returned False.
    with pytest.raises(SolverTimeoutError):
        checker.is_consistent([])
