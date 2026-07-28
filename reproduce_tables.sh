#!/usr/bin/env bash
# Reproduce every table in the ConMin paper, end to end, from one command.
#
#   ./reproduce_tables.sh              # from the committed per-KB CSVs   (~1 min)
#   ./reproduce_tables.sh --full       # re-run the whole sweep first     (~12+ h)
#   ./reproduce_tables.sh --draft      # tables to a scratch dir, nothing official
#
# Output: data/results_conmin/tables/  — 11 .tex + .md, exact-equiv.md, PROVENANCE.md
#
# Every step is gated. The script stops at the first failure and says which one;
# it never emits tables from inputs it could not verify.
set -euo pipefail

CFG="apps/conf_conmin/run_conmin_eval_config.toml"
RESULTS="data/results_conmin"
MODE="from-csv"
TABLES_FLAG="--official"
TABLES_DIR="$RESULTS/tables"

for a in "$@"; do
  case "$a" in
    --full)  MODE="full" ;;
    --draft) TABLES_FLAG=""; TABLES_DIR="/tmp/tables-draft" ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown flag: $a" >&2; exit 2 ;;
  esac
done

cd "$(dirname "$0")"
export PYTHONPATH=.

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die() { printf '\n\033[31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- 0. environment
say "0/5  environment"
python3 -c "import sys; assert sys.version_info >= (3,11), sys.version" \
  || die "Python >= 3.11 required"
python3 -c "import explanation, flamapy" 2>/dev/null \
  || die "the canonical 'explanation' package is not importable — run: pip install -e ../explanation"
python3 -c "import conacq" 2>/dev/null || die "conacq not importable (run from the repo root)"
echo "  ok: $(python3 -V), explanation + conacq importable"

# ---------------------------------------------------------------- 1. the sweep
if [ "$MODE" = "full" ]; then
  say "1/5  full sweep — hours, and it CHANGES published numbers"
  echo "  Five knowledge bases x six sampling strategies x three folds."
  echo "  Measured wall-clock on an M1 Pro: ~12 h total; busybox alone caps at 36,000 s."
  echo "  busybox runs only three samplings (2cov, ff, rs_1n) — by design, see RUN.md."
  echo
  echo "  WARNING: KB_5 (busybox) QuAcq-active ends on a WALL-CLOCK TIMEOUT, not on the"
  echo "  deterministic query rail. Its 1,901 queries are what this machine reached in"
  echo "  36,000 s. A re-run WILL produce a different KB_5 row, and every KB_5 figure in"
  echo "  the paper becomes stale. Use --full only when reproducing from scratch, never"
  echo "  to 'refresh' tables that already match the paper."
  read -r -p "  continue? [y/N] " ok; [ "$ok" = "y" ] || die "aborted by user"
  python3 -m apps.run_conmin_eval "$CFG" -v || die "sweep"
else
  say "1/5  sweep SKIPPED — using the committed per-KB CSVs"
  ls "$RESULTS"/*_long.csv >/dev/null 2>&1 || die "no per-KB *_long.csv in $RESULTS; use --full"
  echo "  found: $(ls "$RESULTS"/*_long.csv | wc -l | tr -d ' ') per-KB long CSVs"
fi

# ---------------------------------------------------------------- 2. freshness
say "2/5  pre-merge freshness gate"
echo "  Refuses to merge a knowledge base whose rows predate the post-fix schema"
echo "  (missing convergence_reason / diagnostic counters). Calls the production"
echo "  predicate apps.make_tables.gates.is_stale, not a re-implementation."
python3 freshness_gate.py || die "freshness gate — a KB is stale; re-run that KB before merging"

# ---------------------------------------------------------------- 3. merge
say "3/5  consolidate"
python3 -m apps.run_conmin_eval "$CFG" --merge -v 2>&1 | tee /tmp/merge.log \
  || die "merge"
if grep -qiE "provenance conflict|non-additive column" /tmp/merge.log; then
  die "merge emitted a provenance/stale-schema warning — read /tmp/merge.log, do not proceed"
fi
echo "  ok: no C-4 provenance conflict, no stale-schema mix"

# ---------------------------------------------------------------- 4. tables
if [ -n "$TABLES_FLAG" ]; then
  say "4/5  generate tables (official)"
  python3 -m apps.make_tables --official -v || die "make_tables"
else
  say "4/5  generate tables (draft -> $TABLES_DIR)"
  python3 -m apps.make_tables --tables-dir "$TABLES_DIR" -v || die "make_tables"
fi
if [ -f "$TABLES_DIR/SELFCHECK-FAILED.md" ]; then
  die "self-check failed — see $TABLES_DIR/SELFCHECK-FAILED.md. The INPUT changed; do NOT re-fit the anchors."
fi

# ---------------------------------------------------------------- 5. verify
say "5/5  verify the emitted artifacts"
PROV="$TABLES_DIR/PROVENANCE.md"
[ -f "$PROV" ] || die "no PROVENANCE.md at $PROV"

sha=$(grep -m1 'git SHA' "$PROV" | tr -d '`' | awk '{print $NF}')
case "$sha" in
  *-dirty) die "PROVENANCE records $sha — the generator had uncommitted changes.
       Commit apps/make_tables/ FIRST, then re-run. The recorded SHA must name the
       code that produced these tables, never a commit that merely happened to be HEAD." ;;
  unknown) die "PROVENANCE could not record a SHA (git unavailable?)" ;;
esac
echo "  ok: generator SHA $sha, clean"

n=$(ls "$TABLES_DIR"/*.tex 2>/dev/null | wc -l | tr -d ' ')
[ "$n" -ge 11 ] || die "expected >= 11 .tex tables, found $n"
echo "  ok: $n .tex tables + exact-equiv.md"

# .md only: in .tex a bare '%' is LaTeX's comment character and would false-positive.
# The caption strings are identical in both renderings, so .md covers the same text.
if grep -qniE '[0-9]+%|pending|tonight|overnight' "$TABLES_DIR"/*.md; then
  echo "  A generated artifact contains a hard-coded percentage or a plan word:"
  grep -niE '[0-9]+%|pending|tonight|overnight' "$TABLES_DIR"/*.md || true
  echo
  echo "  Captions that quantify the data must be DERIVED from the data, and no"
  echo "  artifact may state a plan — it must state the state at generation time."
  die "artifact hygiene"
fi
echo "  ok: no hard-coded percentages, no plan strings"

printf '\n\033[32mDONE\033[0m — tables in %s\n' "$TABLES_DIR"
if [ -n "$TABLES_FLAG" ]; then
  cat <<'EOF'

To put them in the paper (run MANUALLY — nothing here ever writes Overleaf/):

    cp data/results_conmin/tables/*.tex Overleaf/AAAI/tables/
    ./sync.sh AAAI push "regenerate tables"
EOF
fi
