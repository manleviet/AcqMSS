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
call-ordering RuntimeError — now permanent regression guards. GenerateNE's
relocation flipped its guard too. No xfails remain: the last one was DELETED rather
than flipped, because its target — completion reusing one persistent solver — is a
behaviour change (a persistent solver returns different completion witnesses → a
different dataset), not a refactor (ADR-0011).

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
    from conacq.oracle.fm.model import FMOracleModel
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


def test_fm_oracle_model_does_not_build_itself():
    """T6's goal: all four models have an external builder and none builds itself.
    FMOracleModel was the last self-builder — ``from_fm``/``build`` lived on the model
    — and those move to ``FMOracleModelBuilder`` (inheriting AbstractModelBuilder like
    the other three). The model is a pure KB: it holds data, it does not know how to
    load an FM. Permanent guard against the self-build smell returning."""
    from conacq.oracle import FMOracleModel
    assert not hasattr(FMOracleModel, "from_fm"), "FMOracleModel still self-builds (from_fm)"
    assert not hasattr(FMOracleModel, "build"), "FMOracleModel still self-builds (build)"


def test_fm_oracle_has_no_dead_metadata_getters():
    """The API diet (T11.4c): FMOracle's five zero-consumer metadata getters are gone.
    ``get_fm_data`` was the dead root; it alone called ``get_root_feature`` /
    ``get_num_constraints`` / ``get_next_available_id``, and ``get_cnf_clauses`` had
    only the net helper. Their sole reader was the T11 net itself — which was keeping
    a dead API alive — so the five golden keys are dropped WITH the methods (the one
    sanctioned golden-key drop; the drop IS this commit's purpose). Mechanism check
    (hasattr), not ``__all__``. Permanent guard against the dead surface returning."""
    from conacq.oracle import FMOracle
    for name in ("get_fm_data", "get_root_feature", "get_num_constraints",
                 "get_next_available_id", "get_cnf_clauses"):
        assert not hasattr(FMOracle, name), f"FMOracle still exposes dead getter {name}"


def test_one_task_preparation_strategy_and_no_dead_mode_name():
    """The twin prep-strategy ABCs collapse to one ``TaskPreparationStrategy``, and
    the dead ``mode_name`` is gone from all three concrete strategies. ``mode_name``
    had 0 call sites — the ABC forced every implementer to supply something nobody
    read (the inverse of ADR-0010, where the fat ABC carried real enforcement).
    Checked at the DOOR (attribute) AND the LABEL (__all__), per the 4c2 lesson."""
    import explanation.api as api
    from explanation.models.task_preparation import (
        DiagnosisTaskPreparation, TestCaseTaskPreparation)
    from conacq.algorithms.acqmss.task_preparation import ConGenTaskPreparation

    for name in ("TestCaseTaskPreparationStrategy", "DiagnosisTaskPreparationStrategy"):
        assert not hasattr(api, name), f"{name} still exported (door)"
        assert name not in getattr(api, "__all__", []), f"{name} still in api.__all__ (label)"
    assert hasattr(api, "TaskPreparationStrategy"), "the merged ABC is not exported"
    for cls in (DiagnosisTaskPreparation, TestCaseTaskPreparation, ConGenTaskPreparation):
        assert not hasattr(cls, "mode_name"), f"{cls.__name__} still carries the dead mode_name"


def test_no_post_negation_build_hook():
    """The 0-override ``_post_negation_build`` hook is gone. Its docstring reserved it
    for folding a frozen OracleData snapshot at build time — 4c shipped and never
    used it; the reservation expired. T6: a 0-override hook that survives one more
    task starts to grow roots. Permanent guard."""
    from conacq.oracle_bias_model_builder import OracleBiasModelBuilder
    assert not hasattr(OracleBiasModelBuilder, "_post_negation_build")


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
    from conacq.oracle.fm.model import FMOracleModel

    for model in (DiagnosisModel, ConGenModel, QuAcqModel, FMOracleModel):
        assert hasattr(model, "prepare_task"), f"{model.__name__} lacks prepare_task"
        params = list(inspect.signature(model.prepare_task).parameters)
        assert params == ["self", "task_input"], f"{model.__name__}: {params}"


