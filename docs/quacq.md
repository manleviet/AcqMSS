# QuAcq - Constraint Acquisition via Partial Queries (IJCAI 2013)

**Last Updated**: 2026-02-28 (Merged ExampleProvider + QueryGenerator → unified QueryProvider)

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
- `conacq/algorithms/quacq/quacq.py` — Main QuAcq algorithm (oracle mode)
- `conacq/example_generators/query_provider.py` — Unified QueryProvider (pool + SAT strategies)
- `conacq/oracle/` — Oracle implementations (FeatureModelOracle, UserPromptOracle, CachedOracle)

### 2. Example-Based Mode (Batch Learning with FindScope/FindC)

Learn from pre-collected positive/negative examples without an interactive oracle:
1. Init `C_L = {}`, load pre-collected E+/E- examples
2. For each `e` in E- (negative examples):
   - Call `FindScope` to identify violated scope via oracle.is_valid() partial queries
   - Call `FindC` to identify specific constraint using DiscriminatingGenerator
   - Add found constraint to `C_L`
3. Prune bias using E+ (valid examples reject false positive constraints)
4. Return learned `C_L`

**New: Paper-Aligned Discriminating Examples** (commit 260227):
- DiscriminatingGenerator uses C_L[Y] (learned KB restricted to scope) + BG
- No longer uses FM clauses (ground truth) for discrimination
- All queries via oracle.is_valid() — no SAT discrimination
- Query history tagged with 'main', 'findscope', 'findc' sources

**Implementation**:
- `conacq/algorithms/quacq/quacq.py` — QuAcq.learn_from_examples() method (oracle.is_valid())
- `conacq/algorithms/quacq/findscope.py` — FindScope (Algorithm 2, 134 LOC, oracle-based)
- `conacq/algorithms/quacq/findc.py` — FindC (Algorithm 3, oracle.is_valid() + DiscriminatingGenerator)
- `conacq/algorithms/quacq/discriminating_generator.py` — DiscriminatingGenerator (NEW, 66 LOC, C_L[Y] + BG)
- `conacq/example_generators/query_provider.py` — QueryProvider handles both pool-based and SAT-based query generation

## FindScope (Algorithm 2)

Finds the scope (variable set) of a violated constraint using a QuickXPlain-like technique — binary split on variable set, ask partial queries on each half via oracle.is_valid().

**Implementation Details** (commit 260227):
- Uses `oracle.is_valid(partial)` for membership queries on variable subsets
- All partial queries recorded via `record_query(partial, answer, 'findscope')` callback
- Bias pruning uses raw clause maps (no SAT solver needed for scope determination)
- Paper-aligned: membership queries only, no SAT discrimination

**Process**:
1. Start with all variables in scope candidate
2. Binary search: split variables in half
3. Ask partial query on each half via oracle
4. Recurse on half that caused violation
5. Converge to minimal scope
6. Prune rejecting constraints from bias during search

- **Complexity:** O(|S| * log|X|) queries per call

## FindC (Algorithm 3)

After scope `Y` is found, identifies the specific constraint violated by generating discriminating examples from C_L[Y] (learned KB restricted to scope) + BG clauses.

**Implementation Changes (NEW)** (commit 260227):

**DiscriminatingGenerator (NEW)**:
- Generates discriminating examples from C_L[Y] + BG, NOT from FM clauses (ground truth)
- Paper Algorithm 3 line 5: find e' in sol(BG + C_L[Y]) s.t. e' |= c_i, e' |/= c_j
- SAT formula: BG + C_L[Y] + c_i + neg(c_j)
- Returns config dict or None if UNSAT
- Replaces SAT-based narrowing with C_L[Y]-based generation

**Simplified FindC** (commit 260228):
- Removed `_narrow_with_pool` — paper Algorithm 3 uses only DiscriminatingGenerator for narrowing
- FindC no longer accepts `example_provider` or `query_mode` params
- Uses `_narrow_with_generator` (DiscriminatingGenerator) when provided

**Query Recording**:
- All queries recorded via `record_query(config, answer, 'findc')` callback

**Process**:
1. Collect constraints matching scope (exact match preferred, fallback to subset)
2. Filter to constraints that actually reject example e
3. Use DiscriminatingGenerator to narrow candidates via discriminating examples
4. Return first remaining candidate

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

## Query Generation (QueryProvider)

Unified `QueryProvider` class (conacq/example_generators/query_provider.py) merges pool-based and SAT-based strategies:

