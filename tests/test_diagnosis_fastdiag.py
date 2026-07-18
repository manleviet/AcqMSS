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
