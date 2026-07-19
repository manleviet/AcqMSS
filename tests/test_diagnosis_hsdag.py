"""HSDAG-driven diagnosis tests (FastDiag / QuickXPlain / KBDiag /
QuickXPlainWithTestCases combined with the hitting-set DAG).

Split from the former ``test_diagnosis.py`` monolith; shared config and helpers
live in ``tests.diagnosis_helpers``. Behaviour is unchanged.
"""
import pytest
from flamapy.metamodels.configuration_metamodel.transformations import ConfigurationBasicReader

from explanation.models import DiagnosisModelBuilder
from explanation.operations.pysat_explanation_builder import (
    PySATDiagnosisBuilder,
    PySATTestcaseBuilder,
    PySATTestcaseQuickXplainBuilder,
)
from explanation.transformations.testsuite_reader import TestSuiteReader
from profiling import profiler_session
from tests.diagnosis_helpers import (
    PARAM_SPEC,
    SAT4J_ONLY_PARAMS,
    STANDARD_PARAMS,
    Resources,
    _profiler_preset,
    _skip_disabled,
    build_prepared,
    print_profiler_status,
    print_test_header,
)

# =============================================================================
# HSDAG WITH FASTDIAG TESTS
# =============================================================================


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_fastdiag_1diag')
def test_hsdag_fastdiag_1diag(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        builder = (PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis())
        hsdag = builder.with_max_diagnoses(1).build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == ['Diagnosis: [(5) IMPLIES[Smartwatch][Analog]]', 'No conflict found']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_fastdiag_2diag')
def test_hsdag_fastdiag_2diag(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: find two diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        builder = PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis()
        hsdag = builder.with_max_diagnoses(2).build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == ['Diagnoses: [(5) IMPLIES[Smartwatch][Analog]],[(4) IMPLIES[Smartwatch][Cellular]]',
                          'No conflict found']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_fastdiag_all')
def test_hsdag_fastdiag_all(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: find all diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        builder = PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis()
        hsdag = builder.build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnoses: [(5) IMPLIES[Smartwatch][Analog]],[(4) IMPLIES[Smartwatch][Cellular]],[(3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]']

# =============================================================================
# HSDAG WITH QUICKXPLAIN TESTS
# =============================================================================


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_quickxplain_1cs')
def test_hsdag_quickxplain_1cs(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find one conflict."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.with_max_conflicts(1).build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'No diagnosis found']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_quickxplain_dfs')
def test_hsdag_quickxplain_one_depth_first_search(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find one conflict using depth-first search."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.with_max_diagnoses(1).with_depth_first_search(True).build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'Diagnosis: [(5) IMPLIES[Smartwatch][Analog]]']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_quickxplain_2cs')
def test_hsdag_quickxplain_2cs(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find two conflicts."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.with_max_conflicts(2).build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'Diagnoses: [(5) IMPLIES[Smartwatch][Analog]],[(4) IMPLIES[Smartwatch][Cellular]],[(3) OR[NOT[Analog][]][NOT[Cellular][]]]']


@pytest.mark.parametrize(PARAM_SPEC, SAT4J_ONLY_PARAMS)
@_skip_disabled('hsdag_quickxplain_all')
def test_hsdag_quickxplain_all(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find all conflicts."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'Diagnoses: [(5) IMPLIES[Smartwatch][Analog]],[(4) IMPLIES[Smartwatch][Cellular]],[(3) OR[NOT[Analog][]][NOT[Cellular][]]]']

# =============================================================================
# CONFIGURATION AND TEST CASE TESTS
# =============================================================================


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_fastdiag_configuration')
def test_hsdag_fastdiag_with_configuration(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: diagnose with configuration."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        configuration = ConfigurationBasicReader(Resources.CONF_NONVALID).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_CONSISTENT)
                 .with_configuration(configuration)
                 )

        builder = PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis()
        hsdag = builder.build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        assert result == ['Diagnoses: [E-ink = true],[Analog = true]',
                          'Conflict: [E-ink = true, Analog = true]']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_quickxplain_configuration')
def test_hsdag_quickxplain_with_configuration(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find conflicts with configuration."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        configuration = ConfigurationBasicReader(Resources.CONF_NONVALID).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_CONSISTENT)
                 .with_configuration(configuration)
                 )

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == ['Conflict: [E-ink = true, Analog = true]',
                          'Diagnoses: [E-ink = true],[Analog = true]']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_fastdiag_testcase')
def test_hsdag_fastdiag_with_test_case(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: diagnose with test case."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        test_case = ConfigurationBasicReader(Resources.CONF_TESTCASE).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_DEADFEATURE)
                 .with_test_case(test_case)
                 )

        builder = PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis()
        hsdag = builder.build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == ['Diagnoses: [(4) IMPLIES[Smartwatch][Analog]],'
                          '[(alternative) Screen[1,1]Analog High Resolution E-ink]',
                          'Conflict: [(4) IMPLIES[Smartwatch][Analog], '
                          '(alternative) Screen[1,1]Analog High Resolution E-ink]']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_quickxplain_testcase')
def test_hsdag_quickxplain_with_testcase(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find conflicts with test case."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        test_case = ConfigurationBasicReader(Resources.CONF_TESTCASE).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_DEADFEATURE)
                 .with_test_case(test_case)
                 )

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        print(result)
        assert result == ['Conflict: [(4) IMPLIES[Smartwatch][Analog], '
                          '(alternative) Screen[1,1]Analog High Resolution E-ink]',
                          'Diagnoses: [(4) IMPLIES[Smartwatch][Analog]],'
                          '[(alternative) Screen[1,1]Analog High Resolution E-ink]']

# =============================================================================
# HSDAG + KBDIAG TESTS
# =============================================================================


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_kbdiag_1diag_1')
def test_hsdag_kbdiag_1diag_1(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_1)
                 .with_positive_testcases(positive_testcases)
                 )

        builder = None if use_sat4j else PySATTestcaseBuilder.for_debugging()
        if builder is None:
            return

        hsdag = builder.with_max_diagnoses(1).build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]QType, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]]',
            'No conflict found']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_kbdiag_1diag_1_neg')
def test_hsdag_kbdiag_1diag_1_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: find one diagnosis."""
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

        builder = None if use_sat4j else PySATTestcaseBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .with_max_diagnoses(1)
                 .build())
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]SDC, (mandatory) CheckR[1,1]QType]',
            'No conflict found']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_kbdiag_all_1')
def test_hsdag_kbdiag_all_1(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: all diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_1)
                 .with_positive_testcases(positive_testcases)
                 )

        builder = None if use_sat4j else PySATTestcaseBuilder.for_debugging()
        if builder is None:
            return

        hsdag = builder.build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == ('Diagnoses: [(mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]QType, '
                             '(Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], '
                             '(Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, '
                             '(mandatory) CheckR[1,1]SDC, (mandatory) CheckR[1,1]QType]')


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_kbdiag_all_1_neg')
def test_hsdag_kbdiag_all_1_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: all diagnoses."""
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

        builder = None if use_sat4j else PySATTestcaseBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .build())
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == 'Diagnoses: [(mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]SDC, (mandatory) CheckR[1,1]QType],[(mandatory) CheckR[1,1]RecEng, (alternative) RecEng[1,1]UBRec CBRec, (optional) CheckR[0,1]Stat, (mandatory) CheckR[1,1]QType, (or) QType[1,2]MulChoice ImgAnaTask, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (optional) CheckR[0,1]Stat, (mandatory) CheckR[1,1]QType, (or) QType[1,2]MulChoice ImgAnaTask, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (alternative) RecEng[1,1]UBRec CBRec, (mandatory) CheckR[1,1]QType, (or) QType[1,2]MulChoice ImgAnaTask, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (alternative) RecEng[1,1]UBRec CBRec, (optional) CheckR[0,1]Stat, (mandatory) CheckR[1,1]QType, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]QType, (or) QType[1,2]MulChoice ImgAnaTask, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (optional) CheckR[0,1]Stat, (mandatory) CheckR[1,1]QType, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]]'


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_kbdiag_1diag_2')
def test_hsdag_kbdiag_1diag_2(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_2)
                 .with_positive_testcases(positive_testcases)
                 )

        builder = None if use_sat4j else PySATTestcaseBuilder.for_debugging()
        if builder is None:
            return

        hsdag = builder.with_max_diagnoses(1).build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) jplug[1,1]interface, (alternative) interface[1,1]sdi mdi, (optional) diagram_builder[0,1]uml, (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]',
            'No conflict found']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_kbdiag_1diag_2_neg')
