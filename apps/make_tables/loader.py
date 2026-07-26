"""Load per-KB ``{KB}_long.csv`` rows, with a torn-read guard for the live sweep.

The sweep writes ``_long.csv`` non-atomically (``run_conmin_eval.py`` uses a plain
``open(path, 'w')`` truncate, unlike the atomic JSON writes), so a read that races
a rewrite can tear. We snapshot the mtime, read, then re-check: if the file changed
mid-read (or fails to parse), the KB is reported "not ready" (-> ``None`` -> all
``--``) rather than loading a partial/corrupt set.

Per-KB files are authoritative. The merged ``conmin_eval_long.csv`` is a stale
strict-subset (no QuAcq-active rows, no ``quacq_*`` counters), so it is deliberately
NOT read here — using it would reintroduce stale rows the STALE gate exists to reject.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def _read_stable(path: Path) -> Optional[list[dict]]:
    """Read a CSV only if it is not being rewritten (mtime stable across the read).

    Returns the rows, or ``None`` when the file is torn/unreadable or keeps changing.
    """
    for attempt in range(_MAX_RETRIES):
        try:
            mtime_before = path.stat().st_mtime_ns
            with open(path, newline="") as f:
                rows = list(csv.DictReader(f))
            if path.stat().st_mtime_ns == mtime_before:
                return rows
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            # UnicodeDecodeError (a ValueError) can arise when a torn read splits a
            # multibyte sequence — treat like any torn read, never crash (Phase-1 criterion).
            logger.warning("torn/unreadable read of %s: %s -> not-ready", path.name, exc)
            return None
        logger.debug("%s changed mid-read (attempt %d) — retrying", path.name, attempt + 1)
    logger.warning("%s kept changing across %d reads — treating as not-ready",
                   path.name, _MAX_RETRIES)
    return None


def load_kb_rows(results_dir: Path, kb: str) -> Optional[list[dict]]:
    """Rows for one KB, or ``None`` if its file is absent / not-ready (-> all ``--``)."""
    path = results_dir / f"{kb}_long.csv"
    if not path.exists():
        logger.info("no %s — KB %s -> all cells '--'", path.name, kb)
        return None
    rows = _read_stable(path)
    if not rows:  # None (torn) or empty/header-only -> not ready, all cells '--'
        logger.info("%s empty/not-ready — KB %s -> all cells '--'", path.name, kb)
        return None
    logger.info("loaded %d rows for %s", len(rows), kb)
    return rows


def load_all(results_dir: Path, kbs) -> dict[str, Optional[list[dict]]]:
    """Map each KB -> its rows (or ``None`` when absent / not-ready)."""
    return {kb: load_kb_rows(results_dir, kb) for kb in kbs}
