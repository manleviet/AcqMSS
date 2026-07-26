"""The 10 paper tables (v1 §Tables + v2 G1/G3). Each builds a Grid from the Phase-2 core.

Content rules (CW-Impl 2026-07-26): per-KB (never average across KBs); best-value bolding
is the per-row max (``bold_winners``), never a hardcoded winning column; NO ratio/"x" column
comparing ConMin vs QuAcq; the budget/|B| column IS emitted (computed = qa_max_queries/n_bias)
to pre-empt "QuAcq under-budgeted".
"""
from __future__ import annotations

import statistics
from dataclasses import replace
from typing import List

from . import KBS
from .aggregate import cv_mean
from .filters import select
from .formatting import Cell, MISSING, make_cell, bold_winners
from .render import BodyRow, Grid
from .tiers import prf

# Strategy display names (v3: system names in \textsc{}). ConMin == C-union-S.
DISPLAY = {"A": "A", "C": "C", "C∪S": r"\textsc{ConMin}",
           "QuAcq": r"\textsc{QuAcq}", "QuAcq-active": r"\textsc{QuAcq}-a"}
STRATS = ("A", "C", "C∪S", "QuAcq", "QuAcq-active")
CORE_STRATS = ("A", "C", "C∪S", "QuAcq-active")   # eval-prf-core: main-text Sem, 4 strategies (ruling 1)
KB_LABEL = {kb: f"$KB_{{{i + 1}}}$" for i, kb in enumerate(KBS)}
TIERS = (("Desc", "desc"), ("Clause", "clause"), ("Sem", "sem"))


def _note(exclude_2cov: bool) -> str:
    """Caption scope note that matches the actual --exclude-2cov flag (never mis-state scope)."""
    return "Exclude-2COV means." if exclude_2cov else "All six samplings."


def _diag_mean(rows: list, col: str) -> Cell:
    """Mean over ALL folds (incl. budget-capped) — the fairness disclosure must not drop them."""
    vals = []
    for r in rows:
        raw = (r.get(col) or "").strip()
        if raw and raw.lower() != "nan":
            try:
                vals.append(float(raw))
            except ValueError:
                pass
    return Cell(f"{statistics.mean(vals):.1f}", False, False) if vals else Cell(MISSING, False, False)


def _sel(data: dict, kb: str, strat: str, exclude_2cov=True, **kw) -> list:
    rows = data.get(kb)
    return select(rows, strat, exclude_2cov=exclude_2cov, **kw) if rows else []


def _seconds(rows: list) -> Cell:
    st = cv_mean(rows, "total_ms")
    return make_cell(replace(st, value=st.value / 1000.0) if st.value is not None else st, "runtime")


def _budget_ratio(rows: list) -> Cell:
    # A timeout row is bounded by the WALL-CLOCK, not the query budget, so the query-budget/|B|
    # ratio would misrepresent the constraint (5000 was never reached) — show '--' instead.
    if rows and (rows[0].get("convergence_reason") or "") == "timeout":
        return Cell(MISSING, False, False)
    b = cv_mean(rows, "qa_max_queries").value
    nb = cv_mean(rows, "n_bias").value
    return Cell(f"{b / nb:.1f}", False, False) if (b and nb) else Cell(MISSING, False, False)


# ---- 1. eval-prf: KB x tier bands, strategy super-cols, P/R/F1/|KB| ---------------