**Three methods** mapping to three modes:
- `generate_from_pool()` → `example_only` mode: iterate pool, SAT-check satisfies C_L + BG, check violates ≥1 constraint in bias
- `generate_from_sat()` → `oracle` mode: SAT-based generation (max-1/sol heuristics)
- `generate()` → `example_first` mode: try pool first, fallback to SAT

**SAT Heuristics** (in generate_from_sat):
- **max-1**: Find solution of `C_L` maximizing violated constraints in `B` (1s cutoff)
- **sol**: Find first solution of `C_L` violating at least 1 constraint in `B` (cheapest)

**Pool Filtering** (paper Algorithm 1 condition):
- Query `e` must satisfy C_L ∪ BG (checked via SAT solver)
- Query `e` must violate ≥1 constraint in remaining bias (checked via raw clause violation)

## Relation to Codebase

**Core Implementation**:
- `conacq/algorithms/quacq/quacq.py` — QuAcq algorithm + QuAcqResult (DI pattern, mode dispatch, assumption-based learn())
- `conacq/algorithms/quacq/sat_utils.py` — Standalone utility functions (config_to_assumptions, violates_clauses, get_kb_clauses) — NEW
- `conacq/algorithms/quacq/findscope.py` — FindScope (Algorithm 2, 134 LOC, oracle.is_valid() instead of SAT)
- `conacq/algorithms/quacq/findc.py` — FindC (Algorithm 3, oracle.is_valid() + DiscriminatingGenerator narrowing)
- `conacq/algorithms/quacq/discriminating_generator.py` — DiscriminatingGenerator (66 LOC, C_L[Y] + BG)
- `conacq/algorithms/quacq/quacq_model.py` — QuAcqModel (dual to ConGenModel) for interactive learning
- `conacq/algorithms/quacq/quacq_model_builder.py` — QuAcqModelBuilder (fluent builder, auto-prepares on build())
- `conacq/algorithms/quacq/task_preparation.py` — QuAcqTask + QuAcqTaskPreparation (inherited from DiagnosisTask)
- `conacq/algorithms/quacq/_task_compat.py` — Shared duck-typing helpers (get_bg_clauses(), get_clause_map(), get_negated_clauses())
- `conacq/oracle/` — Oracle implementations: FeatureModelOracle, UserPromptOracle, CachedOracle, FMData, BGData
- `conacq/example_generators/` — QueryProvider: unified pool + SAT query generation (query_provider.py)

**Evaluation Support**:
- `conacq/eval/fold_io.py` — Shared CV fold generation for CONGEN/QuAcq comparison
- `conacq/runners/quacq_runner.py` — QuAcq pipeline runner (238 LOC, moved from eval/)
- `conacq/eval/cross_validation.py` — Cross-validation framework (424 LOC)
- `apps/generate_cv_folds.py` — CLI to pre-generate folds (68 LOC)

**Two Paradigms** (Now Unified via Assumption IDs):

1. **CONGEN** (passive): Learns from E+/E- in one batch pass (GenerateNE → ACQMSS → REDUCE)
   - **GenerateNE called internally by `ConGenModel.prepare()`** (not by callers)
   - Uses `ConGenTask` (assumption-based constraint IDs)
   - Immutable checkers after construction

2. **QuAcq** (active/interactive): Two modes via `QuAcqModel` + `QuAcqTask`
   - **Oracle mode**: Queries user via GenerateQuery
     - `QuAcq.learn(oracle_mode='automated'/'interactive')`
     - Real-time user interaction via oracle
   - **Example mode**: Learns from pre-collected E+/E- using FindScope/FindC (no oracle)
     - `QuAcq.learn_from_examples(positive_examples, negative_examples)`
     - Fair comparison via shared CV folds
   - **Shared Infrastructure**: Both modes use `QuAcqModel` + `QuAcqTask` with assumption IDs

**Key Architectural Change** (commit 260226):
- **Assumption-Based ID Representation**: Both ConGen and QuAcq now use **int assumption IDs** exclusively
- **ConGenTask** — CONGEN constraints identified by assumption IDs
- **QuAcqTask** — QuAcq constraints identified by assumption IDs (parallel to ConGenTask)
- **Enables Symmetry**: QuAcq and ConGen share identical SAT-based semantics via assumption literals

**Query History Source Tagging** (NEW):

