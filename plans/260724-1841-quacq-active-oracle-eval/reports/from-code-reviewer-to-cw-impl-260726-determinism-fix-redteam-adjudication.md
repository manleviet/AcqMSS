# Code Red-Team Adjudication — QuAcq determinism fix (3654c2b, FindScope `sorted(R)`)

2 hostile reviewers + controller verification. Read-only; all runs to /tmp; suite green (591p/1s under
PYTHONHASHSEED 0/1/2). RUN.md scoping committed in **4627377**.

## Verdict
The fix is **correct and complete for its goal** (hash-seed independence) — confirmed by R1 on all 4
KBs and by controller in-tree revert test. **R2's two High findings ("phantom test", "no-op") are
REJECTED** as a methodology error. Valid residual concerns are about the stabilized *values* being
solver/order-conditional — corrected in RUN.md.

## The R2 contradiction — resolved definitively (REJECT R2-F1, R2-F2)
R2 claimed the fix is a no-op (parent already deterministic, KB=10/342 across 18 seeds) and the test is
phantom. **Disproved by controller in-tree revert** (the clean way — no worktree):
- Reverted `findscope.py:62` to the unsorted `for k in R`, ran REAL-FM-7 oracle in separate processes:
  **seed 0→KB10/353, seed 1→KB10/341, seed 4→KB9/690, seed 5→KB9/608, unset→{342,341,355}** — the
  parent VARIES.
- Ran the actual determinism test against the unsorted code → **FAILED** (AssertionError, seeds
  disagree). So the test **catches the bug** — not phantom.
- Restored `sorted(R)`; fixed tree → all seeds identical (KB10/342), test passes.
**Root of R2's error:** its "parent worktree" was contaminated by the repo's editable install — `import
conacq` resolved to the *fixed* main tree, so every "parent" run returned the sorted value `342`,
making the parent look deterministic. R2's A/C/C∪S byte-identity confirmation (Finding 4) still stands
(static: FindScope unused by ConMin/ConGen; A/B was 0-content-diff regardless of which tree loaded).
**Lesson to pass to reviewers:** verify worktree isolation under editable installs (or test in-tree via
a revert), and always `-o /tmp`.

## R1 confirms + valid nuances (Accept)
| # | Finding | Sev | Disposition |
|---|---------|-----|-------------|
| R1-refute | Attack "second hash-order source survives" REFUTED — all 4 KBs seed-stable; `sorted(R)` is the sole set-derived config feeding the solver | — | Fix CONFIRMED complete |
| R1-F1 | "Deterministic" is **solver-conditional**: glucose4/cadical → KB=10, minisat → KB=9 (different F1). Committed numbers are glucose4 (eval default) | High | **Fixed** RUN.md (scope to solver) |
| R1-F2 | Canonical order is arbitrary: `n_queries` is an alphabetical artifact (342 sorted vs 353 reverse/var-id). KB reorder-invariant on REAL-FM-7 (F1 stable there); **unverified on fqa/REAL-FM-4** | Med-High | **Fixed** RUN.md (n_queries order-conditional); KB-reorder-invariance on big KBs → report as gate item |
| R1-F3 | Call-site band-aid: the invariant "no set-derived config reaches the encoder unsorted" is enforced nowhere. Robust fix = canonicalize in `config_to_assignment_assumptions` (encoder boundary, external) | Med | Report → recommend boundary canonicalization for robustness (external file; current fix verified complete) |
| R1-F4 | arcade-game oracle learns KB=0 (spins on the multi-violation debt) | Low | Pre-existing #2 debt, out of scope |

## Per-KB cross-seed determinism (oracle, glucose4, seeds {0,1,7}) — R1 + controller
| KB | KB / n_queries / conv | seed-stable |
|---|---|---|
| REAL-FM-7 | 10 / 342 / no_query | YES |
| fqa | 14 / 2000 / max_queries | YES |
| arcade-game | 0 / 300 / max_queries | YES (empty KB — #2 debt) |
| REAL-FM-4 | 12 / 300 / max_queries | YES |

## Mechanism (why one line fixed it)
`partial`'s key order (from iterating the set `R`) became the SAT assumption order; the **persistent
incremental solver** carries phase/activity state from `is_consistent` into the next `find_model`
witness → different query → different learning. `is_consistent` verdicts are order-independent (so
`prune_rejecting` is unaffected), but the witness leaks through solver state. Every other assumption
list (`learned_kb`, `list(set_b)`, `dict.fromkeys(set_c)`, `model_to_config` in var-id order) is
already ordered → `partial` was the sole source.

## Gate recommendation (CW Impl / CW Main)
The fix achieves the goal (hash-seed determinism, verified 4 KBs). Before publishing QuAcq numbers:
1. **Pin the solver of record** (glucose4) explicitly in the eval config, and report QuAcq numbers with
   the solver stated — they are not solver-portable (minisat KB=9 vs glucose4 KB=10).
2. **Verify KB-reorder-invariance on fqa/REAL-FM-4** before trusting per-KB F1 (on REAL-FM-7 only
   `n_queries` moved with order, KB/F1 were invariant; unverified on larger KBs).
3. (Robustness) canonicalize at the encoder boundary (`config_to_assignment_assumptions`) so future
   set-derived configs can't re-break determinism — separate task (external `explanation` pkg).

## Unresolved questions
1. Is glucose4 the intended fixed solver for the paper's numbers? (pin it in config)
2. Is the learned KB (hence F1) reorder-invariant on fqa/REAL-FM-4, or is F1 an alphabetical artifact on
   some KB? (needs a reorder sweep on the large KBs)
3. `n_queries` is canonical-order-dependent (342 vs 353) — publish it as a headline efficiency metric or
   caveat it?
