# ConMin `app-checks` / appendix — counter unit-mismatch audit

- Date: 2026-08-21
- Branch/HEAD: `feat/conmin` @ `fd84762`
- Mandate: read-only. **No file modified.** `data/` untouched, no Overleaf clone present.

## Verdict

**Hypothesis confirmed.** `checks_total` sums two *batch/node*-unit counters (`gate`, `adm`) with three *atomic solver-call*-unit counters (`cRej`, `cQx`, `red`). Every share/percentage derived from that sum — including the KB₅ "87 per cent" — is unit-inconsistent.

Both of the user's specific claims hold:
- `adm` is **node-unit** — confirmed at source and by commit archaeology.
- `cRej` is **solver-call-unit** — confirmed at source and empirically on **810/810** committed rows.

Whether the 87 % figure *reverses* is **KB-dependent**; see Q3. For KB₅ specifically it is **not determinable** from committed data.

## Q1 — granularity of the six `app-checks` columns

Published table reproduced exactly from committed CSVs — filter is `condition=C∪S`, `k=1`, exclude-2COV means (all 5 KBs matched to the digit).

| col | profiler counter | increment site | underlying solver call | unit |
|---|---|---|---|---|
| `gate` | `conmin_admpool_gate_checks` | `conmin.py:186` (`+1`) | `conmin.py:177` `is_consistent_test_cases(…, stop_at_first_violation=True)` | **BATCH** — 1…\|E⁺\| solves counted as 1 |
| `adm` | `shared_admpool_checks` | `acqmss.py:83` (`+1`) | `acqmss.py:76` `is_consistent_test_cases(…, stop_at_first_violation=False)` | **BATCH / node** — exactly \|E′⁺\| solves counted as 1 |
| `cRej` | `conmin_cover_rejection_checks` | `acqmincover.py:110` (`+1`) | `acqmincover.py:111` `is_consistent(...)` | **ATOMIC** — 1:1 |
| `cQx` | `conmin_cover_quickxplain_checks` | `acqmincover.py:124-126` (`+= is_consistent_calls` delta) | QuickXplain internals | **ATOMIC** |
| `red` | `redundancy_consistency_checks` | `reduce.py:90` (`+1`) | `reduce.py:89` `is_consistent(...)` | **ATOMIC** — 1:1 |
| `tot` | `checks_total` | `conmin_cv_evaluator.py:343` | — | **MIXED** — 2 batch + 3 atomic |

Mechanism: `explanation/checker/backend.py:76-86` — `is_consistent_test_cases` loops over `set_tc` calling `is_consistent` once per test case. With `stop_at_first_violation=False` that is **exactly `len(set_tc)` solver calls**; the caller records `+1`.

`is_consistent` itself is `@count_calls(key="is_consistent_calls")` on every concrete backend (`backend.py:125, 180, 258`) — a true atomic counter exists, but is **not** exported to the long CSV (see Q3).

### `adm` was deliberately changed from atomic → batch

| commit | date | `acqmss.py:83` |
|---|---|---|
| `9b4ac26` | 2026-07-23 | `increment("shared_admpool_checks", len(set_tc))` ← **atomic** |
| `63d2d65` | 2026-07-23 | `increment("shared_admpool_checks")` ← **batch** |

Confirms the user's reading of `9b4ac26 → 63d2d65`.

### Internal contradiction — same taxonomy, same day, opposite directions

`3ac559a` (2026-07-23) is the **GAP A** fix. Its own message: `conmin_cover_quickxplain_checks` counted +1 per QX invocation; changed to the `is_consistent_calls` delta — *"same atomic granularity as the cover rejection check, so the §9c total is R1-Q4 complete"*. The in-code comment at `acqmincover.py:117-121` repeats it: *"Keeps this phase's checks in the §9c total at the same atomic granularity as the rejection check above."*

So the **stated design intent of the §9c total is atomic**, and `cQx` was moved *to* atomic — while `63d2d65` moved `adm` *away from* atomic, on the same day. The two fixes pull opposite ways.

### The batch choice is documented, not accidental

`acqmss.py:80-82` and `conmin_cv_evaluator.py:352-355` give a rationale: batch granularity matches ConGen's `paper_consistency_checks`, *"the papers define 'checking all E⁺ = ONE consistency check', ConMin l.535 = ConGen SoSyM l.549, and the 2γ·log₂(n/γ)+2γ bound is batch."* `stage1_batch_checks` is correctly **labelled** BATCH.

The defect is therefore **not** that batch is the wrong unit for Stage-1. It is that `checks_total` adds batch and atomic counters, and the `tot` column + derived percentages inherit the mix. Cover-rejection has no "all E⁺" structure to batch over, so the two phases have genuinely different natural units — the sum cannot be made coherent by relabelling alone.