def _eval_prf(data, exclude_2cov, tier_filter=None, strats=STRATS, label=None, caption=None) -> Grid:
    """P/R/F1/|KB| per KB x strategy for one tier (tier_filter). NO accuracy column (CW Main).

    ``strats``/``label``/``caption`` let the caller emit ``eval-prf`` (main, Sem, 4 strategies,
    exactly 16 numeric cols) and the ``app-prf-desc``/``app-prf-clause`` appendix mirrors — same
    aggregation, dagger, and budget footnote across tiers.
    """
    tiers = TIERS if tier_filter is None else [t for t in TIERS if t[1] == tier_filter]
    banded = tier_filter is None
    headers = (["KB", "tier"] if banded else ["KB"]) + \
        [h for _ in strats for h in ("P", "R", "F1", r"$|\KB|$")]
    body: List[BodyRow] = []
    for ki, kb in enumerate(KBS):
        for ti, (tlabel, prefix) in enumerate(tiers):
            prfs = {s: prf(_sel(data, kb, s, exclude_2cov), prefix) for s in strats}
            f1 = bold_winners([prfs[s]["f1"] for s in strats])
            cells: List[Cell] = []
            for i, s in enumerate(strats):
                cells += [make_cell(prfs[s]["p"]), make_cell(prfs[s]["r"]), f1[i],
                          make_cell(cv_mean(_sel(data, kb, s, exclude_2cov), "n_kb"), "size")]
            if banded:
                lead = [f"\\multirow{{{len(tiers)}}}{{*}}{{{KB_LABEL[kb]}}}" if ti == 0 else "", tlabel]
            else:
                lead = [KB_LABEL[kb]]
            body.append(BodyRow(lead, cells, rule_before=(banded and ti == 0 and ki > 0)))
    if label is None:
        label = "eval-prf" if banded else f"eval-prf-{tier_filter}"
    cap = caption or f"Precision / recall / F1 and $|\\KB|$ per KB and strategy. {_note(exclude_2cov)}"
    return Grid(label, cap, ("ll" if banded else "l") + "cccc" * len(strats),
                headers, body, supercols=[(DISPLAY[s], 4) for s in strats],
                n_leading=2 if banded else 1, full_width=True, tabcolsep="4pt")


# ---- generic per-KB x strategy grid (single or multi metric) ---------------------

def _kb_strat(label, caption, data, metrics, strats=STRATS, exclude_2cov=True,
              bold_metric=None) -> Grid:
    """metrics: list of (header, col, kind). Columns = strategy x metrics."""
    headers = ["KB"] + [f"{h}" for _ in strats for (h, _c, _k) in metrics]
    body = []
    for ki, kb in enumerate(KBS):
        cells: List[Cell] = []
        rowsel = {s: _sel(data, kb, s, exclude_2cov) for s in strats}
        boldset = None
        if bold_metric is not None:
            boldset = bold_winners([cv_mean(rowsel[s], bold_metric) for s in strats])
        for i, s in enumerate(strats):
            for h, col, kind in metrics:
                if col == bold_metric and boldset is not None:
                    cells.append(boldset[i])
                else:
                    cells.append(make_cell(cv_mean(rowsel[s], col), kind))
        body.append(BodyRow([KB_LABEL[kb]], cells))
    supercols = [(DISPLAY[s], len(metrics)) for s in strats] if len(metrics) > 1 else None
    return Grid(label, caption, "l" + "c" * (len(strats) * len(metrics)),
                headers, body, supercols=supercols, full_width=len(strats) * len(metrics) > 6,
                tabcolsep="4pt" if len(strats) * len(metrics) > 6 else None)


# ---- 3. eval-cost (+ budget/|B|) -------------------------------------------------

def _eval_cost(data, exclude_2cov) -> Grid:
    headers = ["KB", r"$|A|$", r"$|C|$", r"$\supp$", r"$|U|$", "checks", "t(s)",
               r"\textsc{QuAcq} t(s)", "q", r"\textsc{QuAcq}-a t(s)", "q", r"budget/$|B|$"]
    body = []
    for kb in KBS:
        cs = _sel(data, kb, "C∪S", exclude_2cov)
        q = _sel(data, kb, "QuAcq", exclude_2cov)
        qa = _sel(data, kb, "QuAcq-active", exclude_2cov)
        cells = [make_cell(cv_mean(cs, "n_mss"), "size"), make_cell(cv_mean(cs, "n_cover"), "size"),
                 make_cell(cv_mean(cs, "n_support"), "size"), make_cell(cv_mean(cs, "n_uncoverable"), "size"),
                 make_cell(cv_mean(cs, "stage1_batch_checks"), "checks"), _seconds(cs),
                 _seconds(q), make_cell(cv_mean(q, "oracle_queries"), "queries"),
                 _seconds(qa), make_cell(cv_mean(qa, "oracle_queries"), "queries"), _budget_ratio(qa)]
        body.append(BodyRow([KB_LABEL[kb]], cells))
    cap = (r"Learning cost. \textsc{ConMin}(raw,$k{=}1$) sizes/checks/time; \textsc{QuAcq} "
           r"time+queries. budget/$|B|$ = \texttt{max\_queries}$/|B|$ (busybox $<1$, below $|B|$); "
           r"a wall-clock-timeout run shows `--` (t(s) is the timeout wall, queries the count "
           r"reached). " + _note(exclude_2cov))
    return Grid("eval-cost", cap, "lrrrrrr rr rr r", headers, body, full_width=True, tabcolsep="4pt")


