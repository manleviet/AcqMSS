"""WipeOutR_FM / WipeOutR_T redundancy-detection tests.

Split from the former ``test_diagnosis.py`` monolith; shared config and helpers
live in ``tests.diagnosis_helpers``. Behaviour is unchanged.
"""
import pytest

from explanation.models import DiagnosisModelBuilder
from explanation.models.task_preparation import cf
from explanation.operations.pysat_explanation_builder import (
    PySATRedundancyConstraintsBuilder,
    PySATRedundancyTestCasesBuilder,
)
from explanation.transformations.testsuite_reader import TestSuiteReader
from profiling import profiler_session
from tests.diagnosis_helpers import (
    PARAM_SPEC,
    STANDARD_PARAMS,
    Resources,
    _profiler_preset,
    _skip_disabled,
    build_prepared,
    print_profiler_status,
    print_test_header,
)

# =============================================================================
# WIPEOUTR_FM TESTS
# =============================================================================


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('wipeoutr_fm_redundancy')
def test_wipeoutr_fm_redundancy(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test WipeOutR_FM: detect redundant constraints in feature model.

    Uses a feature model with a redundant constraint:
    - RedundantFM (root)
      - FeatureA (mandatory)
      - FeatureB (mandatory)
      - FeatureC (optional)
    - Constraint 0: RedundantFM => FeatureA (REDUNDANT - FeatureA is already mandatory)
    - Constraint 1: FeatureC <=> FeatureB (NOT redundant)
    """
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        # Load model with negated forms created during transformation
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_REDUNDANT)
                 .for_redundancy(True)
                 )

        # Verify negated constraint map is populated
        print(f"Constraint map: {list(model.constraint_map.keys())}")
        print(f"Negated constraint map: {list(model.negated_constraint_map.keys())}")
        assert len(model.negated_constraint_map) > 0, "Negated constraint map should be populated"

        # Get constraint IDs and negation map
        set_cf = cf(prepared.task)
        negation_map = prepared.task.negation_map

        print(f"CF (constraint IDs): {set_cf}")
        print(f"negation_map: {negation_map}")
        assert len(set_cf) > 0, "Should have constraints"
        assert len(negation_map) > 0, "Should have negated forms"

        builder = None if use_sat4j else PySATRedundancyConstraintsBuilder.for_redundancy_constraints(profiler)
        if builder is None:
            return

        operation = builder.build()
        operation.use_incremental = is_incremental
        operation.execute(prepared)

        # Get results
        result = operation.get_result()

        print(result)

        profiler.print_summary(include_raw_timers=True)

        assert len(result) == 2, f"Expected 2 lists (redundant and non-redundant), got {len(result)}"
        assert result[0] == 'Redundant constraints: [(Constraint 0) IMPLIES[RedundantFM][FeatureA]]'
        assert result[1] == 'Non-redundant constraints: [(Constraint 1) OR[NOT[FeatureC][]][NOT[FeatureB][]], (optional) RedundantFM[0,1]FeatureC, (mandatory) RedundantFM[1,1]FeatureB, (mandatory) RedundantFM[1,1]FeatureA]'


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('pysat_redundancy_constraints')
def test_pysat_redundancy_constraints(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test PySATRedundancyConstraints operation using WipeOutR_FM algorithm.

    Uses a feature model with a redundant constraint:
    - RedundantFM (root)
      - FeatureA (mandatory)
      - FeatureB (mandatory)
      - FeatureC (optional)
    - Constraint 0: RedundantFM => FeatureA (REDUNDANT - FeatureA is already mandatory)
    - Constraint 1: FeatureC <=> FeatureB (NOT redundant)

    This test verifies the PySATRedundancyConstraints operation wrapper.
    """
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        # Load model with negated forms created during transformation
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_REDUNDANT)
                 .for_redundancy(True)
                 )

        # Verify negated constraint map is populated
        print(f"Constraint map: {list(model.constraint_map.keys())}")
        print(f"Negated constraint map: {list(model.negated_constraint_map.keys())}")
        assert len(model.negated_constraint_map) > 0, "Negated constraint map should be populated"

        # Create and configure the operation using builder
        builder = None if use_sat4j else PySATRedundancyConstraintsBuilder.for_redundancy_constraints(profiler)
        if builder is None:
            return
        operation = builder.build()

        # Execute the operation
        operation.use_incremental = is_incremental
        operation.execute(prepared)

        # Get results
        redundant = operation.get_redundant()
        non_redundant = operation.get_non_redundant()

        # Print formatted messages
        for msg in operation.get_result():
            print(msg)

        profiler.print_summary(include_raw_timers=True)

        # Verify results
        print(f"Found {len(redundant)} redundant and {len(non_redundant)} non-redundant constraints")

        # The constraint "RedundantFM => FeatureA" should be detected as redundant
        assert len(redundant) >= 1, f"Expected at least 1 redundant constraint, got {len(redundant)}"

        # Verify total count matches
        assert len(redundant) + len(non_redundant) == len(prepared.task.set_c), \
            "Total redundant + non-redundant should equal all constraints"

        assert operation.get_result()[0] == 'Redundant constraints: [(Constraint 0) IMPLIES[RedundantFM][FeatureA]]'
        assert operation.get_result()[1] == 'Non-redundant constraints: [(Constraint 1) OR[NOT[FeatureC][]][NOT[FeatureB][]], (optional) RedundantFM[0,1]FeatureC, (mandatory) RedundantFM[1,1]FeatureB, (mandatory) RedundantFM[1,1]FeatureA]'

