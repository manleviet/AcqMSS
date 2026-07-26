# make_tables.py — build complete (report to CW Impl)

**2026-07-26 · branch feat/conmin · plan `plans/260726-1341-make-tables-generator/` (4/4).** Additive only; no learner/runner change; nothing written to `data/results_conmin/*.json` or `Overleaf/`.

## Status
- **All 4 phases done.** `apps/make_tables/` package: `loader` + per-KB gates → `filters`/`aggregate`/`tiers`/`formatting` → `render` + `tables` (11 tables) → `selfcheck` + `tests`.
- **Self-check: 20 anchors PASS / 0 fail / 0 skip** (numeric, tol 5e-3, pre-round floats). `tests/test_make_tables.py` = **15 pass**; full suite **606 pass / 1 skip** (make_tables changes isolated).
- **Compile-check: pdflatex exit 0** on 9 tables vs the real vault preamble (`Overleaf/AAAI/main_short.tex`: `\KB` L69, `\supp` L76) — no undefined-macro, **0 unresolved `\ref`**, 4-page PDF.

## CW-Main layout applied (4 changes)
1. **Main = `eval-prf`** (Semantic tier, 4 strategies A/C/C∪S/QuAcq-active, {P,R,F1}+$|\KB|$ = **exactly 16 numeric cols, NO accuracy**). Appendix tier mirrors renamed **`app-prf-desc` / `app-prf-clause`** (same 4 strategies, same exclude-2COV + `†` + budget convention).
2. Main caption **points to the 5th condition**: QuAcq (example-only) → `app-perset`; accuracy/specificity → `app-accuracy`.
3. **bold = per-row max, computed** (verified: `app-prf-desc` arcade bolds `\textbf{$0.49^{\dagger}$}` = QuAcq-active, NOT ConMin 0.41; `eval-prf` KB2 bolds A 0.87). **No ratio/× column.**
4. Dropped the wide banded/5-strat variants (20-col overflow).

## Anchors pinned (final) / pending
- **Final (abort-level)**: Stage-1 A/C/C∪S sem-F1 all 4 KB; QuAcq example-only sem-F1 RE7/fqa/arcade; QuAcq-active RE7 (sem 0.842, desc 0.240, |KB| 12, 272 q), fqa (sem 0.062, desc 0.056, †max_queries), arcade (sem 0.452, desc 0.495, †max_queries); C∪S desc-headline RE7 0.682.
- **PENDING (TODO gate, NOT pinned)**: QuAcq-active REAL-FM-4 + busybox — finalize after tonight's re-run (`--quacq-active-timeout 7200` → deterministic max_queries). `selfcheck.PENDING_QUACQ_ACTIVE`.
- **budget/|B|** (= `qa_max_queries/n_bias`, computed): RE7 16.9× · fqa 10.9× · arcade 2.8× · RE4 2.4× · busybox 0.75× (below |B| — caption flags it).
- Measured text sentence OK: "REAL-FM-7 convergence = 272 oracle queries; ConMin none." Forbidden: any ~9–10k arcade extrapolation.

## Outputs
11 `.tex`+`.md`: `eval-prf` (main) · `app-prf-desc` `app-prf-clause` · `eval-cost` (budget/|B|) · `app-quacq-diag` (all-6 fairness, all-folds counters) · `app-perset` `app-accuracy` `app-confusion` `app-checks` `app-ksweep` `app-rawred` · `exact-equiv.md` · `PROVENANCE.md`. Default `--tables-dir /tmp/...` (throwaway); `--official` → `data/results_conmin/tables/`.

## Usage
```
# smoke (throwaway):  python -m apps.make_tables
# official (after sweep + --merge):  python -m apps.make_tables --official
# copy into paper (MANUAL, at push time — generator NEVER writes Overleaf/):
cp data/results_conmin/tables/*.tex Overleaf/AAAI/tables/   # then ./sync.sh AAAI push
```

## Unresolved (need CW attention)
1. **exact_equiv is NOT an anomaly** (CW-Impl clarified 2026-07-26; caveat removed): `exact_equiv` = logical equivalence of the *delivered theory* (slice ∪ ¬e⁻ fallbacks ∪ BG/root) via `SemanticEquivalenceChecker`; `sem_*` = name-set P/R/F1 only (BG excluded, root dropped) — two different objects **by design** (`conmin_slice_scorer.py:54-72`). QuAcq-active exact_equiv=1 with sem-F1 0.842 is consistent (cf. RE7 A/C∪S exact_equiv=1 at sem-F1 0.977). `exact-equiv.md` now carries a neutral note; QuAcq-active is learned once/KB → **one** observation, not 18. No action needed.
2. **Official run pending tonight's sweep**: RE4/busybox anchors + official tables regenerate after sweep + `--merge`; then CW Main's independent cell audit.
3. **Commit**: uncommitted (mid-sweep); commit `apps/make_tables/` + `tests/test_make_tables.py` + `plans/` scoped, EXCLUDING `data/results_conmin/*`.
