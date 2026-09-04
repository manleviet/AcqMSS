#!/usr/bin/env bash
# Derive a public artifact from this repository.
#
#   ./release/carve.sh <target> <output-dir>       e.g. ./release/carve.sh sosym-r1 /tmp/out
#
# A target is a directory under release/ holding a keep-list, a patches/ directory and a
# PROVENANCE file. Targets exist because there will be more than one carve -- the
# camera-ready needs another, and a different paper drawing on the same sources needs a
# different selection, not this one's complement. Without the target level, the second
# carve defaults to "copy the first and edit it", which is hand-editing one floor up.
#
# Output is a repository with ONE root commit. Keeping history and keeping it clean are
# not simultaneously achievable here: the unrelated project appears in over a hundred
# commits, and the only in-place way to strip that rewrites commit messages into
# descriptions of work that did not happen. That trade was rejected.
#
# Direction of derivation is AcqMSS -> artifact, never the reverse. See release/README.md.
set -euo pipefail

TARGET="${1:-}"; OUT="${2:-}"
[ -n "$TARGET" ] && [ -n "$OUT" ] || { echo "usage: $0 <target> <output-dir>" >&2; exit 2; }
[ -e "$OUT" ] && { echo "refusing: $OUT already exists" >&2; exit 2; }

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"
T="release/$TARGET"
[ -d "$T" ] || { echo "no such target: $T" >&2; exit 2; }

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
die() { printf '\n\033[31mFAILED: %s\033[0m\n' "$*" >&2; exit 1; }

git diff --quiet && git diff --cached --quiet \
  || die "working tree is dirty. A carve must name a committed state."
SRC_SHA=$(git rev-parse --short HEAD)

# ---------------------------------------------------------------- 1. allowlist
say "1/6  read $T/keep-list"
# A directory prefix admits everything under it, now and in future. That is how
# apps/conf/run_conmin_config.toml, tests/test_make_tables.py, docs/adr/0018 and two
# ConMin evaluators nearly shipped -- four separate times, the same mistake. A line
# ending in "/" must therefore be preceded by a comment justifying the whole directory.
prev=""; bare=0
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in
    ''|\#*) prev="$line"; continue ;;
    */) case "$prev" in \#*) ;; *) echo "  unjustified directory prefix: $line" >&2; bare=1 ;; esac ;;
  esac
  prev="$line"
done < "$T/keep-list"
[ "$bare" -eq 0 ] || die "every keep-list directory prefix needs a comment saying why the whole directory is safe"

# Portable read loop, not mapfile: macOS ships bash 3.2 at /bin/bash and has no
# mapfile. The dangerous part is not that it is missing -- it is that an unset array
# yields nothing, the carve produces an empty tree, and an empty tree looks exactly
# like a successful carve. Hence the count assertion below.
PATTERNS=()
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|\#*) continue ;; esac
  PATTERNS+=("$line")
done < <(cat "$T/keep-list")
[ "${#PATTERNS[@]}" -ge 100 ] \
  || die "keep-list yielded only ${#PATTERNS[@]} patterns -- expected 100+. An empty or
       truncated read produces an empty tree that looks like a successful carve."

# release/ is never shipped: a keep-list enumerates what was excluded, which is a map of
# what was removed. Asserted rather than left implicit.
printf '%s\n' "${PATTERNS[@]}" | grep -q '^release/' \
  && die "keep-list selects release/ -- the artifact must not carry its own carve recipe"

