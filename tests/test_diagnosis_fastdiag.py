"""FastDiag / FastDiagP single-algorithm diagnosis tests.

Split from the former ``test_diagnosis.py`` monolith; shared config and helpers
live in ``tests.diagnosis_helpers``. Behaviour is unchanged.
"""
import pytest

from explanation.models import DiagnosisModelBuilder
from explanation.operations.algorithms.fastdiag import FastDiag
from explanation.operations.algorithms.fastdiagp import FastDiagP
from explanation.operations.pysat_abstract_hsdag_explanation import _format_results
from profiling import ProfilerMode, profiler_session
from tests.diagnosis_helpers import (
    PARAM_SPEC,
    STANDARD_PARAMS,
    Resources,
    _profiler_preset,
    _skip_disabled,
    build_prepared,
    create_checker,
    print_profiler_status,
    print_test_header,
)


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('fastdiag_1diag')
def test_fastdiag_1diag(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test FastDiag with different checker implementations and profiling modes."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        checker = create_checker(use_sat4j, prepared, is_incremental, solver_name)
        fastdiag = FastDiag(checker)
        diagnosis = fastdiag.find_diagnosis(prepared.task.set_c, prepared.task.set_b)

        profiler.print_summary(include_raw_timers=True)

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], prepared.describe)
        print(f"{diag_mess}")
        assert diag_mess == 'Diagnosis: [(5) IMPLIES[Smartwatch][Analog]]'


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('fastdiagp_1diag')
def test_fastdiagp_1diag(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test FastDiagP (parallel) to find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling), ProfilerMode.MULTI_PROCESS) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        checker = create_checker(use_sat4j, prepared, is_incremental, solver_name)
        fastdiagp = FastDiagP(checker)
        diagnosis = fastdiagp.find_diagnosis(prepared.task.set_c, prepared.task.set_b)

        profiler.print_summary(include_raw_timers=True)

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], prepared.describe)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(5) IMPLIES[Smartwatch][Analog]]'


# --- FastDiagP resource-safety guards -----------------------------------------
# No real subprocesses: mp.Pool is replaced with a recording fake so the
# pool-size floor and the exception-path cleanup are asserted deterministically.
import explanation.operations.algorithms.fastdiagp as fdp


class _AlwaysInconsistentChecker:
    """B∪C is always inconsistent, so find_diagnosis proceeds past the early
    return and builds the pool. copy() is unused on the paths exercised here."""

    def is_consistent(self, assumptions):
        return False

    def copy(self):
        return self


class _RecordingPool:
    """Stand-in for mp.Pool that records its worker count and whether it was
    terminated, without spawning processes. Works both as a plain object
    (pre-fix code) and as a context manager (post-fix code)."""

    instances: list = []

    def __init__(self, n):
        self.n = n
        self.terminated = False
        _RecordingPool.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.terminate()
        return False  # never suppress exceptions

    def apply_async(self, fn, args=()):
        raise AssertionError("apply_async must not run on single/failing paths")

    def close(self):
        pass

    def terminate(self):
        self.terminated = True

    def join(self):
        pass


def test_fastdiagp_pool_size_floors_at_one_on_single_vcpu(monkeypatch):
    """On a 1-vCPU host ``min(cpu_count()-1, 4)`` is 0 → ``mp.Pool(0)`` raises
    ValueError. The worker count must floor at 1. A single-constraint ``set_c``
    builds the pool but never dispatches to it (``_fd`` returns on the singleton
    branch), isolating the pool-size question."""
    _RecordingPool.instances.clear()
    monkeypatch.setattr(fdp.mp, "cpu_count", lambda: 1)
    monkeypatch.setattr(fdp.mp, "Pool", _RecordingPool)

    fastdiagp = FastDiagP(_AlwaysInconsistentChecker())
    diag = fastdiagp.find_diagnosis(set_c=[1], set_b=[])

    assert _RecordingPool.instances[-1].n >= 1  # never mp.Pool(0)
    assert diag == [1]                          # behaviour-inert result


def test_fastdiagp_pool_terminated_when_fd_raises(monkeypatch):
    """A raised ``_fd`` must not leak the pool. With a bare ``mp.Pool`` the
    close()/terminate() calls sit *after* the ``_fd`` call and are skipped on
    exception; a context manager terminates the pool on the way out."""
    _RecordingPool.instances.clear()
    monkeypatch.setattr(fdp.mp, "cpu_count", lambda: 2)  # Pool(1); isolate the leak
    monkeypatch.setattr(fdp.mp, "Pool", _RecordingPool)

    fastdiagp = FastDiagP(_AlwaysInconsistentChecker())

    def _boom(*args, **kwargs):
        raise RuntimeError("boom in _fd")

    monkeypatch.setattr(fastdiagp, "_fd", _boom)

    with pytest.raises(RuntimeError):
        fastdiagp.find_diagnosis(set_c=[1, 2], set_b=[])

    assert _RecordingPool.instances[-1].terminated  # cleaned up despite the raise
