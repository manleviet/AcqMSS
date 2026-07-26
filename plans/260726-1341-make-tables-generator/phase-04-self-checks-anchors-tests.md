---
phase: 4
title: Self-checks + anchors + tests
status: completed
effort: ~2.5h
priority: P1
dependencies:
  - 1
  - 2
  - 3
---

# Phase 4: Self-checks, anchors, compile-check, tests, PROVENANCE, report

## Overview
Make the generator self-auditing (v1 §Self-checks + v2 G4), prove one table compiles, add unit tests, emit PROVENANCE, and report to CW Impl. This is what lets CW Main's independent audit pass.

## Self-checks (print to stdout, fail loudly)
**Comparison discipline (red-team #3):** compare **pre-round floats** with tolerance `abs(x-anchor) < 5e-3`, NOT rendered strings — anchors are quoted at 3dp (`0.727`) but cells render at 2dp (`0.73`). Normalize all anchors to one precision.

- **Row counts — per-table expected, and BLOCK not warn (red-team #6, #8).** With the *pinned* Phase-2 filter, the 5 headline strategies each yield **18** all-6 / **15** exclude-2COV. But the count differs by table: **app-ksweep spans k∈{1,2,3,5} → 60**; **app-rawred spans negatives{raw,reduced} → 30**. Assert each table's own expected count. A *loaded* KB/strategy **short** of expectation → **force that KB's cells to `--` (or abort)**, never emit a partial mean as final. Reserve `warn` for the intentionally-absent busybox. QuAcq-active std=0 duplication must NOT be flagged.
### Anchor table (CW-Impl verified 2026-07-26 on refreshed CSV — RULINGS RESOLVED)
All anchors are the **exclude-2COV CV mean** (the table cell), compared as pre-round floats, tol `5e-3`. **Trap to avoid:** never "fix an anchor to match output" — that turns the tripwire into decoration. If an anchor misses, the INPUT is wrong, not the anchor.

**✅ ABORT-level — pin NOW (deterministic; all verified through the modules 2026-07-26):**
- **Stage-1 A / C / C∪S, all 4 KB** (sweep's `--conditions quacq-active` does NOT touch it): C∪S sem-F1 `0.847 / 0.782 / 0.637 / 0.776`; A sem-F1 `0.605 / 0.867 / 0.380 / 0.642` (KB₁₋₄ = RE7/fqa/arcade/RE4).
- **QuAcq-active** (excl-2COV mean; `†` = non-converged `max_queries`; budget/|B| = `qa_max_queries/n_bias`):

  | KB | \|B\| | sem P/R/F1 | desc P/R/F1 | q | reason | drops | budget/\|B\| |
  |---|---|---|---|---|---|---|---|
  | RE7 | 295 | 1.000/0.727/0.842 | 0.250/0.231/0.240 | 272 | no_query (converged) | 10 | 16.9× |
  | fqa | 459 | 1.000/0.032/0.062 | 0.500/0.029/0.056 | 5000 | max_queries † | 354 | 10.9× |
  | arcade | 1755 | 1.000/0.292/0.452 | 0.889/0.343/0.495 | 5000 | max_queries † | 326 | 2.8× |

- **QuAcq example-only** (excl-2COV mean, `pool_exhausted`, deterministic): RE7 sem `0.133/0.006/0.012` desc `0.133/0.010/0.019`; fqa sem `0.800/0.011/0.021` desc `0.700/0.020/0.038`; arcade sem `0.933/0.011/0.022` desc `0.933/0.019/0.037`. (NOT `1.000/0.045/0.087` single-fold, NOT rs_1n alone.)
- **Measured text sentence (CW Main, ok to paper):** "reaching convergence on REAL-FM-7 needs **272** oracle queries; ConMin needs **none**." **FORBIDDEN in the paper:** any "arcade could converge at ~9–10k" extrapolation — unmeasured, internal-only.

**⛔ DO NOT pin yet:**
- **QuAcq-active REAL-FM-4** — still `timeout`/679 q; re-run **tonight** with the 7200 timeout → then deterministic (`max_queries`), then pin.
- **QuAcq-active busybox** — runs **tonight** (`max_queries`=5000 expected). **It WILL have numbers** — do NOT hardcode `--` for busybox; the loader derives `--` from row-presence, so busybox fills in once `busybox-1.18.0_long.csv` lands.
- **DELETE ON SIGHT:** any 0.667-era QuAcq anchor / "A ≫ QuAcq" framing. If reproduced from a Stage-1/QuAcq-active anchor → input stale → abort; do NOT "fix" the anchor. (Never let a passive-QuAcq CV-mean miss trigger a false STALE abort — that is red-team #1's failure mode.)
- **app-rawred:** assert F1/accuracy/`$|\KB|$` equal raw-vs-reduced (0 mismatches verified); do NOT assert reduced `preprocessing_checks`>0 (it's 0.0 too — #8).
- Gates from Phase 1 (per-KB STALE, empty-scope) run before all of this.

## Compile-check (v3 §8) — corrected (red-team #11)
`main_short.tex` (with the `\KB`,`\supp`,… macro defs) is **NOT in the repo** — it lives ONLY in the vault: `…/Cowork/AcqMSS/Overleaf/AAAI/main_short.tex` (repo `paper/` is a separate untracked copy). `pdflatex` **is** installed (`/Library/TeX/texbin/pdflatex`) — the "may be absent" hedge was wrong. So:
- Throwaway `/tmp/*.tex` loads ONLY v3 §2 packages (`booktabs, multirow, array, caption, graphicx` + `\newcolumntype{x}`) **plus the vault `main_short.tex` preamble/macros** (read-only; do NOT edit anything under `Overleaf/`); `\input` ≥1 generated table; compile with `pdflatex`.
- **Assert the vault preamble exists** before claiming a compile-check. If the macros are unavailable, **FAIL the criterion** (a generated `.tex` uses `\KB`/`\supp` → `Undefined control sequence`) — do NOT silently downgrade to a structural lint and call it "compiles clean". Report: compiled, no `??`, no undefined-macro / missing-package.

## Tests
`tests/test_make_tables.py` — unit tests on Phase-2 pure functions using a **tiny synthetic `_long.csv` fixture** (few folds × conditions × samplings, incl. a `timeout` row + a `n/a` row):
- filter selects the right (condition,negatives,k) subset;
- cv_mean = equal-fold nan-skipping mean; convergence grouping never blends;
- all-non-converged → value+flag (→`†`); QuAcq-active std=0 not flagged;
- rounding (trailing zeros, `--`, `{,}`);
- STALE + empty-scope gates fire on crafted stale/nonzero fixtures.
Run `PYTHONPATH=. pytest tests/test_make_tables.py -q` then full suite green. Register any new pytest marker if used.

## PROVENANCE.md
`tables/PROVENANCE.md`: per table → filter + row counts + source files (+ mtimes + git SHA from Phase 1); the `\input` convention (complete float); which cells are `--`/`†`.

## Smoke run (concurrency-safe) + report
- Run on CURRENT data into **`/tmp/tables_smoke`** (never `data/results_conmin/tables/` while the sweep writes; default `--tables-dir` is already throwaway). `--` derived from missing rows only (REAL-FM-4 is ~complete now, NOT hardcoded partial — #12; busybox has no `_long.csv` → `--`).
- **Headline desc — RULING RESOLVED (ruling b):** the paper cites **0.682 (exclude-2COV mean)**, NOT 0.699 (rs_1n). General principle to enforce everywhere: **every quoted number uses the SAME aggregation as the table it points at.** Pin C∪S desc-F1 excl-2COV REAL-FM-7 = **0.682** as an abort-level anchor; record in PROVENANCE. (0.699/rs_1n and the single-fold values are illustrative only — never the citation.)
- Report to CW Impl: anchors pass (KEEP+QuAcq-active abort-level; passive-QuAcq/desc-headline warn-level), row counts, `tables/` file list + PROVENANCE, `--`/`†` cells, compile-check result, suite status, commit SHA. **Official** tables regenerate after the full sweep + `--merge`; passive-QuAcq CV-mean anchor re-captured then.

## Related Code Files
- Create: `apps/make_tables/selfcheck.py`, `tests/test_make_tables.py`, `tables/PROVENANCE.md` (generated)
- Read-only: `Overleaf/AAAI/main_short.tex` (macros), v2 G4 anchors

## Success Criteria
- [ ] Anchor compare uses pre-round floats + `5e-3` tol. KEEP (Stage-1) + QuAcq-active anchors abort-level and pass; passive-QuAcq/desc-headline are warn-level (never false-abort fresh data).
- [ ] Per-table row counts (18/15 pinned, app-ksweep 60, app-rawred 30); short loaded KB → `--`/abort, not a partial mean; QuAcq-active std=0 not flagged.
- [ ] Convergence partition = `aggregate_cv` `{timeout,max_queries}`; `†` only on those; budget read from row.
- [ ] ≥1 table compiles in /tmp against the **vault** preamble (no `??`/undefined-macro); criterion FAILS (not lint-downgrades) if preamble absent.
- [ ] `test_make_tables.py` + full suite green; A/C/C∪S/ConMin byte-identical (no learner touched).
- [ ] PROVENANCE emitted (real header length); report to CW Impl incl. the 2 CW-Main-ruling items (#1 anchor, #4 desc headline) + commit SHA.

## Risk Assessment
- Risk: passive-QuAcq anchor false-aborts fresh data (red-team #1). Mitigation: passive-QuAcq/desc anchors warn-level + re-captured from merged CSV; only Stage-1 + QuAcq-active (std=0) anchors abort. This is the single highest-impact fix.
- Risk: convergence mis-classification daggers the flagship cell (red-team #2). Mitigation: partition sourced from `aggregate_cv` code, unit-tested with a `timeout`+`no_query`+`pool_exhausted` fixture.
- Risk: LaTeX preamble only in vault; pdflatex present. Mitigation: point compile-check at the vault preamble; FAIL (not lint) if absent — flag to CW Impl.
- Risk: numbers in flux during the live sweep. Mitigation: build+unit-test now against synthetic fixtures + stable Stage-1 anchors; official tables + metric-anchor capture gated on sweep+`--merge`.