def test_hsdag_kbdiag_1diag_2_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: find one diagnosis."""
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

        builder = None if use_sat4j else PySATTestcaseBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .with_max_diagnoses(1)
                 .build())
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) jplug[1,1]interface, (alternative) interface[1,1]sdi mdi, (optional) diagram_builder[0,1]uml, (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]',
            'No conflict found']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_kbdiag_all_2')
def test_hsdag_kbdiag_all_2(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: all diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_2)
                 .with_positive_testcases(positive_testcases)
                 )

        builder = None if use_sat4j else PySATTestcaseBuilder.for_debugging()
        if builder is None:
            return

        hsdag = builder.build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == ('Diagnosis: [(mandatory) jplug[1,1]interface, (alternative) interface[1,1]sdi mdi, (optional) diagram_builder[0,1]uml, (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]')


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_kbdiag_all_2_neg')
def test_hsdag_kbdiag_all_2_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: all diagnoses."""
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

        builder = None if use_sat4j else PySATTestcaseBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .build())
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == ('Diagnosis: [(mandatory) jplug[1,1]interface, (alternative) interface[1,1]sdi mdi, (optional) diagram_builder[0,1]uml, (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]')

# =============================================================================
# HSDAG + QUICKXPLAINWITHTESTCASES TESTS
# =============================================================================


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_quickxplainwithtestcases_1diag_1')
def test_hsdag_quickxplainwithtestcases_1diag_1(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_1)
                 .with_positive_testcases(positive_testcases)
                 )

        builder = None if use_sat4j else PySATTestcaseQuickXplainBuilder.for_debugging()
        if builder is None:
            return

        op = builder.with_max_diagnoses(1).build()
        op.use_incremental = is_incremental
        op.execute(prepared)
        result = op.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) CheckR[1,1]SDC, (mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]QType]',
            'Conflicts: [(Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (mandatory) '
            'CheckR[1,1]SDC],[(Constraint 1) OR[NOT[SDC][]][Stat], (mandatory) '
            'CheckR[1,1]SDC],[(mandatory) CheckR[1,1]RecEng],[(mandatory) '
            'CheckR[1,1]QType]']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_quickxplainwithtestcases_1diag_1_neg')
