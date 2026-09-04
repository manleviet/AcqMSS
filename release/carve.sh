#!/usr/bin/env bash
# Derive the public ConGen evaluation artifact from this repository.
#
#   ./release/carve.sh <output-dir>
#
# Produces a repository with ONE root commit: allowlisted files, named patches applied,
# then the release checker. No history is carried. Keeping history and keeping it clean
# are not simultaneously achievable here -- the unrelated project's content is in 100+
# commits, and the only way to strip it in place is --replace-text, which would make
# commit messages describe work that did not happen. That trade was rejected.
#
# WHY A SCRIPT. The first artifact was ten hand-edits deep and nobody could rebuild it.
# A repository whose subject is reproducibility, derived by a process that is not
# reproducible, refutes itself. It also fixes a specific recurring error: while the
# carve was manual, "does this fix belong upstream or in the copy" lived only in
# people's heads, and was answered wrongly four times. Now it is mechanical --
# in this script means carve-side, absent from it means it belongs upstream.
set -euo pipefail

OUT="${1:-}"
[ -n "$OUT" ] || { echo "usage: $0 <output-dir>" >&2; exit 2; }
[ -e "$OUT" ] && { echo "refusing: $OUT already exists" >&2; exit 2; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die() { printf '\n\033[31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

git diff --quiet && git diff --cached --quiet \
  || die "working tree is dirty. The carve must name a committed state."
SRC_SHA=$(git rev-parse --short HEAD)

# ---------------------------------------------------------------- 1. allowlist
say "1/5  read the allowlist"
# A directory prefix admits everything under it, now and in future. That is how
# apps/conf/run_conmin_config.toml, tests/test_make_tables.py, docs/adr/0018 and two
# ConMin evaluators nearly shipped -- four separate times, always the same mistake.
# So a line ending in "/" must be preceded by a comment line justifying the whole
# directory. This is the one rule that cannot live in someone's memory.
prev=""; bare=0
while IFS= read -r line; do
  case "$line" in
    ''|\#*) prev="$line"; continue ;;
    */) case "$prev" in \#*) ;; *) echo "  unjustified directory prefix: $line" >&2; bare=1 ;; esac ;;
  esac
  prev="$line"
done < release/keep-list
[ "$bare" -eq 0 ] || die "every keep-list directory prefix needs a comment saying why the whole directory is safe"

mapfile -t PATTERNS < <(grep -vE '^\s*(#|$)' release/keep-list)
mapfile -t FILES < <(git ls-files | awk -v pats="$(printf '%s\n' "${PATTERNS[@]}")" '
  BEGIN { n = split(pats, P, "\n") }
  { for (i = 1; i <= n; i++) if ($0 == P[i] || index($0, P[i]) == 1) { print; break } }')
[ "${#FILES[@]}" -gt 0 ] || die "allowlist selected no files"
echo "  ${#PATTERNS[@]} patterns select ${#FILES[@]} files from $SRC_SHA"

# ---------------------------------------------------------------- 2. copy
say "2/5  copy into $OUT"
mkdir -p "$OUT"
for f in "${FILES[@]}"; do mkdir -p "$OUT/$(dirname "$f")"; cp "$f" "$OUT/$f"; done

# Examples and folds are filtered to the cells that have a result, mechanically rather
# than by a list, so the filter cannot drift from the data. 148.6 MB of example sets
# produced no number in the paper.
python3 - "$OUT" <<'PY'
import pathlib, sys
out = pathlib.Path(sys.argv[1])
stems = {f.name.split('_cv_')[0]
         for tree in ('data/results_sosym_r1', 'data/results')
         for f in (out / tree).rglob('*_cv_*.json')} if (out / 'data').exists() else set()
removed = 0
for d, suf in (('data/examples', '.json'), ('data/folds', '_folds.json')):
    for f in sorted((out / d).glob('*' + suf)):
        if f.name[:-len(suf)] not in stems:
            f.unlink(); removed += 1
print(f"  dropped {removed} example/fold files with no corresponding result")
PY

# ---------------------------------------------------------------- 3. patches
say "3/5  apply named patches"
# An allowlist removes files; it cannot remove a function from a file that is kept.
# Those edits are patches with names, so the hand-editing this script replaces cannot
# simply move inside it.
shopt -s nullglob
for p in release/patches/*.patch; do
  (cd "$OUT" && git apply --whitespace=nowarn "$HERE/$p") || die "patch failed: $p"
  echo "  applied $(basename "$p")"
done
for n in release/patches/*.new; do
  base=$(basename "$n" .new); cp "$n" "$OUT/$base"; echo "  added   $base"
done

# ---------------------------------------------------------------- 4. root commit
say "4/5  one root commit"
cd "$OUT"
git init -q -b main
git add -A
git -c user.email=manleviet@gmail.com -c user.name="Lê Viết Mẫn" commit -q -m \
"ConGen evaluation artifact

Source code, data and result tables for the ConGen paper, derived from the
development repository at ${SRC_SHA} by release/carve.sh.

One root commit by design. The development history cannot be carried without
also carrying an unrelated project that appears in over a hundred of its
commits, and the only in-place way to strip that would rewrite commit messages
into descriptions of work that did not happen."
echo "  $(git rev-list --count HEAD) commit, $(git ls-files | wc -l | tr -d ' ') files"

# ---------------------------------------------------------------- 5. gates
say "5/5  verify"
cd "$HERE"
# Output must equal the allowlist selection, minus what the example filter removed.
# This is what catches a file the script created but did not intend to ship.
diff <(cd "$OUT" && git ls-files) <(printf '%s\n' "${FILES[@]}" | sort) \
  | grep '^<' && die "output contains files the allowlist did not select"
./scripts/check-release-hygiene.sh "$OUT" || die "release hygiene"

printf '\n\033[32mDONE\033[0m — %s carved from %s\n' "$OUT" "$SRC_SHA"
