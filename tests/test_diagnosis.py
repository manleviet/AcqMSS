"""
Diagnosis Test Suite
====================

This module tests various diagnosis algorithms with different configurations.

To enable/disable specific tests, modify the ENABLED_TESTS dictionary below.
To enable/disable specific parameter combinations, modify ENABLED_PARAMS.
"""
import os
import sys
from contextlib import contextmanager
from typing import cast

from flamapy.metamodels.configuration_metamodel.transformations import ConfigurationBasicReader
from flamapy.metamodels.fm_metamodel.transformations import FeatureIDEReader, UVLReader
from parameterized import parameterized

from explanation.models.pysat_diagnosis_model import DiagnosisModel
from explanation.operations.algorithms.checker import CheckerFactory
from explanation.operations.algorithms.fastdiag import FastDiag
from explanation.operations.algorithms.fastdiagp import FastDiagP
from explanation.operations.algorithms.kbdiag import KBDiag
from explanation.operations.algorithms.profiler import ProfilerMode, ProfilerPreset, use_global_profiler
from explanation.operations.algorithms.quickxplain import QuickXPlain
from explanation.operations.algorithms.wipeoutr_t import WipeOutR_T
from explanation.operations.pysat_abstract_explanation import _format_results
from explanation.operations.pysat_redundancy_testcases import PySATRedundancyTestCases
from explanation.operations.pysat_explanation_builder import (
    PySATDiagnosisBuilder, PySATDebuggingBuilder, PySATRedundancyTestCasesBuilder
)
from explanation.transformations.fm_to_diag_pysat import FmToDiagPysat
from explanation.transformations.testsuite_reader import TestSuiteReader

# =============================================================================
# TEST CONFIGURATION - Enable/Disable Tests Here
# =============================================================================

ENABLED_TESTS = {
    # Single algorithm tests
    'fastdiag_1diag': True,
    'quickxplain_1cs': True,
    'fastdiagp_1diag': True,
    'kbdiag_1diag_1': True,
    'kbdiag_1diag_1_neg': True,
    'kbdiag_1diag_2': True,
    'kbdiag_1diag_2_neg': True,

    # HSDAG with FastDiag
    'hsdag_fastdiag_1diag': True,
    'hsdag_fastdiag_2diag': True,
    'hsdag_fastdiag_all': True,

    # HSDAG with QuickXPlain
    'hsdag_quickxplain_1cs': True,
    'hsdag_quickxplain_dfs': True,
    'hsdag_quickxplain_2cs': True,
    'hsdag_quickxplain_all': True,

    # With configuration/test case
    'hsdag_fastdiag_configuration': True,
    'hsdag_quickxplain_configuration': True,
    'hsdag_fastdiag_testcase': True,
    'hsdag_quickxplain_testcase': True,

    # KBDiag tests
    'hsdag_kbdiag_1diag_1': True,
    'hsdag_kbdiag_1diag_1_neg': True,
    'hsdag_kbdiag_all_1': True,
    'hsdag_kbdiag_all_1_neg': True,
    'hsdag_kbdiag_1diag_2': True,
    'hsdag_kbdiag_1diag_2_neg': True,
    'hsdag_kbdiag_all_2': True,
    'hsdag_kbdiag_all_2_neg': True,

    # WipeOutR_T tests
    'wipeoutr_t_redundancy': True,
}

# =============================================================================
# PARAMETER CONFIGURATION - Enable/Disable Parameter Combinations Here
# =============================================================================

# Individual parameter toggles
ENABLED_PARAMS = {
    'incremental_with_profiling': True,
    'incremental_no_profiling': True,
    'nonincremental_with_profiling': True,
    'nonincremental_no_profiling': True,
    'sat4j_with_profiling': True,
    'sat4j_no_profiling': True,
}

# =============================================================================
# PARAMETER SETS
# =============================================================================

