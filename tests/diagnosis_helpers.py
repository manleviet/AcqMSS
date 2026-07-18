"""Shared configuration and helpers for the per-algorithm diagnosis suites.

Extracted from the former ``test_diagnosis.py`` monolith so each algorithm
lives in its own ``test_diagnosis_<algo>.py``. Nothing here changes behaviour:
the parameter matrices, resource paths, header printing, and checker wiring are
carried over verbatim.

``ENABLED_TESTS`` / ``ENABLED_PARAMS`` are a REAL enable/disable mechanism
(kept intentionally). ``STANDARD_PARAMS`` and friends must be importable at
module-load time because they are arguments to ``@pytest.mark.parametrize`` at
decoration time -- that is why they live in a plain module, not a fixture.
"""
import os

import pytest

from explanation.checker.backend import build_checker, SolverBackend
from explanation.models import DiagnosisModelBuilder
from explanation.models.task_preparation import PreparedTask
from profiling import ProfilerPreset

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
    'quickxplainwithtestcases_1cs_1': True,
    'quickxplainwithtestcases_1diag_1_neg': True,

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

    # HSDAG+QuickXPlainWithTestCases tests
    'hsdag_quickxplainwithtestcases_1cs_1': True,
    'hsdag_quickxplainwithtestcases_1cs_1_neg': True,
    'hsdag_quickxplainwithtestcases_all_1': True,
    'hsdag_quickxplainwithtestcases_all_1_neg': True,

    # WipeOutR_FM tests
    'wipeoutr_fm_redundancy': True,
    'pysat_redundancy_constraints': True,

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

# Argument spec shared by every @pytest.mark.parametrize below; order matches
# the tuples in the matrices and the (former) test-method signatures.
PARAM_SPEC = "name,is_incremental,solver_name,use_sat4j,enable_profiling"


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


def _get_no_sat4j_params():
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
NO_SAT4J_PARAMS = _get_no_sat4j_params()

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


def _profiler_preset(enable_profiling: bool) -> ProfilerPreset:
    """Map enable_profiling flag to ProfilerPreset."""
    return ProfilerPreset.BENCHMARK if enable_profiling else ProfilerPreset.DISABLED


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


def build_prepared(model_builder: DiagnosisModelBuilder):
    """Build the immutable KB model and derive a PreparedTask from the builder.

    Returns (model, prepared): model exposes KB data (constraint_map, ...);
    prepared bundles the pure task and its DescriptionProvider (describe).
    """
    model = model_builder.build()
    prepared = model.prepare_task(model_builder.build_task_input())
    return model, prepared


def create_checker(use_sat4j: bool, prepared: PreparedTask, is_incremental: bool, solver_name: str):
    """Create appropriate checker based on configuration.

    solver_name is threaded through to build_checker (it was dropped before, so the
    matrix's solver_name printed in the header but never reached the solver).
    """
    task = prepared.task
    config = SolverBackend.from_flags(use_incremental=is_incremental, use_sat4j=use_sat4j)
    return build_checker(task, config, solver_name)


def _skip_disabled(test_name: str):
    """Skip decorator for tests disabled in ENABLED_TESTS.

    pytest-native form of the former ``unittest.skipIf``; it attaches a marker
    without wrapping the function, so it composes cleanly with
    ``@pytest.mark.parametrize`` on module-level test functions.
    """
    return pytest.mark.skipif(
        not ENABLED_TESTS.get(test_name, True),
        reason=f'{test_name} disabled in ENABLED_TESTS',
    )
