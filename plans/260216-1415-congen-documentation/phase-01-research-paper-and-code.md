# Phase 1: Research Paper and Code

## Priority
P2

## Status
complete

## Overview
Extract all ConGen algorithm details from the paper and map them to implementation files. This phase produces a structured research summary that Phase 2 uses to write `docs/congen.md`.

## Context Links
- Paper: `paper/AcqMSS.pdf`
- Template: `docs/quacq.md`
- Architecture: `docs/system-architecture.md`
- Codebase summary: `docs/codebase-summary.md`

## Key Insights from Paper

### Paper Structure (7 pages)
1. **Abstract + Introduction** (p1) - Passive learning via MSS of constraint bias
2. **Preliminaries and Working Example** (p2-3) - Vocabulary, definitions, bias, training set, BG
3. **MSS-based Constraint Acquisition** (p3-4) - ConGen, AcqMSS, REDUCE algorithms
4. **Analysis and Evaluation** (p5-6) - Complexity, correctness, completeness, experiments
5. **Conclusion + References** (p6-7)

### Core Definitions (Paper)
- **Definition 1**: Vocabulary (V, D) - variables and domains
- **Definition 2**: Constraint Theory C = {c1..cn}
- **Definition 3**: Target Constraint Theory C_T (ground truth)
- **Definition 4**: Constraint Language L
- **Definition 5**: Constraint Bias B - candidate constraints from L
- **Definition 6**: Constraint Acquisition Problem - given B, BG, E=E+UE-, find KB accepting E+ and rejecting E-

### Algorithm 1: ConGen(E+, E-, B, BG) -> KB
```
1: NE <- GenerateNE(E-)
2: B' <- empty
3: if IsConsistent(E+, NE, BG) then
4:     B' <- AcqMSS(empty, B, NE, E+, BG)
5: else
6:     print "examples inconsistent"
7:     return (empty)
8: end if
9: return (REDUCE(B', NE, BG))
```

### Algorithm 2: AcqMSS(delta, B={c1..cn}, NE, E+, BG) -> B'
```
1:  if delta != empty then
2:      if IsConsistent(NE, E+, B, BG) then
3:          return (B)
4:      end if
5:  end if
6:  if |B| = 1 then
7:      return (empty)
8:  end if
9:  k = floor(|B|/2)
10: B1 = {c1..ck}
11: B2 = {ck+1..cn}
12: B'_beta <- AcqMSS(B1, B1, NE, E+, BG)
13: B'_alpha <- AcqMSS(B1 - B'_beta, B2, NE, E+, BG U B'_beta)
14: return (B'_alpha U B'_beta)
```

### Algorithm 3: REDUCE(B', NE, BG) -> KB
```
1: KB <- B' U NE
2: for c_i in KB do
3:     if IsInconsistent(BG U (KB - {c_i}) U {not(c_i)}) then
4:         KB <- KB - {c_i}
5:     end if
6: end for
7: return (KB)
```

### GenerateNE
- NE = set of negated negative examples
- For each e- in E-: not(e-) in NE
- Uses QuickXPlain to find minimal conflict set per negative example
- Subset minimality assumed for negative examples

### Complexity Analysis (Paper)
- **AcqMSS worst-case**: 2*gamma * log2(n/gamma) + 2*gamma consistency checks
  - gamma = number of elements deleted from B
  - n = number of constraints in B
  - 2*gamma = branching factor + leaf-node checks
- **AcqMSS best-case**: log2(n/gamma) + 2*gamma
- **Conflict determination**: log2(n/gamma) + 2*pi (best), 2*gamma * log2(n/gamma) + 2*pi (worst)
  - pi = assumed conflict set size

### Correctness (Theorem 1)
- Let B' subset of B be returned by AcqMSS, then B' accepts all positive examples
- Proof: AcqMSS only activated if consistent({e+} U NE U BG). Incrementally aggregates B'_beta into BG fulfilling: forall e+ in E+: consistent({e+} U NE U BG U B'_beta)

### Completeness (Theorem 2)
- If forall e+ in E+: consistent({e+} U NE U BG), ConGen will return B' subset of B
- Worst case: B' = empty (all constraints removed)

