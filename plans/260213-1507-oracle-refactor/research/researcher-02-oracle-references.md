# Oracle References and Usage Analysis

**Date:** 2026-02-13
**Author:** researcher
**Scope:** All oracle imports, instantiations, and method calls across codebase

---

## Executive Summary

5 oracle classes consumed by 14 files. Primary consumers: QuAcq, InteractiveLearner, app scripts. Interface: `ask(query) → bool`, `get_feature_ids()`, `get_root_feature()`.

---

## Oracle Class Hierarchy

**Base:** `Oracle` (abstract base in `acqmss/oracle/oracle.py`)
**Concrete FM Oracle:** `FeatureModelOracle` (loads .uvl, validates via SAT)
**Interactive Oracles:** `InteractiveOracle` (abstract), `AutomatedOracle`, `UserPromptOracle`
**Helpers:** `ExampleProvider` (shuffled pool), `CachedOracle` (wrapper), `OracleExtractor` (bias gen)

---

## Core Interface Methods

### FeatureModelOracle
- `is_valid(config: Dict[str, bool]) → bool` — SAT check against FM CNF
- `get_cnf_clauses() → List[List[int]]` — Export FM as CNF
- `get_feature_ids() → Dict[str, int]` — Name → variable ID map
- `get_root_feature() → str` — Root feature name
- `features: List[str]` — Feature name list

### InteractiveOracle
- `ask(query: Dict[str, bool]) → bool` — Membership query (subclasses implement)
- `get_feature_ids() → Dict[str, int]`

### AutomatedOracle (wraps FeatureModelOracle)
- `ask(query) → bool` — Delegates to `fm_oracle.is_valid(query)`
- `get_feature_ids()` — Delegates to `fm_oracle.get_feature_ids()`
- `get_root_feature()` — Delegates to `fm_oracle.get_root_feature()`
- `fm_oracle: FeatureModelOracle` — Wrapped instance

### UserPromptOracle
- `ask(query) → bool` — Prints to terminal, prompts y/n
- Features passed at init: `UserPromptOracle(features: List[str])`

### ExampleProvider
- `next_example() → Optional[Dict[str, bool]]` — Draw from shuffled mixed pool
- `remaining() → int` — Count of undrawn examples

---

## Consumer Analysis

### 1. QuAcq (`acqmss/algorithms/interactive/quacq.py`)

**Imports:**

```python
from conacq.oracle import InteractiveOracle, ExampleProvider
```

**Methods Called:**
- `oracle.ask(query)` (line 75, oracle-based mode)
- `example_provider.next_example()` (line 146, example-based mode)
- `example_provider.remaining()` (line 136)

**Usage Pattern:**
- **Oracle-based mode (`learn`)**: Accepts `InteractiveOracle`, calls `ask()` for membership queries
- **Example-based mode (`learn_from_examples`)**: Accepts `ExampleProvider`, draws examples from pool, validates via FM CNF directly (no oracle `ask()` call)

**Construction:** Passed as parameter; QuAcq does not construct oracles

---

### 2. InteractiveLearner (`acqmss/algorithms/interactive/learner.py`)

**Imports:**

```python
from conacq.oracle import InteractiveOracle, AutomatedOracle, UserPromptOracle, ExampleProvider
```

**Instantiations:**
- `AutomatedOracle(fm_path)` (lines 107, 227) — `from_files()`, `from_examples()`
- `UserPromptOracle(features)` (line 279) — `learn()` interactive mode
- `ExampleProvider(examples, seed)` (line 231) — `from_examples()`

**Methods Called:**
- `oracle.ask(query)` — Implicitly via QuAcq
- `oracle.get_feature_ids()` (line 167) — Extract feature map
- `oracle.get_root_feature()` (line 171) — Extract root for background
- `oracle.fm_oracle.cnf_clauses` (line 232) — Access wrapped FM CNF

**Construction Logic:**
```python
# from_files: automated oracle from FM
oracle = AutomatedOracle(fm_path)

# from_examples: automated oracle + example provider
oracle = AutomatedOracle(fm_path)
learner._example_provider = ExampleProvider(examples, seed)
learner._fm_clauses = oracle.fm_oracle.cnf_clauses

# learn: user prompt oracle for interactive mode
oracle = UserPromptOracle(features)
```

---

### 3. Apps (`apps/run_interactive_eval.py`)

**Imports:**

```python
from conacq.algorithms.interactive import InteractiveLearner, InteractiveResult
```

**Construction:**

```python
learner = InteractiveLearner.from_bias_and_fm_fide(
   fide_fm_path=model_config.oracle,
   bias_path=model_config.bias,
   solver_name=solver_name,
   enable_profiling=True
)
```

**Usage:** Factory method `from_files()` creates `AutomatedOracle` internally; app never touches oracle directly

---