# ---- 10. app-quacq-diag (all-6, counters + budget/|B|) ---------------------------

_DIAG_COUNTERS = [("drops", "quacq_bandaid_drops"), ("findc?", "quacq_findc_unconfirmed"),
                  ("empty", "quacq_empty_scope_appends"), ("prunP", "quacq_prune_partial_pruned"),
                  ("prunC", "quacq_prune_complete_pruned")]


def _app_quacq_diag(data) -> Grid:
    headers = ["KB", "cond"] + [h for h, _ in _DIAG_COUNTERS] + ["q", "reason", r"budget/$|B|$"]
    body = []
    for ki, kb in enumerate(KBS):
        for ci, cond in enumerate(("QuAcq", "QuAcq-active")):
            rows = _sel(data, kb, cond, exclude_2cov=False)   # all-6: disclosure keeps 2cov
            reasons = sorted({(r.get("convergence_reason") or "") for r in rows})
            reason = "--" if not reasons else (reasons[0] or "--") if len(reasons) == 1 else "mixed"
            if reason == "timeout":            # wall-clock bound: show the ceiling, not the query budget
                secs = cv_mean(rows, "qa_timeout_s").value
                reason = f"timeout({secs:.0f}s)" if secs else "timeout"
            # counters + queries over ALL folds — a fairness disclosure must NOT drop capped folds.
            cells = [_diag_mean(rows, c) for _, c in _DIAG_COUNTERS]
            cells += [_diag_mean(rows, "oracle_queries"),
                      Cell(reason, False, False),   # raw; _latex_cell escapes '_', md keeps it
                      _budget_ratio(rows) if cond == "QuAcq-active" else Cell(MISSING, False, False)]
            lead = [f"\\multirow{{2}}{{*}}{{{KB_LABEL[kb]}}}" if ci == 0 else "", DISPLAY[cond]]
            body.append(BodyRow(lead, cells, rule_before=(ci == 0 and ki > 0)))
    cap = (r"QuAcq fairness diagnostics (all six samplings). empty $=$ empty-scope appends "
           r"(0 $\Rightarrow$ precision claim holds). budget/$|B|$ shows the query budget.")
    return Grid("app-quacq-diag", cap, "ll" + "r" * len(_DIAG_COUNTERS) + "rlr",
                headers, body, n_leading=2, full_width=True, tabcolsep="4pt")


# ---- appendix grids reusing _kb_strat -------------------------------------------

