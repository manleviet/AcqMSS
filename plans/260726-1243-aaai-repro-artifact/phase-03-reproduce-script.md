---
phase: 3
title: "Reproduce Script"
status: pending
effort: "~2.5h"
priority: P1
dependencies: [1, 2]
---

# Phase 3: One-command reproduce entry point

## Overview
Add `scripts/reproduce_paper.sh` chaining: env check → 5-KB eval → completeness assert → `--merge` → (guarded) `make_tables` → logical-column diff vs a **committed frozen reference**. Clobber-safe, resumable, hangup-surviving. Bash (repo has no Makefile).

## Locked design (interview + Red Team)
- **make_tables absent OR wrong-CLI → degrade, never abort.** Run only if `apps.make_tables` importable, AND wrap the invocation itself in `|| { echo "table step skipped/failed — reconcile CLI with CW Main v1+v2; CSVs ready at $OUT"; }` so a present-but-different CLI does not `set -e`-kill the run after the multi-hour sweep (Red Team #6).
- **Clobber-safe, enforced (not just default).** `OUT="${1:-data/results_conmin/repro}"`, but a **hard refuse-guard** rejects any `OUT` whose realpath is (or is not strictly under a `repro`-style subtree of) the canonical `data/results_conmin` — so `bash …sh data/results_conmin` exits non-zero instead of overwriting committed JSONs/CSVs (Red Team #5). Add `data/results_conmin/repro/` to `.gitignore` so reviewer output never stages (Red Team #13; `heavy.log` is already `*.log`-ignored — non-issue).
- **Resumable.** Skip a KB when all its expected `{kb}_{es}_eval.json` already exist in `$OUT` (the atomic unit is resume-friendly) → re-run into the same `$OUT` continues instead of recomputing hours of work; makes "idempotent" true (Red Team #7).
- **Reproduction proof = logical columns vs committed frozen reference.** NOT a raw `diff` of the untracked/stale `conmin_eval_cv.csv` (Red Team #2). Diff a **projection** of reproducible columns (`desc_*`, `clause_*`, `sem_*`, `n_kb_*`, `oracle_queries_*` — exclude `*_ms_*`/`memory_mb_*` timing/RSS) against `data/results_conmin/reference/conmin_eval_cv.csv`, a committed frozen post-sweep baseline.

## Prerequisite the plan must flag (sequencing)
The current `data/results_conmin/conmin_eval_{cv,long}.csv` are **untracked + stale** (4 conditions; missing `afaa04b` counters; pre-`b40771c` numbers). The diff reference `data/results_conmin/reference/conmin_eval_cv.csv` must be **frozen + committed from Viet-Man's fresh post-`afaa04b` full sweep** (5 conditions). Until that exists, the diff step warns "no committed reference yet" and skips (does not fail).

## Requirements
- Functional: `bash scripts/reproduce_paper.sh [OUT_DIR]` reproduces the full pipeline into `OUT_DIR`, resumable, from any CWD.
- Non-functional: `set -euo pipefail`; anchored to repo root; actionable failure messages; survives SIGHUP guidance.

## Architecture (script outline)
```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."            # anchor to repo root (Red Team #12)
export PYTHONPATH="$PWD"           # apps importable regardless of editable install
PY=python3
CFG=apps/conf_conmin/run_conmin_eval_config.toml
OUT="${1:-data/results_conmin/repro}"
CANON=data/results_conmin
declare -a KBS=(REAL-FM-7 fqa arcade-game REAL-FM-4)   # busybox handled separately
BUSYBOX_SETS=(2cov ff rs_1n)                            # only feasible sets
ALL_SETS=(2cov ff rs_1n rs_2n rs_3n rs_m)

# 0) clobber refuse-guard (Red Team #5)
mkdir -p "$OUT"
case "$(cd "$OUT" && pwd -P)" in
  "$(cd "$CANON" && pwd -P)") echo "refuse: OUT=$OUT would clobber committed reference data" >&2; exit 2;;
esac

# 1) env check — ASSERTIVE, wheel-pinned (Red Team #10)
$PY - <<'PY'
import sys, importlib.metadata as m
assert sys.version_info >= (3,11), "Python >=3.11 required"
try: ev = m.version("explanation")
except m.PackageNotFoundError: sys.exit("explanation not installed — run: pip install vendor/explanation-0.1.0-py3-none-any.whl  (see README 'Reproducing the paper environment')")
if ev != "0.1.0": print(f"WARNING: explanation {ev} != pinned 0.1.0", file=sys.stderr)
try:
    fv = m.version("flamapy-fm")
    if fv != "2.6.0.dev4": print(f"WARNING: flamapy-fm {fv} != pinned 2.6.0.dev4 (numbers may drift)", file=sys.stderr)
except m.PackageNotFoundError: print("WARNING: flamapy-fm not found", file=sys.stderr)
import importlib.util
if importlib.util.find_spec("apps.run_conmin_eval") is None: sys.exit("apps not importable — run from repo root / pip install -e .")
print(f"env OK: explanation={ev}")
PY

# 2) 5-KB eval into $OUT — RESUMABLE (skip KB if all its sets already present) (Red Team #7)
run_kb () {  # $1=kb ; $2..=sets
  local kb="$1"; shift; local sets=("$@") missing=0
  for es in "${sets[@]}"; do [ -f "$OUT/${kb}_${es}_eval.json" ] || missing=1; done
  if [ "$missing" -eq 0 ]; then echo "skip $kb (all ${#sets[@]} sets present in $OUT)"; return; fi
  nohup nice -n 10 $PY -m apps.run_conmin_eval "$CFG" --kb "$kb" --example-sets "${sets[@]}" -o "$OUT" \
    > "$OUT/${kb}.log" 2>&1                                    # per-KB log (Red Team #11)
}
for kb in "${KBS[@]}"; do run_kb "$kb" "${ALL_SETS[@]}"; done
run_kb busybox-1.18.0 "${BUSYBOX_SETS[@]}"

# 3) completeness assert BEFORE merge (Red Team #3)
missing=()
for kb in "${KBS[@]}";     do for es in "${ALL_SETS[@]}";     do [ -f "$OUT/${kb}_${es}_eval.json" ] || missing+=("${kb}_${es}"); done; done
for es in "${BUSYBOX_SETS[@]}"; do [ -f "$OUT/busybox-1.18.0_${es}_eval.json" ] || missing+=("busybox-1.18.0_${es}"); done
if [ "${#missing[@]}" -gt 0 ]; then echo "INCOMPLETE — missing eval JSONs: ${missing[*]}. NOT merging (would produce a partial-but-authoritative CSV)." >&2; exit 3; fi

# 4) merge (honors -o: run_conmin_eval.py:158,114-115)
$PY -m apps.run_conmin_eval "$CFG" --merge -o "$OUT"

# 5) tables — GUARDED + wrapped (Red Team #6)
if $PY -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('apps.make_tables') else 1)"; then
  $PY -m apps.make_tables "$OUT/conmin_eval_cv.csv" "$OUT/conmin_eval_long.csv" --out "$OUT/tables" \
    || echo "table step skipped/failed — reconcile CLI with CW Main spec v1+v2; merged CSVs ready at $OUT"
else
  echo "table step skipped — apps/make_tables.py not yet added (CW Main deliverable); merged CSVs ready at $OUT"
fi

# 6) reproduction proof — logical columns vs COMMITTED frozen reference (Red Team #2)
REF="$CANON/reference/conmin_eval_cv.csv"
if [ -f "$REF" ]; then
  $PY scripts/diff_logical_cols.py "$OUT/conmin_eval_cv.csv" "$REF"   # projects desc_*/clause_*/sem_*/n_kb_*/oracle_queries_*, excludes *_ms_*/memory_mb_*
else
  echo "no committed reference yet ($REF) — freeze one from the post-afaa04b sweep to enable the reproduction check"
fi
```
(`scripts/diff_logical_cols.py` is a tiny read-only helper: load both CSVs, keep reproducible columns, report mismatches. ~30 lines; created alongside the script.)

## Header comment block (must include)
- **Hardware**: Apple M1 Pro, 8 cores, 16 GB.
- **Busybox caveat**: only `2cov`/`ff`/`rs_1n` feasible; `rs_2n`/`rs_3n`/`rs_m` **infeasible** (~17–25 h each, Stage-1-bound). busybox QuAcq-active may hit the 400 s wall-clock net → reported **non-converged** (`--`), not a number, and is **not** hardware-reproducible (Red Team #8/L).
- **Runtime**: REAL-FM-7 min; fqa/arcade tens-of-min; REAL-FM-4 ~1–3 h; busybox many hours. Total ≈ overnight → **run under `tmux`/`screen`** (script backgrounds each KB with `nohup nice` + per-KB `$OUT/<kb>.log`, but detach the session to survive SIGHUP) (Red Team #11).
- **Resumable**: re-run with the same `$OUT` to continue; delete a KB's `*_eval.json` to force recompute.
- **Determinism**: no `PYTHONHASHSEED` needed (QuAcq canonical-sorted; scope carve-outs per doc).
- **Env**: `pip install vendor/explanation-0.1.0-py3-none-any.whl` (Phase 2).

## Related Code Files
- Create: `scripts/reproduce_paper.sh` (executable) + `scripts/diff_logical_cols.py`
- Modify: `.gitignore` (add `data/results_conmin/repro/`)
- Read-only: `apps/run_conmin_eval.py` (`-o` honored: :158,:114-115; merge glob :61; silent set-skip :270-272), `apps/conf_conmin/run_conmin_eval_config.toml`
- Cross-link: one-liner in `docs/eval-pipeline.md` (Phase 1) + `README.md`.

## Implementation Steps
1. Write `scripts/reproduce_paper.sh` per outline; `chmod +x`; `bash -n` clean.
2. Write `scripts/diff_logical_cols.py` (project reproducible columns, report row/cell mismatches, exit non-zero on diff).
3. Add `.gitignore` entry for `data/results_conmin/repro/`.
4. Header comment block (hardware/busybox/runtime/resume/determinism/env).
5. Cross-link from doc + README.

## Success Criteria
- [ ] `scripts/reproduce_paper.sh` exists, executable, `bash -n` clean; runs from any CWD (anchors to repo root).
- [ ] Refuse-guard: `bash scripts/reproduce_paper.sh data/results_conmin` exits non-zero without writing. Default OUT gitignored.
- [ ] Resumable: second run with same `$OUT` skips completed KBs.
- [ ] Completeness assert blocks `--merge` on any missing eval JSON.
- [ ] make_tables step degrades (skip message) on BOTH absent module and non-zero invocation — verified NOW (module absent).
- [ ] Diff step uses logical-column projection vs a committed reference (or warns cleanly if the reference is absent).
- [ ] Header carries hardware + busybox non-convergence caveat + tmux/detach note.
- [ ] Dry check: env-check block + `--kb REAL-FM-7 -o /tmp/repro_check` + `--merge -o /tmp/repro_check` succeed (proves `-o` honored for eval AND merge); do NOT run the full sweep.

## Risk Assessment
- Risk: committed frozen reference not yet available (depends on Viet-Man's sweep). Mitigation: diff step warns-and-skips; flagged as a sequencing prerequisite.
- Risk: `nohup … &`-less foreground under `set -e` still blocks the terminal for hours. Mitigation: per-KB `nohup nice` + log; header tells reviewer to run under tmux. (KBs still run sequentially — acceptable; parallel is out of scope.)
- Risk: `realpath`/`pwd -P` differences on macOS. Mitigation: use `cd … && pwd -P` (portable); `bash -n` + the /tmp dry check catch bashisms.
