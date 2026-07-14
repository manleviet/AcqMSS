"""Safety net pinning the assumption-ID layout produced by every slice site.

The five ``_assign_sets`` / FM-only slice sites carve set_b / set_c / set_tc /
set_tv out of the flat ``assumptions`` list by offset+stride arithmetic. That
arithmetic determines which assumption literal ends up in which set, so the
whole system's diagnoses depend on it being byte-identical.

These tests pin the EXACT output IDs (length + boundary values + stride) for
controlled inputs BEFORE the arithmetic is refactored behind a shared
``slice_assumptions`` helper. Same inputs → same IDs must hold after the
refactor; a red test means the ID layout drifted. This net also guards the
future AssumptionIdAllocator work.

The four ``_assign_sets`` methods are pure functions of (assumptions, indices,
flags), so they are exercised directly with synthetic lists (values = 100+index,
etc., making the picked indices obvious). Site 5 (an inline slice) is pinned via
a synthetic ``FMOracleModel.prepare()``, plus one real end-to-end anchor through
a transformed feature model.
"""
from flamapy.metamodels.fm_metamodel.transformations import UVLReader

from explanation.models.task_preparation import (
    DiagnosisTaskPreparation,
    # Aliased: leading-"Test" name would trip pytest's class collector.
    TestCaseTaskPreparation as _TestCaseTaskPreparation,
    TaskInput,
)
from explanation.transformations.fm_to_diag_pysat import FmToDiagPysat
from conacq.algorithms.acqmss.task_preparation import ConGenTaskPreparation
from conacq.algorithms.quacq.task_preparation import QuAcqTaskPreparation
from conacq.oracle.fm_oracle_model import FMOracleModel
from tests.resource_paths import DATA_DIR


def _strided(seq):
    """True iff seq is a constant-stride arithmetic sequence (len < 2 → True)."""
    return all(seq[k + 1] - seq[k] == seq[1] - seq[0] for k in range(len(seq) - 1))


# ---------------------------------------------------------------------------
# Site 1 — DiagnosisTaskPreparation._assign_sets  (5 branches, both stride modes)
# assumptions[i] == 100 + i
# ---------------------------------------------------------------------------
_A16 = list(range(100, 116))


def test_site1_config_no_cf_stride2():
    """C = configuration, B = FM + root (step=2 with negated forms)."""
    dia = DiagnosisTaskPreparation()
    set_b, set_c = dia._assign_sets(_A16, TaskInput(configuration={"x": True}), 6, 6, True)
    assert set_b == [100, 102, 104]
    assert set_c == [106, 107, 108, 109, 110, 111, 112, 113, 114, 115]


def test_site1_config_with_cf_stride2():
    """C = configuration + FM, B = root only."""
    dia = DiagnosisTaskPreparation()
    set_b, set_c = dia._assign_sets(
        _A16, TaskInput(configuration={"x": True}, with_cf_in_c=True), 6, 6, True)
    assert set_b == [100]
    assert set_c == [102, 104] + list(range(106, 116))


def test_site1_test_case_stride2():
    """C = FM constraints, B = root + test case (start_id_config == start_id_test)."""
    dia = DiagnosisTaskPreparation()
    set_b, set_c = dia._assign_sets(_A16, TaskInput(test_case={"x": True}), 10, 10, True)
    assert set_b == [100, 110, 111, 112, 113, 114, 115]
    assert set_c == [102, 104, 106, 108]


def test_site1_redundancy_fm_stride2():
    """WipeOutR_FM: C = FM constraint originals (no root), B = {} (step=2)."""
    dia = DiagnosisTaskPreparation()
    set_b, set_c = dia._assign_sets(_A16, TaskInput(for_redundancy=True), 16, 16, True)
    assert set_b == []
    assert set_c == [102, 104, 106, 108, 110, 112, 114]
    assert _strided(set_c)


def test_site1_fm_diagnosis_no_negation_stride1():
    """FM diagnosis without negated forms: B = root, C = all remaining (step=1)."""
    dia = DiagnosisTaskPreparation()
    set_b, set_c = dia._assign_sets(_A16, TaskInput(), 16, 16, False)
    assert set_b == [100]
    assert set_c == list(range(101, 116))