def _get_standard_params():
    """Get standard parameter combinations based on ENABLED_PARAMS config."""
    all_params = [
        ("incremental_with_profiling", True, 'glucose3', False, True),
        ("incremental_no_profiling", True, 'glucose3', False, False),
        ("nonincremental_with_profiling", False, 'glucose3', False, True),
        ("nonincremental_no_profiling", False, 'glucose3', False, False),
        ("sat4j_with_profiling", False, None, True, True),
        ("sat4j_no_profiling", False, None, True, False),
    ]
    return [p for p in all_params if ENABLED_PARAMS.get(p[0], True)]

def _get_sat4j_only_params():
    """Get SAT4J-only parameter combinations."""
    all_params = [
        ("sat4j_with_profiling", False, None, True, True),
        ("sat4j_no_profiling", False, None, True, False),
    ]
    return [p for p in all_params if ENABLED_PARAMS.get(p[0], True)]

def _get_kbdiag_params():
    """Get standard parameter combinations based on ENABLED_PARAMS config."""
    all_params = [
        ("incremental_with_profiling", True, 'glucose3', False, True),
        ("incremental_no_profiling", True, 'glucose3', False, False),
        ("nonincremental_with_profiling", False, 'glucose3', False, True),
        ("nonincremental_no_profiling", False, 'glucose3', False, False),
        # ("sat4j_with_profiling", False, None, True, True),
        # ("sat4j_no_profiling", False, None, True, False),
    ]
    return [p for p in all_params if ENABLED_PARAMS.get(p[0], True)]

STANDARD_PARAMS = _get_standard_params()
SAT4J_ONLY_PARAMS = _get_sat4j_only_params()
KBDIAG_PARAMS = _get_kbdiag_params()

# =============================================================================
# TEST RESOURCES
# =============================================================================

# Get the directory of this test file
TEST_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = os.path.join(TEST_DIR, 'resources')
class Resources:
    FM_INCONSISTENT = os.path.join(RESOURCES_DIR, "smartwatch_inconsistent.fide")
    FM_CONSISTENT = os.path.join(RESOURCES_DIR, "smartwatch_consistent.fide")
    FM_DEADFEATURE = os.path.join(RESOURCES_DIR, "smartwatch_deadfeature.fide")
    CONF_NONVALID = os.path.join(RESOURCES_DIR, "smartwatch_nonvalid.csvconf")
    CONF_TESTCASE = os.path.join(RESOURCES_DIR, "smartwatch_testcase.csvconf")
    # for test cases
    FM_10_1 = os.path.join(RESOURCES_DIR, "FM_10_1.uvl")
    FM_10_1_POSITIVE_TESTCASES = os.path.join(RESOURCES_DIR, "FM_10_1.positive.testcases")
    FM_10_1_NEGATIVE_TESTCASES = os.path.join(RESOURCES_DIR, "FM_10_1.negative.testcases")
    FM_10_2 = os.path.join(RESOURCES_DIR, "FM_10_2.uvl")
    FM_10_2_POSITIVE_TESTCASES = os.path.join(RESOURCES_DIR, "FM_10_2.positive.testcases")
    FM_10_2_NEGATIVE_TESTCASES = os.path.join(RESOURCES_DIR, "FM_10_2.negative.testcases")
    # For WipeOutR_FM tests
    FM_REDUNDANT = os.path.join(RESOURCES_DIR, "redundant_fm.uvl")
    # For WipeOutR_T tests
    REDUNDANT_TESTSUITE = os.path.join(RESOURCES_DIR, "redundant_testsuite.testcases")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

@contextmanager
def profiler_context(enable_profiling: bool, mode: ProfilerMode = ProfilerMode.SINGLE_THREAD):
    """Context manager for profiler setup and teardown."""
    preset = ProfilerPreset.BENCHMARK if enable_profiling else ProfilerPreset.DISABLED
    profiler = use_global_profiler(preset)
    profiler.reset()
    profiler.start(mode=mode)

    try:
        yield profiler
    finally:
        profiler.stop()