## Q2 — `|E⁺|` per KB from committed data (`n_train_pos`)

Unique per `(example_set, fold)`; Stage-1 is k-invariant so k-duplicates collapsed.

| KB | | all samplings min/mean/max | exclude-2COV min/mean/max |
|---|---|---|---|
| $KB_1$ | REAL-FM-7 | 0 / 10.1 / 26 | **4 / 12.1 / 26** |
| $KB_2$ | fqa | 0 / 115.9 / 323 | **10 / 139.1 / 323** |
| $KB_3$ | arcade-game | 0 / 42.6 / 118 | **8 / 50.9 / 118** |
| $KB_4$ | REAL-FM-4 | 0 / 187.3 / 524 | **11 / 224.7 / 524** |
| $KB_5$ | busybox-1.18.0 | 0 / 250.9 / 513 | **240 / 376.3 / 513** |

`n=18` per KB (`n=9` busybox); exclude-2COV `n=15` / `n=6`. The `min=0` rows are 2COV, excluded from the published means.

## Q2b — empirical confirmation that `cRej` is atomic

Tested `checks_cover_rej == n_mss × n_train_neg` on every ConMin row (`condition ∈ {C, C∪S}`, all k, all samplings):

| KB | match |
|---|---|
| $KB_1$…$KB_4$ | 180/180 each |
| $KB_5$ | 90/90 |
| **total** | **810/810 exact** |

Exact equality with the `|A| · |E⁻|` double-loop product is only possible if the counter increments once per solver call. **`cRej` atomic — confirmed empirically, not just by reading.**

(The 76 rows that fail the identity are all `condition=A`, `negatives=n/a`, `cRej=0` — condition A is NE-inert and runs no cover phase. Excluded correctly above. Note 810 *rows* ≠ the appendix's "648 folds" — different counting units, k and negatives-mode multiply rows; not a contradiction, but the appendix's denominator was not reproduced here.)

`paper/appendix.tex` is **not in-repo** (only `paper/evaluation.tex`, which is SoSyM). The appendix text at l.450–456 could not be read; its *substance* was verified empirically instead.

## Q3 — decisive bound test

Stage-1 true atomic cost `S1 ∈ [adm, adm × |E⁺|_root]`. Lower bound: ≥1 solve per counted node — valid here because a node is only reached with non-empty `E′⁺` (`acqmss.py:85-87` returns as soon as `set_tcp` is empty), and exclude-2COV `|E⁺|_min ≥ 4` on every KB. Upper bound: root `|E⁺|`, since `E′⁺` shrinks with depth (`acqmss.py:98, 101-103`).

Crossover ratio = `cRej / adm` = the mean solves-per-node at which Stage-1 overtakes cover-rejection.

| KB | gate | adm (LB) | cRej | red | tot | LB > cRej? | per-row | crossover | root \|E⁺\| | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| $KB_1$ | 1 | 509 | 139 | 78 | 726 | **YES** | **30/30** | 0.27 | 4–26 | **REVERSES** |
| $KB_2$ | 1 | 603 | 3,249 | 178 | 4,031 | no | 6/30 | 5.39 | 10–323 | inconclusive |
| $KB_3$ | 1 | 2,918 | 2,568 | 343 | 5,831 | **YES (mean)** | 20/30 | 0.88 | 8–118 | **reverses at the reported mean**; not uniformly per fold |
| $KB_4$ | 1 | 3,358 | 14,077 | 513 | 17,948 | no | 6/30 | 4.19 | 11–524 | inconclusive |
| $KB_5$ | 1 | 10,675 | 82,694 | 1,362 | 94,732 | no | 0/12 | **7.75** | **240–513** | **inconclusive** |

### Per-KB reading

- **$KB_1$ — reverses, decisively.** The lower bound alone (509 ≥ 1 solve/node) already exceeds `cRej`=139, on **30/30** rows. Published `cRej/tot` = 19.1 %; at just 4 solves/node (= the *minimum* root `|E⁺|`) it drops to 6.1 %.
- **$KB_3$ — reverses at the aggregate the table reports.** Crossover 0.88 < 1, so mean `adm` (2,918) > mean `cRej` (2,568). But only 20/30 individual rows satisfy it, so the reversal is a property of the published mean, not of every fold. Published 44.0 % → 14.7 % at 5 solves/node.
- **$KB_2$, $KB_4$ — inconclusive.** LB < cRej < UB. Crossovers 5.39 / 4.19 sit inside the plausible range of mean `|E′⁺|`.
- **$KB_5$ (the "87 per cent" KB) — NOT DETERMINABLE from committed data.** LB 10,675 < cRej 82,694 < UB 10,675 × 240 = 2,562,000. Per the stated decision rule this is the middle case.

  For the record, the crossover is a mean of **7.75** solves per AdmPool node against a root `|E⁺|` of **240–513**. For the tree-wide mean to stay below 7.75 from a root of ≥240 would require very steep shrinkage. **Suggestive, but not measured — I am not calling it.** If it does exceed, 87.3 % → 60.1 % at 5 solves/node, → 3.1 % at 240.

