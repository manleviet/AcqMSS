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
# `conmin` is deliberately ABSENT, and this note exists so nobody adds it back.
# Case-insensitively it matches fifteen comments in ConGen's own algorithm files that
# say a sibling algorithm exists and how the shared code path is shaped for it --
# `# ConMin assembles F -> S -> C likewise`. None names the venue, the title, or the
# review. That is the line: a proper noun from the paper is blocked; the bare fact that
# a sibling algorithm exists is not. Adding `conmin` makes this gate red on day one,
# and a gate that is red on day one gets relaxed until it checks nothing. Two such
# relaxations were removed from this file already.
for term in "AdmPoolMSS" "AcqMinCover" "maximally general"; do
  if git grep -n "$term" "$REV" -- . 2>/dev/null; then
    echo "  ^ '$term' appears in the tree at $REV" >&2
    fail=1
  fi
done

if git grep -in "AAAI" "$REV" -- . 2>/dev/null; then
  echo "  ^ 'AAAI' appears in the tree at $REV" >&2
  fail=1
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