def print_test_header(name: str, is_incremental: bool, solver_name: str,
                      use_sat4j: bool, enable_profiling: bool):
    """Print standardized test header."""
    print("\n" + "=" * 70)
    print(f"Running test: {name} | is_incremental: {is_incremental} | "
          f"solver_name: {solver_name} | use_sat4j: {use_sat4j} | enable_profiling: {enable_profiling}")

def print_profiler_status(profiler):
    """Print profiler status."""
    status = "ENABLED" if profiler.is_profiling else "DISABLED"
    print(f"Profiler {status}.")

def load_model(fm_path: str, is_incremental: bool = True) -> DiagnosisModel:
    """Load and transform a feature model."""
    feature_model = FeatureIDEReader(fm_path).transform()
    model = cast(DiagnosisModel, FmToDiagPysat(feature_model).transform())
    model.is_incremental = is_incremental
    return model

def load_model_from_uvl(fm_path: str, is_incremental: bool = True) -> DiagnosisModel:
    """Load and transform a feature model."""
    feature_model = UVLReader(fm_path).transform()
    model = cast(DiagnosisModel, FmToDiagPysat(feature_model).transform())
    model.is_incremental = is_incremental
    return model

def create_checker(use_sat4j: bool, model: DiagnosisModel):
    """Create appropriate checker based on configuration."""
    if use_sat4j:
        return CheckerFactory.create_sat4jchecker()
    return CheckerFactory.create_from_model(model)