def build_all(data: dict, exclude_2cov: bool = True) -> List[Grid]:
    """Every LaTeX/MD table Grid (order stable). ``data`` maps every KB -> rows or None."""
    RATE, SIZE = "rate", "size"
    # Main eval-prf (Sem, 4 strategies, exactly 16 numeric cols, NO accuracy). Caption points to
    # where the 5th condition (QuAcq example-only) and accuracy are reported (CW Main).
    main_cap = ("Semantic precision / recall / F1 and $|\\KB|$ per KB (exclude-2COV means; "
                "$^{\\dagger}$ = non-converged: \\texttt{max\\_queries} budget or wall-clock "
                "timeout, per-KB reason in Table~\\ref{tab:app-quacq-diag}). The 5th condition "
                "\\textsc{QuAcq} (example-only) is reported in Table~\\ref{tab:app-perset}; "
                "accuracy/specificity in Table~\\ref{tab:app-accuracy}.")
    tier_cap = ("{tier}-tier precision / recall / F1 and $|\\KB|$ per KB — same exclude-2COV "
                "aggregation and $^{{\\dagger}}$/budget convention as Table~\\ref{{tab:eval-prf}}.")
    grids = [
        _eval_prf(data, exclude_2cov, "sem", strats=CORE_STRATS, label="eval-prf", caption=main_cap),         # MAIN
        _eval_prf(data, exclude_2cov, "desc", strats=CORE_STRATS, label="app-prf-desc",
                  caption=tier_cap.format(tier="Description")),                                                # appendix
        _eval_prf(data, exclude_2cov, "clause", strats=CORE_STRATS, label="app-prf-clause",
                  caption=tier_cap.format(tier="Clause")),                                                     # appendix
        _eval_cost(data, exclude_2cov),
        _app_quacq_diag(data),
        # app-perset (all-6): sem-F1 + |KB| per strategy
        _kb_strat("app-perset", "Semantic F1 and $|\\KB|$ per KB and strategy (all six samplings).",
                  data, [("F1", "sem_f1", RATE), (r"$|\KB|$", "n_kb", SIZE)],
                  exclude_2cov=False, bold_metric="sem_f1"),
        # app-accuracy: accuracy + specificity per strategy
        _kb_strat("app-accuracy", "Accuracy and specificity per KB and strategy. " + _note(exclude_2cov),
                  data, [("acc", "accuracy", RATE), ("spec", "specificity", RATE)],
                  exclude_2cov=exclude_2cov, bold_metric="accuracy"),
        # app-confusion (all-6): tp/tn/fp/fn per strategy
        _kb_strat("app-confusion", "Confusion counts per KB and strategy (all six samplings).",
                  data, [("tp", "tp", SIZE), ("tn", "tn", SIZE), ("fp", "fp", SIZE), ("fn", "fn", SIZE)],
                  exclude_2cov=False),
        # app-checks: ConMin per-phase checks
        _kb_strat("app-checks", "\\textsc{ConMin}($k{=}1$) checks by phase per KB. " + _note(exclude_2cov),
                  data, [("gate", "checks_gate", "checks"), ("adm", "checks_admpool", "checks"),
                         ("cRej", "checks_cover_rej", "checks"), ("cQx", "checks_cover_qx", "checks"),
                         ("red", "checks_redundancy", "checks"), ("tot", "checks_total", "checks")],
                  strats=("C∪S",), exclude_2cov=exclude_2cov),
        _app_ksweep(data, exclude_2cov),
        _app_rawred(data, exclude_2cov),
    ]
    return grids


# ---- 6. app-ksweep: ConMin over k in {1,2,3,5} ----------------------------------

def _app_ksweep(data, exclude_2cov) -> Grid:
    KVALS = ("1", "2", "3", "5")
    metrics = [(r"$\supp$", "n_support", "size"), (r"$|\KB|$", "n_kb", "size"),
               ("F1", "sem_f1", "rate"), ("P", "sem_p", "rate"), ("R", "sem_r", "rate"),
               ("acc", "accuracy", "rate")]
    headers = ["KB", "k"] + [h for h, _, _ in metrics]
    body = []
    for ki, kb in enumerate(KBS):
        for kj, k in enumerate(KVALS):
            rows = _sel(data, kb, "C∪S", exclude_2cov, k=k)
            cells = [make_cell(cv_mean(rows, c), kind) for _, c, kind in metrics]
            lead = [f"\\multirow{{4}}{{*}}{{{KB_LABEL[kb]}}}" if kj == 0 else "", f"${k}$"]
            body.append(BodyRow(lead, cells, rule_before=(kj == 0 and ki > 0)))
    return Grid("app-ksweep", "\\textsc{ConMin}(raw) $k$-sweep per KB. " + _note(exclude_2cov),
                "ll" + "c" * len(metrics), headers, body, n_leading=2, full_width=True, tabcolsep="4pt")


# ---- 7. app-rawred: ConMin(k=1) raw vs reduced ----------------------------------

