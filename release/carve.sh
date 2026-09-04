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

# Selection in python, not awk: passing a newline-separated pattern list through
# `awk -v` does not survive, and the failure mode was an empty selection -- which the
# count assertion above caught, but which would otherwise have carved an empty tree.
FILES=()
while IFS= read -r f; do FILES+=("$f"); done < <(
  git ls-files | python3 -c '
import sys
pats = [l.rstrip("\n") for l in open(sys.argv[1]) if l.strip() and not l.startswith("#")]
for f in (l.rstrip("\n") for l in sys.stdin):
    if any(f == p or f.startswith(p) for p in pats):
        print(f)
' "$T/keep-list")
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
# Whole-file replacements mirror the tree under patches/files/, so a nested path stays
# nested. An earlier flat `*.new` scheme would have written tools/sosym_r1/README.md to
# the repository root -- silently, since nothing checks where a copy lands.
if [ -d "$T/patches/files" ]; then
  (cd "$T/patches/files" && find . -type f) | sed 's|^\./||' | while IFS= read -r rel; do
    mkdir -p "$OUT/$(dirname "$rel")"
    cp "$T/patches/files/$rel" "$OUT/$rel"
    echo "  replaced $rel"
  done
fi

# ---------------------------------------------------------------- 4. root commit
say "4/6  one root commit"
cd "$OUT"
git init -q -b main
# -f, because the artifact ships a .gitignore that matches files this repository
# tracks anyway -- data/bias/linux-2.6.33.3-bias-stats.txt among them. Without it
# the file is copied to disk and then silently left out of the commit.
# Radius measured, not assumed: `git ls-files | git check-ignore --no-index --stdin`
# returns exactly one path. At forty, -f would be reckless rather than safe.
git add -A -f
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
# BOTH directions. The first version only looked for files the allowlist had not
# selected, and was blind to the opposite case -- a selected file missing from the
# output. That is precisely how the shipped .gitignore silently dropped a tracked
# file: copied to disk, absent from the commit, and a one-directional gate saw
# nothing. The example/fold filter is the one legitimate source of absences, so its
# removals are subtracted before comparing.
KEPT=$(cd "$OUT" && git ls-files)
# Expected = allowlist selection, plus whole-file replacements (which are legitimately
# present without being selected: CITATION.cff does not exist upstream, and README.md
# is replaced rather than copied), minus what the example/fold filter removed.
ADDED=$( [ -d "$T/patches/files" ] && (cd "$T/patches/files" && find . -type f | sed 's|^\./||') || true )
WANT=$(printf '%s\n%s\n' "$(printf '%s\n' "${FILES[@]}")" "$ADDED" \
        | grep -v '^$' | grep -v '^data/\(examples\|folds\)/' | sort -u)
GOT=$(printf '%s\n' "$KEPT" | grep -v '^data/\(examples\|folds\)/' | sort)
if [ "$WANT" != "$GOT" ]; then
  echo "  selected but absent from the commit:" >&2
  comm -23 <(printf '%s\n' "$WANT") <(printf '%s\n' "$GOT") | sed 's/^/    /' >&2
  echo "  present but never selected:" >&2
  comm -13 <(printf '%s\n' "$WANT") <(printf '%s\n' "$GOT") | sed 's/^/    /' >&2
  die "output does not equal the allowlist selection"
fi
# Invoked through bash, not by exec bit: a checked-out mode is one more thing that
# can differ between machines, and this gate must run everywhere.
bash ./scripts/check-release-hygiene.sh "$OUT" || die "release hygiene"

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
  echo ""
  # Measured at carve time, never transcribed. A number copied from a report is a claim;
  # a number the script computes is a measurement, and only one of them stays true.
  echo "gitignore radius: $(git ls-files | git check-ignore --no-index --stdin 2>/dev/null | wc -l | tr -d ' ') tracked file(s) also matched by .gitignore"
  echo "                  (this is why the root commit uses \`git add -A -f\`; at forty it would be reckless)"
  echo "escapes:    $(python3 - <<'EOF'
import warnings, pathlib, subprocess
files = subprocess.run(['git','ls-files','*.py'], capture_output=True, text=True).stdout.split()
bad = 0
for f in files:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        try: compile(pathlib.Path(f).read_text(), f, 'exec')
        except SyntaxError: bad += 1; continue
        bad += sum(1 for x in w if 'escape' in str(x.message))
print(f"{len(files)} .py compiled with warnings on, {bad} invalid escape(s)")
EOF
)"
  echo ""
  echo "boundary-guard rules removed from the source repository, by name --"
  echo "a count would not say which, and three deleted looks like three broken:"
  echo "  test_explanation_imports_profiling_only_through_facade"
  echo "  test_explanation_never_imports_conacq"
  echo "  test_profiling_is_a_leaf"
  echo "  Each scanned REPO_ROOT/explanation or /profiling, gone since 4b47c9b, so"
  echo "  none of them could fail: three green lights wired to nothing. An empty"
  echo "  assertion is worse than an absent one -- it is a promise of protection"
  echo "  that does not exist, and it reads as coverage in every report."
  echo ""
  echo "  The rules themselves are NOT abandoned. All three live in the canonical"
  echo "  explanation repository, which does contain those packages:"
  echo "    test_explanation_imports_profiling_only_through_facade"
  echo "    test_explanation_never_imports_an_application  (generalised: no single app there)"
  echo "    test_profiling_is_a_leaf"
} > "$T/PROVENANCE"
cat "$T/PROVENANCE" | sed 's/^/  /'

printf '\n\033[32mDONE\033[0m — %s carved from %s\n' "$OUT" "$SRC_SHA"
