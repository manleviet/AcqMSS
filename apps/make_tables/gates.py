"""STALE INPUT + empty-scope gates (v2). Both scoped PER KB, never global.

STALE (v2 "Input freshness gate"): a KB whose QuAcq/QuAcq-active rows predate the
fix schema — blank ``convergence_reason`` or missing counter columns — is forced to
all ``--`` with a banner, so one stale KB never denies the fresh ones. A global abort
happens only if ZERO KBs survive.

Empty-scope (v2 G3): ``quacq_empty_scope_appends`` is reported per KB even when 0;
non-zero on REAL-FM-4 or busybox retires the sweep-wide "precision 1.000" claim, so
the run stops and reports to CW Impl.
"""
from __future__ import annotations

import logging
from typing import Optional

from . import COUNTER_COLS, QUACQ_CONDITIONS

logger = logging.getLogger(__name__)

# Empty-scope on these KBs invalidates the "precision 1.000" claim (v2 G3).
_EMPTY_SCOPE_GATE_KBS = ("REAL-FM-4", "busybox-1.18.0")


def is_stale(kb: str, rows: list[dict]) -> bool:
    """True if this KB's QuAcq rows are pre-fix (blank convergence / no counters)."""
    if not rows:
        return False
    if not any(col in rows[0] for col in COUNTER_COLS):
        logger.warning("STALE INPUT: %s — diagnostic counter columns absent (pre-afaa04b)", kb)
        return True
    for row in rows:
        if row.get("condition") in QUACQ_CONDITIONS and not (row.get("convergence_reason") or "").strip():
            logger.warning("STALE INPUT: %s — %s row with blank convergence_reason",
                           kb, row.get("condition"))
            return True
    return False


def empty_scope_value(kb: str, rows: list[dict]) -> Optional[float]:
    """Sum of ``quacq_empty_scope_appends`` over the KB's rows (None if column absent)."""
    if not rows or "quacq_empty_scope_appends" not in rows[0]:
        return None
    total = 0.0
    for row in rows:
        raw = (row.get("quacq_empty_scope_appends") or "").strip()
        if raw:
            try:
                total += float(raw)
            except ValueError:
                logger.debug("%s: non-numeric quacq_empty_scope_appends %r ignored", kb, raw)
    return total


def check_empty_scope(kb: str, value: Optional[float]) -> bool:
    """Print the per-KB value; return True if the 'precision 1.000' claim must be retired."""
    logger.info("empty_scope_appends[%s] = %s", kb, "--" if value is None else f"{value:g}")
    if value and kb in _EMPTY_SCOPE_GATE_KBS:
        logger.error("empty_scope_appends non-zero on %s (%g) -> sweep-wide 'precision 1.000' "
                     "is OFF — stop and report to CW Impl", kb, value)
        return True
    return False
