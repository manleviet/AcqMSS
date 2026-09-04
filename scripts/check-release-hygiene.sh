#!/usr/bin/env bash
# Release hygiene for the public ConGen artifact, run FROM HERE against the carved
# repository BEFORE it is published.
#
#   ./scripts/check-release-hygiene.sh <path-to-carved-repo>
#
# It is deliberately NOT shipped inside that artifact. A checker that enumerates the
# terms it forbids is, inside a public repository, the disclosure it exists to prevent
# — searchable, under the author's name, and reporting green because it had exempted
# itself from its own scan. Living here, it needs no self-exemption: it is not inside
# the tree it examines.
set -uo pipefail
TARGET="${1:-}"
if [ -z "$TARGET" ] || [ ! -d "$TARGET/.git" ]; then
  echo "usage: $0 <path-to-carved-repo>" >&2
  exit 2
fi
cd "$TARGET"
fail=0

# Scanned on the committed HEAD, not the working tree. The carve produces a root commit
# from a script, so the only thing that could evade a HEAD scan is a file the script
# wrote but did not commit — and carve.sh's output-equals-allowlist gate is what sees
# that. Two checks are only worth having when they look at different things; an earlier
# version used --untracked here, which made sense while the carve was hand-built and
# the risk was a forgotten `git add`.
REV=HEAD

# CASE-SENSITIVE, and only three terms. Each is a proper noun coined by the other
# project's paper, so a person searching for it is looking for that paper.
#
# `conmin` WAS removed from this list, and putting it back is the correction. The
# observation behind the removal was true -- it matched 26 lines and would have been red
# on day one -- but the conclusion was wrong: the answer to a true red is to fix what it
# points at, not to stop asking. Silencing the bell instead of putting out the fire.
# Those 26 lines are now reworded (they named a sibling algorithm) or cleared (they
# pointed at paths this artifact does not contain), and the check is back on.
for term in "AdmPoolMSS" "AcqMinCover" "maximally general"; do
  if git grep -n "$term" "$REV" -- . 2>/dev/null; then
    echo "  ^ '$term' appears in the tree at $REV" >&2
    fail=1
  fi
done

for term in "AAAI" "conmin"; do
  if git grep -in "$term" "$REV" -- . 2>/dev/null; then
    echo "  ^ '$term' appears in the tree at $REV (case-insensitive)" >&2
    fail=1
  fi
done

# Two numbers that must agree with something outside themselves. Both were found by
# eye during review, which means the next drift is found the same way or not at all.
#
# date-released must be TODAY. It is written to equal the tag date, and it has already
# expired once -- set to 2026-09-03, still there on 2026-09-04. A note in the file
# saying "update this before tagging" did not prevent that, because notes never do.
# Turning a thing that must be remembered into a thing that must be true is the only
# reliable move available.
cff="$TARGET/CITATION.cff"
if [ -f "$cff" ]; then
  today=$(date +%Y-%m-%d)
  released=$(grep -m1 '^date-released:' "$cff" | awk '{print $2}')
  if [ "$released" != "$today" ]; then
    echo "  CITATION.cff date-released is $released, today is $today" >&2
    echo "  It must equal the tag date. Re-run the carve on the day you tag." >&2
    fail=1
  fi
  cff_v=$(grep -m1 '^version:' "$cff" | awk '{print $2}' | tr -d '"')
  py_v=$(grep -m1 '^version = ' "$TARGET/pyproject.toml" 2>/dev/null | cut -d'"' -f2)
  if [ -n "$py_v" ] && [ "$cff_v" != "$py_v" ]; then
    echo "  CITATION.cff version $cff_v != pyproject version $py_v" >&2
    fail=1
  fi
fi

# No path in ANY commit belongs to the other project. With a single root commit this is
# cheap, but it stays because it is the only check that would survive a return to
# carrying history, and it is the one that has actually caught things: two files no
# path filter had matched, one of them live in the working tree.
if git log --all --name-only --format="" \
     | sort -u | grep -E "conmin|make_tables|results_conmin"; then
  echo "  ^ the paths above exist somewhere in history" >&2
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  printf '\n\033[31mFAILED: release hygiene\033[0m\n' >&2
  exit 1
fi
printf '\033[32mOK\033[0m — five release-hygiene checks pass\n'
