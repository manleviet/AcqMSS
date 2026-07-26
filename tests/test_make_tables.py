"""Unit tests for apps.make_tables (Phase-2 core, gates, self-checks, renderers)."""
from __future__ import annotations

from apps.make_tables import gates, selfcheck
from apps.make_tables.aggregate import cv_mean
from apps.make_tables.filters import select
from apps.make_tables.formatting import Cell, bold_winners, fmt, make_cell
from apps.make_tables.render import BodyRow, Grid, latex, markdown
from apps.make_tables.tiers import prf


def _row(condition="C∪S", negatives="raw", k="1", example_set="rs_1n", fold="0",
         convergence_reason="", kb="REAL-FM-7", **cols):
    r = dict(kb=kb, example_set=example_set, fold=fold, condition=condition,
             negatives=negatives, k=k, convergence_reason=convergence_reason)
    r.update({c: str(v) for c, v in cols.items()})
    return r


# ---- filters -------------------------------------------------------------------

def test_filter_exact_condition_negatives_k():
    rows = [_row(condition="C∪S", negatives="raw", k="1"),
            _row(condition="C∪S", negatives="raw", k="2"),      # wrong k
            _row(condition="C∪S", negatives="reduced", k="1"),  # wrong negatives
            _row(condition="A", negatives="n/a", k="")]
    assert len(select(rows, "C∪S")) == 1          # only (C∪S, raw, 1)
    assert len(select(rows, "A")) == 1
    assert len(select(rows, "C∪S", k="2")) == 1   # k override
    assert len(select(rows, "C∪S", negatives="reduced")) == 1


def test_filter_exclude_2cov():
    rows = [_row(example_set="2cov"), _row(example_set="rs_1n")]
    assert len(select(rows, "C∪S")) == 1                       # 2cov dropped by default
    assert len(select(rows, "C∪S", exclude_2cov=False)) == 2


# ---- aggregation ---------------------------------------------------------------

def test_cv_mean_equal_fold_skip_nan():
    rows = [_row(sem_f1="0.2"), _row(sem_f1="0.4"), _row(sem_f1="nan"), _row(sem_f1="")]
    st = cv_mean(rows, "sem_f1")
    assert abs(st.value - 0.3) < 1e-9 and st.n == 2


def test_cv_mean_nonconverged_excluded():
    rows = [_row(convergence_reason="", sem_f1="0.9"),
            _row(convergence_reason="timeout", sem_f1="0.1")]
    st = cv_mean(rows, "sem_f1")
    assert abs(st.value - 0.9) < 1e-9 and st.nonconverged is False


def test_cv_mean_all_nonconverged_reported_and_flagged():
    rows = [_row(convergence_reason="max_queries", sem_f1="0.03", qa_max_queries="5000"),
            _row(convergence_reason="max_queries", sem_f1="0.05", qa_max_queries="5000")]
    st = cv_mean(rows, "sem_f1")
    assert abs(st.value - 0.04) < 1e-9
    assert st.nonconverged is True and st.reason == "max_queries" and st.qa_max_queries == "5000"


def test_cv_mean_std_zero_for_constant():
    rows = [_row(n_kb="12") for _ in range(3)]
    assert cv_mean(rows, "n_kb").std == 0.0


def test_tiers_prf_three_tiers():
    rows = [_row(desc_f1="0.5", clause_f1="0.6", sem_f1="0.7")]
    assert abs(prf(rows, "desc")["f1"].value - 0.5) < 1e-9
    assert abs(prf(rows, "sem")["f1"].value - 0.7) < 1e-9


# ---- formatting ----------------------------------------------------------------

def test_fmt_rounding_and_missing():
    assert fmt(cv_mean([_row(sem_f1="1.0")], "sem_f1")) == "1.00"          # trailing zeros
    assert fmt(cv_mean([_row(n_kb="12")], "n_kb"), "size") == "12.0"
    assert fmt(cv_mean([_row(x="7534.4")], "x"), "checks") == "7534"
    assert fmt(cv_mean([], "sem_f1")) == "--"


def test_bold_winners_marks_max():
    stats = [cv_mean([_row(sem_f1="0.5")], "sem_f1"), cv_mean([_row(sem_f1="0.8")], "sem_f1")]
    cells = bold_winners(stats)
    assert cells[0].bold is False and cells[1].bold is True


# ---- gates ---------------------------------------------------------------------

def test_gate_stale_on_blank_convergence_quacq():
    rows = [_row(condition="QuAcq", convergence_reason="", quacq_empty_scope_appends="0")]
    assert gates.is_stale("k", rows) is True


def test_gate_not_stale_when_stage1_blank_but_quacq_ok():
    rows = [_row(condition="A", convergence_reason="", quacq_empty_scope_appends="0"),
            _row(condition="QuAcq", convergence_reason="pool_exhausted", quacq_empty_scope_appends="0")]
    assert gates.is_stale("k", rows) is False


def test_gate_empty_scope_trips_on_gate_kb():
    rows = [_row(condition="QuAcq-active", convergence_reason="max_queries",
                 quacq_empty_scope_appends="5")]
    val = gates.empty_scope_value("REAL-FM-4", rows)
    assert val == 5.0 and gates.check_empty_scope("REAL-FM-4", val) is True
    assert gates.check_empty_scope("REAL-FM-7", val) is False       # non-gate KB


# ---- self-checks ---------------------------------------------------------------

def test_selfcheck_anchor_pass_and_drift():
    # RE7 C∪S sem_f1 anchor is 0.847; feed matching rows -> pass; shifted -> drift.
    ok = [_row(kb="REAL-FM-7", condition="C∪S", sem_f1="0.847") for _ in range(3)]
    passed, fails, _ = selfcheck.check_anchors({"REAL-FM-7": ok})
    assert passed >= 1 and not any(t.endswith("C∪S/sem_f1") for t, *_ in fails)
    bad = [_row(kb="REAL-FM-7", condition="C∪S", sem_f1="0.900") for _ in range(3)]
    _, fails2, _ = selfcheck.check_anchors({"REAL-FM-7": bad})
    assert any("C∪S/sem_f1" in t for t, *_ in fails2)


# ---- renderers -----------------------------------------------------------------

def test_render_latex_booktabs_dagger_thousands():
    grid = Grid("t", "cap", "lcc", ["KB", "F1", "checks"],
                [BodyRow(["$KB_1$"], [Cell("0.03", True, False), Cell("7534", False, True)])])
    out = latex(grid)
    assert "\\toprule" in out and "\\tabularnewline" in out and "\\hline" not in out
    assert "$0.03^{\\dagger}$" in out and "$7{,}534$" in out and "\\textbf" in out
    assert out.rstrip().endswith("\\end{table}")


def test_render_markdown_demacro_multirow():
    grid = Grid("t", "cap", "ll", ["KB", "x"],
                [BodyRow(["\\multirow{2}{*}{$KB_{1}$}"], [Cell("0.5", False, False)])])
    md = markdown(grid)
    assert "$KB_{1}$" in md and "multirow" not in md
