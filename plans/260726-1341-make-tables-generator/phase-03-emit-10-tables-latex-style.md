---
phase: 3
title: Emit 10 tables + LaTeX style
status: completed
effort: ~3.5h
priority: P1
dependencies:
  - 1
  - 2
---

# Phase 3: Emit the 10 tables (.md + .tex) in the paper's LaTeX house style

## Overview
Wire the Phase-2 core into the 10 table definitions; render each as `.md` (reading) and `.tex` (complete float, `\input`-ready) into `--tables-dir`. Filename = `\label` sans `tab:` (e.g. `eval-prf.tex`).

## Content constraints (CW-Impl 2026-07-26 — the "2.8×" claim was WITHDRAWN)
The narrative is **per-KB, no universal multiplier** — on arcade-game QuAcq-active *wins* desc (0.495 vs C∪S 0.405), while ConMin wins elsewhere. Therefore:
- **Best-value bolding (if any): COMPUTE the per-row max** over the compared cells — **never hardcode ConMin as the winning column.** A daggered (non-converged) cell still participates in its row's value but keep its `†`.
- **Emit NO ratio / "×" column or row** comparing ConMin vs QuAcq.
- **Per-KB readable** (v2): never average across KBs; never blend converged with non-converged (Phase-2 `cv_mean` already enforces the latter).

