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
from conacq.algorithms.conmin import AcqMinCover, NegEncoding
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

        # Prep field parity (teeth: preparation divergence between the pipelines).
        assert list(mt.set_c) == list(ct.set_c)
        assert list(mt.set_b) == list(ct.set_b)
        assert list(mt.set_tc) == list(ct.set_tc)
        assert list(mt.set_neg_tv) == list(ct.set_neg_tv)
        assert mt.negation_map == ct.negation_map

        # ConMin's MSS equals AcqMSS run on the ConGen task (exact set).
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
        """
        _skip_if_no_data(FM_PATH, BIAS_PATH, EXAMPLES_RS_1N_PATH)
        _oracle, prepared = _prepare_conmin(EXAMPLES_RS_1N_PATH)
        result = _acquire(prepared.task, is_incremental=True)
        assert result.n_mss == GOLDEN_MSS_RS_1N_N
        assert _mss_names_sha(result.mss_ids, prepared.describe) == GOLDEN_MSS_RS_1N_SHA


# --------------------------------------------------------------------------- #
# P3 — de-delegation on real data (ff, 3 negatives), REAL checker
# --------------------------------------------------------------------------- #

class TestConMinDeDelegation:
    """The P3 de-delegation: real per-e- neg_encodings + per-e- negation registration.

    NOT a cover-correctness test — the ff negatives violate the FM root, so
    `is_consistent(root ∪ e-)` is UNSAT for some and `cand` degenerates (the
    rejection-test-BG-on-real-FMs question is a deferred P4 decision). This gate
    asserts the invariants that hold regardless: neg_encodings captured, the
    Critical fix (per-e- negations registered), and that the rejection test
    *discriminates* on a BG-consistent negative (a proper, non-saturated subset).
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

        # (3) the rejection test discriminates on a BG-consistent negative: its cand
        # is a proper, non-empty subset of A (not saturated to all-of-A).
        checker = _checker(task, is_incremental=True)
        try:
            bg = list(task.set_b)
            admissible = AcqMSS(checker, m=1, profiler_instance=get_global_profiler()).find_mss(
                delta=[], set_b=list(task.set_c), set_neg_tv=list(task.set_neg_tv),
                set_tc=list(task.set_tc), set_bg=bg)
            bg_consistent = [ne for ne in task.neg_encodings
                             if checker.is_consistent(bg + list(ne.assumption_ids))]
            assert bg_consistent, "expected >=1 BG-consistent negative in the ff fixture"
            ne = bg_consistent[0]
            cand = [c for c in admissible
                    if not checker.is_consistent([c] + bg + list(ne.assumption_ids))]
            assert 0 < len(cand) < len(admissible)  # discriminates (not saturated)
        finally:
            checker.cleanup()


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
