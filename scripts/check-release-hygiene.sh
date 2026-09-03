#!/usr/bin/env bash
# Release hygiene for the public ConGen artifact, run FROM HERE against the carved
# repository BEFORE it is published. It is deliberately not shipped inside that
# artifact: a checker that enumerates the terms it forbids, and exempts itself from
# its own scan, is the disclosure it exists to prevent — searchable, in a public repo,
# reporting green.
#
#   ./scripts/check-release-hygiene.sh <path-to-carved-repo>
#
# The fifth check exists because the first four cannot see history. `git grep` searches
# the working tree, so a file removed today still sits in every commit that touched it,
# and a repository can pass all four while shipping the thing they exist to remove.
# When this set was first run, the fifth check caught two files that no path filter had
# matched — one of them still live in the working tree.
#
# This script names the terms it forbids, so it excludes ITSELF from the working-tree
# scan. That exclusion is one named file and nothing else: a linter's rule list is not
# a violation, but a broad carve-out would hollow the gate out.
set -uo pipefail
TARGET="${1:-}"
if [ -z "$TARGET" ] || [ ! -d "$TARGET/.git" ]; then
  echo "usage: $0 <path-to-carved-repo>" >&2
  exit 2
fi
cd "$TARGET"

fail=0

# --untracked, because plain `git grep` searches only TRACKED files. A new file that
# has not been added yet would sail past every check below, and "not added yet" is
# exactly the state a file is in while someone is preparing a release. Verified by
# planting a violation in an untracked file: without this flag the gate stayed green.
GREP=(git grep --untracked)

# Case-sensitive, and only on prose a reader would read. Identifiers and metric keys
# are deliberately NOT checked: a variable named for the sibling project is a name,
# whereas the same word in a docstring is a reference to its paper. Only the second
# is what a person searching would find.
for term in "AdmPoolMSS" "AcqMinCover" "maximally general"; do
  if "${GREP[@]}" -n "$term" -- . 2>/dev/null; then
    echo "  ^ '$term' appears in the working tree" >&2
    fail=1
  fi
done

if "${GREP[@]}" -in "AAAI" -- . 2>/dev/null; then
  echo "  ^ 'AAAI' appears in the working tree" >&2
  fail=1
fi

# No path in ANY commit belongs to the sibling project.
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
