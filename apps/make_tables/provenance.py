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

# Genuine/over-strong/redundant (G/S/R) split of the QuAcq-active band-aid drops, from an OFFLINE
# entailment classification (NOT emitted by the runner). IN-REPO source of record is the committed
# `data/results_conmin/genuine_split.md` (upstream origin: the Cowork vault findings note section
# A2, 2026-07-26, which the AAAI package does not ship). Committing that copy makes the values
# CITABLE in-repo (traceability); it does NOT make them re-derivable — the per-drop classification
# was never persisted, so unlike the 8/144 exact-equivalence figures these values are NOT
# re-derivable from the committed `_long.csv`. The two committed reports are the PRE-FIX probe
# (23 drops / 14 true, superseded/overcounted) — method only. When a real per-drop classification
# lands, REPLACE genuine_split.md with genuine_classification.json and drop the not-re-derivable
# clause below (a replacement, not a rewrite). Edit this constant (diffable) on re-measurement; do
# not hand-edit PROVENANCE.md (regenerated every run).
_GENUINE_SPLIT = (
    "- **genuine-drop split (G/S/R)** — QuAcq-active band-aid drops classified genuine (G) / "
    "over-strong (S) / redundant (R) by an OFFLINE entailment classification, NOT emitted by the "
    "runner: REAL-FM-7 **1 of 10**, fqa **150 of 354**, arcade-game **35 of 56 — STALE** (superseded "
    "by the fair-budget re-run: raw is now 326; the per-query rate 56/863 = 0.0649 vs 326/5000 = "
    "0.0652 confirms a longer re-run, not a counter-semantics change). Measured **2026-07-26**; the "
    "classification commit was not recorded. **In-repo source of record: "
    "`data/results_conmin/genuine_split.md`** — committed so this citation resolves in-repo "
    "(**traceability only**); its upstream origin is the Cowork vault findings note "
    "`ConMin - Evaluation findings (for writing).md` section A2, which the AAAI package does not "
    "ship. The two committed fairness-measurement reports under `plans/` "
    "(`from-code-reviewer-to-cw-impl-260726-fairness-measurement-redteam.md`, "
    "`from-code-reviewer-to-cw-impl-260726-quacq-active-fairness-measurement.md`) are the **PRE-FIX "
    "probe** (23 drops / 14 true on a superseded 342-query run — the 14-true figure was later found "
    "to overcount; the current post-fix run is 272 queries, `no_query`): cite them for the "
    "classification **method only**, NOT for these values. **These values remain NOT re-derivable "
    "from the committed `_long.csv`** (unlike the 8/144 exact-equivalence figures) — re-measure by "
    "re-adding the env-gated `_FAIRNESS_PROBE` hook to `quacq.py` and re-running the G/S/R entailment "
    "classification per those reports' method (no push-button script — the probe hook is reverted)."
)


def write_skeleton(path: Path, prov: dict, table_labels=(), exclude_2cov: bool = True) -> None:
    """Write ``PROVENANCE.md``: sources, aggregation rules, table variants, and the copy step."""
    # Two rules every string below must obey (each was violated by a line here once):
    #   1. State the state AT GENERATION TIME — never a plan. A file whose job is provenance
    #      cannot contain a prediction, so e.g. busybox status is read from `prov`, not hard-coded.
    #   2. Never imply a reproducibility the artifact does not have. If a figure is NOT
    #      re-derivable from the committed data, the entry says so and names the re-measure command
    #      (an overstated reproducibility is an unlabelled column one level up).
    bb = prov["sources"].get("busybox-1.18.0", {})
    busybox_state = (
        f"busybox QuAcq-active: `busybox-1.18.0_long.csv` is {bb.get('status', 'absent')} at "
        "generation time, so its cells are `--` (not yet merged into the loaded data)."
    )
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
        "", "## Audit trail", "",
        "- **exact-equivalence** figures are DERIVED FROM the committed `_long.csv`, not "
        "negotiated: REAL-FM-7 ConMin attains it on **8/144 rows** but **0/48 "
        "configurations** (never across all folds of any config) — all eight attaining rows are "
        "**one fold** (RS-3n, fold 2, replicated over k in {1,2,3,5} x {raw, reduced}), which is the "
        "entire reason 8/144 is kept. A 1/18; C and QuAcq "
        "example-only 0; QuAcq-active is learned once/KB (one observation). Details in "
        "`exact-equiv.md`. `exact_equiv` (delivered theory incl. BG, via "
        "`SemanticEquivalenceChecker`) and `sem_*` (name-set only, `bg_clauses=[]`) measure "
        "different objects — the earlier 'inconsistent with sem-F1' note was a metric misread, removed.",
        _GENUINE_SPLIT,
        "- **QuAcq-active anchoring**: REAL-FM-4 is **NOT anchored** — it ends on a wall-clock "
        "timeout (non-deterministic: 679 queries at 400 s, 3220 at 7200 s), so its cells are "
        "reported (t(s) = timeout wall, queries = count reached, budget/$|B|$ = `--`) but carry no "
        "deterministic numeric anchor. " + busybox_state,
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
