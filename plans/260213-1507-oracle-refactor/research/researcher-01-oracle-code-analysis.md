# Oracle Package Architecture Analysis

**Date**: 2026-02-13
**Analyst**: researcher-01
**Scope**: `/Users/manleviet/Development/GitHub/AcqMSS/acqmss/oracle/`

---

## Package Exports (`__init__.py`)

```python
Oracle, FeatureModelOracle           # Base oracle + FM implementation
InteractiveOracle                     # Interactive learning interface
AutomatedOracle, UserPromptOracle     # Interactive implementations
CachedOracle                          # Wrapper with caching
ExampleProvider                       # Example-based learning support
```

---

## Abstract Base Classes

### `Oracle` (ABC)
**Location**: `oracle.py:15-57`
**Purpose**: Base protocol for configuration validation
**Abstract Methods**:
- `classify(example: Example) -> ExampleType` — classify example as positive/negative
- `is_valid(assignments: Dict[str, bool]) -> bool` — check configuration validity
- `get_features() -> Set[str]` — all feature names
- `get_feature_ids() -> Dict[str, int]` — feature name to SAT variable mapping

**Dependencies**: `abc.ABC`, `pysat.solvers.Solver`, `acqmss.testcases.data_structures`

### `InteractiveOracle` (ABC)
**Location**: `interactive.py:16-40`
**Purpose**: Interactive membership query interface
**Abstract Methods**:
- `ask(query: Dict[str, bool]) -> bool` — ask if configuration is valid
- `get_feature_count() -> int` — number of features

**Note**: Parallel to `Oracle` but with different method names (`ask` vs `is_valid`). No inheritance relationship.

---

## Concrete Implementations

### `FeatureModelOracle(Oracle)`
**Location**: `oracle.py:59-363`
**Purpose**: SAT-based oracle using feature model as ground truth
**Constructor**: `__init__(fm_path: str)` — loads .uvl file

**Public Methods**:
- `classify(example) -> ExampleType` — inherited from Oracle
- `is_valid(assignments) -> bool` — SAT check with assumptions
- `get_features() -> Set[str]` — all features
- `get_feature_ids() -> Dict[str, int]` — name→ID mapping
- `get_leaf_features() -> Set[str]` — leaf features only
- `get_root_feature() -> str` — root feature name
- `get_valid_configuration(assumptions) -> Optional[Dict]` — generate valid config
- `get_cnf_clauses() -> List[List[int]]` — ground truth CNF
- `get_num_constraints() -> int` — clause count
- `get_constraint_descriptions() -> Set[str]` — extract FM constraint descriptions

**State**:
- `fm_path: str` — path to feature model
- `fm` — flamapy FM object
- `features: Set[str]` — all feature names
- `leaf_features: Set[str]` — leaf features
- `feature_ids: Dict[str, int]` — name→ID mapping (from flamapy)
- `cnf_clauses: List[List[int]]` — ground truth CNF
- `solver: Solver` — persistent PySAT solver (glucose4)

**FM-Specific Dependencies**:
- `flamapy.metamodels.fm_metamodel.transformations.UVLReader` — load .uvl files
- `flamapy.metamodels.pysat_metamodel.transformations.FmToPysat` — CNF conversion
- `flamapy.core.models.ast.ASTOperation` — parse cross-tree constraints

**Key Logic**:
- `_build_cnf()` — extracts CNF + stores flamapy variable mapping as authoritative source
- `_parse_ctc_to_description()` — parses AST to extract requires/excludes/hierarchy constraints
- Maintains persistent SAT solver for incremental queries

### `AutomatedOracle(InteractiveOracle)`
**Location**: `interactive.py:42-94`
**Purpose**: Wrapper around `FeatureModelOracle` for interactive experiments
**Constructor**: `__init__(fm_path: str)` — creates internal `FeatureModelOracle`

**Public Methods**:
- `ask(query) -> bool` — delegates to `fm_oracle.is_valid()`
- `get_feature_count() -> int` — returns `len(fm_oracle.features)`
- `get_features()` — delegates to FM oracle
- `get_feature_ids()` — delegates to FM oracle
- `get_root_feature()` — delegates to FM oracle

**State**:
- `fm_oracle: FeatureModelOracle` — internal oracle instance

**Coupling**: Full dependency on `FeatureModelOracle`. Acts as thin adapter.