# =============================================================================
# WIPEOUTR_T TESTS
# =============================================================================


@pytest.mark.parametrize(PARAM_SPEC, STANDARD_PARAMS)
@_skip_disabled('wipeoutr_t_redundancy')
def test_wipeoutr_t_redundancy(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test PySATRedundancyTestCases operation using WipeOutR_T algorithm.

    Uses the same test suite as test_wipeoutr_t_redundancy:
    - t1: FeatureA = true (REDUNDANT - covered by t3)
    - t2: FeatureC = false (NOT redundant)
    - t3: FeatureA = true, FeatureB = true (more specific than t1)

    This test verifies the PySATRedundancyTestCases operation wrapper.
    """
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        testsuite = TestSuiteReader(Resources.REDUNDANT_TESTSUITE).transform()
        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_uvl(Resources.FM_REDUNDANT)
                 .with_testcases(testsuite)
                 )

        print(f"Test suite has {len(testsuite.testcases)} test cases")
        for i, tc in enumerate(testsuite.testcases):
            print(f"  t{i + 1}: {tc}")

        builder = None if use_sat4j else PySATRedundancyTestCasesBuilder.for_redundancy_test_cases(profiler)
        if builder is None:
            return

        operation = (builder
                     .build())
        operation.use_incremental = is_incremental
        operation.execute(prepared)

        # Get results
        result = operation.get_result()

        print(result)
        profiler.print_summary(include_raw_timers=True)

        assert len(result) == 2, f"Expected 2 lists (redundant and non-redundant), got {len(result)}"
        assert result[0] == 'Redundant test cases: [FeatureA=true]', "Expected 'FeatureA = true' to be redundant"
        assert result[1] == 'Non-redundant test cases: [FeatureC=false, FeatureA=true & FeatureB=true]', \
            "Expected 'FeatureC = false' and 'FeatureA = true & FeatureB = true' to be non-redundant"


def test_wipeoutr_t_single_or_empty_testcase_reads_frozen_tuple():
    """WipeOutR_T's <=1-testcase early return must not assume a list.

    ``PySATRedundancyTestCases`` feeds ``task.set_tc`` — a deep-frozen *tuple*
    (``TestCaseTask.__post_init__`` coerces list->tuple) — into
    ``find_redundant_testcases``. The early return copied it with ``.copy()``,
    which a tuple does not have (``AttributeError``). Only the <=1 branch touched
    it and no test exercised that branch, so the suite stayed green after the
    deep-freeze. Passing a tuple — as production always does — is what makes this
    bite; a list would ``.copy()`` cleanly and hide the defect.
    """
    from explanation.operations.algorithms.wipeoutr_t import WipeOutR_T
    from explanation.models.task_preparation import TestCaseTask

    wipeoutr = WipeOutR_T(checker=None)  # checker is untouched on the <=1 branch
    for ids in ([], [7]):
        task = TestCaseTask(set_tc=ids)
        assert isinstance(task.set_tc, tuple)  # freeze precondition
        redundant, non_redundant = wipeoutr.find_redundant_testcases(
            task.set_tc, task.negation_map)
        assert redundant == []                   # nothing redundant with <=1 case
        assert list(non_redundant) == list(ids)  # content preserved (behaviour-inert)
