"""AcqMSS check accounting: the batch counter and the atomic counter measure
different things, and the atomic one must actually count solver calls.

``shared_admpool_checks`` counts +1 per ``is_consistent_test_cases`` call — one per
AdmPoolMSS node. But that call issues ONE solver call per positive when
``stop_at_first_violation=False`` (explanation/checker/backend.py), so the batch
number understates the real work by |E′⁺| per node. ``shared_admpool_solver_calls``
counts the atomic solves, so the two are in different units and must never be summed.

The expected value is derived INDEPENDENTLY here — a spy checker adds up ``len(set_tc)``
across every call — rather than re-reading the profiler, so a counter that increments
by the wrong amount cannot satisfy the assertion by agreeing with itself.
"""

import json
from pathlib import Path

import pytest

from conacq.algorithms import AcqMSS, ConGenModelBuilder, ConGenTaskInput
from conacq.oracle import FMOracle
from explanation.checker.backend import build_checker, SolverBackend
from profiling import profiler_session, ProfilerPreset

DATA_DIR = Path(__file__).parent.parent / "data"
FM_PATH = DATA_DIR / "fms" / "REAL-FM-7.uvl"
BIAS_PATH = DATA_DIR / "bias" / "REAL-FM-7-bias.json"
EXAMPLES_PATH = DATA_DIR / "examples" / "REAL-FM-7_rs_1n.json"


class _PositiveCountingChecker:
    """Delegating checker that totals the positives handed to each batch check."""

    def __init__(self, inner):
        self._inner = inner
        self.batch_calls = 0
        self.positives_seen = 0

    def is_consistent_test_cases(self, set_c, set_tc, stop_at_first_violation):
        self.batch_calls += 1
        self.positives_seen += len(set_tc)
        return self._inner.is_consistent_test_cases(
            set_c, set_tc, stop_at_first_violation)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def _run_acqmss():
    """Run AcqMSS over REAL-FM-7 rs_1n (|E+| > 1, |B| = 295 ⇒ many recursion levels)."""
    oracle = FMOracle(str(FM_PATH), use_incremental=False)
    model = (ConGenModelBuilder.from_bias(str(BIAS_PATH))
             .with_oracle_data(oracle.oracle_data).build())
    ex = json.loads(EXAMPLES_PATH.read_text())
    pos = [e["assignments"] for e in ex["positive"]]
    neg = [e["assignments"] for e in ex["negative"]]
    task = model.prepare_task(
        ConGenTaskInput.from_examples(oracle.oracle_data, pos, neg)).task

    with profiler_session(ProfilerPreset.BENCHMARK) as profiler:
        checker = build_checker(
            task, SolverBackend.PYSAT_NON_INCREMENTAL, 'glucose4', profiler)
        spy = _PositiveCountingChecker(checker)
        try:
            AcqMSS(spy, profiler_instance=profiler).find_mss(
                delta=list(task.set_c), set_b=list(task.set_c),
                set_neg_tv=list(task.set_neg_tv), set_tc=list(task.set_tc),
                set_bg=list(task.set_b))
            return spy, len(task.set_tc), {
                'batch': profiler.get_metric('shared_admpool_checks', 0),
                'atomic': profiler.get_metric('shared_admpool_solver_calls', 0),
            }
        finally:
            checker.cleanup()


@pytest.mark.skipif(not FM_PATH.exists() or not BIAS_PATH.exists()
                    or not EXAMPLES_PATH.exists(),
                    reason="REAL-FM-7 fixtures not found")
def test_admpool_solver_calls_counts_positives_not_nodes():
    """The atomic counter equals the positives actually handed to the solver."""
    spy, n_positives, counters = _run_acqmss()

    assert n_positives > 1, "fixture must supply |E+| > 1 or the two units coincide"
    assert spy.batch_calls > 1, "fixture must recurse or there is nothing to accumulate"

    # Independently derived expectation — not read back off the profiler.
    assert counters['atomic'] == spy.positives_seen

    # The two counters are in different units. This is what goes red if the atomic
    # increment is ever changed to a plain +1: it would collapse onto the batch count.
    assert counters['atomic'] != counters['batch']
    assert counters['atomic'] > counters['batch']


@pytest.mark.skipif(not FM_PATH.exists() or not BIAS_PATH.exists()
                    or not EXAMPLES_PATH.exists(),
                    reason="REAL-FM-7 fixtures not found")
def test_admpool_batch_counter_still_counts_nodes():
    """The batch counter is unchanged: one per AdmPoolMSS check, not per solve.

    Pins the additive contract from the other side — adding the atomic counter must
    not perturb the batch one that ConGen and ConMin already report.
    """
    spy, _, counters = _run_acqmss()
    assert counters['batch'] == spy.batch_calls
