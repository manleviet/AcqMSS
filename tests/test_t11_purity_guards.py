"""Layer 4 + A6 of the T11 oracle safety net — purity/structure guards.

Each guard pins a STATED goal of the oracle arc so it cannot be quietly dropped.
A guard is written as ``xfail(strict=True)`` while its property does not yet hold;
``strict=True`` means the day it flips green (an xpass) the suite fails loudly, so
the flip is never missed. When a sub-change lands, its guard is turned into a
plain assertion — a permanent regression guard. Job ② leaving the oracle facade
(``test_oracle_does_not_provision``), the frozen ``OracleData`` snapshot, and the
two guards that came with the A6 symptom fix — no post-build mutator, no cached
base-set_c bridge — have landed and are permanent. The behavioural A6 guard is
NOT retired: it is moved onto the new surface
(``test_oracle_background_is_invariant_across_queries`` reads ``oracle_data.get_c()``
= the task's set_c), because ``frozen=True`` blocks rebinding that field, not
mutating its contents in place — so the invariant still needs a live guard (the A5
lesson).

``test_oracle_holds_no_provisioning_object`` (the arrangement guard, stronger than
the facade one) landed once ``FMOracleModel`` became a pure KB and stopped being a
KBProvider. ``test_prepare_task_is_unified_across_models`` and
``test_no_call_prepare_first_runtime_error_in_source`` landed once all three conacq
models (FMOracle · QuAcq · ConGen) carry the pure ``prepare_task`` and shed the
call-ordering RuntimeError — now permanent regression guards. The remaining two
xfails flip at their own sub-changes: GenerateNE's relocation and
``complete_configuration``'s single-solver reuse.

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
# A6 — the class-level cure: the oracle answers, it does not provision
# ---------------------------------------------------------------------------
def test_oracle_does_not_provision(oracle):
    """The oracle FACADE answers questions; it does not provision the algorithm.

    Job ② (kb/assumptions/c/bg_data/root_clauses) lives on the frozen
    ``OracleData`` snapshot, never on the oracle's own surface — so consumers that
    depend on a provisioning protocol cannot bind to the live oracle. The day the
    oracle satisfies either provisioning protocol again, job ② has leaked back
    onto the actor and the door to the next A6 is open (ADR-0009).

    This checks the facade only. That the oracle does not *hold* a live
    provisioning object is a stronger property, guarded separately by
    ``test_oracle_holds_no_provisioning_object`` (flips at T11.4b)."""
    from conacq.oracle import BGProvider, KBProvider
    assert not isinstance(oracle, KBProvider)
    assert not isinstance(oracle, BGProvider)


def test_oracle_holds_no_provisioning_object(oracle):
    """The arrangement, not just the facade: the oracle holds NO live object that
    can provision. A clean facade with ``oracle._oracle_model`` still a KBProvider
    would leave job ② one attribute-access away — exactly the arrangement ADR-0009
    removes. Now enforced: the T3 recipe stripped the model's provisioning getters,
    so the held ``_oracle_model`` is no longer a KBProvider. ``oracle_data`` is the
    frozen snapshot and is meant to be held, so it is exempt. Permanent guard."""
    from conacq.oracle import BGProvider, KBProvider
    for name, val in vars(oracle).items():
        if name == "oracle_data":  # the frozen provisioning snapshot — by design
            continue
        assert not isinstance(val, (KBProvider, BGProvider)), (
            f"oracle holds a live provisioning object at .{name}"
        )


def test_oracle_background_is_invariant_across_queries(oracle):
    """The background the checker sees (``oracle_data.get_c()`` = the task's set_c)
    must not shift across membership queries — a query must never leak into the
    facts the acquisition algorithm treats as true. ``frozen=True`` blocks
    REBINDING the field, not MUTATING its contents in place (``.append(...)`` would
    still run), so a future ``is_valid`` that did ``set_c.extend(...)`` instead of
    ``set_c + ...`` would poison the background exactly like A6, silently. Permanent
    guard for that invariant — moved onto the new surface, not retired."""
    before = list(oracle.oracle_data.get_c())
    feats = sorted(oracle.get_variables())
    rng = random.Random(1)
    for _ in range(50):
        oracle.is_valid({f: rng.choice([True, False]) for f in feats})
    assert oracle.oracle_data.get_c() == before


# ---------------------------------------------------------------------------
# Layer 4 — purity & structure
# ---------------------------------------------------------------------------
def test_oracle_model_has_no_configuration_mutator():
    """The oracle model exposes no post-build mutator: nothing rebinds its task,
    so no query can shift the state a later reader sees. Permanent guard against
    reopening that seam."""
    from conacq.oracle.fm_oracle_model import FMOracleModel
    assert not hasattr(FMOracleModel, "with_configuration")


def test_no_fat_oracle_abc():
    """T11.1's own target: the fat ``Oracle`` ABC is gone. It promised a minimal
    membership interface yet carried an ``ask`` alias and two None-returning stubs
    (``get_variables``/``complete_configuration``) — a base class that hands out
    methods it fakes to None. The oracle world is now typed on the narrow
    ``@runtime_checkable`` protocols (MembershipOracle/CompletableOracle/
    CatalogProvider/GeneratorOracle), so a consumer binds to the 1-3 methods it
    actually needs, not to a class that lies about its surface. Permanent guard
    against a fourth recurrence of the add-new-keep-old shape (after the
    ``with_negation`` no-op and the hardcoded GenerateNE adapter)."""
    import conacq.oracle as oracle_pkg
    from conacq.algorithms import quacq as quacq_pkg
    assert not hasattr(oracle_pkg, "Oracle"), "fat Oracle ABC still exported from conacq.oracle"
    assert "Oracle" not in getattr(oracle_pkg, "__all__", [])
    assert not hasattr(quacq_pkg, "Oracle"), "fat Oracle ABC still re-exported from conacq.algorithms.quacq"


def test_declaring_a_role_without_implementing_it_fails_at_construction():
    """The good half of the deleted fat ABC, restored via ``@abstractmethod`` on the
    narrow protocol members (ADR-0010): a class that DECLARES a role by inheriting
    its protocol but never implements the method is abstract — it raises TypeError
    at construction, not silently at the first query deep in QuAcq's inner loop after
    the eval has been running (the A6 shape: fails silently, no exception, no red
    test). This is the machine-checked half; the class-line declaration is the point
    (ADR-0010). Permanent guard."""
    from conacq.oracle import MembershipOracle

    class ForgotIsValid(MembershipOracle):
        pass

    with pytest.raises(TypeError):
        ForgotIsValid()


def test_prepare_task_is_unified_across_models():
    from explanation.models.pysat_diagnosis_model import DiagnosisModel
    from conacq.algorithms.acqmss.congen_model import ConGenModel
    from conacq.algorithms.quacq.quacq_model import QuAcqModel
    from conacq.oracle.fm_oracle_model import FMOracleModel

    for model in (DiagnosisModel, ConGenModel, QuAcqModel, FMOracleModel):
        assert hasattr(model, "prepare_task"), f"{model.__name__} lacks prepare_task"
        params = list(inspect.signature(model.prepare_task).parameters)
        assert params == ["self", "task_input"], f"{model.__name__}: {params}"


def test_oracle_data_snapshot_is_frozen():
    """Job ② is an immutable value: OracleData is a frozen dataclass, so nothing
    a query does can rebind what the provisioning consumers read. Permanent
    guard (landed with the role split)."""
    from conacq.oracle import OracleData
    assert OracleData.__dataclass_params__.frozen


def test_base_set_c_is_gone_from_source():
    """The cached base-set_c bridge is gone from the oracle source; set_c is read
    from the frozen task. Permanent guard."""
    hits = _grep_source("base_set_c")
    assert hits == [], "base_set_c still present:\n  " + "\n  ".join(hits)


def test_no_call_prepare_first_runtime_error_in_source():
    hits = _grep_source("Call prepare() first")
    assert hits == [], "call-ordering RuntimeError still present:\n  " + "\n  ".join(hits)


def test_generate_ne_not_exported_from_algorithms():
    """GenerateNE is a task-preparation internal — its only production caller is
    ConGenTaskPreparation and it is not in the solve loop — not an algorithm. It must
    be absent from BOTH algorithm facades (top-level ``conacq.algorithms`` and the
    ``conacq.algorithms.acqmss`` subpackage), checked at BOTH levels:

    - the LABEL — ``__all__``, which only governs ``import *``; and
    - the DOOR — the bound attribute. ``from pkg import GenerateNE`` works off the
      module's ``from .generate_ne import GenerateNE`` statement, NOT ``__all__``, so
      a re-added import binding that never touches ``__all__`` would leave the label
      clean while the door swings open. Checking only the label is the same
      one-symbol-watched / wrong-symbol-lives-on hole; this mirrors the fat-ABC guard,
      which pins ``not hasattr(...)`` and ``not in __all__`` both."""
    import conacq.algorithms as algorithms
    import conacq.algorithms.acqmss as acqmss
    for pkg in (algorithms, acqmss):
        assert "GenerateNE" not in getattr(pkg, "__all__", []), f"GenerateNE in {pkg.__name__}.__all__ (label)"
        assert not hasattr(pkg, "GenerateNE"), f"GenerateNE bound on {pkg.__name__} (door)"


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
