"""Layer 3 of the T11 oracle safety net — end-to-end learned-KB golden.

Runs ConGen and QuAcq end-to-end through the oracle on REAL-FM-7 and pins the
learned KB + counts against a frozen golden recorded from the CURRENT code. This
is the brief's stated acceptance ("diagnoses / membership / completion identical
to baseline") and the only layer that exercises the algorithms *through* the
oracle. It is trustworthy because the generators are now instance-seeded
(determinism precondition) and the inputs are fixed fixtures.

Note: neither result type exposes a ``diagnoses`` attribute; the pinnable
learned-KB quantities are ``kb_assumption_ids`` (both), ``n_mss`` (ConGen only),
and ``n_kb``. QuAcq learns an empty KB even at 500 queries on this FM/bias, so
its arm pins the exact query TRAJECTORY (``query_history``) plus convergence — a
deterministic, non-trivial signal that catches a QuAcq behaviour regression even
with an empty learned KB.
"""
import pytest

from tests import t11_e2e_harness as harness
from tests.t11_oracle_net_helpers import FIXTURES_DIR, load_json

_GOLDEN_PATH = FIXTURES_DIR / "layer23_prepared_and_e2e.json"


@pytest.fixture(scope="module")
def layer3_golden():
    if not _GOLDEN_PATH.exists():
        pytest.fail(
            "golden fixture missing — the net is NOT running; "
            "run scripts/build_t11_oracle_net_fixtures.py"
        )
    return load_json(_GOLDEN_PATH)["layer3"]


def test_congen_rs_learned_kb_identical(layer3_golden):
    assert harness.run_congen(harness.EXAMPLES_RS_1N_PATH) == layer3_golden["congen_rs"]


def test_congen_ff_learned_kb_identical(layer3_golden):
    assert harness.run_congen(harness.EXAMPLES_FF_PATH) == layer3_golden["congen_ff"]


def test_quacq_learned_kb_identical(layer3_golden):
    assert harness.run_quacq() == layer3_golden["quacq"]
