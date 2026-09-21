# Round 8 — revised `main-r1.tex` read against the artifact, adversarially

- Date: 2026-09-21
- Manuscript: `Overleaf/SoSyM/main-r1.tex`, mtime 2026-09-20 09:56, 1,273 lines
- Artifact at start: `0f51bfe` (v1.0.0). Re-carved to **`4dece76`** (see Shipped)
- Invariant: no statement in the artifact contradicts the revised manuscript, and no
  statement the manuscript makes about the artifact is false of it

## Enumeration: 57 claims

Method: read §2, §3 (Table 3 remark), §4 (Algorithms 1–3 + prose), §5.1, §5.3, §5.4,
§5.5.5, §5.6, §5.7 and Declarations; extract every sentence asserting something about
the implementation or the data; resolve each against the shipped tree (keep-list set,
not the development repository).

**43 consistent · 12 contradicted · 2 unverifiable from the tree.**

Of the 12: **10 artifact-side (all fixed)**, **2 manuscript-side (reported, not edited)**.

## Contradicted — artifact side (fixed)

| # | Manuscript | Artifact, before | Verdict |
|---|---|---|---|
| 1 | L408 `\caption{ConGen (E⁺, NE, B, BG): KB, with NE = GenerateNE(E⁻) computed beforehand}` | `docs/congen.md:107` Algorithm 1 as `ConGen(E+, E-, B, BG)`, line 1 `NE ← GenerateNE(E-)` | contradicted |
| 2 | L403 "GenerateNE is a preprocessing step that runs **before** ConGen and consults the oracle … Algorithms 1 to 3 issue no query" | same, plus `docs/system-architecture.md:21` "CONGEN: GenerateNE → ACQMSS → REDUCE (internal NE gen)" | contradicted |
| 3 | L405 "The function **Violated** returns the positive examples that `B ∪ NE ∪ BG` still rejects, and only those are passed down" | `docs/congen.md:146` Algorithm 2 with no `Violated`, no `E'⁺`, positives never shrunk | contradicted |
| 4 | Table 3 + L352 remark: ordered pairs × `{→, ∧, ∧̸}`, `c7 = id → db`, duplicate pairs (c2,c8)…(c12,c18) | `docs/congen.md:69` an entirely different numbering — `c7 = id → ¬ga`, `∧̸` rendered as `¬x ∧ ¬y`, no duplicate pairs possible | contradicted |
| 5 | L579 "ConGen returns a constraint theory `KB = {c7, c12, c13}`" (= `id→db, id ∧̸ ga, ga→db`) | `docs/congen.md:101` "KB = {c7, c12, c13} = {id → ¬ga, ¬id ∧ ga, db → ¬ga}" — same labels, three other constraints | contradicted |
| 6 | tab:biasformula last row: ea2468 `n=1,408 … |B|=2,047,362`; caption "contributes no **result** to any table" | `data/fms/SOURCES.md:34` "They contribute **no number to any table in the paper**" | contradicted |
| 7 | Journal template L6 "Please do not use `\input{...}`"; 20 `tabular` blocks typed in the manuscript, 0 `\input` | `README.md:69` and `apps/sosym_r1/make_paper_tables.py:13` "the manuscript `\input`s the fragment" | contradicted |
| 8 | L686 "The set of feature pairs … is configurable: all pairs, leaf-feature pairs only, or **extracted**" | `conacq/bias/bias_generator.py:136` docstring lists only `all` and `leaf` — omitting the mode four of five models use | contradicted |
| 9 | L684 "BG consists solely of the root feature constraint" | `conacq/algorithms/acqmss/task_preparation.py:107` "set_b: Background knowledge (BG) - root from Oracle" — false of the artifact: `set_b == []`, the root is `root_axiom` | contradicted (artifact vs itself) |
| 10 | L408 Algorithm 1 no longer numbers a GenerateNE step | `conacq/algorithms/acqmss/congen.py:73` "Paper Algorithm 1 (steps 2-9 …)" — stale numbering | contradicted |

Also corrected while in the file: `docs/congen.md`'s "logarithmic consistency checks"
bullet, against its own complexity table two sections above (`2γ·log₂(n/γ) + 2γ`).

## Contradicted — manuscript side (reported, `main-r1.tex` untouched)

**M1. L686: "six operators … all of them Boolean and *at most binary in the features
they relate*".** False of the bias. `alternative` and `or` relate a parent to *all* its
children: `clause_generator.py:68` emits `¬parent ∨ child₁ ∨ … ∨ childₙ`. Measured group
arity in the evaluated configs —

