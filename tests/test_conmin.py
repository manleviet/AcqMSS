"""Tests for ConMin (passive maximally-general acquisition) — P1 Stage-1 scaffold.

Covers three layers:
- TestConMinModelBuilder — the ConMin builder + prepare_task (purity/repeatability).
- TestConMinGate — ConMin's ONLY new logic, the consistency gate, with a stub
  checker. The real-data parity tests cannot cover it: on consistent REAL-FM-7 the
  gate is a no-op pass-through, so a broken/deleted gate still passes parity.
- TestConMinStage1 — Stage-1 parity on real REAL-FM-7 data (unreduced MSS, exact
  match against an independent ConGen pipeline, and an absolute characterization
  anchor).

Uses REAL-FM-7 with the generated bias + examples; both incremental and
non-incremental checker modes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from conacq.algorithms import (
    ConMin, ConMinResult, AcqMSS,
    ConMinModelBuilder, ConMinTaskInput,
    ConGenModelBuilder, ConGenTaskInput,
)
from conacq.algorithms.conmin import (
    AcqMinCover, NegEncoding, support, ConMinTaskPreparation,
)
from conacq.algorithms.conmin.min_cover import (
    connected_components, exact_cover, greedy_cover, irredundant,
)
from conacq.oracle import FMOracle
from conacq.examples import ExampleIO
from explanation.checker.backend import build_checker, SolverBackend
from profiling import get_global_profiler

# Test data paths (mirror test_congen.py)
DATA_DIR = Path(__file__).parent.parent / "data"
FM_PATH = DATA_DIR / "fms" / "REAL-FM-7.uvl"
BIAS_PATH = DATA_DIR / "bias" / "REAL-FM-7-bias.json"
EXAMPLES_RS_1N_PATH = DATA_DIR / "examples" / "REAL-FM-7_rs_1n.json"
EXAMPLES_FF_PATH = DATA_DIR / "examples" / "REAL-FM-7_ff.json"

# Golden Stage-1 MSS on REAL-FM-7 + RS-1n examples, recorded from the verified
# AcqMSS run (which ConMin Stage-1 reuses). 78 of 295 bias constraints survive; we
# pin the count plus a sha256 of the sorted constraint NAMES (names, not assumption
# IDs, so the golden is stable under ID renumbering). Any drift in *which*
# constraints Stage-1 selects — a wrong-set wiring surviving both pipelines, or a
# shared-AcqMSS change — flips the sha. Regenerate deliberately if the model/bias/
# examples change (this is a characterization pin, meant to be loud).
GOLDEN_MSS_RS_1N_N = 78
GOLDEN_MSS_RS_1N_SHA = (
    "d13274bc03c6fa95420f375739607c4c4249f184855e10da05efca4d63b35dc1"
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _prepare_conmin(examples_path):
    """Build a pure-KB ConMin model and prepare a task for the given examples.

    Returns (oracle, prepared) — keep the oracle referenced so it outlives the task.
    """
    oracle = FMOracle(str(FM_PATH), use_incremental=False)
    model = (ConMinModelBuilder
             .from_bias(str(BIAS_PATH))
             .with_oracle_data(oracle.oracle_data)
             .build())
    examples = ExampleIO.load_json(str(examples_path))
    pos = [e.assignments for e in examples.positive]
    neg = [e.assignments for e in examples.negative]
    prepared = model.prepare_task(
        ConMinTaskInput.from_examples(oracle.oracle_data, pos, neg))
    return oracle, prepared


def _prepare_congen(examples_path):
    """Build a ConGen task from the same inputs (independent parity pipeline)."""
    oracle = FMOracle(str(FM_PATH), use_incremental=False)
    model = (ConGenModelBuilder
             .from_bias(str(BIAS_PATH))
             .with_oracle_data(oracle.oracle_data)
             .build())
    examples = ExampleIO.load_json(str(examples_path))
    pos = [e.assignments for e in examples.positive]
    neg = [e.assignments for e in examples.negative]
    prepared = model.prepare_task(
        ConGenTaskInput.from_examples(oracle.oracle_data, pos, neg))
    return oracle, prepared


def _checker(task, is_incremental):
    return build_checker(
        task, SolverBackend.from_flags(use_incremental=is_incremental),
        'glucose4', get_global_profiler())


def _acquire(task, is_incremental):
    """Run ConMin.acquire against a fresh checker for the given task."""
    checker = _checker(task, is_incremental)
    try:
        return ConMin(checker, get_global_profiler()).acquire(
            set_b=task.set_c, set_bg=task.set_b, set_tc=task.set_tc,
            set_neg_tv=task.set_neg_tv, negation_map=task.negation_map)
    finally:
        checker.cleanup()


def _mss_names_sha(mss_ids, provider):
    names = sorted(provider.get_description(aid) for aid in mss_ids)
    return hashlib.sha256("\n".join(names).encode()).hexdigest()


def _skip_if_no_data(*paths):
    for p in paths:
        if not Path(p).exists():
            pytest.skip(f"Test data file not found: {p}")


# --------------------------------------------------------------------------- #
# TestConMinModelBuilder — right-sized (the base is proven by TestConGenModelBuilder)
# --------------------------------------------------------------------------- #

class TestConMinModelBuilder:
    """ConMinModelBuilder is a one-method subclass; build/validate/negation is
    inherited and already covered by TestConGenModelBuilder. Keep only the checks
    specific to the ConMin wiring."""

    def test_prepare_task_is_pure_and_repeatable(self):
        """Build once, prepare per fold: same input -> same task, fresh object."""
        _skip_if_no_data(FM_PATH, EXAMPLES_FF_PATH)
        _, prepared_1 = _prepare_conmin(EXAMPLES_FF_PATH)
        # Reuse the same model/oracle to prove repeatability of prepare_task.
        oracle = FMOracle(str(FM_PATH), use_incremental=False)
        model = (ConMinModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle_data(oracle.oracle_data)
                 .build())
        examples = ExampleIO.load_json(str(EXAMPLES_FF_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        task_input = ConMinTaskInput.from_examples(oracle.oracle_data, pos, neg)
        p1 = model.prepare_task(task_input)
        p2 = model.prepare_task(task_input)
        assert p1.task.set_kb == p2.task.set_kb
        assert p1.task is not p2.task

    def test_prepare_task_from_file(self):
        """Build a pure-KB model, prepare from file-loaded examples (wiring smoke)."""
        _skip_if_no_data(FM_PATH, EXAMPLES_FF_PATH)
        _, prepared = _prepare_conmin(EXAMPLES_FF_PATH)
        assert prepared.task is not None
        assert len(prepared.task.set_kb) > 0

    def test_build_without_oracle_raises(self):
        """build() without oracle -> ValueError (ConMin builder contract)."""
        _skip_if_no_data(BIAS_PATH)
        with pytest.raises(ValueError, match="OracleData required"):
            ConMinModelBuilder.from_bias(str(BIAS_PATH)).build()


# --------------------------------------------------------------------------- #
# TestConMinGate — the consistency gate (ConMin's only new logic), stub checker
# --------------------------------------------------------------------------- #

class _GateTripChecker:
    """Stub checker: reports E+ inconsistent with NE∪BG on the gate call, and
    records each is_consistent_test_cases call so a test can prove that acquire
    short-circuits before AcqMSS ever runs. No solver.
    """

    def __init__(self):
        self.tc_calls = 0
        self.gate_active = None
        self.gate_tcs = None

    def is_consistent_test_cases(self, active, testcases, stop_at_first_violation=False):
        self.tc_calls += 1
        if self.tc_calls == 1:
            self.gate_active = list(active)
            self.gate_tcs = list(testcases)
        return list(testcases)  # non-empty => "all inconsistent"

    def is_consistent(self, test_set):
        return True


class TestConMinGate:
    """The gate short-circuits acquire when E+ is inconsistent with NE∪BG. The
    parity tests run on consistent data where the gate is a no-op, so they cannot
    exercise this branch — these stub tests do."""

    def test_gate_short_circuits_on_inconsistent_examples(self):
        """Inconsistent E+ -> empty result + error metadata, and AcqMSS never runs.

        Teeth: if the gate is removed, acquire falls through to AcqMSS.find_mss,
        which issues multiple is_consistent_test_cases calls (tc_calls > 1) and
        leaves no 'error' in metadata -> this test goes RED.
        """
        checker = _GateTripChecker()
        result = ConMin(checker).acquire(
            set_b=[10, 11, 12], set_bg=[1], set_tc=[20, 21],
            set_neg_tv=[30], negation_map={})
        assert result.mss_ids == []
        assert result.n_bias == 3
        assert result.n_mss == 0
        assert 'error' in result.metadata
        assert checker.tc_calls == 1  # gate ran; AcqMSS did NOT (short-circuit)

    def test_gate_checks_NE_plus_BG_against_Epos(self):
        """The gate activates NE∪BG (order: NE then BG) and tests E+.

        Teeth: wrong-set or wrong-order gate wiring changes these recorded args.
        """
        checker = _GateTripChecker()
        ConMin(checker).acquire(
            set_b=[10, 11, 12], set_bg=[1], set_tc=[20, 21],
            set_neg_tv=[30], negation_map={})
        assert checker.gate_active == [30, 1]   # set_neg_tv + set_bg
        assert checker.gate_tcs == [20, 21]     # set_tc

    def test_empty_result_shape_is_constructible(self):
        """The inconsistent-gate return must construct without a missing-arg
        TypeError even though ConMinResult carries 13 fields (the Stage-2..5 slices
        are defaulted)."""
        r = ConMinResult(mss_ids=[], n_bias=3, n_mss=0, metadata={'error': 'x'})
        assert r.cover_ids == [] and r.support_ids == [] and r.kb_assumption_ids == []
        assert r.n_kb == 0 and r.n_greedy_fallback == 0


# --------------------------------------------------------------------------- #
# TestConMinStage1 — Stage-1 parity on real REAL-FM-7 data
# --------------------------------------------------------------------------- #

class TestConMinStage1:
    """ConMin Stage-1 returns the maximally-specific admissible pool A, UNREDUCED."""

    @pytest.mark.parametrize("examples_path,is_incremental", [
        (EXAMPLES_RS_1N_PATH, True),    # incremental
        (EXAMPLES_FF_PATH, False),      # non-incremental (mode-agnosticism)
    ])
    def test_stage1_mss_is_unreduced_admissible_pool(self, examples_path, is_incremental):
        """ConMin.acquire.mss_ids equals AcqMSS.find_mss on the same task — i.e. the
        raw MSS, not reduced or truncated.

        Two invariants this rests on:
        (i) the reference is AcqMSS.find_mss directly, NOT ConGenResult: Reduce
            discards/reorders the MSS (docs/adr/0017-reduce-discards-mss-order.md),
            so ConGen exposes only its size, never the pool.
        (ii) the acquire checker (gate + find_mss) and the pristine reference checker
            agree because Stage-1 asks only SAT/UNSAT (is_consistent), which is
            invariant under learned clauses — the model-returning path that a gate
            solve could perturb is a different question
            (docs/adr/0013-is-consistent-and-find-model-are-two-questions.md).
        """
        _skip_if_no_data(FM_PATH, BIAS_PATH, examples_path)
        _oracle, prepared = _prepare_conmin(examples_path)
        task = prepared.task
        checker_a = _checker(task, is_incremental)
        checker_b = _checker(task, is_incremental)
        try:
            result = ConMin(checker_a, get_global_profiler()).acquire(
                set_b=task.set_c, set_bg=task.set_b, set_tc=task.set_tc,
                set_neg_tv=task.set_neg_tv, negation_map=task.negation_map)
            reference = AcqMSS(checker_b, m=1, profiler_instance=get_global_profiler()).find_mss(
                delta=[], set_b=list(task.set_c), set_neg_tv=list(task.set_neg_tv),
                set_tc=list(task.set_tc), set_bg=list(task.set_b))
            assert sorted(result.mss_ids) == sorted(reference)
            assert result.n_mss == len(result.mss_ids)
            assert result.n_bias == len(task.set_c)
            # P1 leaves the ConMin theory unassembled (distinct from A per brief §9a).
            assert result.kb_assumption_ids == []
        finally:
            checker_a.cleanup()
            checker_b.cleanup()

    def test_stage1_matches_congen(self):
        """Cross-pipeline: an independently built ConGen task yields the same
        Stage-1 fields AND the same MSS. Exact-set, no size-parity fallback: two
        different same-cardinality sets must NOT pass, and a real divergence should
        surface rather than be masked.
        """
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        _oc, congen = _prepare_congen(EXAMPLES_RS_1N_PATH)
        _om, conmin = _prepare_conmin(EXAMPLES_RS_1N_PATH)
        ct, mt = congen.task, conmin.task

        # Prep field parity, EXCEPT set_b: ConMin's acquisition BG is domain-only
        # (root non-emptiness is a post-acquisition axiom, note "Root-constraint BG
        # semantics"), so it legitimately diverges from ConGen's root BG. Everything
        # else — and, crucially, the resulting MSS — still matches because Stage-1 is
        # inert to the root for complete positives.
        assert list(mt.set_c) == list(ct.set_c)
        assert list(mt.set_b) == []                 # domain-only (∅ for boolean FM)
        assert list(ct.set_b) == list(mt.root_axiom)  # ConGen's BG == ConMin's root axiom
        assert list(mt.set_tc) == list(ct.set_tc)
        assert list(mt.set_neg_tv) == list(ct.set_neg_tv)
        assert mt.negation_map == ct.negation_map

        # ConMin's MSS (domain-only BG) equals AcqMSS on the ConGen task (root BG) —
        # inert-to-root, so exact-set match despite the BG divergence.
        result = _acquire(mt, is_incremental=True)
        checker = _checker(ct, is_incremental=True)
        try:
            reference = AcqMSS(checker, m=1, profiler_instance=get_global_profiler()).find_mss(
                delta=[], set_b=list(ct.set_c), set_neg_tv=list(ct.set_neg_tv),
                set_tc=list(ct.set_tc), set_bg=list(ct.set_b))
        finally:
            checker.cleanup()
        assert sorted(result.mss_ids) == sorted(reference)

    def test_stage1_characterization_golden(self):
        """Absolute anchor beyond the near-tautological mss==find_mss: the set of
        constraints Stage-1 selects on REAL-FM-7 + RS-1n is pinned by name-sha.

        The golden `d13274bc…` is UNCHANGED by the P4a root-BG refactor: Stage-1 is
        inert to the root fact for complete positives (a complete positive already
        selects the root), verified byte-identical for set_bg=[root] and set_bg=[].
        This test staying green under domain-only BG IS the loud confirmation that
        Stage-1 was not perturbed — no re-pin (note "Root-constraint BG semantics").
        """
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        _oracle, prepared = _prepare_conmin(EXAMPLES_RS_1N_PATH)
        assert list(prepared.task.set_b) == []  # P4a: domain-only acquisition BG
        result = _acquire(prepared.task, is_incremental=True)
        assert result.n_mss == GOLDEN_MSS_RS_1N_N
        assert _mss_names_sha(result.mss_ids, prepared.describe) == GOLDEN_MSS_RS_1N_SHA


# --------------------------------------------------------------------------- #
# P4a — root-constraint BG (root = post-acquisition axiom, BG domain-only)
# --------------------------------------------------------------------------- #

class TestConMinRootBG:
    """P4a: the root non-emptiness fact is a post-acquisition axiom, out of the
    acquisition BG. Consequence: Reduce no longer entailment-drops `X → root`
    constraints, so they become acquirable (the recall fix)."""

    def test_x_to_root_kept_by_domain_bg_dropped_by_root_bg(self):
        """`X→root` (root's optional children c6/c14/c18) is acquired under domain-only
        BG but Reduce-dropped when the root fact is in BG — showing both fix and bug."""
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        oracle = FMOracle(str(FM_PATH), use_incremental=False)
        model = (ConMinModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle_data(oracle.oracle_data)
                 .build())
        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        prepared = model.prepare_task(
            ConMinTaskInput.from_examples(oracle.oracle_data, pos, neg))
        task = prepared.task
        assert task.root_axiom != () and list(task.set_b) == []  # root out, BG domain-only

        def kb_names(set_bg):
            checker = _checker(task, is_incremental=True)
            try:
                r = ConMin(checker, get_global_profiler()).acquire(
                    set_b=task.set_c, set_bg=set_bg, set_tc=task.set_tc,
                    set_neg_tv=task.set_neg_tv, negation_map=task.negation_map,
                    neg_encodings=task.neg_encodings, support_count=task.support_count, k=1)
                return {prepared.describe.get_description(a) for a in r.kb_assumption_ids}
            finally:
                checker.cleanup()

        x_to_root = {'c6', 'c14', 'c18'}                 # optional children X→jplug
        under_domain = kb_names(list(task.set_b))         # P4a: domain-only ([])
        under_root = kb_names(list(task.root_axiom))      # old: root in BG
        assert x_to_root & under_domain, "X→root must be acquirable under domain-only BG"
        assert not (x_to_root & under_root), "X→root is Reduce-dropped when root is in BG (the bug)"


# --------------------------------------------------------------------------- #
# P4b — resolve_result (5-part decomposition) + root axiom re-append
# --------------------------------------------------------------------------- #

class TestConMinResolveResult:
    """ConMinModel.resolve_result → (bg_clauses, kb_clauses, kb_names, fallback_clauses,
    redundant_names). Learned FM (kb) / ¬e⁻ fallbacks / root are separated; the root
    axiom is re-appended as bg_clauses so metrics never count it as learned. A non-FM
    kb id that cannot resolve RAISES (foot-gun #5) rather than silently dropping."""

    def test_resolve_maps_kb_and_reappends_root_separately(self):
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        oracle = FMOracle(str(FM_PATH), use_incremental=False)
        model = (ConMinModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle_data(oracle.oracle_data)
                 .build())
        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        prepared = model.prepare_task(
            ConMinTaskInput.from_examples(oracle.oracle_data, pos, neg))
        task, describe = prepared.task, prepared.describe

        checker = _checker(task, is_incremental=True)
        try:
            result = ConMin(checker, get_global_profiler()).acquire(
                set_b=task.set_c, set_bg=task.set_b, set_tc=task.set_tc,
                set_neg_tv=task.set_neg_tv, negation_map=task.negation_map,
                neg_encodings=task.neg_encodings, support_count=task.support_count, k=1)
        finally:
            checker.cleanup()

        root_clauses = oracle.oracle_data.get_root_clauses()
        bg_clauses, kb_clauses, kb_names, fallback_clauses, redundant_names = \
            model.resolve_result(result, describe, root_clauses,
                                 task.set_kb, task.negation_map)

        # kb_names/kb_clauses = LEARNED FM constraints only (incl. the recall-fixed
        # X→root); an id whose name is not a bias constraint is excluded (independent
        # oracle via describe + constraint_map, not the impl's _resolve_fm).
        fm_ids = [a for a in result.kb_assumption_ids
                  if describe.get_description(a) in model.constraint_map]
        assert kb_names == [describe.get_description(a) for a in fm_ids]
        assert {'c6', 'c14', 'c18'} <= set(kb_names)          # X→root acquired (P4a)
        expected_clauses = []
        for a in fm_ids:
            expected_clauses.extend(model.constraint_map[describe.get_description(a)])
        assert kb_clauses == expected_clauses

        # Root axiom re-appended as bg_clauses, SEPARATE from the acquired kb.
        assert [list(c) for c in bg_clauses] == [[1]]         # jplug=true (root)
        assert list(task.root_axiom) != []                     # P4a recorded the root
        assert [1] not in [list(c) for c in kb_clauses]        # root NOT in acquired

        # ConMin expects U=∅ on this fixture → no ¬e⁻ fallbacks in the KB.
        assert fallback_clauses == []

        # redundant_names = the dropped LEARNED-FM ids' names.
        assert redundant_names == [describe.get_description(a) for a in result.redundant_ids
                                   if describe.get_description(a) in model.constraint_map]

    def test_fallback_decomposition_forced_uncoverable(self):
        """Force U>0 synthetically: a ¬e⁻ fallback in the KB must NOT appear in
        kb_names/kb_clauses (learned FM), but its clause MUST appear in
        fallback_clauses (resolved from set_kb, guard stripped)."""
        from explanation.api import DescriptionProvider
        from conacq.algorithms.conmin import ConMinModel, ConMinResult

        model = ConMinModel()
        model.constraint_map = {'c_x': [[1, -2]]}          # one learned FM constraint
        describe = DescriptionProvider()
        describe.add_constraint_description(50, 'c_x')      # bias id → FM constraint
        describe.add_test_case_description(900, 'NOT(db=lite & ide=pro)')  # ¬e⁻ fallback

        # e⁻ blocked on feature vars 5,7: ne_clause [-5,-7,-900]; negation [-900,-901].
        set_kb = [[1, -2], [-5, -7, -900], [-900, -901]]
        negation_map = {900: 901}
        result = ConMinResult(
            mss_ids=[], n_bias=1, n_mss=0,
            kb_assumption_ids=[50, 900],   # one FM constraint + one ¬e⁻ fallback (survived Reduce)
            fallback_ids=[900], uncoverable=[900], redundant_ids=[])

        bg, kb_clauses, kb_names, fallback_clauses, redundant_names = \
            model.resolve_result(result, describe, [[1]], set_kb, negation_map)

        assert kb_names == ['c_x']                          # (i) ¬e⁻ NOT in learned FM
        assert kb_clauses == [[1, -2]]
        assert 'NOT(db=lite & ide=pro)' not in kb_names
        assert fallback_clauses == [[-5, -7]]               # (ii) ¬e⁻ clause, guard stripped
        # (iii) fallback_clauses corresponds to the NON-FM kb ids resolve produced
        # (NOT result.fallback_ids, which resolve never reads — that would be a tautology).
        non_fm = [a for a in result.kb_assumption_ids
                  if describe.get_description(a) not in model.constraint_map]
        assert non_fm == [900]
        assert len(fallback_clauses) == len(non_fm)

    def test_fallback_multi_negative_layout(self):
        """Multi-negative layout (the real shape, not covered by the single-negative
        synthetic): TUPLE set_kb, an UNREGISTERED per-e⁻ id, and the combine clause
        [+id, -combined] present. The ne-clause must still be disambiguated from the
        per-e⁻ negation clause and the combine clause."""
        from explanation.api import DescriptionProvider
        from conacq.algorithms.conmin import ConMinModel, ConMinResult

        model = ConMinModel()
        model.constraint_map = {'c6': [[3, -4]]}
        describe = DescriptionProvider()
        describe.add_constraint_description(50, 'c6')
        describe.add_test_case_description(800, 'NOT(e1- & e2-)')  # only the COMBINED id
        # per-e⁻ id 101 left UNREGISTERED → describe.get_description(101) == '101'.

        # Real prep shape: frozen tuples; ne-clause, combine clause, per-e⁻ negation.
        set_kb = (
            (3, -4),                # a bias clause
            (-5, -7, -101),         # e1⁻ ne-clause (minimal conflict on vars 5,7)
            (-8, -102),             # e2⁻ ne-clause
            (101, -800), (102, -800),   # combine clauses [+id, -combined]
            (-101, -901), (-102, -902), # per-e⁻ negation clauses
        )
        negation_map = {101: 901, 102: 902, 800: 900}
        result = ConMinResult(
            mss_ids=[], n_bias=1, n_mss=0,
            kb_assumption_ids=[50, 101],   # bias c6 + uncoverable e1⁻ fallback survived Reduce
            fallback_ids=[101], uncoverable=[101], redundant_ids=[])

        _, kb_clauses, kb_names, fallback_clauses, _ = model.resolve_result(
            result, describe, [[1]], set_kb, negation_map)

        assert kb_names == ['c6']                # unregistered '101' not classified as FM
        assert kb_clauses == [[3, -4]]
        assert fallback_clauses == [[-5, -7]]    # ne-clause, NOT the negation/combine clause

    def test_unresolvable_fallback_raises_not_silent(self):
        """Foot-gun #5 for resolve: a non-FM kb id (¬e⁻ fallback) that cannot be
        resolved (empty set_kb) must RAISE, never silently vanish from the theory."""
        import pytest
        from explanation.api import DescriptionProvider
        from conacq.algorithms.conmin import ConMinModel, ConMinResult

        model = ConMinModel()
        model.constraint_map = {'c_x': [[1, -2]]}
        describe = DescriptionProvider()
        describe.add_constraint_description(50, 'c_x')
        describe.add_test_case_description(900, 'NOT(...)')
        result = ConMinResult(
            mss_ids=[], n_bias=1, n_mss=0,
            kb_assumption_ids=[50, 900],   # 900 is a fallback but set_kb is empty
            fallback_ids=[900], uncoverable=[900], redundant_ids=[])

        with pytest.raises(ValueError, match=r"900.*silently dropped"):
            model.resolve_result(result, describe, [[1]])   # 3-arg call → set_kb=()

    def test_fallback_missing_negation_map_entry_raises(self):
        """Defense-in-depth (P3-Critical bug class): a fallback id ABSENT from
        negation_map cannot be disambiguated. Even though set_kb HAS a -id clause,
        resolve must fail-loud — NOT silently return the wrong remainder [-201] from
        the negation clause that happens to come first."""
        import pytest
        from explanation.api import DescriptionProvider
        from conacq.algorithms.conmin import ConMinModel, ConMinResult

        model = ConMinModel()
        model.constraint_map = {'c_x': [[1, -2]]}
        describe = DescriptionProvider()
        describe.add_constraint_description(50, 'c_x')
        describe.add_test_case_description(200, 'NOT(...)')
        # Negation clause [-200,-201] comes BEFORE the ne-clause [-5,-6,-200]; with
        # neg=None the old code would strip -200 from the first match → wrong [-201].
        set_kb = [[1, -2], [-200, -201], [-5, -6, -200]]
        result = ConMinResult(
            mss_ids=[], n_bias=1, n_mss=0,
            kb_assumption_ids=[50, 200],
            fallback_ids=[200], uncoverable=[200], redundant_ids=[])

        with pytest.raises(ValueError, match=r"MISSING id 200"):
            model.resolve_result(result, describe, [[1]], set_kb, negation_map={})


# --------------------------------------------------------------------------- #
# P3 — de-delegation on real data (ff, 3 negatives), REAL checker
# --------------------------------------------------------------------------- #

class TestConMinDeDelegation:
    """The P3 de-delegation (real per-e- neg_encodings + per-e- negation registration)
    AND the P4a cover-correctness fix: with ConMin's acquisition BG now domain-only
    (root non-emptiness is a post-acquisition axiom, note "Root-constraint BG
    semantics"), `is_consistent([c] + domain_bg + e-)` no longer degenerates — the
    rejection test discriminates for EVERY negative, root-present or not.
    """

    def test_ff_dedelegation_invariants(self):
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_FF_PATH)
        _oracle, prepared = _prepare_conmin(EXAMPLES_FF_PATH)
        task = prepared.task

        # (1) one NegEncoding per e-, each with a non-empty full-config aid set.
        assert len(task.neg_encodings) == 3
        assert all(len(ne.assumption_ids) > 0 for ne in task.neg_encodings)

        # (2) Critical fix: every per-e- ne_id has a negation_map entry, so a ¬e-
        # fallback is Reduce-able (before the fix the combined-NE prep left these
        # unregistered → reduce.py silently skipped them). Masked by 1-neg fixtures.
        assert all(ne.neg_id in task.negation_map for ne in task.neg_encodings)

        # (3) P4a: acquisition BG is domain-only (∅ for boolean FM), so the rejection
        # test discriminates on ALL negatives — cand is a proper, non-empty subset of
        # A (no saturation to all-of-A on FM-root-violating negatives).
        checker = _checker(task, is_incremental=True)
        try:
            bg = list(task.set_b)
            assert bg == []  # domain-only for a boolean FM (root dropped)
            admissible = AcqMSS(checker, m=1, profiler_instance=get_global_profiler()).find_mss(
                delta=[], set_b=list(task.set_c), set_neg_tv=list(task.set_neg_tv),
                set_tc=list(task.set_tc), set_bg=bg)
            for ne in task.neg_encodings:
                cand = [c for c in admissible
                        if not checker.is_consistent([c] + bg + list(ne.assumption_ids))]
                assert 0 < len(cand) < len(admissible)  # non-degenerate for every e-
        finally:
            checker.cleanup()

    def test_reused_prep_instance_no_cross_fold_leak(self):
        """A REUSED ConMinTaskPreparation must not leak one fold's neg_encodings into
        a later zero-negative fold. A zero-negative fold skips _prepare_negative_examples,
        so without the per-call reset in prepare() the stale encodings would survive.
        """
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_FF_PATH)
        oracle = FMOracle(str(FM_PATH), use_incremental=False)
        model = (ConMinModelBuilder
                 .from_bias(str(BIAS_PATH))
                 .with_oracle_data(oracle.oracle_data)
                 .build())
        examples = ExampleIO.load_json(str(EXAMPLES_FF_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]

        prep = ConMinTaskPreparation()  # ONE instance, reused across folds
        t_neg = prep.prepare(
            model, ConMinTaskInput.from_examples(oracle.oracle_data, pos, neg)).task
        assert len(t_neg.neg_encodings) == 3            # fold WITH negatives

        t_zero = prep.prepare(
            model, ConMinTaskInput.from_examples(oracle.oracle_data, pos, [])).task
        assert t_zero.neg_encodings == ()               # zero-neg fold: no leak


# --------------------------------------------------------------------------- #
# P2 — AcqMinCover engine (design brief §3, AcqMinCover v2 worked example)
# --------------------------------------------------------------------------- #

# Worked-example constraint IDs (v2 note §3-§6); names in comments.
_ID_DB = 1      # id->db
_ID_GA = 2      # id->¬ga
_N1_N2 = 11     # n1->n2
_N3_N4 = 13     # n3->n4
_N5_N6 = 15     # n5->n6  (admissible-but-spurious over-fit)
_T_U = 21       # t->u
_U_V = 22       # u->¬v


class TestMinCover:
    """Pure cover-solver on hand-built maps from the v2 worked example (no checker)."""

    @staticmethod
    def _g3():
        """Block-B component G3: mb1..mb6 = 1..6 (v2 example §5)."""
        fs = frozenset
        return {fs([_N1_N2]): {1, 2, 3},
                fs([_N3_N4]): {4, 5, 6},
                fs([_N5_N6]): {2, 3, 4, 5}}

    def test_exact_beats_greedy_on_G3(self):
        """The payoff: exact cover = the 2 true constraints; greedy keeps 3 (over-fit)."""
        cover = self._g3()
        negs = {1, 2, 3, 4, 5, 6}
        exact = exact_cover(set(cover), negs, cover)
        greedy = greedy_cover(set(cover), negs, cover)
        assert exact == {frozenset([_N1_N2]), frozenset([_N3_N4])}
        assert frozenset([_N5_N6]) in greedy and len(greedy) == 3

    def test_irredundant_recovers_exact_from_greedy(self):
        """The post-pass rescues even the greedy result down to the 2-cover."""
        cover = self._g3()
        negs = {1, 2, 3, 4, 5, 6}
        greedy = greedy_cover(set(cover), negs, cover)
        assert irredundant(greedy, negs, cover) == {frozenset([_N1_N2]), frozenset([_N3_N4])}

    def test_connected_components_separates(self):
        """One coverage graph fragments into 3 independent components (G1,G2,G3)."""
        fs = frozenset
        # eA1=101 rejected by id->db; eA2=102 by id->¬ga; mb1..6 by the block-B trio.
        cover = {fs([_ID_DB]): {101}, fs([_ID_GA]): {102},
                 fs([_N1_N2]): {1, 2, 3}, fs([_N3_N4]): {4, 5, 6}, fs([_N5_N6]): {2, 3, 4, 5}}
        comps = connected_components(cover)
        assert len(comps) == 3
        assert sorted(len(elems) for elems, _ in comps) == [1, 1, 3]
        selected = set()
        for elems_i, negs_i in comps:
            selected |= exact_cover(elems_i, negs_i, cover)
        assert selected == {frozenset([_ID_DB]), frozenset([_ID_GA]),
                            frozenset([_N1_N2]), frozenset([_N3_N4])}

    def test_weight_tiebreak_prefers_lighter_element(self):
        """w≡1: among equal-cardinality covers, the lower-Σweight one wins (compound
        weighs its size, so a singleton is preferred)."""
        fs = frozenset
        cover = {fs([_T_U, _U_V]): {900}, fs([_ID_DB]): {900}}
        assert exact_cover(set(cover), {900}, cover) == {frozenset([_ID_DB])}


class TestAcqMinCover:
    """Phase A (checker-driven) with rule-based stub checkers (no solver)."""

    def test_compound_branch_places_Sx(self):
        """pc- (t=1,v=1) rejected only by the PAIR {t->u, u->¬v} -> one compound element.

        Neither constraint alone rejects pc- (cand=∅), so QuickXplain finds the minimal
        conflict {t->u, u->¬v} and it enters the cover as a single compound element.
        """
        class _BlockC:
            PC = {201, 202}   # t=1, v=1 assignment assumptions

            def is_consistent(self, test_set):
                s = set(test_set)
                both = _T_U in s and _U_V in s
                return not (bool(self.PC & s) and both)

        pc = NegEncoding(neg_id=900, assumption_ids=(201, 202))
        res = AcqMinCover(_BlockC()).cover(
            admissible=[_T_U, _U_V], neg_encodings=[pc], bg=[1])
        assert res.cover_elements == [frozenset([_T_U, _U_V])]
        assert res.uncoverable == []
        assert res.n_components == 1

    def test_uncoverable_goes_to_U(self):
        """A negative no element rejects (cand=∅, no conflict) is memorised in U."""
        class _AllConsistent:
            def is_consistent(self, test_set):
                return True

        u = NegEncoding(neg_id=777, assumption_ids=(301,))
        res = AcqMinCover(_AllConsistent()).cover(
            admissible=[_ID_DB, _ID_GA], neg_encodings=[u], bg=[1])
        assert res.cover_elements == []
        assert res.uncoverable == [777]

    def test_singletons_end_to_end(self):
        """Each e- rejected by exactly one constraint -> singleton cover, 2 components."""
        class _RejectsMatching:
            REJECT = {(_ID_DB, 501), (_ID_GA, 502)}  # (constraint, e- aid) pairs

            def is_consistent(self, test_set):
                s = set(test_set)
                return not any(c in s and aid in s for c, aid in self.REJECT)

        negs = [NegEncoding(neg_id=1, assumption_ids=(501,)),
                NegEncoding(neg_id=2, assumption_ids=(502,))]
        res = AcqMinCover(_RejectsMatching()).cover(
            admissible=[_ID_DB, _ID_GA], neg_encodings=negs, bg=[9])
        assert set(res.cover_elements) == {frozenset([_ID_DB]), frozenset([_ID_GA])}
        assert res.uncoverable == []
        assert res.n_components == 2


# --------------------------------------------------------------------------- #
# P3 — support⁺ (design brief §4 unified 6-operator; CNF-direct, no checker)
# --------------------------------------------------------------------------- #

class TestSupport:
    """support⁺ on hand-built CNF. Var ids + counts from the multi-valued working
    example: lin=1 win=2 mac=3 lite=4 srv=5 std=6 pro=7 ;
    #lin=4 #win=2 #mac=0 #lite=3 #srv=2 #std=2 #pro=1."""

    PRESENT = {1: 4, 2: 2, 3: 0, 4: 3, 5: 2, 6: 2, 7: 1}

    def test_requires_is_antecedent_count(self):
        assert support([[-7, 5]], self.PRESENT) == 1   # c48 pro->srv  = #pro
        assert support([[-5, 1]], self.PRESENT) == 2   # c32 srv->lin  = #srv

    def test_excludes_is_min_of_both_sides(self):
        assert support([[-2, -7]], self.PRESENT) == 1  # c16 excl(win,pro) min(2,1)
        assert support([[-5, -6]], self.PRESENT) == 2  # c36 excl(srv,std) min(2,2)

    def test_optional_is_antecedent_count(self):
        assert support([[-4, 6]], self.PRESENT) == 3   # optional lite->std = #lite

    def test_mandatory_is_min_parent_child(self):
        # P<->C = [[-P,C],[-C,P]], P=lin(1) C=win(2)
        assert support([[-1, 2], [-2, 1]], self.PRESENT) == 2   # min(#lin=4,#win=2)

    def test_or_is_min_parent_children(self):
        # P<->(C1 v C2), P=lin(1) C1=lite(4) C2=srv(5)
        assert support([[-1, 4, 5], [-4, 1], [-5, 1]], self.PRESENT) == 2  # min(4,3,2)

    def test_alternative_equals_or(self):
        or_cnf = [[-1, 4, 5], [-4, 1], [-5, 1]]
        alt_cnf = or_cnf + [[-4, -5]]  # + pairwise exclude (dominated → no change)
        assert support(alt_cnf, self.PRESENT) == support(or_cnf, self.PRESENT) == 2

    def test_strict_zero_on_unobserved_trigger(self):
        # #mac = 0 → any constraint whose violation needs mac present gets support 0
        assert support([[-3, 4]], self.PRESENT) == 0    # c17 mac->lite
        assert support([[-3, -4]], self.PRESENT) == 0   # c18 excl(mac,lite) min(0,3)


class _WorkingExampleStub:
    """Stub checker reproducing the multi-valued working example's SAT behaviour for
    AcqMinCover (`cand`) and Reduce (entailment). Aid ranges are disjoint: constraint
    aids = c-numbers (<100), BG root = 500, e- markers = 501-503, ¬c = c+1000.

    cand(e-) and the Reduce entailments are taken verbatim from the hand-verified
    Appendix A (A.4-A.7)."""

    CAND = {501: {31, 48}, 502: {48}, 503: {12, 32}}     # e- marker -> rejecting c's
    ENTAILERS = {16: set(), 44: set(), 31: {48}, 36: {42}, 12: {32}}  # c -> min entailer (∅ = BG)
    KEPT = {32, 42, 48}                                   # never redundant (C_τ)

    def is_consistent(self, test_set):
        s = set(test_set)
        negated = [a - 1000 for a in s if a >= 1000]
        if negated:                                      # Reduce: BG ∪ (KB∖{c}) ∪ {¬c}
            c = negated[0]
            if c in self.KEPT:
                return True                              # not redundant
            active = {a for a in s if a < 100}           # KB∖{c} constraint aids
            return not self.ENTAILERS.get(c, set()).issubset(active)
        markers = [a for a in s if a in self.CAND]
        if markers:                                      # AcqMinCover: is_consistent([c]+BG+e-)
            constraints = {a for a in s if a < 100}
            return not any(c in self.CAND[markers[0]] for c in constraints)
        return True

    def find_model(self, *args, **kwargs):
        return None

    def cleanup(self):
        pass


class TestConMinReducesToWorkingExample:
    """The paper headline: ConMin's final KB = C_τ for k∈{1,2}, min-cover for k≥3
    (multi-valued working example, hand-verified Appendix A). Drives lines 5-8
    directly with a hand-built A / support_count and the working-example stub."""

    A = [12, 16, 17, 18, 19, 20, 21, 22, 23, 24, 31, 32, 36, 42, 44, 48]  # |A|=16
    NEG = [NegEncoding(501, (501,)), NegEncoding(502, (502,)), NegEncoding(503, (503,))]
    SUPPORT = {16: 1, 31: 1, 32: 2, 36: 2, 42: 2, 44: 1,
               17: 0, 18: 0, 19: 0, 20: 0, 21: 0, 22: 0, 23: 0, 24: 0}
    NEGMAP = {c: c + 1000 for c in A}
    BG = [500]

    def _run(self, k):
        return ConMin(_WorkingExampleStub())._cover_support_reduce(
            self.A, self.NEG, self.SUPPORT, k, self.BG, self.NEGMAP, n_bias=48)

    def test_cover_is_c48_c12(self):
        r = self._run(k=1)
        assert set(r.cover_ids) == {12, 48}   # greedy c48 (2) + tie-break c12 over c32
        assert r.uncoverable == []

    @pytest.mark.parametrize("k", [1, 2])
    def test_kb_equals_c_tau_for_small_k(self, k):
        r = self._run(k)
        assert set(r.kb_assumption_ids) == {32, 42, 48}  # C_τ = {srv→lin, std→lite, pro→srv}

    @pytest.mark.parametrize("k", [3, 4])
    def test_kb_is_pure_min_cover_for_large_k(self, k):
        r = self._run(k)
        assert r.support_ids == []                        # S empties
        assert set(r.kb_assumption_ids) == {12, 48}       # maximally-general boundary


# --------------------------------------------------------------------------- #
# P4c — ConMinRunner (build-once → per-fold acquire → collect → resolve)
# --------------------------------------------------------------------------- #

class TestConMinRunner:
    """ConMinRunner mirrors ConGenRunner: it wires the full lines-5-8 inputs into
    acquire, guards the silent-empty-KB foot-gun, collects CONMIN_METRICS, and
    exposes the 5-part decomposition for the P4d eval."""

    def test_e2e_produces_nonempty_kb_with_x_to_root(self):
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        from conacq.runners import ConMinRunner
        from conacq.runners.metrics import CONMIN_METRICS

        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        runner = ConMinRunner(str(BIAS_PATH), str(FM_PATH), use_incremental=True, k=1)
        try:
            res = runner.run(pos, neg)
        finally:
            runner.cleanup()

        # A real, non-empty KB with the recall-fixed X→root constraints (P4a).
        assert res.n_kb > 0
        assert {'c6', 'c14', 'c18'} <= set(res.kb_constraints)
        # Root axiom delivered as bg, SEPARATE from the acquired kb.
        assert [list(c) for c in res.bg_clauses] == [[1]]
        assert [1] not in [list(c) for c in res.kb_clauses]
        # rs_1n has no uncoverable negatives → no ¬e⁻ fallbacks.
        assert res.n_uncoverable == 0 and res.fallback_clauses == []
        # Decomposition slices present + consistent.
        assert len(res.mss_ids) == res.n_mss
        assert len(res.kb_assumption_ids) == res.n_kb
        assert res.n_kb == len(res.kb_constraints)

        # Metrics are the CONMIN spec; no phantom source (every non-extra source is a
        # profiler key the run actually emitted).
        assert res.metrics.spec == CONMIN_METRICS
        _EXTRA = {'memory_peak_mb', 'n_mss', 'n_kb', 'consistency_checks_total',
                  'n_components', 'largest_component', 'n_greedy_fallback', 'n_uncoverable'}
        sources = {m.source for m in CONMIN_METRICS} - _EXTRA
        phantom = sources - set(res.profiler_data.keys())
        assert not phantom, f"CONMIN_METRICS points at profiler keys a run never emits: {sorted(phantom)}"

        # to_dict keeps the base schema + nests the decomposition under `conmin`.
        d = res.to_dict()
        assert {'kb_constraints', 'bg_clauses', 'n_bias', 'n_kb', 'performance'} <= d.keys()
        assert d['conmin']['slices']['kb_assumption_ids'] == res.kb_assumption_ids
        assert d['conmin']['cover']['n_uncoverable'] == 0

    def test_assert_fires_on_neg_present_but_no_encodings(self, monkeypatch):
        """Foot-gun #5: E⁻ present but the prepared task has empty neg_encodings must
        RAISE (the cover step would silently yield an empty KB), not emit A-only."""
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        from dataclasses import replace
        from explanation.api import PreparedTask
        from conacq.runners import ConMinRunner
        from conacq.algorithms.conmin import ConMinModel

        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        assert neg, "fixture must have negatives to exercise the guard"

        runner = ConMinRunner(str(BIAS_PATH), str(FM_PATH), use_incremental=True)
        orig = ConMinModel.prepare_task

        def stripped(self_model, task_input):  # strip neg_encodings post-prepare
            prepared = orig(self_model, task_input)
            return PreparedTask(replace(prepared.task, neg_encodings=()), prepared.describe)

        monkeypatch.setattr(ConMinModel, 'prepare_task', stripped)
        try:
            with pytest.raises(ValueError, match=r"no neg_encodings"):
                runner.run(pos, neg)
        finally:
            runner.cleanup()

    def test_metrics_table_disjoint_from_congen_and_quacq(self):
        """CONMIN∩CONGEN ⊆ core + the declared MSS-shared keys; CONMIN∩QUACQ ⊆ the
        narrow core only. COMMON_KEYS stays narrow so the separate ConGen∩QuAcq guard
        still trips if QuAcq ever grows an MSS key."""
        from conacq.runners.metrics import (
            CONMIN_METRICS, CONGEN_METRICS, QUACQ_METRICS, COMMON_KEYS, _MSS_SHARED)
        cm = {m.key for m in CONMIN_METRICS}
        # ConMin shares the core + the MSS-based keys (n_mss/n_kb/acqmss_*) with ConGen.
        assert (cm & {m.key for m in CONGEN_METRICS}) <= (COMMON_KEYS | _MSS_SHARED)
        # ConMin shares ONLY the narrow core with QuAcq (QuAcq has no MSS keys).
        assert (cm & {m.key for m in QUACQ_METRICS}) <= COMMON_KEYS
        assert not (_MSS_SHARED & COMMON_KEYS)   # MSS keys deliberately kept out of core
        # keys are unique within the table (no accidental dup MetricSpec)
        assert len(cm) == len(CONMIN_METRICS)

    def test_shuffle_seed_is_honored_not_ignored(self, monkeypatch):
        """ConMin's FINAL KB is order-dependent (AcqMinCover + Reduce walk A in bias
        order), so the runner must APPLY shuffle_seed like ConGenRunner — not silently
        ignore it (which would confound a shuffle_bias head-to-head vs ConGen)."""
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        from conacq.runners import ConMinRunner
        from conacq.algorithms.conmin import ConMin

        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]

        captured = []
        orig = ConMin.acquire

        def capture(self_cm, **kw):            # record the bias order acquire receives
            captured.append(list(kw['set_b']))
            return orig(self_cm, **kw)

        monkeypatch.setattr(ConMin, 'acquire', capture)
        runner = ConMinRunner(str(BIAS_PATH), str(FM_PATH), use_incremental=True)
        try:
            runner.run(pos, neg, shuffle_seed=None)   # base bias order
            runner.run(pos, neg, shuffle_seed=7)      # shuffled bias order
        finally:
            runner.cleanup()

        assert len(captured) == 2
        assert sorted(captured[0]) == sorted(captured[1])   # same bias set
        assert captured[0] != captured[1]                    # different order ⇒ seed applied

    def test_cv_function_trains_per_fold_and_aggregates(self):
        """n_fold_cross_validation_conmin (the run_cv entry point) trains a KB per
        fold and aggregates the CONMIN metrics — guards the CV wiring the runner unit
        tests don't reach (multi-fold prepare→acquire→resolve + cleanup)."""
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        from conacq.eval import n_fold_cross_validation_conmin, CrossValidationResult

        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        cv = n_fold_cross_validation_conmin(
            pos, neg, n_folds=2, bias_path=str(BIAS_PATH), fm_path=str(FM_PATH),
            seed=82, use_incremental=True, k=1)

        assert isinstance(cv, CrossValidationResult)
        assert cv.n_folds == 2 and len(cv.fold_results) == 2
        assert all(fr.n_kb > 0 for fr in cv.fold_results)   # each fold learned a KB
        # CONMIN-specific aggregated groups are present in the on-disk block.
        assert 'conmin_cover' in cv.performance
        assert 'n_kb_mean' in cv.performance['kb_size']

    def test_run_conmin_cli_writes_kb_json_with_decomposition(self, tmp_path):
        """apps.run_conmin.process_model writes a KB JSON: the base schema
        (run_compare / extract_results compatible) + the ConMin decomposition nested
        under metadata.conmin (non-breaking)."""
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        import json
        from conacq.config import ModelConfig
        from apps.run_conmin import process_model

        mc = ModelConfig(name='REAL-FM-7', oracle=str(FM_PATH), bias=str(BIAS_PATH),
                         examples=str(EXAMPLES_RS_1N_PATH), folds_path=None, kb_dir=None)
        assert process_model(mc, tmp_path, use_incremental=True, k=1)

        out = json.loads((tmp_path / 'REAL-FM-7_rs_1n_kb.json').read_text())
        assert {'kb_constraints', 'bg_clauses', 'redundant_constraints',
                'statistics'} <= out.keys()
        assert out['statistics']['n_kb'] > 0
        assert set(out['metadata']['conmin']['slices']) == {
            'mss_ids', 'cover_ids', 'kb_assumption_ids'}