QuAcqRunner.run() now tracks source of each query for progressive evaluation:
- `record_query(config, answer, source='main')` — Tag query as 'main' or 'findc'
- `query_history: List[Tuple[Dict, bool, str]]` — 3-tuple with source tag
- `QuAcqRunResult.query_history` — Propagates query history with tags
- Use case: ProgressiveEvaluator filters main-loop queries for ConGen comparison

```python
# Query history format
quacq_result = quacq_runner.run(mode='automated')
for config, answer, source in quacq_result.query_history:
    if source == 'main':
        # Main learning loop query
    elif source == 'findc':
        # FindC discrimination query
```

**Assumption ID Architecture** (Current):

QuAcq mirrors ConGen's assumption-based design. Both use `prepare_kb()` to assign int assumption IDs:

```
Assumption ID Layout (shared between ConGen and QuAcq):
  Part 1: Root feature assumption IDs (from Oracle FM)
  Part 2: Root feature negated assumptions (from Oracle FM)
  Part 3: BG constraint pair (root + negated, from Oracle BGData)
  Part 4: Tseitin variables (for negation encoding)
  Part 5: Bias constraint pairs (original + negated) [QuAcq]
  Part 6: NE pairs (original + negated) [ConGen, from GenerateNE]

Key Classes (in conacq/algorithms/quacq/):
- QuAcqTask(DiagnosisTask): Pure data container for interactive learning state (no methods)
  - Inherited from DiagnosisTask: set_kb, assumptions, set_b, set_c, negation_map
  - Interactive-specific fields:
    - bias: Set[int] — Remaining bias constraint assumption IDs
    - learned_kb: List[int] — Discovered constraint assumption IDs
    - background_clauses: List[List[int]] — Raw BG CNF (no guards; for SAT violation checking)
    - constraint_clauses: Dict[int, List[List[int]]] — Constraint CNF by assumption ID
    - negated_clauses: Dict[int, List[List[int]]] — Negated constraint CNF by assumption ID
    - feature_ids: Dict[str, int] — Feature name → SAT variable ID
    - id_to_feature: Dict[int, str] — SAT variable ID → feature name
  - **Note**: Behavior (algorithms) moved to sat_utils.py standalone functions, not task methods
- QuAcqModel: QuAcq dual to ConGenModel (quacq_model.py)
- QuAcqModelBuilder: Fluent builder, auto-prepares on build() (quacq_model_builder.py)
- QuAcqTaskPreparation: Prepares QuAcqTask via prepare_kb() (task_preparation.py)
- _task_compat: Shared helpers (get_bg_clauses(), get_clause_map(), get_negated_clauses())
```

**Inheritance Pattern** (Refactored):
- **DiagnosisTask** (Base): Common assumption-based fields
  - `set_kb: List[List[int]]` — CNF clauses with assumption literals
  - `assumptions: List[int]` — All possible assumption IDs
  - `set_b: List[int]` — Background knowledge assumption IDs
  - `set_c: List[int]` — Bias assumption IDs
  - `negation_map: Dict[int, int]` — Mapping: original_id → negated_id
- **QuAcqTask(DiagnosisTask)** (Derived): Interactive learning specifics
  - All inherited fields from DiagnosisTask
  - Adds interactive state: bias (Set[int]), learned_kb (List[int])
  - Adds raw clause storage: background_clauses, constraint_clauses, negated_clauses
  - Adds feature mapping: feature_ids, id_to_feature

**Field Semantics** (Consistent with ConGen):
- `set_b: List[int]` — Assumption IDs for background knowledge constraints
  - Used for KB operations in SAT-based queries
- `background_clauses: List[List[int]]` — Raw CNF clauses (without assumption guards)
  - Extracted from Oracle's BG constraint data
  - Used for violation detection and SAT discrimination paths
  - Fixes: Correct interpretation of assumptions vs. clause structures

**Shared Infrastructure**:
- Both use same SAT solvers (IncrementalPySATChecker, NonIncrementalPySATChecker)
- Both use same FM representation and bias generation pipeline
- Both use same evaluation framework (cross_validation, accuracy metrics)
- Fair comparison via shared CV folds (fold_io.py)
- Both support n-fold cross-validation with pre-generated folds
- Constraint name resolution moved to runner layer (QuAcqRunner.resolve_kb() pattern)

## Oracle Implementations

**Base Classes** (conacq/oracle/base.py):
- `Oracle` — Abstract base class for configuration validators

