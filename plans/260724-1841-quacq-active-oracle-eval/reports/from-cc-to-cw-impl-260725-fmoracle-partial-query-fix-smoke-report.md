# CC → CW Impl — FMOracle partial-query fix + REAL-FM-7 smoke (GATE input)

Fix approved after the whole-QuAcq conformance red-team. Read-only smoke on ONE KB; **no sweep run**
(Viet-Man's, post-gate). `PYTHONPATH=. pytest tests/ -q` green (**582p/1s**). Two commits landed.

## The semantics change (exact)
`conacq/oracle/fm/oracle.py` `is_valid(assignments)` now branches on complete vs partial:
- **COMPLETE** (`len(assignments) == len(name_to_id)`): unchanged — `is_consistent(task.set_c + config)`.
  For a full config, extension-SAT ≡ solution-check, so this is byte-identical for every
  complete-config caller.
- **PARTIAL** (only FindScope): `return not _partial_violates_fully_assigned_clause(assignments)` —
  the paper rule (Bessiere et al., IJCAI 2013): negative iff some FM CNF clause whose variables are
  ALL assigned is violated (all literals false); clauses with any unassigned variable are untestable.
  New helper iterates `self._fm_clauses` (verified aux/Tseitin-free) via `id_to_name`.

Also (H-2, committed with the eval arc): `_eval_quacq_fold` now passes `shuffle_seed=meta['fold']`
so example-only QuAcq is reproducible (was `shuffle_seed=None`).

## Caller audit (the hard guardrail)
Grepped every `.is_valid(` caller. **The ONLY caller passing PARTIAL assignments is
`conacq/algorithms/quacq/findscope.py:64`** (QuAcq FindScope). All others pass COMPLETE configs —
verified empirically: pool `example.assignments` are 14/14 (REAL-FM-7) & 179/179 (fqa);
`generate_from_sat` and `DiscriminatingGenerator` configs are complete; `random_sampling`,
`feature_frequency`, `base` (example labeler), the main-loop query (`quacq.py:211`), `findc.py:129`,
and tests all pass full configs. **No non-QuAcq caller passes partials** → guardrail satisfied.

## Byte-identical complete-config test
`tests/test_fmoracle_partial_query.py::test_complete_config_isvalid_byte_identical_to_solution_check`
(REAL-FM-7 + fqa): explicit valid config (SAT-derived) + explicit invalid (all-deselected) + **200
random complete configs each** → `is_valid == independent solution check`, **0 mismatches**. Complete
path proven unchanged.

## REAL-FM-7 before → after (example mode, all 6 example-sets × folds)
| metric | before | after |
|---|---|---|
| FindScope scope sizes handed to FindC | size-1 (unmatchable) | **all size-2** |
| FindC "no candidates with scope" | 100% of drops | **0** (every scope now matches ≥1 binary candidate) |
| FindC drop-rate | 56.5% (13/23) | **43.5%** (10/23) |
| constraints learned | 10 | **13** |
| eval QuAcq semantic-F1 (mean, 18 folds) | 0.0653 | **0.0786** |
| eval QuAcq |KB| (mean / max) | 0.56 / 2 | **0.72 / 2** |

## Scope / bias observation + binary-vs-n-ary read
- The fix **resolves the under-localization + discard** (RC-1/RC-3): FindScope now emits size-2
  scopes and FindC finds candidates for **all** of them (0 "no candidates"). The residual 43.5% shifts
  to a *different, benign* cause — candidates found but they don't reject `e`.
- **REAL-FM-7 FM clause arity: `{1:1, 2:19, 3:2}`** — 1 root (unary) + 19 binary + **2 ternary**. The
  bias is binary-only. So the negatives whose violation is a ternary/structural (root) constraint are
  **genuinely un-acquirable** by a binary-bias QuAcq — that is the residual, a real limitation, not a
  bug. (REAL-FM-7 is the smallest / least-affected KB; the 100%-drop KBs fqa/arcade/REAL-FM-4 had
  size-1 scopes and should benefit more — to be measured in the sweep, not claimed here.)

## Golden re-baseline (transparency)
The oracle fix changes QuAcq's oracle-mode query trajectory, so `test_t11_e2e_learned_kb::
test_quacq_learned_kb_identical` (T11 safety net) went stale — its golden literally encoded the buggy
empty-KB trajectory. Re-baselined via `scripts/build_t11_oracle_net_fixtures.py` (the script's
sanctioned "deliberate re-baseline"). **Diff-guarded: only `layer3.quacq` changed; `layer2`
(prepared-task ids), `congen_ff`, `congen_rs` are byte-identical** → ConGen guardrail holds. (Oracle
mode still shows `n_kb=0` at `max_queries=15` due to the liveness spin, which is out of scope by
instruction; the reportable baseline is example mode.)

## Commits (on feat/conmin)
1. **`de9e2a7`** `feat(conmin): QuAcq-active oracle-mode eval condition + eval robustness fixes` — the
   prior uncommitted arc (QuAcq-active feature + timeout rail + `--merge` blank-fill fix + aggregate
   non-converged handling + H-2 + their tests). NOTE: this was the whole uncommitted lump, not only the
   merge fix — they were developed together in the same files, so committing separately would require
   hunk-splitting intertwined edits.
2. **`cb28412`** `fix(oracle): paper-faithful partial-query semantics in FMOracle.is_valid` — this fix
   + golden re-baseline + `test_fmoracle_partial_query.py`.
No CSVs / `/tmp` / scratch committed; the busybox sweep JSONs and `plans/` stay untracked as before.

## Gate recommendation (CW Impl decides — I did NOT run the sweep)
The fix is **correct and necessary** (paper-faithful, complete-config byte-identical, mechanism defect
resolved). But on REAL-FM-7 the sem-F1 uplift is **modest (0.065 → 0.079)** because a large residual is
**genuinely un-acquirable** (ternary/structural target constraints over a binary bias). This is the
"binary-target limitation" branch you flagged: QuAcq is now *faithful* but *recovers little* on these
FMs. Two honest options for CW Main:
- **Report** QuAcq as a faithful-but-weak baseline (the low F1 is a real property of binary-bias QuAcq
  on feature models, now with correct semantics), **or**
- **Drop** the QuAcq comparison as not-informative.
Either way, **the code fix should stay** (it's a correctness fix). Recommend measuring fqa/arcade/
REAL-FM-4 post-fix (they had 100% drop; likely bigger uplift) before the final report/drop decision.

## Unresolved questions
1. Is the target a binary constraint network? If yes, ternary/structural FM constraints are inherently
   un-acquirable → the residual is an expected limitation to document, not a bug.
2. Gate: is 0.079 (from 0.065) "materially non-empty faithful" enough to report, or drop QuAcq? Needs
   the mid/large-KB post-fix numbers (the sweep) to decide — CW Impl call.
3. Oracle-mode liveness spin + phantom tests remain (out of scope by instruction) — QuAcq-active stays
   NO-GO; only example-mode is the reportable baseline.