## Tables (v1 §"Tables to emit" + v2 G3). Exclude-2COV unless noted "all-6".
| # | label | scope | columns |
|---|---|---|---|
| 1 | `eval-prf` | main; KB×tier(Desc,Clause,Sem) × strategy super-cols | P/R/F1/`$|\KB|$` per strategy. Also emit `eval-prf-{sem,desc,clause}` split files + optional `eval-prf-core` (A/C/C∪S/QuAcq-active) — Open Q2 |
| 2 | `exact-equiv.md` | reference (md only) | per KB×strategy `exact_equiv` (one-sentence source; ≈ sem-F1=1, non-zero only KB₁/RS-3n=0.33) |
| 3 | `eval-cost` | appendix | ConMin(raw,k=1): `$|A||C||S||U|$`+checks+t(s); QuAcq & QuAcq-active: t(s)+queries+**budget/`$|B|$`** (= `qa_max_queries/n_bias`, COMPUTED not hardcoded — RE7 16.9×, fqa 10.9×, arcade 2.8×, RE4 2.4×, busybox 0.75×; preempts "QuAcq under-budgeted"). Caption must flag busybox is **below** `$|B|$` (0.75×) |
| 4 | `app-confusion` | appendix, **all-6** | per KB×sampling×strategy: `tp/tn/fp/fn` (fold mean) |
| 5 | `app-perset` | appendix, **all-6** | per KB×sampling: sem-F1 + `$|\KB|$` per strategy |
| 6 | `app-ksweep` | appendix | ConMin(raw) per KB×k∈{1,2,3,5}: `$|S||\KB|$` F1 prec rec acc |
| 7 | `app-rawred` | appendix | ConMin(k=1) raw vs reduced: F1, acc, `$|\KB|$` (must agree), `preprocessing_checks`. **NB (red-team #8):** on REAL-FM-7 reduced `preprocessing_checks`=**0.0**, not N — do NOT assert "reduced>0"; assert only raw==reduced equality of F1/acc/`$|\KB|$` |
| 8 | `app-checks` | appendix | ConMin(raw,k=1) per KB: `checks_{gate,admpool,cover_rej,cover_qx,redundancy,total}` |
| 9 | `app-accuracy` | appendix | per KB×strategy: accuracy + specificity |
| 10 | `app-quacq-diag` | appendix (v2 G3, fairness), **all-6** (red-team #9 — a disclosure table must NOT drop 2cov) | per KB×{QuAcq,QuAcq-active}, fold-mean: `quacq_bandaid_drops`,`quacq_findc_unconfirmed`,`quacq_empty_scope_appends`,`quacq_prune_partial_pruned`,`quacq_prune_complete_pruned`,`oracle_queries`,`convergence_reason`,`qa_max_queries`,`qa_timeout_s`,`n_bias`,**budget/`$|B|$`** (computed) |
`eval-fms` (KB list w/ #features/domain) is **author-maintained — do NOT generate** (may emit `n_bias` for cross-check only).

## LaTeX house style (v3 — non-negotiable)
- Skeleton: `\begin{table}[t]\centering\small` … `\begin{tabular}{lcc…}\toprule` … rows end `\tabularnewline` … `\bottomrule\end{tabular}\caption{…}\label{tab:…}\end{table}`. Full-width → `table*`.
- **booktabs only** (`\toprule/\midrule/\bottomrule`); **no** `\hline`/vertical rules. Row terminator `\tabularnewline` (not `\\`). Caption AFTER `tabular`, then `\label`.
- Super-cols: `\multicolumn{4}{c}{\textsc{ConMin}}` + `\cmidrule(lr){2-5}`. Tier bands: `\multirow` KB label + `\midrule` between KB blocks; tier order Desc,Clause,Sem.
- `\setlength{\tabcolsep}{4pt}` ONLY when wide; overflow → `table*` → `\tabcolsep` → split; **never** `\resizebox`.
- Non-converged (`convergence_reason ∈ {timeout, max_queries}` ONLY — red-team #2; `pool_exhausted`/`no_query` are NOT daggered): `$0.03^{\dagger}$`; legend in `\caption`: `$^{\dagger}$ did not converge (\texttt{max\_queries}=5000, ${\approx}11\times|B|$)`. **Read the budget (`qa_max_queries`/`qa_timeout_s`) and the `${\approx}n\times|B|$` multiple from the row** — do NOT hardcode 5000 (passive QuAcq has blank budget). Budget as ×|B| deliberate.
- Numbers: fixed decimals w/ trailing zeros; `--` en-dash; thousands `{,}` inside math (`$7{,}534$`).
- **Reuse macros** (`\KB`,`\BG`,`\NE`,`\CS`,`\supp`,`\dom`,`\var`,`\cand`,`\cons`,`\incons`) — header is `$|\KB|$`, support is `\supp`, NOT `$|KB|$`/`support+`. Names in `\textsc{}`. NEVER emit highlight macros `\pp{}`/`\ppn{}`/`\vtwo{}`/`\shrt{}`.
- No new packages / `threeparttable` / `siunitx`. Each table = complete float.
- Caption states exclude-2COV where applied.
- **`\input` path (red-team #11):** the paper `\input`s from `paper/tables/` (repo `paper/` is untracked); the generator writes to `data/results_conmin/tables/`. Resolve before shipping: emit relative to the paper's include root, OR add a documented copy step (`data/results_conmin/tables/*.tex → paper/tables/`) recorded in PROVENANCE. Confirm the paper's actual include root with CW Impl.

## Related Code Files
- Created: `apps/make_tables/render.py` (Grid model + booktabs-LaTeX float + Markdown — latex+markdown combined), `tables.py` (10 builders + exact_equiv_md), `formatting.py` (+Cell/make_cell/bold_winners), `__main__.py` (emission wired).
- Read-only: v1 §Tables, v3 §1–6, `n_bias` for the `†` budget ×|B| computation

## DONE (2026-07-26) + flags for CW
- 12 Grids (eval-prf + 3 tier splits + eval-cost + app-quacq-diag + app-perset/accuracy/confusion/checks/ksweep/rawred) + `exact-equiv.md` emitted `.tex`+`.md`. Anchors reproduce; **pdflatex compile of 5 tables vs the real vault preamble = exit 0** (1 Overfull hbox = the wide 22-col `eval-prf`, layout-only). Suite 591✓. Code-reviewed (no Crit/High; fixed M1 caption-honesty under `--no-exclude-2cov`, M2 app-quacq-diag all-folds aggregation + reason-distribution).
- **Flags for CW Impl:** (1) which `eval-prf` layout the paper `\input`s — full 22-col banded vs the tier splits vs `eval-prf-core` (Open Q2); the banded one overflows even `table*`. (2) `exact-equiv.md` shows the **pooled** exact-equiv mean (RE7 ConMin 0.07), NOT the per-sampling RS-3n 0.33 (that 0.33 is a per-fold text sentence, not a table cell). (3) `\input` path (red-team #11) still owed: generator writes `data/results_conmin/tables/`, paper includes from `paper/tables/` — copy-step vs relative path, confirm include root.

## Implementation Steps
1. `latex.py`: helpers for float wrapper, super-col header + `\cmidrule`, `\multirow` bands, `†` marker + caption legend, macro-aware headers, `{,}` thousands.
2. `markdown.py`: plain pipe tables (same cells, no LaTeX).
3. `tables.py`: one function per table = (filter spec + column list + exclude/all-6 + caption) → calls Phase-2 core → both renderers.
4. Emit every `<label>.tex` + `<label>.md` + `exact-equiv.md` to `--tables-dir`.
5. Two-QuAcq-columns: example-only now, QuAcq-active fills where rows exist, else `--`.

## Success Criteria
- [ ] All 10 tables (+ `eval-prf` splits + `exact-equiv.md`) emitted as `.tex`+`.md`.
- [ ] `.tex` matches v3 exactly (booktabs, `\tabularnewline`, `\small`, `\cmidrule(lr)`, `\multirow`, macros, `$x^{\dagger}$`); no `\hline`/`\resizebox`/new packages/highlight macros.
- [ ] exclude-2COV applied per spec; per-sampling tables keep all 6; busybox `--`.
- [ ] Each table a complete float; filename = label sans `tab:`.

## Risk Assessment
- Risk: `eval-prf` (5 groups × tiers) overflows column width. Mitigation: emit `eval-prf-core` + per-tier splits; `table*`+`\tabcolsep` before splitting; never `\resizebox`.
- Risk: wrong macro name (`\supp` vs `\support`). Mitigation: grep the paper's macro defs (Phase 4 compile-check catches undefined ones).