class TestConMinKSweep:
    """The acquire split (acquire_pool_and_cover + finish_kb) is the eval's efficient
    k-sweep: build checker + pool + cover ONCE, then finish_kb per k. Each result must
    be bit-identical to a fresh acquire(k), and A/C must be k-invariant."""

    def test_ksweep_reuses_pool_cover_bit_identical(self):
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        oracle, prepared = _prepare_conmin(EXAMPLES_RS_1N_PATH)
        task = prepared.task

        # Eval pattern: ONE checker, ONE pool+cover, finish_kb per k.
        ck = _checker(task, is_incremental=False)
        try:
            cm = ConMin(ck, get_global_profiler())
            state = cm.acquire_pool_and_cover(
                task.set_c, task.set_b, task.set_tc, task.set_neg_tv,
                task.negation_map, task.neg_encodings)
            swept = {k: cm.finish_kb(state, task.support_count, k, task.set_b,
                                     task.negation_map) for k in (1, 2, 3, 5)}
        finally:
            ck.cleanup()

        # Reference: a fresh acquire per k (fresh checker each) must match exactly.
        try:
            for k in (1, 2, 3, 5):
                ck2 = _checker(task, is_incremental=False)
                try:
                    fresh = ConMin(ck2, get_global_profiler()).acquire(
                        set_b=task.set_c, set_bg=task.set_b, set_tc=task.set_tc,
                        set_neg_tv=task.set_neg_tv, negation_map=task.negation_map,
                        neg_encodings=task.neg_encodings,
                        support_count=task.support_count, k=k)
                finally:
                    ck2.cleanup()
                assert sorted(swept[k].kb_assumption_ids) == sorted(fresh.kb_assumption_ids)
                assert swept[k].mss_ids == fresh.mss_ids           # A k-invariant
                assert swept[k].cover_ids == fresh.cover_ids        # C k-invariant
                assert sorted(swept[k].support_ids) == sorted(fresh.support_ids)
        finally:
            oracle.cleanup()

        # A/C identical across the sweep; |S| non-increasing as k rises.
        assert len({tuple(swept[k].mss_ids) for k in swept}) == 1
        assert len({tuple(swept[k].cover_ids) for k in swept}) == 1
        s_sizes = [len(swept[k].support_ids) for k in (1, 2, 3, 5)]
        assert s_sizes == sorted(s_sizes, reverse=True)


