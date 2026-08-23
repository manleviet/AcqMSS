# Non-discriminating tests — standing register

Tests that are **correct assertions but cannot currently fail**, because no available
fixture separates the right behaviour from the wrong one. Each is green for a reason
that is not "the code is verified".

This is the debt that goes missing first: the test passes, nobody remembers why, and
years later someone cites it as coverage. Collected here so the reason lives in one
place rather than scattered across four docstrings.

Convention: an entry leaves only when a discriminating fixture exists, or the assertion
is replaced by one that bites. Two below were replaced that way and are kept as record.

| # | test | why it cannot fail | status |
|---|---|---|---|
| 1 | post-Reduce NE counting (C6) | every REAL-FM-7 fixture drops 0 NE in Reduce | **replaced** |
| 2 | full-theory FP vs training negatives (NE-clause) | bias constraints already reject them on all 54 folds | **replaced** |
| 3 | index-pairing canary (C4) | variable ids are contiguous from 1 | **narrowed** |
| 4 | CN2 determinism (C4) | variation confined to discarded rules | **open** |

---

## 1. `test_ne_count_comes_from_the_post_reduce_kb` — C6, `ff4566b`

**Claim**: `n_ne` counts the POST-Reduce KB, not the NE prepared for acquisition.

**Why a value comparison could not fail**: Reduce drops an NE only when the rest of the
KB entails it. Measured across all six REAL-FM-7 example sets: prepared NE = 1 and
`n_ne` = 1 in every one, so **0 dropped everywhere**. Asserting `n_ne <= prepared`
passes whether or not the count is taken before Reduce.

**Resolution**: replaced with a structural assertion —
`len(kb_names) + len(ne_names) == len(result.kb_assumption_ids)` — which pins the count
to Reduce's own output regardless of fixture.

**Would re-open if**: a KB is added where Reduce drops an NE; then the value comparison
becomes meaningful and worth adding back as a second check.

## 2. `test_delivered_theory_carries_the_memorized_negatives` — NE-clause, `65153ec`

**Claim**: the delivered theory rejects every training negative (Definition 6).

**Why the full-theory FP assertion could not fail**: measured before/after across 54
folds (REAL-FM-7, fqa, arcade-game) — FP = 0 on every fold **already**, without the NE
clauses, because the learned bias constraints reject those negatives on their own. Two
compounding reasons: C7 tightened the theories by restoring the root-implying
constraints, and CV accuracy scores the TEST fold while Definition 6 constrains the
TRAINING negatives.

**Resolution**: the load-bearing assertion is now that the ¬e⁻ clauses reject the
negatives **by themselves** — true whatever the bias learned, so it bites on any
fixture. Mutation-verified. The full-theory FP assertion is retained as a Definition 6
guard and documented as non-discriminating.

## 3. `test_cnf_is_invariant_under_column_permutation` — C4, `6a45026` / `5311009`

**Claim**: the rule→CNF conversion is independent of column order.

**Why it barely bit**: the production column order sorts by variable id, and ids are
**contiguous from 1** on every KB here (REAL-FM-7 1–14, arcade-game 1–65, fqa 1–179,
REAL-FM-4 1–291). So column index *i* and variable id *i+1* coincide, and an
index-paired implementation is right by accident in every production case. Name
resolution does not fix a wrong answer — it removes the coincidence the correctness
rests on.

**Consequence**: this guards a *regression*, not a live bug. Under an index-pairing
mutation only **1 of 8** tests failed, because every fixture used the id-sorted order
and therefore agreed with the bug.

**Resolution (partial)**: fixtures now default to a permuted order chosen by enumerating
all six permutations and taking the one that mis-maps **all three** features. Coverage
under the same mutation: **1/8 → 6/8**. The two survivors touch no literal at all
(empty rule set, unconditional rule) and cannot catch it in principle. A separate test
guards the premise itself by asserting the real FM's ids are not alphabetical.

**Still non-discriminating for**: a non-contiguous catalog, which no fixture has. That
is the case where index-pairing breaks silently in production.

## 4. `test_learner_is_deterministic_across_repeated_fits[cn2]` — C4, `fdd2d63` — **OPEN**

**Claim**: repeated CN2 fits on one table give identical rules.

**Why it cannot fail for CN2**: Orange's CN2 is genuinely nondeterministic without a
global RNG reset — but the variation is confined to the rules the adapter **discards**.
Measured on one tie-prone fixture over 20 fits:

| | full Orange rule list | subset the adapter keeps |
|---|---|---|
| without seed reset | **2** distinct | 1 distinct |
| with seed reset | 1 distinct | 1 distinct |

Removing the reset leaves the test green. The reset is kept because the nondeterminism
is real and it costs nothing — not because a test proves it necessary.

**This is one sample, not a proof.** On another fold or KB the variation could reach the
kept rules. The test still discriminates for RIPPER and the decision tree.

**Would close if**: a fixture is found where the kept subset varies without the reset —
worth a short search once the sweep data exists, since real folds are far larger and
more tie-prone than a 6-row table.

---

## Coverage notes — NOT register entries

Kept apart on purpose: an assertion that CAN fail is a test, whatever data drives it.
These record that no PRODUCTION fixture exercises a path, which is a statement about
coverage, not about discriminating power.

- **NE discarded by Reduce** (`test_ne_accounting_closes_when_reduce_discards_an_ne`,
  `conacq/algorithms/acqmss/congen_model.py`). Reduce drops 0 NE on all six REAL-FM-7
  example sets, so the path is never taken by real data. The test drives it
  synthetically — moving an NE id from `kb_assumption_ids` to `redundant_ids`, exactly
  what Reduce does — and runs the real resolution path. Mutation-verified: restoring the
  pre-fix discard turns it red. So it belongs here, not in the table above.

---

## Pattern worth keeping

Three of the four were found by **mutating the code and checking the test actually goes
red**, not by reading the test. A test written to assert the right property can still be
unable to fail; only mutation distinguishes the two. Where a mutation left tests green,
the fix was an oracle the implementation cannot satisfy by agreeing with itself —
Orange's own `Rule.evaluate_data` for the selector translation, Reduce's own output for
the NE count.
