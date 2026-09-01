# CC → CW handoff — re-score, gap correction, busybox cap sensitivity

Branch `feat/sosym-r1`, HEAD `ce07649`. Tree clean. `check_paper_numbers.py`: **63/63 green**.
Window 2026-08-31 10:17 → 2026-09-01 08:03.

## What landed

| commit | what |
|---|---|
| `fc14a86` | 12 busybox example-first folds, cap 1,000 (step 5) |
| `e555532` | track `backfill_ne_clauses.py` + positive-control test; `-o` docstring |
| `4a580e5` | 56 interactive CV files re-scored **into a separate tree** |
| `3a6d8e8` | disarm the NE backfill (`--cv-dir` required); fill interactive NE from record |
| `2150c16` | `measure_corrected_gap_table.py` — the gap, with both trees named |
| `07042a0` | re-derived gap table; superseded the N-item table |
| `61548d9` | assert the passive-vs-active **invariants**, not per-cell gaps |
| `bd57dc5` | reframe: the published comparison hid the oracle benefit |
| `9f10c82` | busybox cap-5,000 fold — 5× budget buys nothing |
| `ce07649` | assert busybox is the identical theory at both caps |

## Results that matter

**Re-score went to `data/results_sosym_r1/`, source untouched.** Verified two ways: source
`git status` empty, and 0/56 source files carry `exact_equiv` while 56/56 copies do.
`run_compare` config mode ignores `-o` and writes to `kb_dir` (`:223`) — the standing
"always `-o`" rule does not reach it. Documented in the docstring.

**Exact equivalence, interactive: 0/168, nothing unmeasured.** Not backfilled: QuAcq's
`QuAcqTaskInput` carries only `oracle_data`, so it never sees an example and cannot
memorise one; all 168 folds already record `n_ne == 0`. Regenerating would have
manufactured a theory the algorithm never delivered (56 clauses on busybox rs_1n).

**The N-item gap table reproduced from no tree.** Its old column is `data/results`
exactly; its "corrected" column pairs a corrected ConGen column with an **uncorrected**
iterative one. Superseded, not edited — second occurrence of the pairing failure.

**The real defect is mode collapse.** 11 of 18 published cells carried the identical
iterative F1 under both modes, so the oracle benefit read as **+0.0000**. Corrected:
0 of 18 zero, range **+0.0919 to +0.6206**. The 20× rise in the iterative column is
that benefit becoming visible, not a loss of margin.

**Query-cost result, load-bearing and unaffected:**
- example-only never beats ConGen — **0 of 28 cells**
- the single example-first win (arcade rs_3n) costs **5,000 queries against zero**, and
  the same baseline on the same cell **loses by +0.4668 at 118 queries**
- REAL-FM-7 exhausted every askable question (`no_query`, 18 folds) and still lost

**Stopping rules mean three things:** 66 `max_queries` (budget-limited), 18 `no_query`
(converged), 84 `pool_exhausted` (data-limited). "Bounded by budget" holds for 66 of 168.

**busybox cap sensitivity — the run did NOT time out.** Finished on `max_queries` with
28 min to spare.

| | cap 1,000 | cap 5,000 |
|---|---|---|
| \|KB\| | 14 | **14 — identical SET** |
| wall clock | 2.12 h | **15.53 h** (7.32×) |
| s / query | 7.6 | 11.2 |

Same range on the others: fqa ×1.44, REAL-FM-4 ×1.37, arcade ×1.34. busybox ×1.00 — the
largest model moving least, not the probe lacking resolution.

## Two defects I caused and caught

1. `e555532`'s message credited the backfill with producing the ConGen tree. It did not —
   `cross_validation.py:230` stores `ne_clauses` natively. Corrected in `3a6d8e8`.
2. The busybox assertions first read the cap-1,000 fold from `partials/`, which is
   **gitignored**. A fresh clone would have skipped 8 checks through an `exists()` guard,
   and a skipped check reads exactly like a passing one. Both folds now live under
   `cap_probe_busybox/`; missing inputs fail.

Also fixed: `published()` counted 19 cells by checking only the ConGen half —
`data/results/congen` has a `REAL-FM-4_rs_1n` file with no interactive counterpart, so its
old gap was never computable. A cell is correctable only if both halves exist. 18, not 19.

## Unresolved

1. **`timeout_s = 16 h` is this machine's experience, not a justified margin.** The run
   finished with 28 minutes of headroom. A slower machine stamps `timeout` and loses
   comparability. The reason sits in `config.toml`; the number has no basis.
2. **Cross-model gaps are not on a common budget** (1,000 / 5,000 / `no_query` at
   953–2,386) and cannot be — REAL-FM-7 runs out of askable questions. Each row states its
   own; per-cell gaps deliberately unasserted.
3. **OLD records no `n_queries` at all**, so the published comparison cannot be restated
   in query-cost terms even approximately.
4. **`paper/` is untracked and untouched by me.** Drafts written this week carry the
   pre-correction framing; nothing in the repo gates them. CW owns this.
