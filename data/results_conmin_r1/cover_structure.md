# Cover structure — what AcqMinCover selects (2026-10-26)

Source: `apps/conmin_r1/cover_structure.py` over the persisted folds in `kbs/` (condition C, all
samplings incl. 2-COV, 72 folds, 91 cover elements); full listing in `cover_structure.txt`.
Target hierarchy and depth from `data/fms/<kb>.uvl`. Derived data; nothing in the submitted
tables changes.

| KB (tree depth) | operators in the cover | parent depth of the elements | relation in target |
|---|---|---|---|
| KB1 REAL-FM-7 (2) | mandatory 9, alternative 9, optional 1, excludes 1 | 0: 8, 1: 11, 2: 1 | 19/20 (1 cross-tree unchecked) |
| KB2 fqa (5) | alternative 17, or 6 | 0: 6, 1: 3, 3: 13, 4: 1 | 19/23 |
| KB3 arcade-game (7) | mandatory 15, or 3, alternative 3, requires 1 | 0: 5, 1: 6, 2: 6, 3–6: 7 | 19/24 (1 unchecked) |
| KB4 REAL-FM-4 (9) | alternative 18, mandatory 6 | 0: 2, 2: 6, 3: 5, 4: 7, 5: 1, 8: 3 | **6/24** |

Findings.
1. The cover is almost entirely hierarchy constraints (mandatory / alternative / or groups);
   2 of 91 elements are cross-tree. The selection criterion is rejection degree, not tree
   position: a sampled negative almost always violates a mandatory near the root or selects
   the wrong number of children of a large group, so one such constraint rejects most negatives.
2. The cover often selects a *stronger* candidate than the target: `alternative` where the
   target has an `or` group (KB4 18/24: Homepage, Preferences, Producttype, Targetingcriteria,
   Sortingfilters, …; KB2 Security, UserType; KB3 Board). Every negative that violates the
   or-group also violates the alternative, and the alternative rejects more, so the greedy /
   fixed-order choice prefers it. The alternative is in A only because no training positive
   selects two children — A's positive-scarcity over-fitting, which the cover inherits. Reduce
   (order fallbacks → S → C) then removes the true or-group from S as entailed by the
   alternative in C. Same mechanism as c12 vs c32 in the working example.
3. Consequence for the paper: minimality in *element count* does not favour the most general
   theory in *solution set*. A fix for the revision: among candidate rejectors of the same
   negatives, prefer the logically weakest (an entailed candidate before its entailer).

## 4. What the k=1 output contains (`apps/conmin_r1/output_structure.py`, 2026-10-26)

ConMin k=1, 15 Table-5 folds per KB, every constraint classified against the target UVL
(description level). Cross-tree split by matching bias `requires`/`excludes` against the UVL
constraint section (a few `A | !B` forms are not parsed and count as spurious: fqa 8, arcade 3).

| KB | constraints/fold | target relation | cross-tree in target | cross-tree not in target | operator neighbour |
|---|---|---|---|---|---|
| KB1 | 14.9 | 54% | 21/224 | 72/224 (32%) | 9 (4%): mand↔opt 4, or↔alt 5 |
| KB2 | 108.5 | 68% | 8 | 462 (28%) | 44 (3%): alt vs or 36, mand vs opt 8 |
| KB3 | 162.0 | 18% | 234 | 1,725 (71%) | 42 (2%): alt vs or 23, opt vs mand 19 |
| KB4 | 223.4 | 63% | 163 | 812 (24%) | 262 (8%): alt vs or 204, mand vs opt 44, opt vs mand 14 |

Reading. The non-target part of the output is dominated by cross-tree `requires`/`excludes`
between features that never (excludes) or always (requires) co-occur in the training positives
— classic co-occurrence over-fitting that positive diversity resolves. Operator neighbours
(an over-strong `alternative` for an `or`, `mandatory` for `optional`) are 2–8%. Part of the
"not in target" cross-tree set is semantically entailed (siblings of an alternative group
exclude each other; a child requires its parent); the semantic tier's P_std (.78/.89/.52/.78)
bounds the truly spurious share at 11–48%. The "errors are near misses of true constraints,
cheap to repair" argument therefore covers only the small operator-neighbour class.
