# QuAcq - Constraint Acquisition via Partial Queries (IJCAI 2013)

**Last Updated**: 2026-02-13

**Paper:** Bessiere, Coletta, Hebrard, Katsirelos, Lazaar, Narodytska, Quimper, Walsh

## Overview

QuAcq (Quick Acquisition) — active learning algorithm that learns constraint networks by asking the user **partial queries** (assignments to subsets of variables), instead of membership queries on all variables.

## Implementation Modes

AcqMSS implements QuAcq in **two modes**:

### 1. Oracle-Based Mode (Original Algorithm 1)

Interactive learning through membership queries:
1. Init `C_L = {}` (empty learned network)
2. Generate query `e` satisfying `C_L` but violating at least 1 constraint in bias `B`
3. Ask oracle: `ASK(e)`
   - **yes** → remove all constraints in `B` that `e` violates
   - **no** → call FindScope + FindC to find and add 1 constraint to `C_L`
4. Repeat until convergence or collapse

**Implementation**:
- `acqmss/algorithms/interactive/quacq.py` — Main QuAcq algorithm (oracle mode)
- `acqmss/algorithms/interactive/query_generator.py` — GenerateQuery heuristics
- `acqmss/oracle/interactive.py` — AutomatedOracle, UserPromptOracle

### 2. Example-Based Mode (New — Batch Learning with FindScope/FindC)

Learn from pre-collected positive/negative examples without an interactive oracle:
1. Init `C_L = {}`, load pre-collected E+/E- examples
2. For each `e` in E- (negative examples):
   - Call `FindScope` to identify violated scope via partial queries (ConsistencyChecker)
   - Call `FindC` to identify specific constraint from candidates
   - Add found constraint to `C_L`
3. Prune bias using E+ (valid examples reject false positive constraints)
4. Return learned `C_L`

**Implementation**:
- `acqmss/algorithms/interactive/quacq.py` — QuAcq.learn_from_examples() method
- `acqmss/algorithms/interactive/findscope.py` — FindScope (Algorithm 2, 134 LOC)
- `acqmss/algorithms/interactive/findc.py` — FindC (Algorithm 3, 208 LOC)
- `acqmss/algorithms/interactive/learner.py` — InteractiveLearner facade (from_examples() API)
- `acqmss/oracle/interactive.py` — ExampleProvider for batch examples

## FindScope (Algorithm 2)

Finds the scope (variable set) of a violated constraint using a QuickXPlain-like technique — binary split on variable set, ask partial queries on each half.

**Process**:
1. Start with all variables in scope candidate
2. Binary search: split variables in half
3. Ask partial query on each half
4. Recurse on half that caused violation
5. Converge to minimal scope

- **Complexity:** O(|S| * log|X|) queries per call

## FindC (Algorithm 3)

After scope `Y` is found, identifies the specific constraint violated by generating discriminating examples.

**Process**:
1. Collect constraints matching scope (exact match preferred, fallback to subset)
2. Use example pool to test candidates
3. Generate SAT queries if needed (query_mode=example_first)
4. Return first matching constraint

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

## Experimental Results (Paper)

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
6. **Batch mode** (NEW) — Example-based learning with FindScope/FindC requires no oracle

## Query Generation Heuristics

- **max-1**: Find solution of `C_L` maximizing violated constraints in `B` (1s cutoff)
- **sol**: Find first solution of `C_L` violating at least 1 constraint in `B` (cheapest)
- **max-1** generally needs fewer queries; **sol** is faster per query
- **FindScope/FindC** uses both SAT-based queries and example pool matching

## Relation to Codebase

**Core Implementation**:
- `acqmss/algorithms/interactive/quacq.py` — Main QuAcq algorithm (439 LOC)
- `acqmss/algorithms/interactive/findscope.py` — FindScope (Algorithm 2, 134 LOC)
- `acqmss/algorithms/interactive/findc.py` — FindC (Algorithm 3, 208 LOC)
- `acqmss/algorithms/interactive/learner.py` — InteractiveLearner facade (426 LOC, from_examples() API)
- `acqmss/oracle/oracle.py` — Oracle, FeatureModelOracle base classes (362 LOC)
- `acqmss/oracle/interactive.py` — InteractiveOracle, AutomatedOracle, UserPromptOracle, ExampleProvider (297 LOC)

**Evaluation Support**:
- `acqmss/eval/fold_io.py` — Shared CV fold generation for CONGEN/QuAcq comparison (145 LOC)
- `acqmss/eval/interactive_runner.py` — QuAcq pipeline runner (197 LOC)
- `acqmss/eval/interactive_metrics.py` — QuAcq-specific metrics (391 LOC)
- `apps/generate_cv_folds.py` — CLI to pre-generate folds (68 LOC)

**Two Paradigms**:
- **CONGEN** (passive): Learns from E+/E- in one batch pass (GenerateNE → ACQMSS → REDUCE)
  - Caller invokes GenerateNE separately before CONGEN
  - Results merged into task via merge_ne_into_task()
  - Immutable checkers after construction

- **QuAcq oracle mode** (active/interactive): Queries user via GenerateQuery
  - Persists across questions to refine KB incrementally
  - Real-time user interaction (manual or AutomatedOracle)

- **QuAcq example mode** (batch): Learns from E+/E- using FindScope/FindC (no oracle)
  - Same E+/E- as CONGEN but processed algorithmically
  - Fair comparison via shared CV folds (fold_io.py)

**Shared Infrastructure**:
- Both use same SAT solvers (IncrementalPySATChecker, NonIncrementalPySATChecker)
- Both use same FM representation and bias generation pipeline
- Both use same evaluation framework (cross_validation, accuracy metrics)
- Fair comparison via shared CV folds (fold_io.py)
- Both support n-fold cross-validation with pre-generated folds

## Oracle Implementations

**Base Classes** (acqmss/oracle/oracle.py):
- `Oracle` — Abstract base class for configuration validators
- `FeatureModelOracle` — FM-based oracle using flamapy

**Concrete Oracles** (acqmss/oracle/interactive.py):
- `AutomatedOracle` — Automated oracle for both modes (FM-based or constraint-based)
- `UserPromptOracle` — Interactive user oracle (prompts on command line)
- `CachedOracle` — Caching wrapper to avoid re-asking same query
- `ExampleProvider` — Batch example interface for FindC algorithm

**Critical**: Feature ID consistency
- Uses flamapy's variable mapping (tree traversal order) as authoritative source
- Ensures feature_ids match SAT variable IDs in CNF clauses
- Alphabetical sorting would cause critical mismatch between Oracle and SAT solver

## Cross-Validation Support

Both CONGEN and QuAcq support n-fold cross-validation with shared infrastructure:

```python
# Shared fold generation and loading
from acqmss.eval.fold_io import generate_folds, load_folds, save_folds

# Pre-generate folds once for reproducible evaluation
folds = generate_folds(E_plus, E_minus, n_splits=5, seed=42)
save_folds(folds, 'data/cv_folds.json')

# Load same folds for both CONGEN and QuAcq
fold_data = load_folds('data/cv_folds.json')

# Fair comparison: both algorithms use identical train/test splits
congen_results = cross_validation_congen(..., fold_data=fold_data)
quacq_results = cross_validation_interactive(..., fold_data=fold_data)
```

**Key Features**:
- Per-fold bias shuffling (shuffle_seeds in FoldData)
- Query mode control: `example_only` or `example_first` (SAT fallback)
- Convergence tracking (query count, termination reason)
- Intersected KB (consensus across folds)
