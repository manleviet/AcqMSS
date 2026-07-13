"""Layer 4 + A6 of the T11 oracle safety net — purity/structure guards.

Each guard pins a STATED goal of the oracle arc so it cannot be quietly dropped.
A guard is written as ``xfail(strict=True)`` while its property does not yet hold;
``strict=True`` means the day it flips green (an xpass) the suite fails loudly, so
the flip is never missed. When a sub-change lands, its guard is turned into a
plain assertion — a permanent regression guard. The get_c-invariance guard (the
one intended behaviour change) and the two that come with it — no post-build
mutator, no cached base-set_c bridge — have landed and are permanent; the
remaining five stay xfail until their sub-changes arrive.

Reasons describe the invariant that flips the guard, not a plan label (plan
headers get renumbered; the behavioural target is stable).
"""
import inspect
from pathlib import Path
import random

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONACQ_DIR = REPO_ROOT / "conacq"
EXPLANATION_DIR = REPO_ROOT / "explanation"


def _grep_source(needle, roots=(CONACQ_DIR, EXPLANATION_DIR)):
    """Every `path:line` under roots (excluding bytecode) whose line contains needle."""
    hits = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if needle in line:
                    hits.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    return hits


# ---------------------------------------------------------------------------
# A6 — the one intended behaviour change: get_c() must stop tracking the last query
# ---------------------------------------------------------------------------
def test_get_c_is_invariant_across_queries(oracle):
    """get_c() stays constant across membership queries — a query must never leak
    into the background the oracle hands downstream. Now enforced (the oracle
    computes each query's set_c locally); permanent regression guard."""
    before = list(oracle.get_c())
    feats = sorted(oracle.get_variables())
    rng = random.Random(1)
    for _ in range(50):
        oracle.is_valid({f: rng.choice([True, False]) for f in feats})
    assert oracle.get_c() == before


# ---------------------------------------------------------------------------
# Layer 4 — purity & structure
# ---------------------------------------------------------------------------
def test_oracle_model_has_no_configuration_mutator():
    """The oracle model exposes no post-build mutator: nothing rebinds its task,
    so no query can shift the state a later reader sees. Permanent guard against
    reopening that seam."""
    from conacq.oracle.fm_oracle_model import FMOracleModel
    assert not hasattr(FMOracleModel, "with_configuration")


@pytest.mark.xfail(
    strict=True,
    reason="the four models still have divergent prepare signatures; they must "
           "unify on prepare_task(self, task_input) -> PreparedTask",
)
def test_prepare_task_is_unified_across_models():
    from explanation.models.pysat_diagnosis_model import DiagnosisModel
    from conacq.algorithms.acqmss.congen_model import ConGenModel
    from conacq.algorithms.quacq.quacq_model import QuAcqModel
    from conacq.oracle.fm_oracle_model import FMOracleModel

    for model in (DiagnosisModel, ConGenModel, QuAcqModel, FMOracleModel):
        assert hasattr(model, "prepare_task"), f"{model.__name__} lacks prepare_task"
        params = list(inspect.signature(model.prepare_task).parameters)
        assert params == ["self", "task_input"], f"{model.__name__}: {params}"


@pytest.mark.xfail(
    strict=True,
    reason="no frozen OracleData snapshot exists yet; prepare_task still needs a "
           "live oracle threaded through the caller",
)
def test_oracle_data_snapshot_is_frozen():
    from conacq.oracle import OracleData  # noqa: F401 — absent today
    assert OracleData.__dataclass_params__.frozen


def test_base_set_c_is_gone_from_source():
    """The cached base-set_c bridge is gone from the oracle source; set_c is read
    from the frozen task. Permanent guard."""
    hits = _grep_source("base_set_c")
    assert hits == [], "base_set_c still present:\n  " + "\n  ".join(hits)


@pytest.mark.xfail(
    strict=True,
    reason="models still raise a call-ordering RuntimeError; a pure model built "
           "eagerly has no 'call prepare() first' gate",
)
def test_no_call_prepare_first_runtime_error_in_source():
    hits = _grep_source("Call prepare() first")
    assert hits == [], "call-ordering RuntimeError still present:\n  " + "\n  ".join(hits)


@pytest.mark.xfail(
    strict=True,
    reason="GenerateNE is still exported from conacq.algorithms; it belongs behind "
           "the acquisition workflow, not the package facade",
)
def test_generate_ne_not_exported_from_algorithms():
    import conacq.algorithms as algorithms
    assert "GenerateNE" not in getattr(algorithms, "__all__", [])


@pytest.mark.xfail(
    strict=True,
    reason="complete_configuration rebuilds its SAT solver on every call; it must "
           "reuse a single solver across calls",
)
def test_complete_configuration_builds_solver_once(oracle, monkeypatch):
    import conacq.oracle.fm_oracle as fm_oracle_module

    constructions = {"n": 0}
    real_solver = fm_oracle_module.Solver

    def counting_solver(*args, **kwargs):
        constructions["n"] += 1
        return real_solver(*args, **kwargs)

    monkeypatch.setattr(fm_oracle_module, "Solver", counting_solver)

    partial = {sorted(oracle.get_variables())[0]: True}
    oracle.complete_configuration(partial)
    oracle.complete_configuration(partial)
    assert constructions["n"] == 1