def skip_if_disabled(test_name: str):
    """Decorator to skip test if disabled in ENABLED_TESTS."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not ENABLED_TESTS.get(test_name, True):
                print(f"\n[SKIPPED] {test_name} is disabled in ENABLED_TESTS")
                return
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator


# =============================================================================
# SINGLE ALGORITHM TESTS
# =============================================================================

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('fastdiag_1diag')
def test_fastdiag_1diag(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test FastDiag with different checker implementations and profiling modes."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)
        model.prepare_diagnosis_task()

        checker = create_checker(use_sat4j, model)
        fastdiag = FastDiag(checker)
        diagnosis = fastdiag.find_diagnosis(model.get_c(), model.get_b())

        profiler.print_summary(include_raw_timers=True)

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], model)
        print(f"{diag_mess}")
        assert diag_mess == 'Diagnosis: [(5) IMPLIES[Smartwatch][Analog]]'

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('quickxplain_1cs')
def test_quickxplain_1cs(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test QuickXPlain to find one conflict."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)
        model.prepare_diagnosis_task()

        checker = create_checker(use_sat4j, model)
        quickxplain = QuickXPlain(checker)
        conflict = quickxplain.find_conflict(model.get_c(), model.get_b())

        profiler.print_summary(include_raw_timers=True)

        cs_mess = _format_results("Conflict", "Conflicts", [conflict], model)
        print(f"{cs_mess}")
        assert cs_mess == 'Conflict: [(3) OR[NOT[Analog][]][NOT[Cellular][]], (4) IMPLIES[Smartwatch][Cellular], (5) IMPLIES[Smartwatch][Analog]]'

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('fastdiagp_1diag')
def test_fastdiagp_1diag(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test FastDiagP (parallel) to find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling, ProfilerMode.MULTI_PROCESS) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)
        model.prepare_diagnosis_task()

        checker = create_checker(use_sat4j, model)
        fastdiagp = FastDiagP(checker)
        diagnosis = fastdiagp.find_diagnosis(model.get_c(), model.get_b())

        profiler.print_summary(include_raw_timers=True)

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], model)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(5) IMPLIES[Smartwatch][Analog]]'

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('kbdiag_1diag_1')
def test_kbdiag_1diag_1(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_1, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()

        model.prepare_debugging_task(positive_testcases)

        checker = create_checker(use_sat4j, model)
        kbdiag = KBDiag(checker)
        _, diagnosis = kbdiag.find_diagnosis(model.get_c(), model.get_b(), model.get_tc())

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], model)

        profiler.print_summary(include_raw_timers=True)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(mandatory) CheckR[1,1]RecEng , (mandatory) CheckR[1,1]QType , (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]]'

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('kbdiag_1diag_1_neg')
def test_kbdiag_1diag_1_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_1, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_1_NEGATIVE_TESTCASES).transform()

        model.prepare_debugging_task(positive_testcases, negative_testcases)

        checker = create_checker(use_sat4j, model)
        kbdiag = KBDiag(checker)
        _, diagnosis = kbdiag.find_diagnosis(model.get_c(), model.get_b(), model.get_tc(), model.get_neg_tv())

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], model)

        profiler.print_summary(include_raw_timers=True)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(mandatory) CheckR[1,1]RecEng , (mandatory) CheckR[1,1]SDC , (mandatory) CheckR[1,1]QType ]'

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('kbdiag_1diag_2')
def test_kbdiag_1diag_2(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_2, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_2_NEGATIVE_TESTCASES).transform()

        model.prepare_debugging_task(positive_testcases)

        checker = create_checker(use_sat4j, model)
        kbdiag = KBDiag(checker)
        _, diagnosis = kbdiag.find_diagnosis(model.get_c(), model.get_b(), model.get_tc(), model.get_neg_tv())

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], model)

        profiler.print_summary(include_raw_timers=True)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(mandatory) jplug[1,1]interface , (alternative) interface[1,1]sdi mdi , (optional) diagram_builder[0,1]uml , (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]'

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('kbdiag_1diag_2_neg')
def test_kbdiag_1diag_2_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_2, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_2_NEGATIVE_TESTCASES).transform()

        model.prepare_debugging_task(positive_testcases, negative_testcases)

        checker = create_checker(use_sat4j, model)
        kbdiag = KBDiag(checker)
        _, diagnosis = kbdiag.find_diagnosis(model.get_c(), model.get_b(), model.get_tc(), model.get_neg_tv())

        diag_mess = _format_results("Diagnosis", "Diagnoses", [diagnosis], model)

        profiler.print_summary(include_raw_timers=True)
        print(diag_mess)
        assert diag_mess == 'Diagnosis: [(mandatory) jplug[1,1]interface , (alternative) interface[1,1]sdi mdi , (optional) diagram_builder[0,1]uml , (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]'

# =============================================================================
# HSDAG WITH FASTDIAG TESTS
# =============================================================================

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_fastdiag_1diag')
def test_hsdag_fastdiag_1diag(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)

        builder = PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis()
        hsdag = builder.with_max_diagnoses(1).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == ['Diagnosis: [(5) IMPLIES[Smartwatch][Analog]]', 'No conflict found']

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_fastdiag_2diag')
def test_hsdag_fastdiag_2diag(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: find two diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)

        builder = PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis()
        hsdag = builder.with_max_diagnoses(2).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == ['Diagnoses: [(5) IMPLIES[Smartwatch][Analog]],[(4) IMPLIES[Smartwatch][Cellular]]',
                          'No conflict found']

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_fastdiag_all')
def test_hsdag_fastdiag_all(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: find all diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)

        builder = PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis()
        hsdag = builder.build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnoses: [(5) IMPLIES[Smartwatch][Analog]],[(4) IMPLIES[Smartwatch][Cellular]],[(3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]']

# =============================================================================
# HSDAG WITH QUICKXPLAIN TESTS
# =============================================================================

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_quickxplain_1cs')
def test_hsdag_quickxplain_1cs(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find one conflict."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.with_max_conflicts(1).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'No diagnosis found']

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_quickxplain_dfs')
def test_hsdag_quickxplain_one_depth_first_search(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find one conflict using depth-first search."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.with_max_diagnoses(1).with_depth_first_search(True).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'Diagnosis: [(5) IMPLIES[Smartwatch][Analog]]']

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_quickxplain_2cs')
def test_hsdag_quickxplain_2cs(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find two conflicts."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.with_max_conflicts(2).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'Diagnoses: [(5) IMPLIES[Smartwatch][Analog]],[(4) IMPLIES[Smartwatch][Cellular]],[(3) OR[NOT[Analog][]][NOT[Cellular][]]]']

@parameterized.expand(SAT4J_ONLY_PARAMS)
@skip_if_disabled('hsdag_quickxplain_all')
def test_hsdag_quickxplain_all(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find all conflicts."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_INCONSISTENT, is_incremental)

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Conflict: [(5) IMPLIES[Smartwatch][Analog], (4) IMPLIES[Smartwatch][Cellular], (3) OR[NOT[Analog][]][NOT[Cellular][]]]',
            'Diagnoses: [(5) IMPLIES[Smartwatch][Analog]],[(4) IMPLIES[Smartwatch][Cellular]],[(3) OR[NOT[Analog][]][NOT[Cellular][]]]']

# =============================================================================
# CONFIGURATION AND TEST CASE TESTS
# =============================================================================

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_fastdiag_configuration')
def test_hsdag_fastdiag_with_configuration(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: diagnose with configuration."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_CONSISTENT, is_incremental)
        configuration = ConfigurationBasicReader(Resources.CONF_NONVALID).transform()

        builder = PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis()
        hsdag = builder.with_configuration(configuration).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        assert result == ['Diagnoses: [E-ink = true],[Analog = true]',
                          'Conflict: [E-ink = true, Analog = true]']

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_quickxplain_configuration')
def test_hsdag_quickxplain_with_configuration(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find conflicts with configuration."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_CONSISTENT, is_incremental)
        configuration = ConfigurationBasicReader(Resources.CONF_NONVALID).transform()

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.with_configuration(configuration).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == ['Conflict: [E-ink = true, Analog = true]',
                          'Diagnoses: [E-ink = true],[Analog = true]']

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_fastdiag_testcase')
def test_hsdag_fastdiag_with_test_case(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with FastDiag: diagnose with test case."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_DEADFEATURE, is_incremental)
        test_case = ConfigurationBasicReader(Resources.CONF_TESTCASE).transform()

        builder = PySATDiagnosisBuilder.for_diagnosis_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_diagnosis()
        hsdag = builder.with_test_case(test_case).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == ['Diagnoses: [(4) IMPLIES[Smartwatch][Analog]],'
                          '[(alternative) Screen[1,1]Analog High Resolution E-ink ]',
                          'Conflict: [(4) IMPLIES[Smartwatch][Analog], '
                          '(alternative) Screen[1,1]Analog High Resolution E-ink ]']

@parameterized.expand(STANDARD_PARAMS)
@skip_if_disabled('hsdag_quickxplain_testcase')
def test_hsdag_quickxplain_with_testcase(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with QuickXPlain: find conflicts with test case."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model(Resources.FM_DEADFEATURE, is_incremental)
        test_case = ConfigurationBasicReader(Resources.CONF_TESTCASE).transform()

        builder = PySATDiagnosisBuilder.for_conflict_sat4j() if use_sat4j else PySATDiagnosisBuilder.for_conflict()
        hsdag = builder.with_test_case(test_case).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        print(result)
        assert result == ['Conflict: [(4) IMPLIES[Smartwatch][Analog], '
                          '(alternative) Screen[1,1]Analog High Resolution E-ink ]',
                          'Diagnoses: [(4) IMPLIES[Smartwatch][Analog]],'
                          '[(alternative) Screen[1,1]Analog High Resolution E-ink ]']

# =============================================================================
# HSDAG + KBDIAG TESTS
# =============================================================================

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('hsdag_kbdiag_1diag_1')
def test_hsdag_kbdiag_1diag_1(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_1, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()

        builder = None if use_sat4j else PySATDebuggingBuilder.for_debugging()
        if builder is None:
            return

        hsdag = builder.with_positive_test_cases(positive_testcases).with_max_diagnoses(1).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) CheckR[1,1]RecEng , (mandatory) CheckR[1,1]QType , (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]]',
            'No conflict found']

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('hsdag_kbdiag_1diag_1_neg')
def test_hsdag_kbdiag_1diag_1_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_1, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_1_NEGATIVE_TESTCASES).transform()

        builder = None if use_sat4j else PySATDebuggingBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .with_positive_test_cases(positive_testcases)
                 .with_negative_test_cases(negative_testcases)
                 .with_max_diagnoses(1)
                 .build())
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) CheckR[1,1]RecEng , (mandatory) CheckR[1,1]SDC , (mandatory) CheckR[1,1]QType ]',
            'No conflict found']

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('hsdag_kbdiag_all_1')
def test_hsdag_kbdiag_all_1(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: all diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_1, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()

        builder = None if use_sat4j else PySATDebuggingBuilder.for_debugging()
        if builder is None:
            return

        hsdag = builder.with_positive_test_cases(positive_testcases).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == ('Diagnoses: [(mandatory) CheckR[1,1]RecEng , (mandatory) CheckR[1,1]QType , '
                             '(Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], '
                             '(Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng , '
                             '(mandatory) CheckR[1,1]SDC , (mandatory) CheckR[1,1]QType ]')

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('hsdag_kbdiag_all_1_neg')
def test_hsdag_kbdiag_all_1_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: all diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_1, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_1_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_1_NEGATIVE_TESTCASES).transform()

        builder = None if use_sat4j else PySATDebuggingBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .with_positive_test_cases(positive_testcases)
                 .with_negative_test_cases(negative_testcases)
                 .build())
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == 'Diagnoses: [(mandatory) CheckR[1,1]RecEng , (mandatory) CheckR[1,1]SDC , (mandatory) CheckR[1,1]QType ],[(mandatory) CheckR[1,1]RecEng , (alternative) RecEng[1,1]UBRec CBRec , (optional) CheckR[0,1]Stat , (mandatory) CheckR[1,1]QType , (or) QType[1,2]MulChoice ImgAnaTask , (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng , (optional) CheckR[0,1]Stat , (mandatory) CheckR[1,1]QType , (or) QType[1,2]MulChoice ImgAnaTask , (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng , (alternative) RecEng[1,1]UBRec CBRec , (mandatory) CheckR[1,1]QType , (or) QType[1,2]MulChoice ImgAnaTask , (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng , (alternative) RecEng[1,1]UBRec CBRec , (optional) CheckR[0,1]Stat , (mandatory) CheckR[1,1]QType , (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng , (mandatory) CheckR[1,1]QType , (or) QType[1,2]MulChoice ImgAnaTask , (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]],[(mandatory) CheckR[1,1]RecEng , (optional) CheckR[0,1]Stat , (mandatory) CheckR[1,1]QType , (Constraint 0) OR[NOT[CBRec][]][NOT[SDC][]], (Constraint 1) OR[NOT[SDC][]][Stat]]'

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('hsdag_kbdiag_1diag_2')
def test_hsdag_kbdiag_1diag_2(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_2, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()

        builder = None if use_sat4j else PySATDebuggingBuilder.for_debugging()
        if builder is None:
            return

        hsdag = builder.with_positive_test_cases(positive_testcases).with_max_diagnoses(1).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) jplug[1,1]interface , (alternative) interface[1,1]sdi mdi , (optional) diagram_builder[0,1]uml , (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]',
            'No conflict found']

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('hsdag_kbdiag_1diag_2_neg')
def test_hsdag_kbdiag_1diag_2_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: find one diagnosis."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_2, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_2_NEGATIVE_TESTCASES).transform()

        builder = None if use_sat4j else PySATDebuggingBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .with_positive_test_cases(positive_testcases)
                 .with_negative_test_cases(negative_testcases)
                 .with_max_diagnoses(1)
                 .build())
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result)
        assert result == [
            'Diagnosis: [(mandatory) jplug[1,1]interface , (alternative) interface[1,1]sdi mdi , (optional) diagram_builder[0,1]uml , (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]',
            'No conflict found']

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('hsdag_kbdiag_all_2')
def test_hsdag_kbdiag_all_2(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: all diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_2, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()

        builder = None if use_sat4j else PySATDebuggingBuilder.for_debugging()
        if builder is None:
            return

        hsdag = builder.with_positive_test_cases(positive_testcases).build()
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == ('Diagnosis: [(mandatory) jplug[1,1]interface , (alternative) interface[1,1]sdi mdi , (optional) diagram_builder[0,1]uml , (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]')

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('hsdag_kbdiag_all_2_neg')
def test_hsdag_kbdiag_all_2_neg(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """HSDAG with KBDIAG: all diagnoses."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with (profiler_context(enable_profiling) as profiler):
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_10_2, is_incremental)
        positive_testcases = TestSuiteReader(Resources.FM_10_2_POSITIVE_TESTCASES).transform()
        negative_testcases = TestSuiteReader(Resources.FM_10_2_NEGATIVE_TESTCASES).transform()

        builder = None if use_sat4j else PySATDebuggingBuilder.for_debugging()
        if builder is None:
            return

        hsdag = (builder
                 .with_positive_test_cases(positive_testcases)
                 .with_negative_test_cases(negative_testcases)
                 .build())
        hsdag.execute(model)
        result = hsdag.get_result()

        profiler.print_summary(include_raw_timers=True)
        print(result[0])
        assert result[0] == ('Diagnosis: [(mandatory) jplug[1,1]interface , (alternative) interface[1,1]sdi mdi , (optional) diagram_builder[0,1]uml , (Constraint 0) OR[NOT[gui_builder][]][NOT[sdi][]]]')