### 4. Tests (`tests/test_interactive.py`)

**Imports:**

```python
from conacq.oracle import FeatureModelOracle, InteractiveOracle, AutomatedOracle, CachedOracle
```

**Fixture:**
```python
def oracle():
    return AutomatedOracle(str(FM_PATH))
```

**Instantiation:**
```python
oracle = AutomatedOracle(str(FM_PATH))
```

**Methods Called:**
- `oracle.ask(query)` — Direct calls in tests
- Tests assume `ask()` interface for all interactive oracles

---

### 5. CONGEN Apps (`apps/run_congen.py`, `apps/run_congen_eval.py`)

**Imports:**

```python
from conacq.oracle import FeatureModelOracle
```

**Instantiation:**
```python
oracle = FeatureModelOracle(model_config.path)
```

**Usage:** Example generation only; calls `oracle.is_valid(config)` to validate testcases

---

### 6. Example Generators (`apps/generate_examples.py`, `acqmss/testcases/generators/*.py`)

**Imports:**

```python
from conacq.oracle import FeatureModelOracle, Oracle
```

**Construction:**
```python
oracle = FeatureModelOracle(fm_path)
```

**Methods Called:**
- `oracle.is_valid(config)` — Filter invalid configs
- `oracle.features` — Feature list for random sampling

**Pattern:** Generators accept `Oracle` base type, only call `is_valid()`

---

### 7. FindC (`acqmss/algorithms/interactive/findc.py`)

**Imports:**

```python
from conacq.oracle import ExampleProvider
```

**Usage:**
```python
c_id = find_c(
    e=query,
    scope=scope,
    task=task,
    fm_clauses=fm_clauses,
    example_provider=example_provider,  # Optional
    solver_name=self.solver_name,
    query_mode=query_mode
)
```

**Methods Called:**
- `example_provider.next_example()` — Draw examples for FindC search when `query_mode='example_first'`

---

## Summary of Consumer Expectations

### Interface Requirements
1. **Membership queries:** `ask(config: Dict[str, bool]) → bool`
2. **Feature metadata:** `get_feature_ids() → Dict[str, int]`, `get_root_feature() → str`
3. **Validation:** `is_valid(config: Dict[str, bool]) → bool` (for example generation)
4. **CNF export:** `cnf_clauses: List[List[int]]` (for example-based mode)

### Construction Patterns
- **Apps:** Use `InteractiveLearner.from_files()` factory (hides oracle construction)
- **Tests:** Direct `AutomatedOracle(fm_path)` instantiation
- **CONGEN:** Direct `FeatureModelOracle(fm_path)` instantiation
- **Generators:** Accept `Oracle` base type parameter

### Dependency Chain
```
App → InteractiveLearner.from_files()
        ↓
    AutomatedOracle(fm_path)
        ↓
    FeatureModelOracle(fm_path) ← Core FM validation
```

---

## Files Importing Oracle Classes

### Direct Imports (14 files)
1. `acqmss/oracle/interactive.py` — Defines `AutomatedOracle`, `UserPromptOracle`
2. `acqmss/oracle/oracle_extractor.py` — Bias generation from FM
3. `acqmss/algorithms/interactive/quacq.py` — QuAcq algorithm
4. `acqmss/algorithms/interactive/learner.py` — InteractiveLearner
5. `acqmss/algorithms/interactive/findc.py` — FindC algorithm
6. `apps/run_interactive_eval.py` — Interactive eval script
7. `apps/run_congen.py` — CONGEN script
8. `apps/run_congen_eval.py` — CONGEN evaluation
9. `apps/generate_examples.py` — Example generation
10. `tests/test_interactive.py` — Interactive tests
11. `tests/test_congen.py` — CONGEN tests
12. `acqmss/testcases/generators/base.py` — Generator base
13. `acqmss/testcases/generators/nwise_coverage.py` — N-wise generator
14. `acqmss/testcases/generators/feature_frequency.py` — FF generator

### Package Exports (`acqmss/oracle/__init__.py`)
```python
from .oracle import Oracle, FeatureModelOracle
from .interactive import InteractiveOracle, AutomatedOracle, UserPromptOracle, CachedOracle
from .oracle_extractor import OracleData
```

---

## Key Observations

1. **AutomatedOracle is primary concrete implementation** for automated experiments
2. **InteractiveLearner hides oracle construction** from apps via factory methods
3. **QuAcq supports two modes:**
   - Oracle-based: calls `oracle.ask()`
   - Example-based: uses `ExampleProvider`, validates via FM CNF directly
4. **FeatureModelOracle used directly** by CONGEN and generators for `is_valid()` checks
5. **No oracle subclass overrides `get_feature_ids()` or `get_root_feature()`** — all delegate to `FeatureModelOracle`

---

## Unresolved Questions

None — interface and usage patterns are clear.
