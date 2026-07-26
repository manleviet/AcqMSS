"""Row-level CV aggregation for one table cell (v1 aggregation + v2 G2).

A cell = the mean over ALL rows already filtered to (condition, negatives, k) and
exclude-2COV — pooled across samplings AND folds, each fold weighted equally, NOT a
mean-of-per-sampling-means. Non-converged folds (``convergence_reason`` in
{timeout, max_queries}) are excluded from the mean, mirroring
``conacq.eval.conmin_cv_evaluator.aggregate_cv`` (~line 409, the single source of
truth for that partition). If EVERY fold is non-converged (v2 G2.3) the cell is
still reported — the recall lower bound we must disclose — but flagged so the LaTeX
renderer marks it with a dagger, never ``--``.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Optional

# Mirrors conacq/eval/conmin_cv_evaluator.py::aggregate_cv (~:409): the ONLY reasons that
# mark a partial (non-converged) theory. pool_exhausted / no_query / empty_bias / '' converge.
NONCONVERGED_REASONS = ("timeout", "max_queries")


@dataclass(frozen=True)
class CellStat:
    """One aggregated cell: value + dispersion + convergence provenance."""
    value: Optional[float]        # None -> render as '--'
    std: float = 0.0
    n: int = 0                    # folds/rows averaged
    nonconverged: bool = False    # every fold capped -> dagger (still reported)
    reason: str = ""              # convergence reason to name in the dagger caption
    qa_max_queries: str = ""      # budget provenance for the caption (read from the row)
    qa_timeout_s: str = ""


def _to_float(raw) -> Optional[float]:
    """Parse a CSV cell to float; blank / 'nan' / unparseable -> None (skip in the mean)."""
    if raw is None:
        return None
    text = raw.strip() if isinstance(raw, str) else raw
    if text == "" or (isinstance(text, str) and text.lower() == "nan"):
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def cv_mean(rows: list[dict], col: str) -> CellStat:
    """Mean of ``col`` over already-filtered ``rows``, excluding non-converged folds."""
    if not rows:
        return CellStat(value=None)
    converged = [r for r in rows if r.get("convergence_reason") not in NONCONVERGED_REASONS]
    all_nonconv = not converged            # v2 G2.3: report + dagger, never '--'
    used = rows if all_nonconv else converged
    vals = [v for r in used if (v := _to_float(r.get(col))) is not None]
    if not vals:
        return CellStat(value=None, nonconverged=all_nonconv)
    rep = used[0]
    return CellStat(
        value=statistics.mean(vals),
        std=statistics.stdev(vals) if len(vals) > 1 else 0.0,
        n=len(vals),
        nonconverged=all_nonconv,
        reason=(rep.get("convergence_reason") or "") if all_nonconv else "",
        qa_max_queries=(rep.get("qa_max_queries") or "") if all_nonconv else "",
        qa_timeout_s=(rep.get("qa_timeout_s") or "") if all_nonconv else "",
    )
