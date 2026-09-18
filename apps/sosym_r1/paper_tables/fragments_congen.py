"""The fragments describing ConGen alone: inputs, cost, and learned-KB quality.

Every builder returns exactly one ``tabular`` environment. Rows are the six
sampling strategies in the paper's order and columns are $KB_1$..$KB_5$, unless
the quantity is per-KB only (``tab:fm_summary``), in which case the KBs are rows.
"""
from __future__ import annotations

from pathlib import Path

from . import latex as tex
from .frozen import (KB_LABELS, KNOWLEDGE_BASES, SAMPLINGS, TIERS, is_not_run)
from .read_results import ResultTree, bias_stats, example_sizes


def _grid(tree: ResultTree, value):
    """rows = sampling, columns = KB; ``value(folds, stem, samp)`` fills a cell."""
    rows = []
    for samp, samp_label in SAMPLINGS:
        cells = [samp_label]
        for stem, *_ in KNOWLEDGE_BASES:
            not_run = is_not_run(stem, samp)
            folds = [] if not_run else tree.require(stem, samp)
            cells.append(value(folds, stem, samp, not_run))
        rows.append(cells)
    return rows


def fm_summary(tree: ResultTree, data: Path) -> str:
    """#features, |B|, #clauses and the domain, one row per knowledge base.

    Static inputs, not results -- generated anyway so the gate covers them. |B| and
    #clauses are read from the committed bias statistics rather than recounted
    here: those files are what the bias generator actually produced, and a second
    count of the same thing would be a second chance to be wrong.
    """
    rows = []
    for stem, label, short, domain in KNOWLEDGE_BASES:
        s = bias_stats(data / "bias", stem)
        rows.append([f"{label} ({short})", tex.count(s["features"]),
                     tex.count(s["bias"]), tex.count(s["clauses"]), domain])
    return tex.tabular("lrrrl",
                       [["", r"\#features", r"$|B|$", r"\#clauses", "domain"]], rows)


def example_sizes_table(tree: ResultTree, data: Path) -> str:
    """|E+| and |E-| per knowledge base and sampling strategy."""
    header = [[""] + [tex.multicolumn(2, lb) for lb in KB_LABELS],
              ["Strategy"] + [c for _ in KB_LABELS for c in (r"$|E^+|$", r"$|E^-|$")]]
    rules = [tex.cmidrules(len(KB_LABELS), 2), ""]
    rows = []
    for samp, samp_label in SAMPLINGS:
        cells = [samp_label]
        for stem, *_ in KNOWLEDGE_BASES:
            if is_not_run(stem, samp):
                # One marker spanning both columns: the unit was not run, so neither
                # |E+| nor |E-| exists, and two separate markers would suggest two
                # separate absences.
                cells.append(tex.multicolumn(2, tex.NA))
                continue
            sizes = example_sizes(data / "examples", stem, samp)
            cells += [tex.count(sizes[0]), tex.count(sizes[1])]
        rows.append(cells)
    return tex.tabular("l" + "rr" * len(KB_LABELS), header, rows, rules)


def acqmss_runtime(tree: ResultTree, data: Path) -> str:
    """AcqMss consistency checks / runtime (ms), the paper's two-quantity shape."""
    def cell(folds, stem, samp, not_run):
        if not_run:
            return tex.NA
        checks = tree.consistency_checks(folds)
        ms = tree.runtime_ms(folds)
        return f"{tex.count(checks)}~/~{tex.millis(ms)}"
    return tex.tabular("l" + "r" * len(KB_LABELS),
                       [["Strategy", *KB_LABELS]], _grid(tree, cell))


def acqmss_phases(tree: ResultTree, data: Path) -> str:
    """Per-phase cost: AcqMss, Reduce, preprocessing, and the total including it.

    Three phases and a total, per knowledge base, as the mean over the six sampling
    strategies' per-fold means. Checks above runtime, both in the paper's units.

    WHY THE MEAN OVER SAMPLINGS: the per-phase story is about the algorithm's shape
    -- Reduce is linear in |B'| while AcqMss is logarithmic in n/gamma -- and that
    shape does not depend on which sampler produced the examples. A 6x5 grid per
    phase would be four tables, and none of them would say anything the shape does
    not already say.
    """
    rows = []
    phases = (("AcqMss", "acqmss"), (r"\textsc{Reduce}", "reduce"),
              ("GenerateNE / QuickXplain", "preprocessing"), ("total", "total"))
    for quantity, fmt in (("checks", tex.count), ("runtime (ms)", tex.millis)):
        for phase_label, key in phases:
            cells = [f"{quantity}, {phase_label}"]
            for stem, *_ in KNOWLEDGE_BASES:
                vals = []
                for samp, _ in SAMPLINGS:
                    if is_not_run(stem, samp):
                        continue
                    folds = tree.require(stem, samp)
                    block = (tree.phase_checks(folds) if quantity == "checks"
                             else tree.phases_ms(folds))
                    if block[key] is not None:
                        vals.append(block[key])
                cells.append(fmt(sum(vals) / len(vals) if vals else None))
            rows.append(cells)
    return tex.tabular("l" + "r" * len(KB_LABELS),
                       [["Quantity and phase", *KB_LABELS]], rows)