### `UserPromptOracle(InteractiveOracle)`
**Location**: `interactive.py:96-181`
**Purpose**: Human-in-the-loop oracle via terminal prompts
**Constructor**: `__init__(features: list, verbose: bool = True)`

**Public Methods**:
- `ask(query) -> bool` — prompts user, returns y/n answer
- `get_feature_count() -> int` — returns `len(features)`
- `get_query_count() -> int` — number of queries asked

**State**:
- `features: Set[str]` — feature names
- `verbose: bool` — detailed vs compact display
- `_query_count: int` — query counter

**Dependencies**: None (no FM coupling)

### `CachedOracle(InteractiveOracle)`
**Location**: `interactive.py:183-254`
**Purpose**: Caching wrapper for any `InteractiveOracle`
**Constructor**: `__init__(base_oracle: InteractiveOracle)`

**Public Methods**:
- `ask(query) -> bool` — check cache, delegate if miss
- `get_feature_count()` — delegates to base
- `get_cache_stats() -> Dict` — hits, misses, size
- `clear_cache()` — reset cache

**State**:
- `base_oracle: InteractiveOracle` — wrapped oracle
- `_cache: Dict[tuple, bool]` — config→answer mapping
- `_cache_hits: int`, `_cache_misses: int` — stats

**Dependencies**: None (generic wrapper)

### `ExampleProvider`
**Location**: `interactive.py:256-298`
**Purpose**: Iterator for shuffled example pool (example-based QuAcq)
**Constructor**: `__init__(examples: List[Dict[str, bool]], seed: int = None)`

**Public Methods**:
- `next_example() -> Optional[Dict]` — get next example, None if exhausted
- `is_exhausted() -> bool` — check if pool empty
- `remaining() -> int` — examples left

**State**:
- `_examples: List[Dict]` — shuffled example pool
- `_index: int` — current position

**Dependencies**: `random` (for shuffling)

---

## Oracle Extractor

### `OracleData` (dataclass)
**Location**: `oracle_extractor.py:16-103`
**Purpose**: Extract and package oracle data for evaluation

**Fields**:
- `descriptions: Set[str]` — constraint descriptions (Strategy 1)
- `clauses: List[List[int]]` — CNF clauses (Strategy 2)
- `clause_set: Set[Tuple]` — normalized sorted clauses
- `feature_map: Dict[str, int]` — name→ID mapping
- `root_feature: str` — root feature name

**Factory Methods**:
- `from_uvl(uvl_path: Path) -> OracleData` — creates temp `FeatureModelOracle`, extracts data, cleans up
- `from_oracle(oracle: FeatureModelOracle) -> OracleData` — extracts from existing oracle

**Dependencies**: `FeatureModelOracle` (temporary or injected)

---

## Architecture Issues

### 1. Dual Oracle Abstractions
- `Oracle` (for CONGEN) vs `InteractiveOracle` (for QuAcq) have overlapping purposes
- `Oracle.is_valid()` ≈ `InteractiveOracle.ask()` — same concept, different names
- `AutomatedOracle` wraps `FeatureModelOracle` just to adapt method names

### 2. FM-Specific Logic Embedded in Generic Oracle
`FeatureModelOracle` mixes:
- Generic oracle interface (`classify`, `is_valid`)
- FM-specific methods (`get_leaf_features`, `get_root_feature`, `get_constraint_descriptions`)
- Flamapy coupling (`UVLReader`, `FmToPysat`, AST parsing)

**Result**: Cannot easily add non-FM oracles (e.g., SQL database, REST API)

### 3. Shared Methods Across Oracle Types
Both `Oracle` and `InteractiveOracle` need:
- `get_features()` / `get_feature_count()`
- `get_feature_ids()` (AutomatedOracle exposes this)
- Membership query (`is_valid()` / `ask()`)

### 4. No Generic Oracle Protocol
- No shared interface for common operations across oracle types
- `UserPromptOracle` reimplements feature tracking separately
- `ExampleProvider` unrelated to oracle hierarchy despite being in same module

---

## Unresolved Questions

1. Should `Oracle` and `InteractiveOracle` merge into single protocol?
2. How to support non-FM oracles (e.g., web API, custom validators)?
3. Should FM-specific methods (`get_root_feature`, `get_constraint_descriptions`) move to separate FM-specific interface?
4. Is `AutomatedOracle` necessary, or can `FeatureModelOracle` directly implement both interfaces?
5. Should `ExampleProvider` be part of oracle package or moved to testcases/examples module?
