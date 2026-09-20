# Revision-added paper numbers: asserted, and their sources shipped

- Date: 2026-09-20
- Branch: `feat/sosym-r1`
- Scope: every figure `main-r1.tex` prints that `check_paper_numbers.py` did not assert
- Gate: **104 → 263 checks** (159 new), green
- Mutation: **158 of 158** module assertions shown red on an altered value; the 159th
  (in-file) shown red by hand

## Enumeration method

Not from the request's list. Two passes:

1. **Token diff** `main-r1.tex` against the frozen submission `s1/main.tex` — every
   numeric literal in r1 absent from s1, by line. Script:
   `enumerate_numbers.py` (scratch; regenerable in five lines, not committed).
2. **Read** of §3 (Table 3 remark), §5.3, §5.4, §5.5.1 for claims whose *tokens* are
   old but whose *assertion* is new — the Table 3 remark is the whole of this class.

The request's eight items all appear. The diff added seven more, listed below.

## What is now asserted, and from what

| # | Claim (paper) | Source |
|---|---|---|
| 12 | tab:biasformula: n, h_bin, h_grp, k, \|B\| for 5 KBs + ea2468 | `data/bias-config/*.yaml` **and** `data/bias/*-bias-stats.txt`, independently |
| 12 | `\|B\| = 2(h_bin+h_grp) + 3C(k,2)` exact on all six | same, recomputed |
| 12b | KB1 is the documented exception (`cross_tree_mode: all`, k = n); the other five `extracted` | bias configs |
| 12c | KB5 838 hierarchical / 58 cross-tree; KB3 36 / 34; ea2468 keeps 1,168 of 1,408 | bias stats |
| 13 | reduction column 1.0 / **105** / 3.6 / 61 / 165 / 1.5 | derived from 12 |
| 14 | ea2468: 1,752 QuickXplain runs, >46 h | `data/folds/ea2468_*_folds.json` + the probe report's rate |
| 15 | read-aloud row: 13/1 examples, 295 candidates, 515/92/6/613 checks, 194 ms, γ = 203, bound ≈ 625 | `data/results_sosym_r1/congen/REAL-FM-7_rs_1n_*.json` |
| 16 | m = \|2-COV\| = 9 / 16 / 14 / 18 / 21 for RS(m) | `data/examples/*_rs_m.json`, `*_2cov.json` |
| 17 | KB5 RS(n) fold 4.1–4.3 h; KB4 grows 3.6× / 8.3×; the two n/a cells ≈ 2 and 4 days | congen results |
| 18 | order sensitivity: 12 folds > 0.1, their identity, median 0.004, max 0.077, desc max 0.46 | `order_sensitivity.json`, F1 recomputed from per-permutation P/R |
| 18b | KB3 RS(n) description F1 0.313 vs semantic 0.660 | congen results |
| 19 | working example: 18 entries, 12 distinct, the six duplicate pairs; figure's MSS/KB consistent with them | derived from the enumeration rule Table 3 states |
| 1 | \|Cτ\| **as an ordered sequence** KB1..KB5 = 22, 342, 130, 428, 994 | already counted from UVL; order was not asserted |

Files: `apps/sosym_r1/revision_{bias_composition,ea2468_limit,run_cost,order_and_working_example}.py`,
called by `check_paper_numbers.py`; `apps/sosym_r1/mutate_revision_checks.py` is the
liveness proof.

## Findings (three paper edits, one doc defect)

**1. tab:biasformula KB2 reduction was 104; it recomputes to 105.** The column is
`(2h + 3C(n,2)) / |B|`. On KB2 that is 47,979/459 = **104.53 → 105**. 104 is what
`3C(n,2) / |B|` gives (104.12) — the same ratio with the hierarchical candidates dropped
from the numerator but kept in the denominator. Every other row is identical under both
readings, which is why nothing caught it; KB1 is the row that settles which is meant,
since only the whole-bias ratio makes k = n come out at exactly 1.0. **Edited: table +
prose, 104 → 105.**

