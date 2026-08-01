"""Unit tests for apps.make_tables (Phase-2 core, gates, self-checks, renderers)."""
from __future__ import annotations

from apps.make_tables import gates, selfcheck
from apps.make_tables.aggregate import cv_mean
from apps.make_tables.filters import select
from apps.make_tables.formatting import Cell, bold_winners, fmt, make_cell
from apps.make_tables.render import BodyRow, Grid, latex, markdown, prf_compact
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

def _re7_fixture(cus_sem="0.847"):
    """A REAL-FM-7 fixture covering every RE7 anchor (so none is 'broken')."""
    rows = []

    def add(cond, neg, k, **cols):
        for fold in "012":
            rows.append(_row(kb="REAL-FM-7", condition=cond, negatives=neg, k=k, fold=fold, **cols))

    add("A", "n/a", "", sem_f1="0.605")
    add("C∪S", "raw", "1", sem_f1=cus_sem, desc_f1="0.682")
    add("QuAcq", "n/a", "", sem_f1="0.012")
    add("QuAcq-active", "n/a", "", sem_f1="0.842", desc_f1="0.240", n_kb="12", oracle_queries="272")
    return {"REAL-FM-7": rows}


def test_selfcheck_anchor_pass_drift_and_broken():
    # matching values -> all RE7 anchors pass; fqa/arcade/RE4 legitimately skip (KB not loaded)
    passed, fails, skipped = selfcheck.check_anchors(_re7_fixture())
    assert not fails and passed >= 8 and skipped > 0
    # drift on one anchor -> failure
    _, fails2, _ = selfcheck.check_anchors(_re7_fixture(cus_sem="0.900"))
    assert any("C∪S/sem_f1" in t for t, *_ in fails2)
    # empty cell on a LOADED KB -> BROKEN (failure), not a silent skip (red-team C1)
    broken = {"REAL-FM-7": [_row(kb="REAL-FM-7", condition="C∪S", sem_f1="") for _ in range(3)]}
    _, fails3, _ = selfcheck.check_anchors(broken)
    assert any("C∪S/sem_f1" in t for t, *_ in fails3)


# ---- renderers -----------------------------------------------------------------

def test_render_latex_booktabs_dagger_thousands_bold():
    grid = Grid("t", "cap", "lcccc", ["KB", "F1", "checks", "r", "big"],
                [BodyRow(["$KB_1$"], [Cell("0.03", True, False), Cell("7534", False, True),
                                      Cell("0.85", False, True), Cell("4729.8", False, False)])])
    out = latex(grid)
    assert "\\toprule" in out and "\\tabularnewline" in out and "\\hline" not in out
    assert "$0.03^{\\dagger}$" in out          # dagger -> math
    assert "$\\mathbf{7{,}534}$" in out         # bold thousands -> \mathbf (in-math bold), not \textbf
    assert "\\textbf{0.85}" in out             # bold plain rate -> \textbf (text mode)
    assert "$4{,}729.8$" in out                # >=1000 FLOAT grouped too (red-team M3)
    assert out.rstrip().endswith("\\end{table}")


def test_render_latex_escapes_tex_specials():
    grid = Grid("t", "cap", "lc", ["KB", "reason"],
                [BodyRow(["$KB_1$"], [Cell("a_b&c%d", False, False)])])
    out = latex(grid)
    assert "a\\_b\\&c\\%d" in out               # _, &, % all escaped (red-team M5)


def test_render_markdown_demacro_multirow():
    grid = Grid("t", "cap", "ll", ["KB", "x"],
                [BodyRow(["\\multirow{2}{*}{$KB_{1}$}"], [Cell("0.5", False, False)])])
    md = markdown(grid)
    assert "$KB_{1}$" in md and "multirow" not in md


# ---- compact / raw cells (paper layout) ----------------------------------------

def test_prf_compact_drops_leading_zero_and_keeps_bold_and_dagger():
    """`.p/.r/.f1` folding must survive both markers: a sub-1 rate loses its leading zero,
    1.00 keeps its digit, \\textbf stays bold and a non-converged value stays daggered."""
    cell = prf_compact([Cell("1.00", False, False), Cell("0.03", True, False),
                        Cell("0.85", False, True)])
    assert cell.raw is True
    assert cell.text == "1.00/$.03^{\\dagger}$/\\textbf{.85}"


def test_markdown_raw_cell_keeps_markers_but_row_label_keeps_dollars():
    """Regression: the raw-cell Markdown path strips ``$`` and rewrites \\textbf, which is right for
    a DATA cell and wrong for a row label — one shared de-macro helper broke ``$KB_{1}$``."""
    grid = Grid("t", "cap", "ll", ["KB", "P/R/F1"],
                [BodyRow(["$KB_{1}$"],
                         [prf_compact([Cell("1.00", False, False), Cell("0.03", True, False),
                                       Cell("0.85", False, True)])])])
    md = markdown(grid)
    assert "$KB_{1}$" in md                      # label untouched
    assert "1.00/.03†/**.85**" in md             # data cell de-macroed


def test_supercol_spacer_emits_blank_cells_and_no_rule():
    """An empty super-column name is a spacer. The blank cells MUST be emitted: a short header row
    silently shifts every later \\multicolumn left of the \\cmidrule meant to underline it."""
    grid = Grid("t", "cap", "lcccc", ["KB", "a", "b", "c", "d"],
                [BodyRow(["x"], [Cell("1", False, False)] * 4)],
                supercols=[("first", 1), ("", 2), ("last", 1)])
    head = [ln for ln in latex(grid).splitlines() if "multicolumn" in ln][0]
    assert head.count("&") == 4                  # 1 leading + 1 + 2 spacers + 1 = 5 cells
    rules = [ln for ln in latex(grid).splitlines() if "cmidrule" in ln][0]
    assert rules.count("cmidrule") == 2          # spacer contributes no rule
    assert "{5-5}" in rules                      # 'last' underlines col 5, not col 3