def accuracy_all(tree: ResultTree, data: Path) -> str:
    """Predictive accuracy, mean $\\pm$ standard deviation over the three folds."""
    def cell(folds, stem, samp, not_run):
        if not_run:
            return tex.NA
        mean, sd = tree.accuracy(folds)
        return tex.plus_minus(mean, sd)
    return tex.tabular("l" + "r" * len(KB_LABELS),
                       [["Strategy", *KB_LABELS]], _grid(tree, cell))


def comparison_strategies(tree: ResultTree, data: Path) -> str:
    """F1 under each of the three comparison strategies.

    PER-FOLD MEAN, not the intersected knowledge base. The two are different
    quantities and the submitted table printed the second under a per-fold label.
    """
    header = [[""] + [tex.multicolumn(3, lb) for lb in KB_LABELS],
              ["Strategy"] + [short for _ in KB_LABELS for _t, short in TIERS]]
    rules = [tex.cmidrules(len(KB_LABELS), 3), ""]
    rows = []
    for samp, samp_label in SAMPLINGS:
        cells = [samp_label]
        for stem, *_ in KNOWLEDGE_BASES:
            if is_not_run(stem, samp):
                cells.append(tex.multicolumn(3, tex.NA))
                continue
            folds = tree.require(stem, samp)
            cells += [tex.quality(tree.tier_f1(folds, t)) for t, _ in TIERS]
        rows.append(cells)
    return tex.tabular("l" + "rrr" * len(KB_LABELS), header, rows, rules)


def semantic_pr(tree: ResultTree, data: Path) -> str:
    """Semantic precision, recall, and exact equivalence as attained/scored.

    ONE TABLE, not two. Precision and recall are the two halves of the semantic
    tier and are read together; exact equivalence is the same question asked at
    its strictest, and a reader who sees 1.000 recall beside 0/3 equivalence has
    learned something that two separate tables would have kept apart.
    """
    header = [[""] + [tex.multicolumn(3, lb) for lb in KB_LABELS],
              ["Strategy"] + [c for _ in KB_LABELS for c in ("P", "R", "eq.")]]
    rules = [tex.cmidrules(len(KB_LABELS), 3), ""]
    rows = []
    for samp, samp_label in SAMPLINGS:
        cells = [samp_label]
        for stem, *_ in KNOWLEDGE_BASES:
            if is_not_run(stem, samp):
                cells.append(tex.multicolumn(3, tex.NA))
                continue
            folds = tree.require(stem, samp)
            attained, scored = tree.exact_equivalence(folds)
            cells += [tex.quality(tree.semantic(folds, "precision")),
                      tex.quality(tree.semantic(folds, "recall")),
                      (f"{attained}/{scored}" if scored else tex.UNDEFINED)]
        rows.append(cells)
    return tex.tabular("l" + "rrr" * len(KB_LABELS), header, rows, rules)


def kb_size(tree: ResultTree, data: Path) -> str:
    """|MSS| before Reduce and |KB| after it, both per-fold means.

    |KB| is ``statistics.n_kb`` as the corrected scorer defines it: the constraints
    the run finished with, negative-example constraints included where the run
    kept them. That policy is what the accuracy and F1 columns were scored against,
    so a different count here would not describe the same knowledge base.
    """
    header = [[""] + [tex.multicolumn(2, lb) for lb in KB_LABELS],
              ["Strategy"] + [c for _ in KB_LABELS for c in (r"$|MSS|$", r"$|KB|$")]]
    rules = [tex.cmidrules(len(KB_LABELS), 2), ""]
    rows = []
    for samp, samp_label in SAMPLINGS:
        cells = [samp_label]
        for stem, *_ in KNOWLEDGE_BASES:
            if is_not_run(stem, samp):
                cells.append(tex.multicolumn(2, tex.NA))
                continue
            folds = tree.require(stem, samp)
            cells += [tex.count(tree.statistic(folds, "n_mss")),
                      tex.count(tree.statistic(folds, "n_kb"))]
        rows.append(cells)
    return tex.tabular("l" + "rr" * len(KB_LABELS), header, rows, rules)
