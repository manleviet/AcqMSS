#!/usr/bin/env bash
# Falsify the release-hygiene patterns: prove each one CAN fail, and prove none of them
# fires on text that must survive.
#
#   ./scripts/falsify_hygiene_patterns.sh
#
# Why this exists as a separate script. A pattern that matches nothing and a pattern
# that matches nothing *because it is broken* produce the same green. That is not
# hypothetical here: the first version of the process-vocabulary patterns used \b for
# word boundaries, and `git grep -E` is POSIX ERE, in which \b is not a word boundary.
# Run against a tree that contained R3-Q5, R2-Q13, C2's and C9's, it matched zero files
# and reported success. The gate was switched on and guarding nothing.
#
# So every pattern is checked in both directions before it is trusted:
#   POSITIVE -- a constructed line it MUST match, or the pattern is inert;
#   NEGATIVE -- real text from this repository it must NOT match, or the gate goes red
#               on the published algorithm and gets switched off within the week.
#
# The negatives are the load-bearing half. `B1, B2 = split(B)` is the bias split in the
# paper's own pseudocode, and "code review checklist" is ordinary English; a vocabulary
# blacklist would have to forbid both. These patterns match a SHAPE -- a code used as an
# actor -- which is what is actually decodable by a reader.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
pass=0

# Kept identical to check-release-hygiene.sh by the assertion at the bottom, which
# refuses to pass if the two lists drift apart. A falsification of yesterday's pattern
# proves nothing about today's.
PATTERNS=(
  "Cowork"
  "checklist item"
  "R[0-9]+-Q[0-9]+"
  "(^|[^A-Za-z0-9_])[A-C][0-9]{1,2}'s([^A-Za-z0-9_]|\$)"
  "(^|[^A-Za-z0-9_])[A-C][0-9]{1,2} (must|will|owns|is responsible)"
)

POSITIVES=(
  "Cowork-layer analysis harness for the cost accounting"
  "Closing that is checklist item C10(a)."
  "which answers N1 and R2-Q13 better than a larger number would"
  "    C2's deliberate regeneration sets the environment variable once."
  "# The results C2 must regenerate deliberately, and that"
)

# Real lines from this repository that must survive every pattern.
NEGATIVES=(
  "        B1, B2 = split(B)"
  "        # B1, B2 = split(B)"
  "        Q2 = AcqMSS(delta=B1, B1, NE, E'+, BG)"
  "- Code review checklist (12 items)"
  "and different semantic F1."
  "\"\"\"Run the rule-learner baselines (C4) over the same folds as acquisition."
  "The decisive argument came from the T9 refactor that immediately preceded"
  "# 4. Numbers quoted in A5 / B7 / B20."
)

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

say "1/3  every pattern must match its positive (proves the pattern is not inert)"
for i in "${!PATTERNS[@]}"; do
  pat="${PATTERNS[$i]}"; pos="${POSITIVES[$i]}"
  if printf '%s\n' "$pos" | grep -qE "$pat"; then
    printf '  \033[32mok\033[0m   /%s/\n' "$pat"; pass=$((pass + 1))
  else
    printf '  \033[31mINERT\033[0m /%s/ did not match its own positive:\n    %s\n' "$pat" "$pos" >&2
    fail=1
  fi
done

say "2/3  no pattern may match text that must survive"
for neg in "${NEGATIVES[@]}"; do
  hit=""
  for pat in "${PATTERNS[@]}"; do
    printf '%s\n' "$neg" | grep -qE "$pat" && hit="$pat"
  done
  if [ -z "$hit" ]; then
    printf '  \033[32mok\033[0m   survives: %s\n' "$neg"; pass=$((pass + 1))
  else
    printf '  \033[31mFALSE POSITIVE\033[0m /%s/ matched text that must survive:\n    %s\n' "$hit" "$neg" >&2
    fail=1
  fi
done

# A falsification run against a stale copy of the patterns is worse than none: it
# certifies patterns that are not the ones the gate uses. Compared as sorted text, so
# reordering the list is allowed and editing it is not silently allowed.
say "3/3  these patterns are the ones the gate actually runs"
GATE=scripts/check-release-hygiene.sh
mine=$(printf '%s\n' "${PATTERNS[@]}" | sort)
theirs=$(sed -n '/^for pat in /,/; do$/p' "$GATE" \
  | sed 's/^for pat in //; s/; do$//' \
  | tr -d '\\\n' | tr '"' '\n' | sed '/^ *$/d' | sort)
if [ "$mine" = "$theirs" ]; then
  printf '  \033[32mok\033[0m   %d patterns, identical to %s\n' "${#PATTERNS[@]}" "$GATE"
  pass=$((pass + 1))
else
  printf '  \033[31mDRIFT\033[0m this script and %s carry different patterns\n' "$GATE" >&2
  diff <(printf '%s\n' "$mine") <(printf '%s\n' "$theirs") | sed 's/^/    /' >&2
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  printf '\n\033[31mFAILED: pattern falsification\033[0m\n' >&2
  exit 1
fi
printf '\n\033[32mOK\033[0m — %d falsification checks pass (%d patterns, %d survivors)\n' \
  "$pass" "${#PATTERNS[@]}" "${#NEGATIVES[@]}"