FILES=()
while IFS= read -r f; do FILES+=("$f"); done < <(
  git ls-files | awk -v pats="$(printf '%s\n' "${PATTERNS[@]}")" '
    BEGIN { n = split(pats, P, "\n") }
    { for (i = 1; i <= n; i++) if ($0 == P[i] || index($0, P[i]) == 1) { print; break } }')
[ "${#FILES[@]}" -gt 0 ] || die "allowlist selected no files"
echo "  ${#PATTERNS[@]} patterns select ${#FILES[@]} files from $SRC_SHA"

# ---------------------------------------------------------------- 2. copy
say "2/6  copy into $OUT"
mkdir -p "$OUT"
for f in "${FILES[@]}"; do mkdir -p "$OUT/$(dirname "$f")"; cp "$f" "$OUT/$f"; done

# Examples and folds are filtered to cells that have a result -- mechanically, so the
# filter cannot drift from the data. 148.6 MB of example sets produced no number.
python3 - "$OUT" <<'PY'
import pathlib, sys
out = pathlib.Path(sys.argv[1])
stems = {f.name.split('_cv_')[0]
         for tree in ('data/results_sosym_r1', 'data/results')
         if (out / tree).is_dir()
         for f in (out / tree).rglob('*_cv_*.json')}
removed = 0
for d, suf in (('data/examples', '.json'), ('data/folds', '_folds.json')):
    if not (out / d).is_dir():
        continue
    for f in sorted((out / d).glob('*' + suf)):
        if f.name[:-len(suf)] not in stems:
            f.unlink(); removed += 1
print(f"  dropped {removed} example/fold files with no corresponding result")
PY

# ---------------------------------------------------------------- 3. patches
say "3/6  apply $T/patches"
# An allowlist removes files; it cannot remove a function from a file that is kept.
# Those are named patches, so the hand-editing this script replaces cannot move inside it.
shopt -s nullglob
for p in "$T"/patches/*.patch; do
  (cd "$OUT" && git apply --whitespace=nowarn "$HERE/$p") || die "patch failed: $p"
  echo "  applied $(basename "$p")"
done
for n in "$T"/patches/*.new; do
  base=$(basename "$n" .new); cp "$n" "$OUT/$base"; echo "  added   $base"
done

# ---------------------------------------------------------------- 4. root commit
say "4/6  one root commit"
cd "$OUT"
git init -q -b main
git add -A
git -c user.email=manleviet@gmail.com -c user.name="Lê Viết Mẫn" commit -q -m \
"ConGen evaluation artifact

Source code, data and result tables for the ConGen paper, derived from the
development repository at ${SRC_SHA} by release/carve.sh ${TARGET}.

One root commit by design. The development history cannot be carried without
also carrying an unrelated project that appears in over a hundred of its
commits, and the only in-place way to strip that would rewrite commit messages
into descriptions of work that did not happen."
OUT_SHA=$(git rev-parse --short HEAD)
echo "  $(git rev-list --count HEAD) commit, $(git ls-files | wc -l | tr -d ' ') files, $OUT_SHA"

# ---------------------------------------------------------------- 5. gates
say "5/6  verify"
cd "$HERE"
# Output must equal the allowlist selection minus what the example filter removed. This
# is the check that sees a file the script created but did not intend to ship.
if diff <(cd "$OUT" && git ls-files) <(printf '%s\n' "${FILES[@]}" | sort) | grep -q '^<'; then
  diff <(cd "$OUT" && git ls-files) <(printf '%s\n' "${FILES[@]}" | sort) | grep '^<' >&2
  die "output contains files the allowlist did not select"
fi
./scripts/check-release-hygiene.sh "$OUT" || die "release hygiene"

# ---------------------------------------------------------------- 6. provenance
say "6/6  record provenance"
# Without this, "this is the artifact for revision 1" is an assertion with nothing
# behind it -- which is exactly what cost two days on the previous carve.
{
  echo "target:     $TARGET"
  echo "carved:     $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "source:     AcqMSS $SRC_SHA ($(git rev-parse --abbrev-ref HEAD))"
  echo "artifact:   $OUT_SHA"
  echo "files:      ${#FILES[@]} selected by keep-list, before the example/fold filter"
} > "$T/PROVENANCE"
cat "$T/PROVENANCE" | sed 's/^/  /'

printf '\n\033[32mDONE\033[0m — %s carved from %s\n' "$OUT" "$SRC_SHA"
