> **SUPERSEDED 2026-08-29 01:30 — the diagnosis below is wrong.** It reads the old
> `tp+fn = 342` as the ground-truth extraction having over-counted. The extraction is
> correct: a hand count from the `.uvl` agrees with it on all five models
> (22 / 342 / 130 / 428 / 994). 342 is FQA's clause count, and the old arcade file was
> scored against FQA's target theory — the `kb_dir` cross-model defect, not an extraction
> change. See
> `n-item-260829-0122-published-semantic-scored-against-the-wrong-model-report.md`.
> Kept unedited as the record of how the wrong conclusion was reached: every number in it
> is real, and the reasoning was sound up to the point where a coincidence — 342 being both
> "the old count" and "FQA's count" — went unchecked.

# Why the published .525 becomes 0.655, and a second defect in the same block

Date 2026-08-29. Branch `feat/sosym-r1`. `evaluation.tex:363` reports semantic F1 **.525**
for KB₃ (Arcade) RS(n) ConGen; the current sweep gives **0.6550** on that cell. The
revision cannot cite a number it no longer contains, so the cause had to be determined
rather than guessed.

## Cause: the ground-truth clause set shrank, 342 → 130

Not the acquisition, not the code that learns, not the route outside the repo.

| | tp | fp | fn | \|Cτ\| = tp+fn |
|---|---|---|---|---|
| old (`data/results/congen`, 2026-02-28) | 117 | 38 | 225 | **342** |
| new (`data/results_sosym`) | 122 | 121 | 8 | **130** |

`GroundTruthData.from_uvl('arcade-game')` returns **130** clauses today, matching the new
denominator exactly. The arithmetic closes on all four published figures:

    recall     117/342 = 0.342   ->   122/130 = 0.938
    precision  117/155 = 0.755   ->   122/243 = 0.502

`tp` barely moves (117 → 122). Recall rises because the denominator fell; precision falls
because a smaller target theory entails fewer of the KB's clauses, so `fp` rises 38 → 121.
**One change accounts for both numbers** — an explanation that covered only recall would
have left the precision drop for a reviewer to ask about.

## What was eliminated, and how

| candidate | verdict | evidence |
|---|---|---|
| the out-of-repo assembly route (N10) | **not it** | .525 reproduces exactly from committed `data/results` |
| regenerated example sets | **not it** | fold 0 train/test identical: 39/4, 20/2 |
| C7, or any acquisition change | **not it** | the OLD KB re-scored with TODAY's comparator gives P 0.5061 / R 0.9538 — within noise of the new KB's 0.5021 / 0.9385 |

That last row is the decisive one and it cost no build: score the old learned KB with the
current comparator. Same KB, two scorers, two answers. **The two-point experiment at C7 is
therefore unnecessary — it would return negative**, and we know that without running it.

## The open half of this: which count is correct

Provenance (`0dc9542` routes `ground_truth` through the `explanation.api` façade) is worth
finding but is not the gate. The gate is whether **130** or **342** reproduces from the
model by hand.

What is established: the current extraction yields 130 clauses, **all distinct**, shaped as
1 root unit + 120 binary + 9 group clauses, against a model with 34 cross-tree constraints,
9 `mandatory` blocks, 4 `optional`, 18 `or`. That is consistent with a standard encoding.
342 is 2.63× larger — not an integer multiple, so not naive duplication either.

**Consistency is not a hand count.** Nothing here yet proves 130 is right; it proves the
new numbers are internally coherent. The hand count is still owed.

If 342 turns out to be an over-count, this is a new N item rather than a line in B7: a
published figure that was wrong in the direction that *understated* our own result.
Disclosed as a correction it is strong; left for a reviewer to notice as an unexplained
jump it is not.

## Second defect, same block: the sibling lists are truncated samples

Each fold's `evaluation.semantic` carries `metrics` **and** sibling `tp` / `fp` / `fn`
lists. They are not a second counting system — they are capped samples, and nothing in
their names says so:

    metrics: tp=117  fp=38   fn=225        <- the real counts
    sibling: len(tp)=0  len(fp)=20  len(fn)=20

`kb_comparator.py:265,331,332` truncate with `[:20]` ("Limit to 20"), and the semantic
tier never populates `tp` at all, so `len(tp)` is **always 0**. Observed across folds:
`(0,1,20)`, `(0,8,20)`, `(0,13,20)`, `(0,20,20)` — `fn` is always exactly 20 because every
fold has more than 20.

Anything downstream that reads `len(sem['fn'])` as a count gets 20 for every fold, and
`len(sem['tp'])` gets 0 for every fold, with no error raised. Read `metrics`; treat the
lists as illustrative only. Worth a name in the field or a check before the tables are
built.

## Unresolved

1. The hand count of Cτ for arcade-game, against 130 and 342. Needs no machine time.
2. Which commit changed the extraction (`0dc9542` is the candidate, unverified).
3. Whether the truncated sibling lists are read as counts anywhere in the table path.
