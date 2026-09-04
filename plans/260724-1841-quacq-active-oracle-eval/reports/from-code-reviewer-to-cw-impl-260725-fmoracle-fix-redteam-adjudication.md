# Code Red-Team Adjudication — FMOracle partial-query fix (cb28412 + H-2 in de9e2a7)

2 hostile reviewers (partial-query correctness; regression/guardrail/golden/perf) + controller
5-KB verification. Read-only; **no source touched**; `pytest -q` green (582p/1s).

## Verdict: the fix is CORRECT and SAFE — keep it.
Both reviewers independently reimplemented the IJCAI-2013 partial rule and confirmed the
implementation matches it. Every correctness/regression/golden attack is **refuted with evidence**.
No fix-blocking finding. Residual = one subtle-but-benign side effect + coverage/data hardening.

## Refuted attacks (independently verified — recorded so they aren't re-litigated)
- **Golden legitimacy:** new `layer3.quacq` == independent paper-rule reference **15/15**; only the 4
  extension-SAT over-rejection entries changed; `layer2` + both ConGen arms byte-identical. Not a
  blessed bug.
- **Complete-path byte-identity:** 0 mismatches on all 5 KBs (300 random + 40 SAT-valid each);
  `_fm_clauses ≡ task.set_c` (0/500); **aux/Tseitin-free on all 5 KBs**; boundary sound by pigeonhole.
- **Literal convention / units / dups / root:** correct (`+id⇒selected`; `is_valid({root:F})=False`,
  `{root:T}/{}=True`).
- **FindScope scope quality:** localizes the REAL violated FM clause (traced on 4 negatives), not
  coincidental; **monotonicity invariant 0/11,404**.
- **A/C/C∪S/ConMin isolation:** H-2 `shuffle_seed=meta['fold']` reaches only `_eval_quacq_fold`;
  QuAcq-active (`mode='automated'`) ignores it; ConMin path separate. CachedOracle unused in eval.
- **No accuracy regression (controller):** REAL-FM-7 QuAcq before→after — sem-F1 0.065→**0.079**,
  recall 0.035→**0.043** (UP), accuracy 0.884→0.902, precision 0.500→0.556. All axes improve.

## Findings (all Accept-as-documented; none fix-blocking)

| # | Finding | Sev | Disposition |
|---|---------|-----|-------------|
| RT-1 | FindScope now prunes FM-entailed bias candidates on extension-unsat *positive* partials | Med | Accept — benign on 5 KBs, document + add prune-safety test |
| RT-2 | QuAcq/QuAcq-active learned behavior has no regression net (T11 golden pins an empty-KB trajectory only) | Med | Accept — add a non-empty-KB golden or document trajectory-only |
| RT-3 | Committed `data/results_conmin/*_eval.json` QuAcq columns stale (seed=None + old semantics) | Med | Accept — regenerate before any paper cite (RUN.md already flags) |
| RT-4 | The 2 new oracle tests are near-tautological (reference reimplements the rule; parity rarely hits valid configs; violating partial built from the rule's own sign convention) | Low | Accept — strengthen with independent pysat + SAT-derived valid configs |
| RT-5 | Partial path is O(all clauses)/query, ~2× slower on busybox (322µs vs 158µs; sub-ms) | Low | Accept — not material; optional var-indexed clause lookup |
| RT-6 | No empty-clause guard in the satisfaction check | Low | Accept — 0 empty clauses on all 5 KBs; note the assumption |
| RT-7 | "size-1→size-2" over-generalizes (root-off → size-1, n-ary group → size≥3, both unmatchable) | Info | Accept — wording; the residual is the binary-bias limitation |

### RT-1 detail (the one substantive finding)
Pre-fix, an extension-unsat partial got `is_valid=False` → FindScope returned `[]` (no prune).
Post-fix it is correctly paper-positive (`True`) → FindScope's positive branch runs `prune_rejecting`,
which removes bias candidates the partial violates — **including FM-entailed ones** (evidence:
REAL-FM-7 rs_3n pruned `gui_builder→interface`, `compiler→interface`, `diagram_builder→interface`,
`jplug→interface`, `jplug↔interface`). **Benign on all 5 eval KBs:** every pruned entailed constraint
is *trivially redundant* (routed through the mandatory-always-true `interface`), so `sol(C_L)` is
unchanged and recall did not drop (controller data above). **Unsound in principle:** on an FM whose
implied binary constraint is solution-restricting and not reconstructible from the surviving bias,
this would strip a non-redundant target → false-accepts. Arguably paper-faithful (a positive example
should prune violated bias candidates that aren't FM-entailed at the queried scope), but the eval must
define whether "target" = FM direct clauses or FM logical closure (Unresolved #1).

## Recommended low-risk follow-up (touches committed code → your call, CW Impl)
1. **Strengthen the 2 oracle tests** (RT-4): reference the complete path against an independent
   `pysat` solve (no fallback); seed the parity test with SAT-derived valid configs; add a
   convention-independent partial-violation case.
2. **Add a prune-safety test** (RT-1): after example-mode QuAcq on ≥1 KB, assert no *non-redundant*
   FM-entailed constraint is pruned (i.e. `sol(learned)` not reduced by the extra pruning).
3. (Optional) empty-clause guard (RT-6): one-line defensive skip.
Deferred/not-mine: RT-3 (regenerate committed JSONs = Viet-Man's sweep), RT-2 non-empty golden (no KB
learns non-empty in oracle mode; example mode learns 1–2 — could be pinned), RT-5 perf (immaterial).

## Unresolved questions
1. Ground truth for scoring/target: `sol(FM)` (semantic) or the set of FM-entailed binary bias
   constraints? Under the latter, RT-1's pruning of entailed constraints is a direct recall loss even
   when redundant. (Determines whether RT-1 is benign or a real regression.)
2. Is there an eval KB where a binary FM-entailed bias constraint is non-redundant (implied only via an
   n-ary group / unlearnable path)? Neither reviewer could construct one from the 5 shipped KBs; if one
   exists, RT-1 escalates to a proven precision/recall regression.
3. The re-recorded T11 golden now locks in the new FindScope pruning as an oracle — accepted here
   because it matches the independent paper-rule reference and ConGen/layer2 are byte-identical.