def test_every_prepare_strategy_inherits_the_contract():
    """Population sweep — the guard that watches the author, not a remembered list.

    AST-scan explanation/ + conacq/ for EVERY class defining a method named
    ``prepare`` that returns ``PreparedTask``, then assert each is a subclass of
    ``TaskPreparationStrategy``. It names no concrete strategy in its assertion: it
    enumerates the population by the contract's own shape, so a strategy added later
    that forgets to inherit is caught without editing this test.

    Two exclusions, both by MECHANISM, not by a by-name exception list:
      - ``issubclass`` is reflexive, so ``TaskPreparationStrategy`` itself passes free.
      - the filter is the method NAME ``prepare`` + a ``PreparedTask`` return, so
        ``prepare_task`` (the MODEL contract, guarded by
        ``test_prepare_task_is_unified_across_models``) and ``build_oracle_data``
        (``-> OracleData``, a different operation) drop out on their own.

    Why it exists: the model-layer guard above checks ``prepare_task`` and never saw
    ``QuAcqTaskPreparation``'s drifted strategy signature. This guard watches the
    strategy layer the model-layer guard is blind to. Permanent guard."""
    import ast
    import importlib
    import pathlib

    from explanation.api import TaskPreparationStrategy

    repo = pathlib.Path(__file__).resolve().parent.parent
    checked = []
    offenders = []
    for pkg in ("explanation", "conacq"):
        for path in (repo / pkg).rglob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for item in node.body:
                    if (isinstance(item, ast.FunctionDef)
                            and item.name == "prepare"
                            and item.returns is not None
                            and "PreparedTask" in ast.unparse(item.returns)):
                        module = ".".join(path.relative_to(repo).with_suffix("").parts)
                        cls = getattr(importlib.import_module(module), node.name)
                        checked.append(node.name)
                        if not issubclass(cls, TaskPreparationStrategy):
                            offenders.append(f"{node.name} ({module})")
    assert checked, "population scan found no prepare()->PreparedTask classes — the scan itself is broken"
    assert not offenders, (
        "classes with prepare()->PreparedTask that do not inherit TaskPreparationStrategy: "
        + ", ".join(offenders))


def test_quacq_strategy_signature_matches_the_contract():
    """QuAcqTaskPreparation.prepare takes (self, model, task_input) like every other
    strategy — not (self, model, oracle_data). The drift existed because prepare_task
    unpacked task_input.oracle_data before handing it down; the strategy now receives
    the whole QuAcqTaskInput and extracts oracle_data itself. Permanent guard."""
    from conacq.algorithms.quacq.task_preparation import QuAcqTaskPreparation
    params = list(inspect.signature(QuAcqTaskPreparation.prepare).parameters)
    assert params == ["self", "model", "task_input"], params


def test_fm_oracle_task_prep_has_no_prepare_name_collision():
    """FMOracleTaskPreparation is a static two-view factory, NOT a strategy: forcing it
    to inherit TaskPreparationStrategy is wrong — its task view ``prepare_task`` is a
    @staticmethod with no ``task_input`` (measured: it does not fit the contract). The
    only defect was the NAME — ``prepare() -> OracleData`` collided with the strategy's
    ``prepare() -> PreparedTask``. Renamed to ``build_oracle_data()``; ``prepare_task``
    survives. Permanent guard against the collision returning."""
    from conacq.oracle.fm.task_preparation import FMOracleTaskPreparation
    assert not hasattr(FMOracleTaskPreparation, "prepare"), "the colliding prepare name is still present"
    assert hasattr(FMOracleTaskPreparation, "build_oracle_data"), "the renamed job-② factory is missing"
    assert hasattr(FMOracleTaskPreparation, "prepare_task"), "the PreparedTask view was lost"


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


# ---------------------------------------------------------------------------
# T11b.0 — the deferred deep-immutable-Task ratchet (flips at T13)
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason="Task is shallow-frozen; deep-freeze lands with T13 (its blast radius is "
           "the labeler tree T13 restructures — 13 .copy() sites, 10 in hsdag/labeler/)",
)
def test_task_is_deeply_frozen():
    """The Task family must become deeply immutable: the list-valued solve fields
    become tuples that reject in-place mutation, so a task cannot be poisoned after
    construction — the same silent-drift class the oracle arc kept killing. RED today
    (Task is only shallow-frozen: ``set_c.append`` succeeds — pinned as the current
    contract by ``test_task_is_only_shallow_frozen``).

    Written NOW, at the moment of deferral, not at T13 when the work is done: a
    deferral without a ratchet is a wish, and the brief that holds the promise is
    deleted at project close, so a promise living only there evaporates by
    construction (T11b design §1). T13 flips this (removes the marker) and deletes
    ``test_task_is_only_shallow_frozen`` in the same change.

    Safe to write despite the T11.5 lesson — a red xfail can still be *wrong* (that
    one demanded solver reuse, which silently changed 18/20 witnesses). The
    difference, measured before authorising this ratchet: a missed deep-freeze site
    calls ``tuple.append``/``tuple.copy`` and raises AttributeError AT THE CALL — a
    loud failure, not a silently-different result. (``negation_map`` stays a dict:
    MappingProxyType does not pickle, which would break FastDiagP's multiprocessing.)"""
    from explanation.models.task_preparation import DiagnosisTask, TestCaseTask
    from conacq.algorithms.acqmss.task_preparation import ConGenTask
    from conacq.algorithms.quacq.task_preparation import QuAcqTask

    for task_cls in (DiagnosisTask, TestCaseTask, ConGenTask, QuAcqTask):
        task = task_cls(set_c=[1])
        with pytest.raises((TypeError, AttributeError)):
            task.set_c.append(999)  # a tuple rejects this; a list (today) does not