**Concrete Oracles** (conacq/oracle/):
- `FeatureModelOracle` — FM-based oracle using flamapy (fm_oracle.py)
- `UserPromptOracle` — Interactive user oracle (prompts on command line) (user_prompt.py)
- `CachedOracle` — Caching wrapper to avoid re-asking same query (cached.py)

**Query Generation** (conacq/example_generators/):
- `QueryProvider` — Unified query provider: pool-filtered + SAT-based strategies (query_provider.py)
  - `generate_from_pool()`: Pool iteration with paper condition (satisfies C_L+BG, violates ≥1 bias)
  - `generate_from_sat()`: SAT-based generation (max-1/sol heuristics)
  - `generate()`: Combined pool-first + SAT fallback

**Critical**: Feature ID consistency
- Uses flamapy's variable mapping (tree traversal order) as authoritative source
- Ensures feature_ids match SAT variable IDs in CNF clauses
- Alphabetical sorting would cause critical mismatch between Oracle and SAT solver

## Removed Classes (Deleted This Session)

The following classes are **no longer available**:

| Class | Replacement | File Deleted | Reason |
|-------|-------------|--------------|--------|
| `InteractiveTask` | `QuAcqTask` | `task.py` | String-based constraint names; QuAcqTask uses assumption IDs |
| `InteractiveLearner` | `QuAcqModelBuilder` + `QuAcq` | `learner.py` | High-level facade; use builder pattern instead |
| `InteractiveResult` (alias) | `QuAcqResult` | `result.py` | Merged into `quacq.py` |

**Recommended Pattern** (DI-based, post-refactor):
```python
from conacq.algorithms.quacq import QuAcqModelBuilder, QuAcq
from conacq.example_generators import QueryProvider
from conacq.oracle import FeatureModelOracle

# Build and prepare model
oracle = FeatureModelOracle('data/fms/model.uvl')
model = (QuAcqModelBuilder.from_bias('data/bias/model.json')
         .with_oracle(oracle)
         .build())  # Returns prepared QuAcqModel

# Build QuAcq with dependencies (oracle mode)
query_provider = QueryProvider(solver_name='glucose4')
discrim_gen = DiscriminatingGenerator()
quacq = QuAcq.for_oracle(checker, oracle, query_provider, discrim_gen)

# Run learning (returns raw assumption IDs)
result = quacq.learn(
    set_c=model.task.set_c,
    set_b=model.task.set_b,
    set_kb=model.task.set_kb,
    negation_map=model.task.negation_map,
    assumptions=model.task.assumptions,
    background_clauses=model.task.background_clauses,
    feature_ids=model.task.feature_ids,
    id_to_feature=model.task.id_to_feature,
    constraint_clauses=model.task.constraint_clauses,
    negated_clauses=model.task.negated_clauses,
    mode='oracle',
    max_queries=1000
)

# Runner layer resolves constraint names (matches ConGen pattern)
kb_names, kb_clauses = model.resolve_kb(result.kb_assumption_ids)
print(f"Learned KB: {kb_names}")
print(f"Queries: {result.n_queries}")
```

**Example-Based Mode**:
```python
from conacq.example_generators import QueryProvider

# QueryProvider with pool for example-based learning
query_provider = QueryProvider(solver_name='glucose4', pool=examples_list, seed=42)
quacq = QuAcq.for_examples(checker, oracle, query_provider)

# Run with pool only
result = quacq.learn(..., mode='example_only', ...)

# Or pool + SAT fallback (needs discrim_gen)
result = quacq.learn(..., mode='example_first', ...)
```

**QuAcqResult Representation** (NEW: Algorithm returns IDs only):
- `kb_assumption_ids: List[int]` — Primary: learned constraints as assumption IDs (from algorithm)
- `kb_constraints: List[str]` — Secondary: resolved names (populated by runner via `model.resolve_kb()`)

Pattern matches ConGen: algorithm returns assumption IDs, runner resolves names.

## Cross-Validation Support

Both CONGEN and QuAcq support n-fold cross-validation with shared infrastructure:

```python
# Shared fold generation and loading
from conacq.eval.fold_io import generate_folds, load_folds, save_folds

# Pre-generate folds once for reproducible evaluation
folds = generate_folds(E_plus, E_minus, n_splits=5, seed=42)
save_folds(folds, 'data/cv_folds.json')

# Load same folds for both ConGen and QuAcq
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
