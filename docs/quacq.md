# QuAcq - Constraint Acquisition via Partial Queries (IJCAI 2013)

**Paper:** Bessiere, Coletta, Hebrard, Katsirelos, Lazaar, Narodytska, Quimper, Walsh

## Overview

QuAcq (Quick Acquisition) — active learning algorithm that learns constraint networks by asking the user **partial queries** (assignments to subsets of variables), instead of membership queries on all variables.

## Implementation Modes

AcqMSS implements QuAcq in **two modes**:

### 1. Oracle-Based Mode (Original Algorithm 1)
1. Init `C_L = {}` (empty learned network)
2. Generate query `e` satisfying `C_L` but violating at least 1 constraint in bias `B`
3. Ask oracle: `ASK(e)`
   - **yes** → remove all constraints in `B` that `e` violates
   - **no** → call FindScope + FindC to find and add 1 constraint to `C_L`
4. Repeat until convergence or collapse

### 2. Example-Based Mode (New — Batch Learning)
1. Init `C_L = {}`, load pre-collected E+/E- examples
2. For each `e` in E- (negative examples):
   - Call `FindScope` to identify violated scope via partial queries (ConsistencyChecker)
   - Call `FindC` to identify specific constraint from candidates
   - Add found constraint to `C_L`
3. Prune bias using E+ (valid examples reject false positive constraints)
4. Return learned `C_L`

### FindScope (Algorithm 2)

Finds the scope (variable set) of a violated constraint using a QuickXPlain-like technique — binary split on variable set, ask partial queries on each half.

- **Complexity:** O(|S| * log|X|) queries per call

### FindC (Algorithm 3)

After scope `Y` is found, identifies the specific constraint violated by generating discriminating examples.

- **Complexity:** O(|Gamma|) queries per call

## Complexity Analysis

| Component | Queries |
|---|---|
| Find target network or collapse | O(\|C_T\| * (log\|X\| + \|Gamma\|)) |
| Prove convergence | O(\|B\|) |
| FindScope per call | O(\|S\| * log\|X\|) |
| FindC per call | O(\|Gamma\|) |

## Optimality

- **Optimal** on language `{=, !=}` with Boolean domain → O(n log n) queries
- **Not optimal** on language `{<}` — QuAcq needs Omega(n log n) while O(n) is achievable

## Experimental Results

| Benchmark | \|C_L\| | #queries | avg query size | time/query |
|---|---|---|---|---|
| Random (50 vars, sparse) | 12 | 196 | 24 | 0.23s |
| Random (50 vars, dense) | 86 | 1074 | 14 | 0.14s |
| Golomb-8 | 91 | 488 | 5 | 0.32s |
| Zebra | 62 | 656 | 8 | 0.10s |
| Sudoku 9x9 | 810 | 8645 | 21 | 0.16s |

## Key Advantages

1. **Partial queries** — shorter, easier for users to answer
2. **No positive examples needed** — unlike Conacq.1 and ModelSeeker
3. **Fast query generation** — uses heuristics (max-1, sol), no expensive optimization
4. **Scalable** — queries grow logarithmically with |B|
5. **Usable as solver** — stop when a complete positive example is found

## Query Generation Heuristics

- **max-1**: Find solution of `C_L` maximizing violated constraints in `B` (1s cutoff)
- **sol**: Find first solution of `C_L` violating at least 1 constraint in `B` (cheapest)
- **max-1** generally needs fewer queries; **sol** is faster per query

## Relation to Codebase

**Core Implementation**:
- `acqmss/algorithms/interactive/quacq.py` — Main QuAcq algorithm (oracle + example modes)
- `acqmss/algorithms/interactive/findscope.py` — FindScope (Algorithm 2, 134 LOC)
- `acqmss/algorithms/interactive/findc.py` — FindC (Algorithm 3, 208 LOC)
- `acqmss/algorithms/interactive/learner.py` — InteractiveLearner facade (from_examples() API)
- `acqmss/algorithms/interactive/user_interface.py` — Oracle + ExampleProvider interfaces

**Evaluation Support**:
- `acqmss/eval/fold_io.py` — Shared CV fold generation for CONGEN/QuAcq comparison
- `apps/generate_cv_folds.py` — CLI to pre-generate folds

**Two Paradigms**:
- **CONGEN** (passive): Learns from E+/E- in one batch pass (GenerateNE → ACQMSS → REDUCE)
- **QuAcq oracle mode** (active): Queries user interactively via GenerateQuery
- **QuAcq example mode** (batch): Learns from E+/E- using FindScope/FindC (no oracle)

**Shared Infrastructure**:
- Both use same SAT solvers (IncrementalPySATChecker, NonIncrementalPySATChecker)
- Both use same FM representation and bias generation pipeline
- Both use same evaluation framework (cross_validation, accuracy metrics)
- Fair comparison via shared CV folds (fold_io.py)