# ---------------------------------------------------------------------------
# Site 2 — TestCaseTaskPreparation._assign_sets (explanation, stride 2)
# ---------------------------------------------------------------------------
def test_site2_testcase_with_negatives():
    tc = _TestCaseTaskPreparation()
    set_b, set_c, set_tc, set_tv = tc._assign_sets(list(range(200, 216)), 4, 8, True)
    assert set_b == [200]
    assert set_c == [201, 202, 203]
    assert set_tc == [204, 206]          # originals of the TC region [4:8]
    assert set_tv == [208, 210, 212, 214]  # originals of the TV region [8:]


def test_site2_testcase_without_negatives():
    tc = _TestCaseTaskPreparation()
    set_b, set_c, set_tc, set_tv = tc._assign_sets(list(range(200, 212)), 4, 12, False)
    assert set_b == [200]
    assert set_c == [201, 202, 203]
    assert set_tc == [204, 206, 208, 210]
    assert set_tv == []


# ---------------------------------------------------------------------------
# Site 3 — ConGenTaskPreparation._assign_sets (conacq, stride 2)
# ---------------------------------------------------------------------------
def test_site3_congen_assign_sets():
    congen = ConGenTaskPreparation()
    set_b, set_c, set_tc, set_tv = congen._assign_sets(list(range(300, 320)), 2, 8, 12, True)
    assert set_b == [300]
    assert set_c == [302, 304, 306]      # bias originals [bias_start:tc:2]
    assert set_tc == [308, 310]
    assert set_tv == [312, 314, 316, 318]


# ---------------------------------------------------------------------------
# Site 4 — QuAcqTaskPreparation._assign_sets (conacq static, stride 2)
# ---------------------------------------------------------------------------
def test_site4_quacq_assign_sets():
    set_b, set_c = QuAcqTaskPreparation._assign_sets(list(range(400, 410)), 2)
    assert set_b == [400]
    assert set_c == [402, 404, 406, 408]  # bias originals [bias_start::2]
    assert _strided(set_c)


# ---------------------------------------------------------------------------
# Site 5 — fm_oracle_model FM-only slice (originals of Part 3), via a synthetic
# FMOracleModel. Pins: stride 2, starts at the first assumption id, and is
# DISJOINT from the Part-4 variable-assignment assumptions.
# ---------------------------------------------------------------------------
def _synthetic_oracle_model():
    model = FMOracleModel()
    model.constraint_map = {"root": [[1]], "c2": [[-1, 2]], "c3": [[-1, 3]]}
    model.negated_constraint_map = {
        "NOT(root)": [[-1]], "NOT(c2)": [[1], [-2]], "NOT(c3)": [[1], [-3]],
    }
    model.name_to_id = {"f1": 1, "f2": 2, "f3": 3}
    model.next_available_id = 4
    return model


def test_site5_fm_only_slice_layout():
    model = _synthetic_oracle_model()
    first_id = model.next_available_id
    prepared = model.prepare_task()

    # With no prep-time configuration, task.set_c IS the FM-only slice.
    fm_only = prepared.task.set_c
    assert fm_only == [4, 6, 8]          # originals of the three FM-constraint pairs
    assert fm_only[0] == first_id
    assert _strided(fm_only)             # stride 2

    assignment_assumptions = (
        list(prepared.assignment_map.pos_assignment_to_assumption.values())
        + list(prepared.assignment_map.neg_assignment_to_assumption.values())
    )
    # FM-only slice must contain NO variable-assignment assumption.
    assert set(fm_only).isdisjoint(assignment_assumptions)


# ---------------------------------------------------------------------------
# Real end-to-end anchor — a transformed FM through DiagnosisModel.prepare_task.
# arcade-game reserves next_available_id 156 (see test_transformations_*), so the
# redundancy set_c (FM originals, root pair skipped) starts at 158, stride 2.
# ---------------------------------------------------------------------------
def test_arcade_game_redundancy_set_c_layout():
    fm = UVLReader(str(DATA_DIR / "fms" / "arcade-game.uvl")).transform()
    model = FmToDiagPysat(fm, create_negation=True).transform()
    set_c = model.prepare_task(TaskInput.redundancy_fm()).task.set_c
    assert len(set_c) == 70
    assert set_c[0] == 158       # 156 (root) + 2 → skip the root pair
    assert set_c[-1] == 296
    assert _strided(set_c)       # stride 2 throughout
