# Step 0 — Golden/results inventory for B2/B3 determinism regen (READ-ONLY)

**Purpose:** map every frozen artifact to the code it is a function of, so B2 (`quacq.py:140`) and B3 (`reduce.py:63`) regen scope is known **before** touching code. Artifact for Cowork to approve; no code changed this turn.
**Method:** verified against code on HEAD `7e9d87d` (branch `feat/redesign-abc-v2`). Every mapping below cites a real call-site.
**Convention:** B1 = example-mode pool seed (ADR-0015, deferred to paper-writing); B2 = QuAcq bias order (ADR-0016); B3 = REDUCE MSS order (ADR-0017).

---

## 1. The dependency spine (who produces what)

```
quacq.py:140  set(set_c)  ──► QuAcq query order ──► learned_kb ─┐
                                                                 ├─► reduce.py:63 ──► final KB (kb_assumption_ids, n_kb)
congen.py    AcqMSS b_prime ────────────────────────────────────┘        │
                                                                          └─► ConGen final KB
```

**Decisive finding — `reduce.py` has TWO consumers** (`grep "reduce.reduce"`):
- `conacq/algorithms/acqmss/congen.py:130` — ConGen final KB.
- `conacq/algorithms/quacq/quacq.py:246` — QuAcq final KB (`set_b_prime=learned_kb, set_neg_tv=[]`).

⇒ **QuAcq output is a function of BOTH B2 and B3.** ConGen output is a function of **B3 only** (B2 = `quacq.py:140`, not on the ConGen path).

**Two nuances that shrink the blast radius:**
- **n_mss is PRE-reduce** (`congen.py:126`, `len(b_prime)` before `reduce()`). So B3 does **not** move `n_mss` (78/102) — only `n_kb` / `kb_assumption_ids` / accuracy.
- **QuAcq KB is empty on REAL-FM-7** (`test_t11_e2e_learned_kb.py:12`). There `reduce([])→[]`, so on that fixture B3 is a **no-op** for QuAcq; only B2 (trajectory) moves it. QuAcq's B3 sensitivity shows up only where its learned KB is non-empty (the synthetic `test_quacq.py` pins).

---

## 2. Artifact inventory (each frozen artifact → source → B-sensitivity)