def _app_rawred(data, exclude_2cov) -> Grid:
    metrics = [("F1", "sem_f1", "rate"), ("acc", "accuracy", "rate"),
               (r"$|\KB|$", "n_kb", "size"), ("prep", "preprocessing_checks", "checks")]
    headers = ["KB", "neg"] + [h for h, _, _ in metrics]
    body = []
    for ki, kb in enumerate(KBS):
        for ni, neg in enumerate(("raw", "reduced")):
            rows = _sel(data, kb, "C∪S", exclude_2cov, negatives=neg)
            cells = [make_cell(cv_mean(rows, c), kind) for _, c, kind in metrics]
            lead = [f"\\multirow{{2}}{{*}}{{{KB_LABEL[kb]}}}" if ni == 0 else "", neg]
            body.append(BodyRow(lead, cells, rule_before=(ni == 0 and ki > 0)))
    return Grid("app-rawred", "\\textsc{ConMin}($k{=}1$) raw vs reduced (F1/acc/$|\\KB|$ agree). " + _note(exclude_2cov),
                "ll" + "c" * len(metrics), headers, body, n_leading=2, full_width=False)


# ---- exact-equiv (Markdown reference only) ---------------------------------------

_COND_NAME = {"A": "A", "C": "C", "C∪S": "ConMin",
              "QuAcq": "QuAcq(exonly)", "QuAcq-active": "QuAcq-active"}


def exact_equiv_counts(rows: list, cond: str):
    """(rows_attaining, rows_scored, configs_all_folds, n_configs) for one KB x condition.

    A 'configuration' = (example_set, k, negatives); it 'attains' when ALL its folds do.
    Returns None for QuAcq-active (learned once/KB → collapse, handled by the caller).
    """
    sub = [r for r in rows if r.get("condition") == cond]
    attain = sum(1 for r in sub if r.get("exact_equiv") == "1")
    by_cfg: dict = {}
    for r in sub:
        by_cfg.setdefault((r.get("example_set"), r.get("k"), r.get("negatives")), []) \
            .append(r.get("exact_equiv") == "1")
    cfg_all = sum(1 for v in by_cfg.values() if v and all(v))
    return attain, len(sub), cfg_all, len(by_cfg)


def exact_equiv_md(data) -> str:
    """Reference: exact-equivalence COUNTS per KB x condition (reproducible from `_long.csv`)."""
    lines = ["# exact-equiv (reference — attainment counts per KB × condition)", "",
             "exact-equivalence is logical equivalence of the delivered theory (including BG) via "
             "`SemanticEquivalenceChecker`; it does NOT require the named-constraint P/R/F1 "
             "(name-set only, BG excluded) to be 1.",
             "Counts are reproducible from the committed `_long.csv` (same principle as the "
             "band-aid counters). A *configuration* = (example_set, k, negatives); it attains only "
             "when ALL its folds do.",
             "> **QuAcq-active is learned once per KB and scored on every fold** — its 18 identical "
             "rows are ONE observation, so the denominator is collapsed to 1, NOT 18.", "",
             "| KB | condition | rows attaining / scored | configs (all-folds) / total |",
             "|---|---|---|---|"]
    for kb in KBS:
        rows = data.get(kb)
        for cond in STRATS:
            name = _COND_NAME[cond]
            if not rows:
                lines.append(f"| {KB_LABEL[kb]} | {name} | -- | -- |")
                continue
            if cond == "QuAcq-active":                       # collapse: one observation per KB
                sub = [r for r in rows if r.get("condition") == cond]
                attained = bool(sub) and all(r.get("exact_equiv") == "1" for r in sub)
                lines.append(f"| {KB_LABEL[kb]} | {name} | "
                             f"{1 if attained else 0} / 1 obs (learned once/KB) | n/a |")
                continue
            a, n, cfg_all, ncfg = exact_equiv_counts(rows, cond)
            rowcell = f"{a} / {n} ({round(100 * a / n)}%)" if n else "--"
            lines.append(f"| {KB_LABEL[kb]} | {name} | {rowcell} | {cfg_all} / {ncfg} |")
    lines += ["", "Text sentence (v1): among the passive strategies, exact structural equivalence "
              "is attained only on REAL-FM-7 (ConMin 8/144 rows = 6%, but 0/48 configurations "
              "across all folds; A 1/18); elsewhere 0. (busybox pending its overnight run.)"]
    return "\n".join(lines) + "\n"