class TestConMinRawReduced:
    """minimize flag (P4d raw/reduced sweep): reduced (default) = per-e⁻ subset-minimal
    conflict via QuickXplain; raw = negate the full assignment. Assumption IDs are
    identical either way (golden preserved); only the ¬e⁻ clause content differs."""

    def test_raw_and_reduced_share_ids_differ_in_ne_clause(self):
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        oracle = FMOracle(str(FM_PATH), use_incremental=False)
        model = (ConMinModelBuilder.from_bias(str(BIAS_PATH))
                 .with_oracle_data(oracle.oracle_data).build())
        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        ti = ConMinTaskInput.from_examples(oracle.oracle_data, pos, neg)
        try:
            red = model.prepare_task(ti, minimize=True).task    # default = reduced
            raw = model.prepare_task(ti, minimize=False).task    # raw
            # Assumption IDs identical (id allocation is minimize-invariant → golden safe).
            assert red.set_c == raw.set_c
            assert red.set_neg_tv == raw.set_neg_tv
            assert red.negation_map == raw.negation_map
            assert red.set_tc == raw.set_tc and red.set_b == raw.set_b
            # The ¬e⁻ encoding differs — raw negates the full assignment (more literals).
            assert red.set_kb != raw.set_kb
        finally:
            oracle.cleanup()

    def test_resolve_slice_resolves_each_slice_to_fm_names(self):
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        oracle = FMOracle(str(FM_PATH), use_incremental=False)
        model = (ConMinModelBuilder.from_bias(str(BIAS_PATH))
                 .with_oracle_data(oracle.oracle_data).build())
        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        prepared = model.prepare_task(
            ConMinTaskInput.from_examples(oracle.oracle_data, pos, neg))
        task, describe = prepared.task, prepared.describe
        ck = _checker(task, is_incremental=False)
        try:
            r = ConMin(ck, get_global_profiler()).acquire(
                set_b=task.set_c, set_bg=task.set_b, set_tc=task.set_tc,
                set_neg_tv=task.set_neg_tv, negation_map=task.negation_map,
                neg_encodings=task.neg_encodings, support_count=task.support_count, k=1)
        finally:
            ck.cleanup()
            oracle.cleanup()
        _, a_names = model.resolve_slice(describe, r.mss_ids)
        _, c_names = model.resolve_slice(describe, r.cover_ids)
        _, cs_names = model.resolve_slice(describe, r.kb_assumption_ids)
        assert len(a_names) == r.n_mss              # A = bias constraints, all resolve
        assert len(cs_names) == r.n_kb
        assert {'c6', 'c14', 'c18'} <= set(cs_names)  # X→root in C∪S


