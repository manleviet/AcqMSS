---
name: rebaselined-golden-verify-against-independent-oracle
description: When a fix REBASELINES a safety-net golden (not records from old code), verify the new values against an independent reference oracle, not just regen-to-pass
metadata:
  type: feedback
---

When a commit re-baselines an existing golden fixture because behavior legitimately
changed (e.g. `tests/fixtures/t11_oracle_net/layer23_prepared_and_e2e.json` `layer3.quacq`),
the new golden is only trustworthy if its values match an INDEPENDENT reference, not just
"whatever the new code emits."

**Why:** a rebaseline can silently bless a new bug — the test goes green because it was
regenerated from the same (possibly wrong) code path. This is the mirror of
[[golden-recorded-from-old-code]] (which guards recording from post-change code).

**How to apply:** reimplement the claimed rule independently (here: the IJCAI-2013 partial-query
paper rule over the FM's raw CNF) in a throwaway script, recompute every changed golden entry,
and confirm (a) new golden == independent reference on ALL entries, (b) the entries that CHANGED
vs the old golden are exactly the ones the fix's stated mechanism predicts (here: the 4 partial
queries where extension-SAT over-rejected), and (c) the claimed-untouched siblings (layer2,
ConGen arms) are byte-identical. Also check what the golden actually PINS — the T11 quacq arm
pins only a 15-query trajectory with n_kb=0, so it cannot catch a QuAcq learned-KB regression.
