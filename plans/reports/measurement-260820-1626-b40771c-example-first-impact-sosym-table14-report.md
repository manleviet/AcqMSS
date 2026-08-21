# b40771c impact on example-first & SoSyM Table 14 — measurement report

- Date: 2026-08-20
- Branch/HEAD: `feat/conmin` @ `fd84762`
- Mandate: measure only. **No repo file modified** — `git diff --stat HEAD` empty; reference JSON sha256 unchanged (`5142334f1d3801d5…`). Configs + counterfactual probe live in the session scratchpad; runs redirected via `run_cv -o <scratchpad>`.
- Host: darwin, 8 cores, glucose4, `solver_mode=incremental`, single process.

## TL;DR

1. Rerun of `REAL-FM-7_rs_1n` interactive/example_first on HEAD is **NOT byte-identical** to `data/results/interactive/REAL-FM-7_rs_1n_cv_incremental_example_first.json`.
2. example_first **does** traverse b40771c — proven by call path, by permanent diagnostic counters, and by an in-memory counterfactual revert. **C1 does not narrow.**
3. `max_queries` in force when `data/results/interactive/` was generated = **1000** (config never edited in whole history + all 54 example_first folds pinned at [1000,1035]).
4. Wall-clock example-first rs_1n on HEAD: KB1 8.4 s, KB2 74.2 s, KB3 169.2 s (total ≈ 4.2 min) vs reference ≈ 24 min.
5. **Table 14 (`tab:iterative_semantic`) is fed by the stale pre-fix `data/results/interactive/`** → its Iterative rows are stale w.r.t. b40771c. Largest exposure: KB3.

## Method

Config copied to scratchpad, edited to `algorithm="interactive"`, `query_mode="example_first"`, single model `REAL-FM-7_rs_1n`. HEAD config ships `algorithm="congen"` + only REAL-FM-4 enabled, so an unmodified in-repo invocation cannot produce the requested run.

Note `run_cv.py:76` sets `output_dir = base_dir / algorithm` → a default run would have **overwritten** the reference file. All runs used `-o <scratchpad>`.

Counterfactual arm: `revert_b40771c_probe.py` rebinds two attributes before `runpy.run_module("apps.run_cv")` — call sites resolve both at call time, so no source edit is needed:

- `findscope.prune_rejecting` → wrapper forcing `include_bg=True` (pre-fix)
- `FindC._narrow_with_generator` → falls back to `candidates[0] if candidates else None` (pre-fix). Restoring the inner tail also restores the pre-fix outer `return remaining[0]`, since `run()` returns any non-None result from it.

## Q1 — byte-identical? **No**

sha256 REF `5142334f…` vs HEAD `4baab064…`; size 99,206 B → 18,675 B.

Three independent causes; only (c) is algorithmic.

### (a) Pipeline stage — not an algorithm difference

HEAD `run_cv` emits `evaluation: null` (per-fold + intersected) and `summary: null` **by design** — `conacq/eval/report.py:253,266,272` ("eval placeholders"). Reference has them filled (embeds tp/fp/fn constraint lists) → accounts for ~80 KB of the delta. Filler identified: see "Resolved #2".

### (b) Schema drift

Fold `performance` lost `n_kb, n_mss, congen_runtime_ms, acqmss_runtime_ms, acqmss_calls`; gained a `profiler` sub-dict.

### (c) Genuine divergence — `REAL-FM-7_rs_1n`, 3 folds

| field | REF | HEAD |
|---|---|---|
| `mean_accuracy` | 1.0 | 0.9444 |
| `fold_accuracies` | [1, 1, 1] | [0.8333, 1, 1] |
| fold `n_kb` | [7, 1, 1] | [0, 2, 3] |
| `intersected_kb.n_kb` | 1 (`c103 gui_builder excludes sdi`) | **0** |
| fold0 precision / specificity / FP | 1.0 / 1.0 / 0 | 0.833 / 0.0 / 1 |
| `consistency_checks` | [1001, 1000, 1004] | [1009, 1002, 1006] |
| `findscope_calls` | [1463, 1482, 1491] | [1365, 1211, 1076] |
| `findc_calls` | [159, 164, 165] | [91, 109, 72] |
| `prune_calls` | [197, 178, 177] | [372, 451, 435] |
| `prune_is_consistent_calls` | [12491, 17540, 17477] | [32155, 35276, 37372] |
| `dis_gen_calls` | [4, 0, 0] | [91, 107, 69] |
| `total_runtime_ms` | 12,723 | 8,093 |

