# N-item: the published semantic figures were scored against another model's target theory

Date 2026-08-29. Branch `feat/sosym-r1`.

**Claim.** In `tab:iterative_semantic`, the semantic F1 for KB₁ (REAL-FM-7) and KB₃
(Arcade) was computed against KB₂'s (FQA's) target theory rather than each model's own.
The error understates our own results, by up to **+0.83** on KB₁ and **+0.39** on KB₃.

This supersedes the earlier framing that the ground-truth extraction over-counted. It did
not: the extraction is correct on all five models, verified two independent ways below.

## The hand count, and the attempt to refute it

`tools/sosym_r1/count_target_clauses.py` counts each model's clauses from the `.uvl` using
the textbook FM→CNF encoding — root unit, mandatory 2, optional 1, or-group 1+n,
alternative group 1+n+n(n−1)/2, one clause per cross-tree line (verified: every constraint
line in these five models is a pure disjunction). It reads no result file.

| model | by hand | extractor | agree |
|---|---|---|---|
| REAL-FM-7 | 22 | 22 | yes |
| fqa | **342** | 342 | yes |
| arcade-game | **130** | 130 | yes |
| REAL-FM-4 | 428 | 428 | yes |
| busybox-1.18.0 | 994 | 994 | yes |

The first run of this counter disagreed with the extractor on **all five** models. The
defect was in the counter, not the extractor: a feature carrying two group blocks in
sequence (`optional` then `mandatory` under one parent) had the first block overwritten
before its children were counted. Recording that because the disagreement was the useful
event — had the counter been written to agree, it would have confirmed nothing.

busybox is the case that matters for this check: 8 alternative groups, whose pairwise
exclusions grow quadratically, and 994 clauses. It agrees exactly.

## What actually happened

`342` is FQA's clause count. **Every one of the 18 old ConGen files reports `tp+fn = 342`**,
whatever model it belongs to:

| directory | folds scored against the wrong model |
|---|---|
| `data/results/congen` | 12 of 18 files (all 18 used FQA's Cτ) |
| `data/results/interactive` | **72 of 108 folds** |
| `data/results_sosym/congen` | **0 of 84** |
| `data/results_sosym/interactive` | **0 of 150** |

This is the `kb_dir` defect: `run_compare` scores every file in a directory with the oracle
of the block it sits under, and the block's `name` filters nothing. One block naming FQA
scored the whole directory. The revision's data is clean because `make_score_configs.py`
now writes one block per file and `reject_foreign_knowledge_bases` refuses a foreign
knowledge base.

## The correction, with its own control

Semantic F1, ConGen, old (published) against new:

| cell | published | corrected | Δ |
|---|---|---|---|
| KB₁ REAL-FM-7 rs_1n | 0.1762 | **0.8747** | +0.6985 |
| KB₁ REAL-FM-7 rs_3n | 0.1348 | **0.9329** | +0.7981 |
| KB₁ REAL-FM-7 2cov | 0.0784 | **0.9047** | +0.8263 |
| KB₁ REAL-FM-7 ff | 0.1923 | **0.8054** | +0.6131 |
| KB₂ fqa rs_1n | 0.9448 | 0.9448 | **+0.0000** |
| KB₂ fqa rs_3n | 0.9474 | 0.9474 | **+0.0000** |
| KB₂ fqa ff | 0.9106 | 0.9168 | +0.0062 |
| KB₂ fqa 2cov | 0.8906 | 0.8669 | −0.0237 |
| KB₃ arcade rs_1n | 0.5249 | **0.6550** | +0.1301 |
| KB₃ arcade 2cov | 0.3235 | **0.7131** | +0.3895 |
| KB₃ arcade ff | 0.5130 | **0.7131** | +0.2000 |
| KB₃ arcade rs_3n | 0.5682 | 0.5740 | +0.0059 |

**KB₂ is the control.** It is the only model that was scored against its own target theory,
and it is the only one whose figures do not move — the two small KB₂ deltas are the
genuine effect of the code state, the size of everything else measured this week. A defect
that moved all three columns would have been indistinguishable from a general change; one
that moves exactly the two wrongly-scored columns and leaves the correctly-scored one alone
is the diagnosis stated as a measurement.

The published row `ConGen RS(n): 0.176 / 0.945 / 0.525` reproduces exactly from
`data/results`, so the numbers are ours and the arithmetic was faithful — to the wrong
target theory.

## Why this is disclosed rather than quietly fixed

The error runs against our own interest: it makes ConGen look far worse than it is on two
of three knowledge bases, and the correction improves every affected figure. Published as
a correction, with the control that identifies it, it is evidence the pipeline is now
checked. Left for a reviewer to notice as an unexplained jump between versions, it reads
as the opposite.

## Unresolved

1. Which change made the revision's scoring correct is provenance, not part of the claim.
   The guard and the per-file config are in place and the new data is clean on 234 folds.
2. `tab:iterative_accuracy` and the runtime table draw on the same contaminated directory;
   whether accuracy is affected has not been checked here.
3. The old `data/results` tree remains committed and wrong. It is the input the published
   tables came from, so it is evidence and should not be silently regenerated.