**2. The order-sensitivity exclusion was described by the wrong property.** The paper
said 0.077 holds "wherever the fold has more than one positive example". Measured: the
twelve folds that move by more than 0.1 are **not** the low-positive folds — seven of
them train on 4 to 17 positives, and ten of the fifteen folds that do train on ≤1
positive move by 0.077 or less. What the twelve *are* is exactly the 2-COV, RS(m) and FF
folds of KB₁ and KB₃. The three numbers (0.004, 0.077, 0.46) are correct under that
partition. **Edited: §5.3 and §5.6 (twice), restated by the measured membership.**

**3. The 95 s ea2468 rate cannot be recomputed, and was measured elsewhere.** The probe's
raw output (`ea2468_probe.jsonl`, `ea2468_run.log`) was never committed and does not
exist anywhere — repo, history or scratch. It was also measured on an **Apple M1 Pro /
16 GB**, not the M4 Pro / 48 GB of §5.3. No data file was fabricated. Instead:
the committed probe report is now the cited provenance and the gate *parses* its figures,
and the 46 h is recomputed from committed fold files (1,752 QuickXplain runs × 94.8 s =
46.1 h). **Edited: §5.3 says the rate is a probe on a different machine and that the
artifact ships the report, not the raw output.**

**4. `data/bias-config/README.md` is stale.** It logs "Cross-tree mode: all" for
REAL-FM-4, fqa and arcade-game; their YAML says `extracted`, and the built biases agree
with the YAML. The paper is right, the log is wrong. Not fixed here (it is a captured
console log, and the gate now asserts the YAML directly) — flagged.

## Unassertable, and why

- **"Reduce never keeps both members of a commutative pair", on the walkthrough.** No
  code path builds the working-example bias: the evaluation generator speaks
  mandatory/optional/alternative/or/requires/excludes and cannot express `{→, ∧, ∧̸}`
  over ordered pairs. Asserting it would mean inventing three fixtures (a toy UVL, a toy
  bias, toy examples) and hoping the implementation reproduces a hand-drawn trace. What
  *is* asserted is the enumeration (18, 12, the six pairs, derived not transcribed) and
  that the figure's own MSS `{c7,c12,c13,c18}` and theory `{c7,c12,c13}` differ by
  exactly one member of exactly one duplicate pair.
- **The 95 s rate itself.** See finding 3.

## Artifact changes

- `keep-list`: the four revision modules + the mutation harness (the section is
  file-by-file by design, so they would not have shipped); both ea2468 probe reports.
- `carve.sh`: one named exception to the mechanical example/fold filter — ea2468 fold
  files (112 KB) have no result but now have a reader, and the filter prints a positive
  kept-count and refuses to pass if the exception matches nothing. Their example sets
  (148.6 MB) stay dropped.
- `patches/prose-ea2468-probe-reports.patch`: rewords the four spots in the two probe
  reports that name a sibling algorithm's runners or a numbered review item.
- `release/README.md`: the stated `MINIMUM_CHECKS` floor, 90 → 250.

## Shipped

Carve `88667be` from source `cadc596`, published to `main` and `v1.0.0` (verified by
fetching the tag back: it resolves to `88667be`). `CITATION.cff` `date-released:
2026-09-20`, the tag day.

Acceptance, measured in the carved tree, not assumed:

| gate | result |
|---|---|
| `check_paper_numbers.py` | **258** checks, green (263 here; the artifact drops the two sections that read `data/results`) |
| `check_paper_tables.py` | 1,420 cells, 0 mismatched |
| `reproduce_tables_sosym.sh` | exit 0; `git status` clean afterwards, so every table regenerated byte-identical |
| `pytest tests/ -q` | **341 passed**, 0 failed, 0 skipped — no red test names |
| hygiene scan | empty (carve step 5) |

Here: 680 passed, 1 skipped, unchanged from the documented baseline.

## Unresolved

1. The second probe measured that **AcqMss**, not preprocessing, dominates ea2468
   (93.5 % of wall). §5.3 still frames the limit through preprocessing. Not wrong — it
   states 46 h as what happens *before acquisition starts* — but one clause would make
   "we stopped at KB₅" airtight. Not added; it is a new claim, not an assertion of an
   existing one.
2. The manuscript's tables are hand-transcribed from the generated fragments. The cells
   are gated (`check_paper_tables.py`), the transcription is not. §5.5.1's read-aloud row
   is now checked against the JSON, which covers one row of one table.
3. `data/bias-config/README.md` (finding 4) — regenerate or delete?