Learned constraint sets nearly disjoint — only `gui_builder excludes sdi` shared, and in different folds.

### Seed is NOT a confound

Config at results commit `0b0313a` had `seed = 82`; HEAD has `42` (changed at `f0a8ee5`, 2026-06-18, **after** the results). Ran both: identical results (`n_kb [0,2,3]`, same `consistency_checks`, same constraints). Folds come from `folds_path` → `seed` inert on this path. Verified for REAL-FM-7 example_first only.

### Provenance gap driving (c)

Reference committed at `0b0313a` (**2026-02-28**) — five months and **26** `conacq/algorithms/quacq/`-touching commits before b40771c (2026-07-26). Also 24 commits in `conacq/oracle/`, 15 in `conacq/eval/`. A REF-vs-HEAD diff therefore measures cumulative drift, not b40771c. Isolation required the counterfactual (Q2).

## Q2 — does example_first traverse b40771c? **Yes, heavily**

### Call path

```
apps/run_cv.py:190                  n_fold_cross_validation_interactive(query_mode='example_first')
conacq/eval/cross_validation.py:449 → QuAcqRunner(query_mode=…)   conacq/runners/quacq_runner.py:119
conacq/algorithms/quacq/quacq.py    QuAcq.learn(mode='example_first')
  :194  query_provider.generate(...)          ← ONLY mode-specific step
  :213  answer = oracle.is_valid(query)
  :218  answer=True  → prune_rejecting(...)   include_bg defaults True (b40771c preserved this)
  :225  answer=False → FindScope(...).run(...)
          findscope.py:89  recursion, ask_query=True
          findscope.py:64  partial → oracle.is_valid(partial)
          findscope.py:72  prune_rejecting(..., include_bg=False)      ← b40771c hunk 1
          sat_utils.py:44  base = ([root] if include_bg else []) + …   ← b40771c hunk 1
  :236  FindC(...).run(...)
          findc.py:148  candidates[0] if len(candidates)==1 else None  ← b40771c hunk 2
          findc.py:108  return None                                     ← b40771c hunk 2
```

The main loop is **mode-agnostic after query generation**. `mode` selects only the query *source* (`generate_from_sat` / `generate_from_pool` / `generate`). Nothing gates FindScope/FindC on `mode`. The mode-scoped guards at `quacq.py:255,263` are the *liveness band-aid*, not the FindScope/FindC entry.

### Empirical — diagnostic counters (added by `afaa04b`), per fold

- `quacq_findc_unconfirmed` = **91 / 106 / 69** (266) — counts exactly hunk-2 decisions (`None` instead of `remaining[0]`)
- `quacq_prune_partial_pruned` = **0 / 6 / 57** (63) — constraints pruned at the `include_bg=False` site (hunk 1)

329 hits in one 3-fold run.

### Counterfactual A/B (seed held; both seeds tested, identical)

| arm | fold `n_kb` | counters |
|---|---|---|
| HEAD | [0, 2, 3] | findc_unconfirmed 91/106/69; prune_partial 0/6/57 |
| b40771c reverted | **[5, 2, 6]** | **neither counter present** |

Learned sets differ substantially. b40771c materially changes example_first output.

### On "example-only byte-identical" in the commit message