| model | group child-counts |
|---|---|
| REAL-FM-7 | 2×2 |
| arcade-game | 2×2, 3×4, 4×2, **13×1** |
| busybox-1.18.0 | 2×2, 3×5, 4×1 |
| REAL-FM-4 | 2×14, 3×14, 4×5, 5×2, 6×1, 7×1, **9×2** |
| fqa | 2×13, 3×7, 4×9, 5×5, 6×1, 7×1 |

so one bias candidate on KB₃ relates 14 features. Suggested repair: "…Boolean, binary
for the four non-group operators and n-ary in a group's children for `alternative` and
`or`." Nothing else changes — the closed form already counts a group candidate as two
constraints regardless of arity, and it is exact on all six models.

**M2. L1170 (§5.7): "The bias is restricted to binary requires and excludes
constraints".** False twice: the bias also contains `mandatory`, `optional`,
`alternative` and `or` (every `-bias-stats.txt` lists all six operators), and two of
those are n-ary per M1. It also contradicts §5.3's own six-operator sentence. The threat
being stated is real — completeness is bounded by the bias language — so the repair is
the scope, not the claim: "restricted to the six operators of Section 5.3".

## Unverifiable from the tree

- **L656 machine**: "MacBook Pro with Apple M4 Pro, 48 GB RAM, macOS 15". Nothing in the
  tree records the host. Timing provenance (`sweep-ledger.json`) records units and
  overlaps, not hardware.
- **L711 rate**: "about 95 seconds" per QuickXplain run on ea2468. Report-sourced, as
  §5.3 now says; raw sampler output was never committed. The *projection* built on it
  (1,752 runs → >46 h) recomputes from committed folds and is asserted.

## Spot-checks that held (selection)

| Claim | Source | Result |
|---|---|---|
| Algorithm 2 carries `E'⁺` | `acqmss.py:74-110` | `is_consistent_test_cases` → `set_tcp` → both recursive calls ✓ |
| Algorithm 1 receives NE | `congen.py:64`, `prepare_task` | ✓ |
| fresh solver per negative (L711) | `generate_ne.py:157` `build_checker(... NON_INCREMENTAL)` inside the loop | ✓ |
| positives/negatives folded separately (L714) | `conacq/eval/folds.py:50-62` | separate shuffles, separate round-robin ✓ |
| bias order shuffled once per fold, fixed seed | `folds.py:65`, `cross_validation.py:197` | ✓ |
| FF: 10n safety bound (L732) | `apps/generate_examples.py:52` `'ff': 10 * n` | ✓ |
| FF: attainable combinations only | `feature_frequency.py:173-180` witness-checked reachability | ✓ |
| rule learners: both classes ≥ 10 training instances (L1082) | `conacq/baselines/evaluation.py:52,109` | ✓ |
| … holds for 8 of 28, all random sampling | `baselines.json` | exactly 8, all `rs_*` ✓ |
| rule-learner accuracy > 0.94 (§2) | `baselines.json` | cell means 0.9442–0.9983 ✓ |
| cross-process test guards FF (L1182) | `test_generator_characterization.py:231` subprocess × 2 `PYTHONHASHSEED` | ✓ |
| NE excluded from all three tiers | `apps/run_compare.py:88-95` | ✓ stated from both sides |
| bias reduction 70.4–99.9 % | results tree | exact ✓ |
| ConGen delivers 7–687 constraints | results tree | 6.7–687.0 ✓ |
| iterative delivers 0–8.7, six cells none | results tree | exact ✓ |
| KB₃ RS(n): 177 delivered vs 130 clauses | results tree | 176.7 ✓ |

## Shipped

Re-carve **`4dece76`** from source `d483b52`, published to `main` and `v1.0.0`.
`CITATION.cff` `date-released: 2026-09-21` — the hygiene gate refused the first carve of
the day because it still read 2026-09-20, which is the behaviour that rule exists for.

Acceptance in the carved tree: six hygiene checks pass, 258 paper-number checks, 1,420
table cells 0 mismatched, `reproduce_tables_sosym.sh` exit 0 with a clean `git status`,
342 tests passed. Here: 263 checks, 681 passed / 1 skipped.

## Unresolved

1. M1 and M2 need a decision in `main-r1.tex`. Both are one-clause repairs; neither
   changes a number.
2. The manuscript transcribes the generated fragments by hand (the template forbids
   `\input`). `check_paper_tables.py` holds the *fragments* to the data; nothing holds
   the *manuscript* to the fragments. A diff-the-transcription gate would need the
   manuscript inside the repository, which it is not.
3. §5.3's BG sentence is true of what BG contains (one clause, the root) but the
   acquisition runs with `set_b == []` and applies the root afterwards — tiers exclude
   it, exact equivalence includes it. No shipped document now says otherwise. Worth one
   clause in the paper if a reviewer asks how BG enters Algorithms 1–3.
