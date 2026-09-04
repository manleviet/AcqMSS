---
name: quacq-findscope-determinism-test-phantom
description: The QuAcq FindScope sorted(R) determinism fix + its cross-hash-seed test are a no-op/phantom on REAL-FM-7 — verify determinism regressions against the pre-fix code and a KB that actually diverged
metadata:
  type: project
---

Commit 3654c2b `fix(quacq): make FindScope order-independent` changed `findscope.py:62` to
`{k: e[k] for k in sorted(R) ...}` and added
`tests/test_quacq.py::TestQuAcqOracleProgress::test_oracle_learning_deterministic_across_hash_seeds`
(subprocess, seeds 0/1/7, oracle mode, REAL-FM-7).

Empirically (parent worktree 3654c2b~1, unsorted `for k in R`):
- REAL-FM-7 oracle mode is DETERMINISTIC across 18 PYTHONHASHSEEDs (0,1,2,3,4,5,7,10,11,12,13,17,23,42,99,100,777,12345) → `KB=10, Q=342, no_query`, identical KB constraints. Fix produces the SAME values → fix is a **no-op** for the headline example.
- REAL-FM-7 example_only mode: deterministic (KB=0, pool_exhausted).
- fqa oracle mode: deterministic across seeds 4/5/0 (KB=6). So the commit's "KB∈{6,10}" is plausibly fqa(6) vs REAL-FM-7(10) — two different KBs each deterministic, misread as one KB's nondeterminism.

Consequences: the shipped test PASSES on the buggy parent (r0==r1==r7 all agree) → **phantom guard**, no regression protection. Could not reproduce the claimed divergence (KB∈{6,10}, Q∈{341..690}) on any tried KB.

Verified-good guardrails: A/C/C∪S (ConMin) and ConGen (acqmss) do NOT import findscope (only `quacq.py`/`quacq/__init__.py` do). A/B ConMin run `--no-quacq-active` REAL-FM-7 parent-vs-fix: 0 content diffs across A(18)/C(36)/C∪S(144)/QuAcq(18) rows (only timing cols differ). Suite 591p/1s green under PYTHONHASHSEED 0/1/2.

**Why:** determinism fixes need a failing-on-parent test and a KB that actually diverged; recording a config that was already deterministic blesses a no-op. See [[golden-recorded-from-old-code]].
**How to apply:** when reviewing any AcqMSS QuAcq/FindScope determinism change, run the test's exact logic against the pre-fix code — it MUST fail on parent — and pick a KB where the parent genuinely diverges (larger KBs / busybox where scope R grows), not REAL-FM-7.