def test_hsdag_quickxplainwithtestcases_1diag_1_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
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

        builder = None if use_sat4j else PySATTestcaseQuickXplainBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .with_max_diagnoses(1)
                 .build())
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) CheckR[1,1]SDC, (mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]QType]',
            'Conflicts: [(mandatory) CheckR[1,1]SDC],[(mandatory) CheckR[1,1]RecEng],[(mandatory) CheckR[1,1]QType]']


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_quickxplainwithtestcases_all_1')
def test_hsdag_quickxplainwithtestcases_all_1(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_session(_profiler_preset(enable_profiling)) as profiler):
        print_profiler_status(profiler)

        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_10_1)
                 .with_positive_testcases(positive_testcases)
                 )

        builder = None if use_sat4j else PySATTestcaseQuickXplainBuilder.for_debugging()
        if builder is None:
            return

        hsdag = builder.build()
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == ('Diagnoses: [(mandatory) CheckR[1,1]SDC, (mandatory) CheckR[1,1]RecEng, '
                             '(mandatory) CheckR[1,1]QType],[(Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], '
                             '(Constraint 1) OR[NOT[SDC][]][Stat], (mandatory) CheckR[1,1]RecEng, '
                             '(mandatory) CheckR[1,1]QType],[(Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], '
                             '(mandatory) CheckR[1,1]SDC, (mandatory) CheckR[1,1]RecEng, (mandatory) '
                             'CheckR[1,1]QType]')


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('hsdag_quickxplainwithtestcases_all_1_neg')
def test_hsdag_quickxplainwithtestcases_all_1_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
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

        builder = None if use_sat4j else PySATTestcaseBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .build())
        hsdag.use_incremental = is_incremental
        hsdag.execute(prepared)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == ('Diagnoses: [(mandatory) CheckR[1,1]RecEng, (mandatory) CheckR[1,1]SDC, '
                             '(mandatory) CheckR[1,1]QType],[(mandatory) CheckR[1,1]RecEng, '
                             '(alternative) RecEng[1,1]UBRec CBRec, (optional) CheckR[0,1]Stat, '
                             '(mandatory) CheckR[1,1]QType, (or) QType[1,2]MulChoice ImgAnaTask, '
                             '(Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) '
                             'OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (optional) '
                             'CheckR[0,1]Stat, (mandatory) CheckR[1,1]QType, (or) QType[1,2]MulChoice '
                             'ImgAnaTask, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) '
                             'OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (alternative) '
                             'RecEng[1,1]UBRec CBRec, (mandatory) CheckR[1,1]QType, (or) '
                             'QType[1,2]MulChoice ImgAnaTask, (Constraint 0) '
                             'OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) '
                             'OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (alternative) '
                             'RecEng[1,1]UBRec CBRec, (optional) CheckR[0,1]Stat, (mandatory) '
                             'CheckR[1,1]QType, (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint '
                             '1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (mandatory) '
                             'CheckR[1,1]QType, (or) QType[1,2]MulChoice ImgAnaTask, (Constraint 0) '
                             'OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) '
                             'OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng, (optional) '
                             'CheckR[0,1]Stat, (mandatory) CheckR[1,1]QType, (Constraint 0) '
                             'OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]]')