### Corollary 1
- AcqMSS fails bias reduction iff exists e+ in E+: NOT consistent({e+} U NE)

### Remark 1
- If B' = empty, ConGen returns only NE derived from E-

### Working Example (Paper Tables 1-6, Figure 1)
- 3 variables: id, db, ga (Boolean)
- Target: C_T = {id->db, id NOT_AND ga}
- Bias B = 18 constraints (c1..c18): all binary operators {->, AND, NOT_AND} between pairs
- BG = {ga->db}
- E+ = {not_id AND ga, id AND db AND not_ga}
- E- = {id AND not_db}
- NE = {not(id AND not_db)}
- AcqMSS returns B' = {c7, c12, c13, c18}
- REDUCE removes c18 -> final KB = {c7, c12, c13}

### Experimental Setup (Paper)
- Feature model knowledge bases (Heradio et al. 2022) as oracle
- Feature hierarchy -> BG, component requirements/incompatibilities -> bias B
- Three sampling methods: RS (random), 2-COV (n-wise coverage), FF (feature frequency)
- Example sizes: n, 2n, 3n, m (where n = #features, m = min valid configs including all pairs)
- n-fold cross-validation with accuracy = (TP+TN)/(TP+TN+FP+FN)
- Tables 7-12: Results (marked TBD in paper draft)

## Code-to-Paper Mapping

| Paper Concept | Implementation File | LOC | Key Class/Function |
|---|---|---|---|
| Algorithm 1 (ConGen) | `acqmss/algorithms/congen.py` | 228 | `ConGen.acquire()` |
| Algorithm 2 (AcqMSS) | `acqmss/algorithms/acqmss.py` | 104 | `AcqMSS.find_mss()` |
| Algorithm 3 (REDUCE) | `acqmss/algorithms/reduce.py` | 155 | `Reduce.reduce()` |
| GenerateNE | `acqmss/algorithms/generate_ne.py` | 193 | `GenerateNE.generate()` |
| Task preparation | `acqmss/algorithms/task_preparation.py` | 435 | `ConGenTaskPreparation` |
| ConGenModel | `acqmss/algorithms/congen_model.py` | 186 | `ConGenModel` |
| Builder | `acqmss/algorithms/congen_model_builder.py` | 157 | `ConGenModelBuilder` |
| Bias B | `acqmss/bias/` | ~1,250 | `BiasGenerator`, `ClauseGenerator` |
| E+/E- generation | `acqmss/example_generators/` | ~1,285 | RS, FF, 2-COV strategies |
| Cross-validation | `acqmss/eval/cross_validation.py` | 504 | `n_fold_cross_validation()` |
| ConGen runner | `acqmss/eval/congen_runner.py` | 228 | `ConGenRunner` |
| Accuracy metrics | `acqmss/eval/accuracy.py` | 170 | `AccuracyCalculator` |
| QuickXPlain (NE) | `explanation/operations/algorithms/quickxplain.py` | 80 | `QuickXPlain` |
| KBDiag (MSS) | `explanation/operations/algorithms/kbdiag.py` | 100 | `KBDiag` |
| ConsistencyChecker | `explanation/operations/algorithms/checker.py` | 450 | ABC + implementations |

## Implementation Details Not in Paper

1. **ConGenModel.prepare()**: Runs GenerateNE internally (callers don't invoke separately)
2. **Builder pattern**: `ConGenModelBuilder` encapsulates file loading + model construction
3. **CheckerModel protocol**: `get_kb()`, `get_assumptions()`, `use_incremental` for CheckerFactory
4. **Assumption-based representation**: All data as List[int] assumption IDs, mode-agnostic
5. **negation_map**: Dict[int, int] maps assumption ID -> negated form for REDUCE
6. **Tseitin encoding**: Used to negate CNF clauses for REDUCE redundancy checks
7. **CV fold reuse**: `model.prepare(fold_pos, fold_neg)` can be called multiple times
8. **Profiler integration**: `@measure_time`, `@count_calls` decorators on all algorithm methods

## Todo

- [x] Read and extract paper algorithms
- [x] Read and extract paper definitions
- [x] Read and extract complexity analysis
- [x] Read and extract working example
- [x] Map paper concepts to source files
- [x] Identify implementation details beyond paper