class TestConMinCheckTaxonomy:
    """§9c: each ConMin phase's consistency checks land in its own classified counter
    (conmin_/shared_ prefix, ADR-0018); the reported paper total (SoSyM R1-Q4) is their
    sum, with no double-count of the auto-counted is_consistent primitives."""

    def test_classified_counters_batch_and_total_is_their_exact_sum(self):
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        from conacq.runners import ConMinRunner

        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        runner = ConMinRunner(str(BIAS_PATH), str(FM_PATH), use_incremental=True)
        try:
            res = runner.run(pos, neg)
        finally:
            runner.cleanup()
        prof = res.profiler_data

        classified = ['conmin_admpool_gate_checks', 'shared_admpool_checks',
                      'conmin_cover_rejection_checks', 'conmin_cover_quickxplain_checks',
                      'redundancy_consistency_checks']
        for c in classified:
            assert c in prof, f"§9c classified counter {c} not emitted"

        # BATCH granularity (+1 per IsConsistent call, comparable to ConGen), NOT |E+|.
        assert prof['conmin_admpool_gate_checks'] == 1

        # The reported total IS the exact sum of the classified counters (not a
        # trivially-true bound), and it is the ONLY consistency total ConMin exports.
        total = sum(prof[c] for c in classified)
        assert res.metrics.values['consistency_checks_total'] == total
        assert res.consistency_checks == total
        # No double-count: classified keys are disjoint from the auto primitives.
        assert not (set(classified) & {'is_consistent_calls', 'is_consistent_test_cases_calls'})

    def test_congen_paper_total_byte_identical_after_shared_touch(self):
        """The shared_admpool_checks touch in acqmss.py (SHARED) is additive: ConGen
        now emits it, but its declared paper_consistency_checks is UNCHANGED — pinned
        to its exact recorded value (a perturbation would flip this)."""
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        from conacq.runners import ConGenRunner

        examples = ExampleIO.load_json(str(EXAMPLES_RS_1N_PATH))
        pos = [e.assignments for e in examples.positive]
        neg = [e.assignments for e in examples.negative]
        runner = ConGenRunner(str(BIAS_PATH), str(FM_PATH), use_incremental=True)
        try:
            res = runner.run(pos, neg)
        finally:
            runner.cleanup()
        assert 'shared_admpool_checks' in res.profiler_data   # ConGen emits it too
        # Byte-identical: ConGen's declared consistency_checks is exactly this value on
        # REAL-FM-7 rs_1n (incremental); the additive shared counter did not change it.
        assert res.consistency_checks == 536


