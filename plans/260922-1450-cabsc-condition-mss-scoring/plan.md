# Score the MSS (B′) as the CABSC condition

- Requested: Viet-Man, 2026-09-22, during the minimal-change review of `main-r1.tex`
- Branch: `feat/cabsc-condition-mss-scoring`, off `a1fd276` (the tree that carved v1.0.0 = `4dece76`)
- Status: **done**, both tasks measured on all 84 folds

## Why

Reviewer R3-Q4 asks why the passive methods named in the paper are not run as
baselines. The revision answers with an argued omission. CABSC does not need to be
excused: Proposition 1 proves its objective is met, under this bias, by the conjunction
of every bias constraint consistent with E⁺ — which the paper identifies with what
AcqMss returns. That set is B′, the MSS before Reduce, and it is already in the
committed data. Scoring it evaluates CABSC instead of excusing it.

## Tasks

1. Score B′ beside the delivered KB on all 84 folds, per knowledge base and strategy.
2. Decide the paper's identification claim (`A` = what AcqMss returns) on the data.

## Decisions taken here

- **Implemented in AcqMSS, not in the artifact.** The request named the artifact repo;
  the derivation runs AcqMSS → artifact and never the reverse (`release/README.md` §1),
  and the two trees carry identical `data/results_sosym_r1` and `conacq/`. The artifact
  picks this up at the next carve.
- **A is computed by evaluation, not by SAT.** Every example in this evaluation is a
  complete assignment (asserted in the script), so "c accepts e⁺" is arithmetic.
- **The equivalence question is measured, not inferred from a score.** See the report.

## Outcome

- Task 1: B′ recovers more (semantic recall 1.000 on 81 of 84 folds against the
  delivered KB's 67) and delivers 1.4× to 1,659× as many constraints, so its precision
  collapses. Median semantic F1 delta −0.221.
- Task 2: the identification holds on **all 73 folds that have a positive example** and
  fails on **exactly the 11 that have none**, where it is vacuous. The paper's sentence
  needs a scope, not a retraction.

Report: `reports/measurement-260922-1458-mss-as-cabsc-condition-report.md`
Data: `data/results_sosym_r1/cabsc_condition/cabsc_condition.json`
Code: `apps/sosym_r1/measure_mss_as_cabsc_condition.py`