# =============================================================================
# WIPEOUTR_T TESTS
# =============================================================================

@parameterized.expand(KBDIAG_PARAMS)
@skip_if_disabled('wipeoutr_t_redundancy')
def test_wipeoutr_t_redundancy(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test PySATRedundancyTestCases operation using WipeOutR_T algorithm.

    Uses the same test suite as test_wipeoutr_t_redundancy:
    - t1: FeatureA = true (REDUNDANT - covered by t3)
    - t2: FeatureC = false (NOT redundant)
    - t3: FeatureA = true, FeatureB = true (more specific than t1)

    This test verifies the PySATRedundancyTestCases operation wrapper.
    """
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_context(enable_profiling) as profiler:
        print_profiler_status(profiler)

        model = load_model_from_uvl(Resources.FM_REDUNDANT, is_incremental)
        testsuite = TestSuiteReader(Resources.REDUNDANT_TESTSUITE).transform()

        print(f"Test suite has {len(testsuite.testcases)} test cases")
        for i, tc in enumerate(testsuite.testcases):
            print(f"  t{i + 1}: {tc}")

        builder = None if use_sat4j else PySATRedundancyTestCasesBuilder.for_redundancy_test_cases(profiler)
        if builder is None:
            return

        operation = (builder
                     .with_test_cases(testsuite)
                     .build())
        operation.execute(model)

        # Get results
        result = operation.get_result()

        print(result)
        profiler.print_summary(include_raw_timers=True)

        assert len(result) == 2, f"Expected 2 lists (redundant and non-redundant), got {len(result)}"
        assert result[0] == 'Redundant test cases: [FeatureA=true]', "Expected 'FeatureA = true' to be redundant"
        assert result[1] == 'Non-redundant test cases: [FeatureC=false, FeatureA=true & FeatureB=true]', \
            "Expected 'FeatureC = false' and 'FeatureA = true & FeatureB = true' to be non-redundant"

# =============================================================================
# TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all enabled test cases."""
    print("\n" + "=" * 70)
    print(" DIAGNOSIS TEST SUITE ".center(70, "="))
    print("=" * 70)

    # Map test names to functions
    test_functions = [
        ("FastDiag 1 Diagnosis", 'fastdiag_1diag', test_fastdiag_1diag),
        ("QuickXPlain 1 Conflict", 'quickxplain_1cs', test_quickxplain_1cs),
        ("FastDiagP 1 Diagnosis", 'fastdiagp_1diag', test_fastdiagp_1diag),
        ("KBDiag 1 Diagnosis 1", 'kbdiag_1diag_1', test_kbdiag_1diag_1),
        ("KBDiag 1 Diagnosis 1 neg", 'kbdiag_1diag_1_neg', test_kbdiag_1diag_1_neg),
        ("KBDiag 1 Diagnosis 2", 'kbdiag_1diag_2', test_kbdiag_1diag_2),
        ("HS-DAG FastDiag 1 Diagnosis", 'hsdag_fastdiag_1diag', test_hsdag_fastdiag_1diag),
        ("HS-DAG FastDiag 2 Diagnoses", 'hsdag_fastdiag_2diag', test_hsdag_fastdiag_2diag),
        ("HS-DAG FastDiag All Diagnoses", 'hsdag_fastdiag_all', test_hsdag_fastdiag_all),
        ("HS-DAG QuickXPlain 1 Conflict", 'hsdag_quickxplain_1cs', test_hsdag_quickxplain_1cs),
        ("HS-DAG QuickXPlain DFS", 'hsdag_quickxplain_dfs', test_hsdag_quickxplain_one_depth_first_search),
        ("HS-DAG QuickXPlain 2 Conflicts", 'hsdag_quickxplain_2cs', test_hsdag_quickxplain_2cs),
        ("HS-DAG QuickXPlain All Conflicts", 'hsdag_quickxplain_all', test_hsdag_quickxplain_all),
        ("HS-DAG FastDiag with Config", 'hsdag_fastdiag_configuration', test_hsdag_fastdiag_with_configuration),
        ("HS-DAG QuickXPlain with Config", 'hsdag_quickxplain_configuration', test_hsdag_quickxplain_with_configuration),
        ("HS-DAG FastDiag with Test Case", 'hsdag_fastdiag_testcase', test_hsdag_fastdiag_with_test_case),
        ("HS-DAG QuickXPlain with Test Case", 'hsdag_quickxplain_testcase', test_hsdag_quickxplain_with_testcase),
        ("HS-DAG KBDiag 1 Diagnosis 1", 'hsdag_kbdiag_1diag_1', test_hsdag_kbdiag_1diag_1),
        ("HS-DAG KBDiag 1 Diagnosis 1 neg", 'hsdag_kbdiag_1diag_1_neg', test_hsdag_kbdiag_1diag_1_neg),
        ("HS-DAG KBDiag All Diagnoses 1", 'hsdag_kbdiag_all_1', test_hsdag_kbdiag_all_1),
        ("HS-DAG KBDiag All Diagnoses 1 neg", 'hsdag_kbdiag_all_1_neg', test_hsdag_kbdiag_all_1_neg),
        ("HS-DAG KBDiag 1 Diagnosis 2", 'hsdag_kbdiag_1diag_2', test_hsdag_kbdiag_1diag_2),
        ("HS-DAG KBDiag 1 Diagnosis 2 neg", 'hsdag_kbdiag_1diag_2_neg', test_hsdag_kbdiag_1diag_2_neg),
        ("HS-DAG KBDiag All Diagnoses 2", 'hsdag_kbdiag_all_2', test_hsdag_kbdiag_all_2),
        ("HS-DAG KBDiag All Diagnoses 2 neg", 'hsdag_kbdiag_all_2_neg', test_hsdag_kbdiag_all_2_neg),
        ("WipeOutR_T Redundancy", 'wipeoutr_t_redundancy', test_wipeoutr_t_redundancy),
    ]

    passed = 0
    failed = 0
    skipped = 0

    for display_name, test_key, test_func in test_functions:
        if not ENABLED_TESTS.get(test_key, True):
            print(f"\n[SKIPPED] {display_name}")
            skipped += 1
            continue

        try:
            test_func()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[FAILED] {display_name}")
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f" RESULTS: {passed} passed, {failed} failed, {skipped} skipped ".center(70, "="))
    print("=" * 70 + "\n")

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)