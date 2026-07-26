"""PROVENANCE skeleton: source-file mtimes, git SHA, real header length.

The point is an auditable CSV->table link: CW Main re-derives sample cells from
exactly these source files. Phase 3/4 append per-table filter + row counts. Every
value here is derived from the files/git (no wall-clock), so output stays stable.
"""
from __future__ import annotations

import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def _git_sha(repo: Path) -> str:
    """Current HEAD SHA of the repo holding ``repo`` (``unknown`` if unavailable)."""
    try:
        out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=10, check=False)
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def collect(results_dir: Path, loaded: dict) -> dict:
    """Gather source provenance for the loaded KBs (file, mtime, rows, cols, status)."""
    sources = {}
    for kb, rows in loaded.items():
        path = results_dir / f"{kb}_long.csv"
        if not path.exists():
            sources[kb] = {"file": path.name, "status": "absent"}
            continue
        stat = path.stat()
        sources[kb] = {
            "file": path.name,
            "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "n_rows": len(rows) if rows else 0,
            "n_cols": len(rows[0]) if rows else 0,
            "status": "loaded" if rows else "not-ready",
        }
    return {"git_sha": _git_sha(results_dir), "sources": sources}


# eval-prf (Sem, 4 strategies) is the MAIN-text table; the tier mirrors are appendix (CW Main).
_MAIN_TABLE = "eval-prf"
_APPENDIX_PRF = ("app-prf-desc", "app-prf-clause")
_ALL6_TABLES = ("app-quacq-diag", "app-perset", "app-confusion")


def write_skeleton(path: Path, prov: dict, table_labels=(), exclude_2cov: bool = True) -> None:
    """Write ``PROVENANCE.md``: sources, aggregation rules, table variants, and the copy step."""
    lines = [
        "# PROVENANCE — make_tables",
        "",
        f"- git SHA: `{prov['git_sha']}`",
        f"- aggregation: exclude-2COV={'ON (headline tables)' if exclude_2cov else 'OFF'}; "
        f"all-six samplings for {', '.join(_ALL6_TABLES)}. Non-converged "
        "(`convergence_reason` in {timeout, max_queries}) excluded from the mean unless ALL "
        "folds are capped, then reported with a dagger.",
        "- sources (per-KB `_long.csv`, authoritative; the merged CSV is a stale subset, unused):",
        "",
    ]
    for source in prov["sources"].values():
        detail = ", ".join(f"{k}={v}" for k, v in source.items() if k != "file")
        lines.append(f"  - `{source['file']}` — {detail}")
    if table_labels:
        lines += ["", "## Table variants", "",
                  f"- **MAIN**: `{_MAIN_TABLE}` (Semantic tier, A/C/C∪S/QuAcq-active — 16 numeric cols, "
                  "NO accuracy). QuAcq example-only in `app-perset`; accuracy in `app-accuracy`.",
                  f"- **APPENDIX (tier mirrors)**: {', '.join('`' + t + '`' for t in _APPENDIX_PRF if t in table_labels)} "
                  "(same 4 strategies + aggregation + `†`/budget convention as the main table).",
                  "- appendix tables: " + ", ".join(f"`{t}`" for t in table_labels
                                                     if t != _MAIN_TABLE and t not in _APPENDIX_PRF) + "."]
    lines += [
        "", "## `\\input` contract (ruling 3 — NEVER write Overleaf/)", "",
        "- The generator writes ONLY to `data/results_conmin/tables/`. `Overleaf/AAAI/` is a "
        "separate git clone that only Viet-Man pushes (`./sync.sh AAAI push`); an auto-written "
        "artifact there gets overwritten on pull and mixes sources — so it is NEVER touched here.",
        "- The paper uses `\\input{tables/<label>}`. Copy the files across at push time (run "
        "MANUALLY, not by this script):",
        "",
        "  ```bash",
        "  cp data/results_conmin/tables/*.tex Overleaf/AAAI/tables/   # then: ./sync.sh AAAI push",
        "  ```",
    ]
    path.write_text("\n".join(lines) + "\n")
    logger.info("wrote provenance -> %s", path)