That is a claim about *outcome on that pool*, not code reachability. example_only reaches the same sites: `data/results_conmin/tables/app-quacq-diag.md` QuAcq-ex rows (`reason=pool_exhausted` ⇒ example_only) print `declined` 1.1 / 0.4 / 0.0 / 1.3 / 0.6 and `pruned_p` 16.1 / 2.4 / 24.4 / 0.4 / 11.2 — non-zero on 4 of 5 KBs.

## Q3 — `max_queries` actually used = **1000**

1. **Config**: `max_queries = 1000` introduced at `af37e3a` (2026-02-26); full `git log -p apps/conf/run_cv_config.toml` shows exactly one `+max_queries` line and **no later edit** through HEAD. In force at `0b0313a`.
2. **In the result files.** `consistency_checks` ← profiler `paper_consistency_checks` (`conacq/runners/metrics.py:67`), incremented at the three oracle-query sites `quacq.py:210`, `findscope.py:63`, `findc.py:132`:
   - all **54/54** example_first folds ∈ **[1000, 1035]** — min exactly 1000, none below
   - all **54/54** example_only folds ∈ **[4, 234]**

   Cap binds in example_first for every fold. The 0–35 overshoot is the documented soft ceiling (`quacq.py:173` — `max_queries`/deadline checked between outer iterations; an in-flight FindScope/FindC overruns). example_only stops at pool exhaustion, nowhere near the cap — the contrast rules out coincidence.
3. **Gap**: stop reason is **not serialized** — `convergence_reason` is absent from the fold dict emitted by `report.py`. Inferred from the overshoot signature, not read directly.

Caveat: at `0b0313a` the committed config said `query_mode = "example_only"`, yet that commit contains **both** `_example_only` and `_example_first` files ⇒ the example_first files came from an **uncommitted** config edit. Config-at-commit is authoritative for `max_queries` (never edited in the whole history) but **not** for `query_mode`.

## Q4 — wall-clock, example-first, rs_1n, 3-fold, HEAD

| KB | paper id | n_bias | HEAD `real` | HEAD `total_runtime_ms` | per-fold ms | REF ms | speedup |
|---|---|---|---|---|---|---|---|
| REAL-FM-7 | $KB_1$ | 295 | **8.37 s** | 8,132 | 2408 / 2770 / 2914 | 12,723 | 1.6× |
| fqa | $KB_2$ | 459 | **74.24 s** | 73,991 | 18686 / 22502 / 32670 | 258,109 | 3.5× |
| arcade-game | $KB_3$ | 1,755 | **169.20 s** | 168,980 | 56841 / 58026 / 53919 | 1,169,106 | 6.9× |

Total ≈ **252 s (4.2 min)** vs reference ≈ 1,440 s (24 min). `real` includes ~0.5 s interpreter + flamapy startup. Speedup consistent with the recorded checker gate split (T19).

Learned KB sizes diverge from reference on every KB:

| KB | REF fold `n_kb` | HEAD fold `n_kb` |
|---|---|---|
| $KB_1$ REAL-FM-7 | [7, 1, 1] | [0, 2, 3] |
| $KB_2$ fqa | [4, 2, 2] | [2, 14, 2] |
| $KB_3$ arcade-game | [1, 1, 0] | **[10, 12, 22]** |

Runs deterministic — REAL-FM-7 reproduced identically across two invocations and across both seeds.

## Resolved — previously open questions

### #1 Table 14 identity & lineage (user-supplied, verified in-repo)

**Table 14 = `tab:iterative_semantic`** — Overleaf `SoSyM/main-r1.tex` l.797; in-repo source `paper/evaluation.tex:357`. Caption: *Semantic F1-score (structural KB quality) comparison: ConGen vs. iterative approaches*. Rows: ConGen (passive) / Iterative example-only / Iterative example-first × {RS(n), RS(3n), 2-COV, FF}; cols $KB_1$ REAL-FM-7, $KB_2$ FQA, $KB_3$ Arcade (`paper/evaluation.tex:109-111`).

Two **separate papers, separate pipelines** — earlier conflation corrected:

| paper | results dir | generator | b40771c status |
|---|---|---|---|
| **SoSyM** (Table 14) | `data/results/interactive/` | `apps/extract_results.py` → `paper/tables/` | **PRE-fix** — committed 2026-02-28 |
| ConMin / AAAI | `data/results_conmin/` | `apps/make_tables/` → `data/results_conmin/tables/` | POST-fix — `_long.csv` mtimes 2026-07-26T10:53+, i.e. 4 min after b40771c (10:49:57) |

`apps/make_tables/__main__.py:23` hardcodes `_DEFAULT_RESULTS = "data/results_conmin"` — it never reads `data/results/interactive/`. `apps/make_tables` is **not** the SoSyM generator.

### #2 Which stage fills `evaluation` / `summary`?

`apps/run_compare.py:128-155` — loads each `*_cv_*.json`, sets `fold['evaluation']` (:136), `ik['evaluation']` (:142), `data['summary']` (:146), then rewrites **in place** via `write_json_atomic(cv_file, data)` (:155).

Full SoSyM chain: `run_cv` → `data/results/interactive/*_cv_*.json` (`evaluation: null`) → `run_compare` (fills in place) → `extract_results` → `paper/tables/`.

Note `run_compare.py:141` guards intersected fill on `ik.get('kb_constraints')` non-empty. HEAD yields `intersected_kb = []` for REAL-FM-7_rs_1n → that block would stay `null` even after `run_compare`.

## Implication for C1 / Table 14

C1 does **not** narrow. Table 14's Iterative rows derive from pre-fix data that b40771c demonstrably changes.

Cells at risk — Table 14, Iterative example-first, RS($n$) row is currently:

| | $KB_1$ | $KB_2$ | $KB_3$ |
|---|---|---|---|
| Iterative — example-first, RS($n$) | 0.064 | 0.057 | 0.046 |

Largest exposure **$KB_3$ (Arcade)**: HEAD learns [10, 12, 22] constraints vs reference [1, 1, 0]. A ~10–20× increase in learned KB size will move semantic F1 well off 0.046. $KB_2$ fold1 also jumps 2 → 14.

Direction of the paper's qualitative claim (iterative sem-F1 ≪ ConGen) is **not** established either way by this report — sem-F1 was not computed here because `run_compare` was not run (out of "no sweep" scope). The claim needs re-derivation, not assumption.

Example-only rows are on the same stale pipeline and reach the same code sites (see Q2), so they are also suspect despite the commit's example-only claim.

## Reproduction

```bash
# scratchpad config: algorithm="interactive", query_mode="example_first", one model
uv run --no-sync python -m apps.run_cv <scratchpad>/rerun_fm7_rs1n.toml -v -o <scratchpad>/out
#   MUST pass -o: run_cv.py:76 writes to <output_dir>/interactive/ and would overwrite the reference

# counterfactual (b40771c reverted in memory, no source edit)
uv run --no-sync python <scratchpad>/revert_b40771c_probe.py --revert <cfg> -o <scratchpad>/outB
```

To regenerate Table 14: full SoSyM sweep (3 KBs × 6 samplings × 2 query modes) → `run_compare` → `extract_results`. Not run here.

## Unresolved

1. Regenerated Table 14 numbers — requires the SoSyM sweep + `run_compare` + `extract_results`; explicitly out of scope this session. $KB_3$ expected to move most.
2. Whether the paper's qualitative conclusion (iterative ≪ ConGen structurally) survives regeneration. HEAD learns *more* constraints on $KB_2$/$KB_3$ and *fewer* on $KB_1$ fold0 — net sem-F1 direction unknown without running the scorer.
3. Do the other 25 quacq-touching commits also shift Table 14? Counterfactual isolated b40771c only; reverted arm [5,2,6] still ≠ reference [7,1,1], so residual drift exists and is unattributed.
4. Whether `data/results/interactive/` should be regenerated in place or versioned alongside a fix-note — a reproducibility/provenance decision, not a measurement.
5. `convergence_reason` is not serialized into CV JSON. Adding it would make future max_queries questions readable rather than inferred.