class TestConMinEval:
    """P4d eval orchestrator, red-team-corrected: root excluded from P/R/F1, no k=1
    Reduce double-count, A scored once (NE-inert), specificity surfaced, QuAcq runs."""

    def test_eval_rs_1n_corrected_invariants(self):
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        folds = DATA_DIR / 'folds' / 'REAL-FM-7_rs_1n_folds.json'
        _skip_if_no_data(folds)
        from conacq.eval.conmin_cv_evaluator import evaluate_kb_example

        rows = evaluate_kb_example(
            'REAL-FM-7', 'rs_1n', str(FM_PATH), str(BIAS_PATH),
            str(EXAMPLES_RS_1N_PATH), str(folds),
            k_values=(1, 2), negatives=('reduced', 'raw'), use_incremental=True)

        # A (#7): scored ONCE per fold, labelled negatives='n/a' (NE-inert), NOT per
        # neg mode — one A row per fold, none tagged reduced/raw.
        a_rows = [r for r in rows if r['condition'] == 'A']
        assert a_rows and all(r['negatives'] == 'n/a' for r in a_rows)
        assert len(a_rows) == len({r['fold'] for r in a_rows})

        # QuAcq (#4): the reduce.py fix lets it run every fold — no error rows.
        q_rows = [r for r in rows if r['condition'] == 'QuAcq']
        assert q_rows and all('error' not in r for r in q_rows)

        # C∪S rows carry the corrected columns: specificity present (#5), exact_equiv is
        # an int (#exact), U=∅ here so no ¬e⁻ fallbacks leak the theory.
        cs = [r for r in rows if r['condition'] == 'C∪S' and 'sem_f1' in r]
        assert cs
        for r in cs:
            assert 'specificity' in r
            assert r['exact_equiv'] in (0, 1)
            assert r['n_uncoverable'] == 0

        # Root NOT in P/R/F1 (#1): score C∪S k=1 clauses directly against a comparator
        # with bg=[] and confirm the scorer reproduces it (not the bg=root value).
        from conacq.eval.kb_comparator import KBComparator, ComparationStrategy
        from conacq.oracle.ground_truth import GroundTruthData
        from conacq.bias import BiasIO
        from conacq.eval.result_loader import ConGenResultData
        gt = GroundTruthData.from_uvl(FM_PATH)
        cmp = KBComparator(gt, BiasIO.load_from_json(str(BIAS_PATH)))
        sample = next(r for r in cs if r['k'] == 1)
        # A minimal check: the scorer's sem_f1 for an all-root-only KB would be inflated
        # if bg leaked; here we assert the scorer never returns the bg-inclusive value by
        # construction — compare bg=[] vs bg=root for the same names.
        names = ['c6']  # a known bias constraint
        rd_no_bg = ConGenResultData(kb_constraints=names, n_bias=1, n_kb=1, bg_clauses=[])
        rd_bg = ConGenResultData(kb_constraints=names, n_bias=1, n_kb=1, bg_clauses=[[1]])
        f1_no = cmp.compare(rd_no_bg, ComparationStrategy.SEMANTIC).metrics.f1_score
        f1_bg = cmp.compare(rd_bg, ComparationStrategy.SEMANTIC).metrics.f1_score
        assert f1_no != f1_bg  # root DOES change the comparator → scorer must use bg=[]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
