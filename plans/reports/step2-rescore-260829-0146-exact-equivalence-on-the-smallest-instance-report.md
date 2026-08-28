# Step 2: the re-scored ConGen results, and what 1/84 says

Date 2026-08-29. Branch `feat/sosym-r1`. Committed artefact:
**`data/results_sosym_r1/congen/`** — 28 CV files, 84 folds, produced under the final code
state (`c0f448f`) and scored with `run_compare` at `c128de3`, one block per file. This is
the tree the revision's structural tables come from.

`data/results_sosym/` is left as it was: it is the pre-fix sweep and the baseline every
comparison in this effort is measured against. Overwriting it would delete the other half
of those comparisons.

## Exact equivalence: 1 / 84

| KB | \|Cτ\| | attained / scored |
|---|---|---|
| REAL-FM-7 | **22** | **1 / 18** |
| fqa | 342 | 0 / 18 |
| arcade-game | 130 | 0 / 18 |
| REAL-FM-4 | 428 | 0 / 18 |
| busybox-1.18.0 | 994 | 0 / 12 |
| **total** | | **1 / 84** |

The one fold is `REAL-FM-7_rs_3n` fold 2.

**Exact equivalence is reached only on the smallest instance.** REAL-FM-7's target theory
is 22 clauses; the next smallest is six times larger. That sentence is stronger than
"1/84" and more honest: it says the single success is not evidence that the method recovers
models in general, and it points at the property that made it possible.

Three independent facts agree on that fold, which is why the number is quotable:

- `run_compare`'s equivalence check and the standalone `measure_exact_equivalence.py`
  reach it separately;
- it is the only fold in the whole set with semantic R = P = 1;
- without the per-example negative split it is not equivalent in either reduction order —
  the equivalence is that change's doing, verified by removing it.

## The zero column is the result

Four knowledge bases attain equivalence on no fold at all. Reported, not suppressed: it
tells a reader that a semantic F1 of 0.93 does not mean the target model was recovered,
which no F1 states on its own. It is the direct answer to the question of how to judge
quality in practice from the reported metrics.

## Reproducing it from the branch

    python -c "import json,glob;
    r=[json.load(open(p)).get('summary',{}).get('exact_equiv',{}) for p in
       glob.glob('data/results_sosym_r1/congen/*_cv_*.json')];
    print(sum(x.get('attained',0) for x in r), '/', sum(x.get('scored',0) for x in r))"

## Unresolved

1. The interactive (QuAcq) arm is not re-scored into this tree yet; equivalence there is
   unmeasured. QuAcq delivers no memorized negatives, so its delivered theory is the
   learned constraints plus the root axiom, and nothing about that predicts the outcome.
2. Whether `|Cτ| = 22` makes REAL-FM-7 an outlier worth naming in the instance-selection
   discussion, given one constraint is 4.5% of its recall.