### What must be measured to close it

One counter: the `is_consistent_calls` **delta** around `acqmss.py:76`, exactly mirroring the pattern already in `acqmincover.py:122-126`. ~4 lines, additive, ConMin+ConGen-safe (`shared_` prefix already established).

Re-run cost — Stage-1 only, since `stage1_ms` is k-invariant (summed from committed `stage1_ms` over unique `(kb, example_set, fold)`):

| KB | runs | Stage-1 total | mean/run | max/run |
|---|---|---|---|---|
| $KB_1$ | 18 | 17.6 s | 0.98 s | 2.75 s |
| $KB_2$ | 18 | 409 s | 22.7 s | 77 s |
| $KB_3$ | 18 | 2,529 s (42 min) | 141 s | 480 s |
| $KB_4$ | 18 | 70,481 s (19.6 h) | 3,916 s | 15,270 s |
| $KB_5$ | 9 | 355,232 s (**98.7 h**) | 39,470 s (11.0 h) | 107,170 s (29.8 h) |
| **all** | 81 | **428,669 s ≈ 119 h ≈ 5.0 days** | | |

Cheapest path to a real answer on the 87 % claim: instrument, then re-run **one** $KB_5$ fold ≈ **11 h** (mean) / 29.8 h (worst). Full $KB_5$ ≈ 4.1 days. $KB_1$+$KB_2$+$KB_3$ together ≈ 49 min — but $KB_1$/$KB_3$ need no re-run, they are already decided by the lower bound.

## Q4 — how `checks_total` is computed

`conacq/eval/conmin_cv_evaluator.py:343`:

```python
checks_total = gate + admpool + cover_rej + cover_qx + redundancy
```

**Yes — it adds `adm` and `cRej` directly**, no scaling, no unit reconciliation. Sources bound at `conmin_cv_evaluator.py:182-185` (`conmin_admpool_gate_checks`, `shared_admpool_checks`, `conmin_cover_rejection_checks`, `conmin_cover_quickxplain_checks`) and `:204` (`redundancy_consistency_checks`).

Separately, `stage1_batch_checks = paper_consistency_checks` (`:190`) is the gate+AdmPool batch figure and is honestly labelled BATCH — the mislabelling is confined to `checks_total` and anything derived from it (`tot` column, the 87 % share).

## Bottom line for camera-ready

- The `tot` column and every percentage derived from it mix units. That is a real defect regardless of how Q3 resolves.
- $KB_1$: the phase ranking as published is **wrong** — Stage-1 dominates cover-rejection even at the most conservative bound.
- $KB_3$: published ranking wrong at the reported mean.
- $KB_5$ (the 87 % sentence): **cannot be confirmed or refuted** from committed data. Do not defend it and do not retract it on this evidence; measure it.
- Minimum honest fix without new measurement: stop summing the two families — report Stage-1 as batch checks and cover/Reduce as atomic solves in separate columns, drop `tot` and the % sentence.

## Unresolved

1. True Stage-1 atomic solve count — needs the `is_consistent_calls` delta at `acqmss.py:76`; not in the committed CSV (61 cols, no `is_consistent_calls`). Blocks $KB_2$/$KB_4$/$KB_5$.
2. Appendix text at `appendix.tex:450-456` not verifiable in-repo — no `paper/appendix.tex`, no Overleaf clone. Substance verified empirically (810/810); exact wording and the "648 folds" denominator not checked.
3. "648 ConMin folds" vs the 810 ConMin rows found here — different counting units (k × negatives-mode multiply rows). Which denominator the appendix intends was not resolved.
4. Whether the intended fix is *all-batch* or *all-atomic*. `3ac559a` says atomic; `63d2d65` + the ConMin l.535 / ConGen SoSyM l.549 convention say batch for Stage-1. This is an authorial decision, not a measurement — cover-rejection has no E⁺ batch structure, so neither convention makes the raw sum coherent.
5. `gate` is a `stop_at_first_violation=True` call: it does \|E⁺\| solves when the gate passes, 1…\|E⁺\| when it fails. Its atomic cost is data-dependent and also unmeasured, though at `gate`=1 it is negligible either way.
