# ConGen check-unit factors and AcqMss shrink ratio

Generated 2026-08-22T17:02:04+00:00 from `data/results/congen` at repo `c377567-dirty`.

Regenerate with `python3 tools/sosym_r1/congen_check_unit_factors.py .`

⚠ **Stale inputs.** These results predate ADR-0015, ADR-0016, ADR-0017 and checklist items C6, C7, C11, so the knowledge bases they produced are not what the revision will publish. The ratios are expected to be more robust than the contents, since they are structural properties of the recursion, but that is an expectation. Re-run after the sweep.

⚠ **Preprocessing is absent.** ConGen calls GenerateNE with `profiler=None`, so its solves never reach `is_consistent_calls`. `acq_calls` is AcqMss only. Closing that gap is checklist item C10(a).

## Per knowledge base and sampling (mean over folds)

| KB | sampling | folds | nodes | AcqMss solves | Reduce solves | solves/node | train \|E+\| | shrink |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| REAL-FM-4 | rs_1n | 3 | 10,772 | 978,405 | 2,149 | 90.87 | 174.7 | 0.520 |
| REAL-FM-7 | rs_1n | 3 | 1,545 | 8,732 | 277 | 5.65 | 8.7 | 0.653 |
| REAL-FM-7 | rs_2n | 3 | 1,613 | 17,913 | 210 | 11.10 | 17.3 | 0.640 |
| REAL-FM-7 | rs_3n | 3 | 1,631 | 26,823 | 188 | 16.44 | 25.3 | 0.649 |
| REAL-FM-7 | rs_m | 3 | 1,398 | 4,991 | 397 | 3.56 | 5.3 | 0.667 |
| REAL-FM-7 | 2cov | 3 | 30 | 144 | 885 | 4.80 | 0.0 | — |
| REAL-FM-7 | ff | 3 | 1,357 | 3,983 | 430 | 2.93 | 4.0 | 0.733 |
| arcade-game | rs_1n | 3 | 9,271 | 169,903 | 1,625 | 18.33 | 39.3 | 0.466 |
| arcade-game | rs_2n | 3 | 9,723 | 349,490 | 1,117 | 35.94 | 78.0 | 0.461 |
| arcade-game | rs_3n | 3 | 9,871 | 538,208 | 944 | 54.52 | 117.3 | 0.465 |
| arcade-game | rs_m | 3 | 6,560 | 32,790 | 3,503 | 5.01 | 8.7 | 0.577 |
| arcade-game | 2cov | 3 | 4,286 | 4,530 | 4,127 | 3.03 | 0.7 | — |
| arcade-game | ff | 3 | 8,230 | 49,260 | 2,454 | 5.98 | 11.3 | 0.528 |
| fqa | rs_1n | 3 | 2,118 | 62,097 | 677 | 29.33 | 108.0 | 0.272 |
| fqa | rs_2n | 3 | 2,139 | 127,042 | 651 | 59.42 | 215.3 | 0.276 |
| fqa | rs_3n | 3 | 2,233 | 188,877 | 607 | 84.60 | 322.7 | 0.262 |
| fqa | rs_m | 3 | 1,429 | 4,728 | 1,035 | 3.30 | 10.0 | 0.330 |
| fqa | 2cov | 3 | 30 | 500 | 1,377 | 16.67 | 0.0 | — |
| fqa | ff | 3 | 1,867 | 22,198 | 838 | 11.92 | 39.3 | 0.303 |

## Headline

- **Conversion factor** (solver calls per node) spans **1.04× to 93.70×** across 57 folds. Adding `consistency_checks` to `redundancy_consistency_checks` is wrong by that factor, which is why Table 9 reports both units.

- **Shrink ratio, on the controlled comparison only.** The RS family triples \|E+\| while holding the knowledge base, the bias and the fold structure fixed, so it is the only place the claim can be tested. A knowledge base needs all three to appear here:
  - `REAL-FM-4`: **not testable**, only 1/3 of the RS family present
  - `REAL-FM-7`: 0.653 / 0.640 / 0.649 — spread **0.012** while \|E+\| triples
  - `arcade-game`: 0.466 / 0.461 / 0.465 — spread **0.005** while \|E+\| triples
  - `fqa`: 0.272 / 0.276 / 0.262 — spread **0.014** while \|E+\| triples

  On the 3 knowledge base(s) where all three are present, the ratio barely moves while \|E+\| triples, yet differs substantially between knowledge bases. That supports reporting B17's pruning **per knowledge base** rather than as a single hedged number. It is not established for a knowledge base whose RS family is incomplete.

- Non-RS samplings, for reference only (\|E+\| not controlled): `REAL-FM-7/rs_m` 0.667, `REAL-FM-7/ff` 0.733, `arcade-game/rs_m` 0.577, `arcade-game/ff` 0.528, `fqa/rs_m` 0.330, `fqa/ff` 0.303

- **Excluded from every shrink figure** (fewer than 3 training positives, so the denominator is an artefact): `REAL-FM-7/2cov` (3/3 folds), `arcade-game/2cov` (3/3 folds), `fqa/2cov` (3/3 folds)

## Input provenance

| file | sha256 (first 16) | bytes |
|---|---|---:|
| `REAL-FM-4_rs_1n_cv_incremental.json` | `1c77a9250f17665e` | 156,334 |
| `REAL-FM-7_2cov_cv_incremental.json` | `9abcd23b8f69311e` | 113,583 |
| `REAL-FM-7_ff_cv_incremental.json` | `4ca75fa34f39778f` | 126,539 |
| `REAL-FM-7_rs_1n_cv_incremental.json` | `1b53f28d38af11e7` | 120,636 |
| `REAL-FM-7_rs_2n_cv_incremental.json` | `4148946944b0b5ac` | 126,982 |
| `REAL-FM-7_rs_3n_cv_incremental.json` | `dfe9242baba452ef` | 122,824 |
| `REAL-FM-7_rs_m_cv_incremental.json` | `feeb147f264f64cb` | 123,287 |
| `arcade-game_2cov_cv_incremental.json` | `70e72232e2af0a0b` | 199,354 |
| `arcade-game_ff_cv_incremental.json` | `543bcb97965f1f51` | 204,998 |
| `arcade-game_rs_1n_cv_incremental.json` | `357bb9702714fe05` | 228,044 |
| `arcade-game_rs_2n_cv_incremental.json` | `6fabf8be9a0786fd` | 255,465 |
| `arcade-game_rs_3n_cv_incremental.json` | `63987dbc1083ed6c` | 253,729 |
| `arcade-game_rs_m_cv_incremental.json` | `526eae7ee91f861e` | 213,023 |
| `fqa_2cov_cv_incremental.json` | `b4a7db4e6739b2d3` | 260,552 |
| `fqa_ff_cv_incremental.json` | `a901d3f755d0319a` | 240,749 |
| `fqa_rs_1n_cv_incremental.json` | `1c647929426225eb` | 243,207 |
| `fqa_rs_2n_cv_incremental.json` | `2e5ed5437d5a55f1` | 254,297 |
| `fqa_rs_3n_cv_incremental.json` | `ac13410dc79354d1` | 258,878 |
| `fqa_rs_m_cv_incremental.json` | `ca185dd71fcfeeb4` | 224,517 |