| # | Artifact | Tracked | Source it is a function of | B2 | B3 | B1 |
|---|---|---|---|:--:|:--:|:--:|
| 1 | `tests/test_quacq.py` KB/trajectory pins (`kb_assumption_ids==[10,12]/[10]`, `len==2/3`, `n_kb=3`, `query_history`) | ✓ | QuAcq run (synthetic bias, **non-empty** KB) | ✓ | ✓ | — |
| 2 | `tests/fixtures/t11_oracle_net/layer23_prepared_and_e2e.json` → key `["quacq"]` (query trajectory; empty KB) via `test_t11_e2e_learned_kb.py::test_quacq_learned_kb_identical` | ✓ | QuAcq trajectory on REAL-FM-7 | ✓ | — (empty KB) | — |
| 3 | same file → keys `["congen_rs"]` (kb=17,n_mss=78), `["congen_ff"]` (kb=18,n_mss=102) via `test_congen_*_learned_kb_identical` | ✓ | ConGen E2E (n_kb post-reduce; **n_mss pre-reduce = stable**) | — | ✓ (n_kb only) | — |
| 4 | `tests/fixtures/t11_oracle_net/congen_runner.json` via `test_t11_congen_runner_net.py` | ✓ | ConGen runner output | — | ✓ | — |
| 5 | `data/results/congen/*.json` (19) | ✓ | ConGen CV (n_kb, reduction, accuracy, #CC) | — | ✓ | — |
| 6 | `data/results/interactive/*_example_{first,only}.json` (36) | ✓ | ConGen **example-mode** CV | — | ✓ | ✓ |
| 7 | `tests/resources/t9_extraction_golden/results_tables.{md,tex}` via `test_t9_metrics_safety_net.py` | ✓ | `extract_results(data/results/congen)` — re-extract only, no re-run | — | ✓* | — |
| 8 | `paper/tables/results_tables.{md,tex}` (+ `old/`) — ACQMSS Tables 7/9/10/11 | ✗ (untracked) | paper tables from `data/results` | — | ✓ | ✓ |
| 9 | `tests/fixtures/t11_oracle_net/{trace,queries}_*.json` (REAL-FM-7/arcade/busybox) via `test_t11_oracle_trace_net.py` | ✓ | **Oracle** replay on a **fixed** query set (`"only READS … never regenerates"`) | — | — | — |
| 10 | `layer23…json` prepared-task-ID keys via `test_t11_prepared_task_ids.py` | ✓ | deterministic task **preparation** | — | — | — |
| 11 | `data/results/old_results/*` (252) | ✓ | archived runs; read only by `from_json` **schema** sweep (not value-pinned) | — | —† | —† |

\* #7 only changes **if** `data/results/congen` (#5) is regenerated — the extraction test re-extracts frozen data, it does not re-run ConGen. #5 and #7 are a coupled pair.
† #11 reorder-insensitive at the schema level; needs regen only if you want the archived snapshots to reflect new numbers (probably out of scope — confirm).

---

## 3. B2 blast radius (fix `quacq.py:140`, QuAcq bias order)

Regenerate (all attributable to bias-order):
- **#1** `test_quacq.py` pins (query_history certainly; KB content where non-empty).
- **#2** `layer23…json["quacq"]` trajectory.
- **QuAcq CV data** `data/results/quacq/*` — **does not exist today** (run_quacq writes there; never committed). Only needed if the paper reports QuAcq numbers (see open Q1).

**Not touched by B2:** ConGen (#3–#8), oracle traces (#9), prepared IDs (#10). B2 does **not** enter the ConGen/AcqMSS extraction tables.

⚠️ **Test-side mirror:** `test_quacq.py:192/498/589` contain their own `remaining_bias = set(task.set_c)` (mirroring the bug). The B2 fix must decide whether these are (a) exercising `generate_from_sat` with a set input (leave), or (b) need aligning so the test actually pins the *ordered* behavior. The "knob-has-teeth" test (ADR-0016 contract) belongs here.

## 4. B3 blast radius (fix `reduce.py:63`, REDUCE order) — run AFTER B2

Regenerate (all attributable to reduce-reorder):
- **ConGen:** #3 (`congen_rs`/`congen_ff` **n_kb only**, n_mss stable), #4 congen_runner.json, #5 `data/results/congen/*`, #6 `data/results/interactive/*` (reduce path; B1 stays deferred), #7 t9 extraction golden (after #5), #8 paper ACQMSS tables.
- **QuAcq (OVERLAP):** #1 `test_quacq.py` KB pins **again** — the incremental reduce-reorder delta on top of B2's already-regenerated values.

**Not touched by B3:** #2 (QuAcq empty KB on REAL-FM-7 → reduce no-op), #9, #10, n_mss.

## 5. The overlap and its sequencing (the point of two separate commits)

**Overlap set = #1 `test_quacq.py` KB pins** — a function of BOTH B2 and B3 (QuAcq calls `reduce`).

Clean-diff protocol (why B2 first, then B3, each its own commit):
1. **Commit B2:** fix `quacq.py:140` → regen #1 (+#2). The #1 diff = **bias-order** effect. Cowork reviews; suite green.
2. **Commit B3:** fix `reduce.py:63` → regen #1 **again** (incremental) + #3–#8. The #1 diff at this step = **reduce-reorder** effect *on top of* the post-B2 values; the ConGen diffs (#3–#8) = reduce-reorder. Each diff maps to exactly one fix.

If B3 ran first (or both together), #1's diff would blend two causes and violate "one golden diff = one fix." Ordering is load-bearing.

## 6. Regen mechanics (proposed — confirm before I run)

- **Test-embedded goldens (#1–#4):** regenerated by running the pipeline in-process; #2–#4 are recorded JSON fixtures rebuilt by their recorder scripts (e.g. `scripts/build_t11_oracle_net_fixtures.py` for the t11 net — confirm the exact script per fixture).
- **CV data (#5,#6):** re-run `apps.run_congen` / `apps.run_cv` (and example-mode variants) on the affected FMs → overwrite `data/results/{congen,interactive}/*`.
- **Extraction golden + paper (#7,#8):** `python -m apps.extract_results --results-dir data/results/congen --output-dir …` → refresh `tests/resources/t9_extraction_golden/*` and `paper/tables/*`.
- Every step's diff itemized (cell/row + "caused by reorder, not a new bug") as the Cowork review artifact **before** commit.

---

## 7. Open questions for Cowork (blockers before B2 code)

1. **QuAcq paper footprint.** The frozen extraction/paper tables (Tables 7/9/10/11, T9 golden) are **ACQMSS/ConGen only**; `data/results/quacq/` does not exist. Does the paper report QuAcq numbers anywhere (a separate table, or the QuAcq→ConGen pipeline)? If **no**, B2's regen scope is just #1+#2 (test goldens) with **zero** paper/data-results impact. If **yes**, point me at the QuAcq results source to regenerate.
2. **`data/results` regen authority.** #5/#6 are 55 tracked JSONs. Confirm I re-run the pipeline to overwrite them (vs. you regenerate them out-of-band and I only update the test goldens). Which config files drive the canonical CV runs (`apps/conf/*.toml`)?
3. **`old_results` (#11).** Leave frozen (schema-only), or regenerate to match new numbers? I propose leave — confirm.
4. **example-mode coupling (#6).** `data/results/interactive/*` sit under both B3 (reduce) and B1 (example seed, deferred). Regenerating them now for B3 would bake in the *current* unseeded example order (B1 not yet fixed). Options: (a) defer #6 entirely until B1 lands, or (b) regen #6 for B3 now and again at B1. I lean (a) to avoid a double-regen churn — confirm.
5. **Fixture recorder scripts.** Confirm the exact recorder for each of #2/#3/#4 (t11 net + congen_runner) so the regen is reproducible, not hand-edited.

**No code touched this turn.** `progress.md` self-report already superseded by Cowork's verified entry (nothing to revert). Awaiting inventory approval before B2 code.
