"""QuickXPlain single-algorithm conflict-detection tests.

Split from the former ``test_diagnosis.py`` monolith; shared config and helpers
live in ``tests.diagnosis_helpers``. Behaviour is unchanged.
"""
import pytest

from explanation.models import DiagnosisModelBuilder
from explanation.operations.algorithms.quickxplain import QuickXPlain
from explanation.operations.pysat_abstract_hsdag_explanation import _format_results
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
@_skip_disabled('quickxplain_1cs')
def test_quickxplain_1cs(name, is_incremental, solver_name, use_sat4j, enable_profiling):
    """Test QuickXPlain to find one conflict."""
    print_test_header(name, is_incremental, solver_name, use_sat4j, enable_profiling)

    with profiler_session(_profiler_preset(enable_profiling)) as profiler:
        print_profiler_status(profiler)

        model, prepared = build_prepared(DiagnosisModelBuilder
                 .from_fide(Resources.FM_INCONSISTENT)
                 )

        checker = create_checker(use_sat4j, prepared, is_incremental, solver_name)
        quickxplain = QuickXPlain(checker)
        conflict = quickxplain.find_conflict(prepared.task.set_c, prepared.task.set_b)

        profiler.print_summary(include_raw_timers=True)

        cs_mess = _format_results("Conflict", "Conflicts", [conflict], prepared.describe)
        print(f"{cs_mess}")
        assert cs_mess == 'Conflict: [(3) OR[NOT[Analog][]][NOT[Cellular][]], (4) IMPLIES[Smartwatch][Cellular], (5) IMPLIES[Smartwatch][Analog]]'
