"""KBDiag single-algorithm diagnosis tests.

Split from the former ``test_diagnosis.py`` monolith; shared config and helpers
live in ``tests.diagnosis_helpers``. Behaviour is unchanged.
"""
import pytest

from explanation.models import DiagnosisModelBuilder
from explanation.operations.algorithms.kbdiag import KBDiag
from explanation.operations.pysat_abstract_hsdag_explanation import _format_results
from explanation.transformations.testsuite_reader import TestSuiteReader
from profiling import profiler_session
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
@_skip_disabled('kbdiag_1diag_1')
def test_kbdiag_1diag_1(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_1)
                 .with_positive_testcases(positive_testcases)
                 )

        checker = create_checker(use_sat4j, prepared, is_incremental, solver_name)
        kbdiag = KBDiag(checker)
        _, diagnosis = kbdiag.find_diagnosis(prepared.task.set_c, prepared.task.set_b, prepared.task.set_tc)

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], prepared.describe)

        profiler.print_summary(include_raw_timers=True)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]QType, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]]'


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('kbdiag_1diag_1_neg')
def test_kbdiag_1diag_1_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_1_NEGATIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_1)
                 .with_positive_testcases(positive_testcases)
                 .with_negative_testcases(negative_testcases)
                 )

        checker = create_checker(use_sat4j, prepared, is_incremental, solver_name)
        kbdiag = KBDiag(checker)
        _, diagnosis = kbdiag.find_diagnosis(prepared.task.set_c, prepared.task.set_b, prepared.task.set_tc, prepared.task.set_neg_tv)

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], prepared.describe)

        profiler.print_summary(include_raw_timers=True)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]SDC, (mandatory) CheckR[1,1]QType]'


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('kbdiag_1diag_2')
def test_kbdiag_1diag_2(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_2_NEGATIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_2)
                 .with_positive_testcases(positive_testcases)
                 .with_negative_testcases(negative_testcases)
                 )

        checker = create_checker(use_sat4j, prepared, is_incremental, solver_name)
        kbdiag = KBDiag(checker)
        _, diagnosis = kbdiag.find_diagnosis(prepared.task.set_c, prepared.task.set_b, prepared.task.set_tc, prepared.task.set_neg_tv)

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], prepared.describe)

        profiler.print_summary(include_raw_timers=True)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(mandatory) jplug[1,1]interface, (alternative) interface[1,1]sdi mdi, (optional) diagram_builder[0,1]uml, (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]'


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('kbdiag_1diag_2_neg')
def test_kbdiag_1diag_2_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_2_NEGATIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_2)
                 .with_positive_testcases(positive_testcases)
                 .with_negative_testcases(negative_testcases)
                 )

        checker = create_checker(use_sat4j, prepared, is_incremental, solver_name)
        kbdiag = KBDiag(checker)
        _, diagnosis = kbdiag.find_diagnosis(prepared.task.set_c, prepared.task.set_b, prepared.task.set_tc, prepared.task.set_neg_tv)

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], prepared.describe)

        profiler.print_summary(include_raw_timers=True)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(mandatory) jplug[1,1]interface, (alternative) interface[1,1]sdi mdi, (optional) diagram_builder[0,1]uml, (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]'
