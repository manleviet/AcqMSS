# Oracle Interface Usage Mapping — Complete Codebase Scan

**Scanned:** 260+ Python files (oracle, algorithms, example_generators, interactive, eval, apps, tests, bias)
**Date:** 2026-02-17 | **Scope:** AcqMSS v1.0

## Summary

**Key Finding:** Oracle interface is fragmented—callers use 11+ methods across 4 distinct contexts. Core methods (`get_features`, `is_valid`, `complete_configuration`) used extensively; advanced FM-specific methods (`get_root_feature`, `get_constraint_descriptions`) localized to specific modules.

**Abstract Methods in `Oracle` ABC (base.py):**
- `is_valid()` — membership query validation
- `get_features()` — feature name set
- `get_feature_ids()` — feature→SAT ID mapping
- `complete_configuration()` — solve for full valid config from partial
- `get_cnf_clauses()` — raw CNF clauses

**Extended Methods in `FeatureModelOracle` (FM-specific):**
- `get_root_feature()` — FM root node name
- `get_num_constraints()` — constraint count
- `get_constraint_descriptions()` — human-readable constraint strings
- `get_c()` — constraint assumption IDs (internal extension)
- `get_kb()`, `get_assumptions()` — merged KB/assumptions from model
- `get_raw_fm_clauses()` — FM clauses (not assumptions)

---

## Method Usage Table

| Method | Location | Line | Purpose | Can Get Elsewhere? |
|--------|----------|------|---------|-------------------|
| **get_features()** | base.py | 34 | Init generator features | No (instance-specific) |
| | random_sampling.py | 266 | Feature iteration | No |
| | feature_frequency.py | (init) | Feature iteration | No |
| | test_interactive.py | 202 | Test: invalid config | No |
| **get_feature_ids()** | base.py | 35 | Feature→ID map | Via model.variables |
| | learner.py | 156 | Build task mapping | Via model.variables |
| | test_interactive.py | 52 | Task conversion | Via model |
| | test_interactive.py | 324 | Verify root ID | Via model |
| | test_congen.py | 308 | Verify IDs match FM | Via model.variables |
| **get_feature_count()** | test_interactive.py | 190 | Sanity check | Count `.get_features()` |
| | generate_examples.py | 143 | Report metric | Count `.get_features()` |
| **is_valid()** | base.py | 55 | Classify examples | **Caller responsibility** |
| | feature_frequency.py | 111 | Classify config | **Caller responsibility** |
| | random_sampling.py | 143 | Classify config | **Caller responsibility** |
| | test_interactive.py | 204 | Test validation | **Caller responsibility** |
| | test_interactive.py | 217 | Cached oracle test | **Caller responsibility** |
| | test_interactive.py | 224 | Cache hit test | **Caller responsibility** |
| | quacq.py | 76 | Query oracle (ask alias) | **Caller responsibility** |
| **ask()** | quacq.py | 76 | Query oracle (is_valid alias) | **Caller responsibility** |
| **complete_configuration()** | base.py | 77 | Generate valid config | **Caller responsibility** |
| | feature_frequency.py | 198 | Generate valid config | **Caller responsibility** |
| | feature_frequency.py | 200 | Fallback valid config | **Caller responsibility** |
| **get_cnf_clauses()** | learner.py | 213 | Store FM clauses for eval | Via FMOracleModel.get_raw_fm_clauses() |
| **get_root_feature()** | learner.py | 160 | Extract root for BG | FM-specific, no alt |
| | task_preparation.py | 113 | ConGen metadata | FM-specific, no alt |
| | test_interactive.py | 323 | Verify root in task | FM-specific, no alt |
| | test_interactive.py | 337 | Verify root ID | FM-specific, no alt |
| | test_congen.py | 70 | Test root propagation | FM-specific, no alt |
| **get_num_constraints()** | task_preparation.py | 114 | ConGen metadata | FM-specific, no alt |
| **get_constraint_descriptions()** | **Not found** in main code | — | (Cached but unused) | — |
| **get_c()** | generate_ne.py | 71 | Constraint assumptions | Via oracle model (internal) |
| **get_kb()** | generate_ne.py | 95 | Merge oracle KB | Via oracle model (internal) |
| **get_assumptions()** | generate_ne.py | 96 | Merge assumptions | Via oracle model (internal) |
| **get_raw_fm_clauses()** | — | — | (internal only) | — |

---

## Caller Dependency Map

### acqmss/example_generators/
- **base.py**: Lines 34–35, 55, 77
  - Calls: `get_features()`, `get_feature_ids()`, `is_valid()`, `complete_configuration()`
  - Purpose: Init, feature iteration, classification, config generation

- **random_sampling.py**: Line 266 (and earlier init)
  - Calls: `get_features()`, `is_valid()`
  - Purpose: Negative example generation

- **feature_frequency.py**: Init + lines 111, 198, 200
  - Calls: `get_features()`, `get_feature_ids()`, `is_valid()`, `complete_configuration()`
  - Purpose: Biased invalid/valid example generation

**Alternative source**: All could get `get_features()` and `get_feature_ids()` from `model.variables` (once) rather than oracle.

### acqmss/algorithms/interactive/
- **learner.py**: Lines 156, 160, 213
  - Calls: `get_feature_ids()`, `get_root_feature()`, `get_cnf_clauses()`
  - Purpose: Task initialization, root feature extraction, FM clause caching

- **quacq.py**: Line 76
  - Calls: `ask()` (alias for `is_valid()`)
  - Purpose: Query oracle during learning

**Note**: `get_feature_ids()` and `get_cnf_clauses()` could come from model once (passed in).

### acqmss/algorithms/
- **task_preparation.py**: Lines 113–114
  - Calls: `get_root_feature()`, `get_num_constraints()`
  - Purpose: Extract FM metadata for task setup

- **generate_ne.py**: Lines 71, 95–96
  - Calls: `get_c()`, `get_kb()`, `get_assumptions()`
  - Purpose: Merge oracle KB with result KB for QuickXPlain

**Note**: `generate_ne.py` uses internal oracle methods (`get_kb()`, etc.)—tight coupling to oracle model internals.

### acqmss/bias/
- **bias_generator.py**: Line 43
  - Calls: `config.get_feature_ids()` (on BiasConfig, NOT oracle)
  - Purpose: Setup bias generator

### apps/
- **generate_examples.py**: Line 143
  - Calls: `get_features()` (via `.len()`)
  - Purpose: Report feature count

- **generate_bias_config.py**: Lines 244–245, 262, 404
  - Calls: `fm.get_features()`, `fm.get_constraints()` (on Flamapy FM, NOT oracle)
  - Purpose: Extract FM metadata

### tests/
- **test_interactive.py**: Lines 52, 190, 202, 204, 215–217, 223–224, 323–324, 337–339
  - Calls: `get_feature_ids()`, `get_feature_count()`, `get_features()`, `ask()`, `get_root_feature()`
  - Purpose: Fixture setup, validation tests, root feature verification

- **test_congen.py**: Lines 70, 308
  - Calls: `get_root_feature()`, `get_feature_ids()`
  - Purpose: Root propagation tests, ID verification

- **test_diagnosis.py**: Lines 210, 250, 274, etc.
  - Calls: `model.get_kb()`, `model.get_assumptions()`, `model.get_c()`, etc.
  - Purpose: Model-level tests (uses model, not oracle directly)

---

## Three Distinct Usage Patterns

### Pattern A: Example Generation (High-frequency, hot path)
**Files**: `base.py`, `random_sampling.py`, `feature_frequency.py`
**Methods**: `get_features()`, `get_feature_ids()`, `is_valid()`, `complete_configuration()`
**Impact**: ~40% of oracle calls; performance-critical
**Coupling**: Loose—passes oracle to generator; can be abstracted

### Pattern B: Learning Task Setup (Medium-frequency, init phase)
**Files**: `learner.py`, `task_preparation.py`, `test_congen.py`
**Methods**: `get_feature_ids()`, `get_root_feature()`, `get_num_constraints()`, `get_cnf_clauses()`
**Impact**: ~30% of oracle calls; executed once per model
**Coupling**: Moderate—direct oracle method calls; tightly bound to FeatureModelOracle

### Pattern C: NE Generation & Diagnosis (Low-frequency, computation phase)
**Files**: `generate_ne.py`, `quacq.py`
**Methods**: `get_c()`, `get_kb()`, `get_assumptions()`, `ask()`
**Impact**: ~20% of oracle calls; invoked per constraint search
**Coupling**: **Tight**—uses internal `_oracle_model` fields; breaks encapsulation

---

## Data Flow Diagram

```
Oracle (ABC)
├── get_features() ──> Example Generators
├── get_feature_ids() ──> Generators, Learner, Task Setup
├── is_valid() ──> Generators, QuAcq
├── complete_configuration() ──> Generators
├── get_cnf_clauses() ──> Learner (for evaluation)
├── get_root_feature() ──> Learner, Task Setup
├── get_num_constraints() ──> Task Setup
└── [FM-specific internals]
    ├── get_c() ──> GenerateNE (for QuickXPlain)
    ├── get_kb() ──> GenerateNE (for KB merge)
    └── get_assumptions() ──> GenerateNE (for assumptions merge)
```

---

## Unresolved Questions

1. **Why does `get_constraint_descriptions()` exist in `FeatureModelOracle` but is never called?** (Cached, unused)
2. **Should `get_c()`, `get_kb()`, `get_assumptions()` be in the abstract Oracle ABC?** (Currently FeatureModelOracle-only, used internally by GenerateNE)
3. **Is GenerateNE supposed to be internal to oracle or a separate algorithm?** (Currently tight coupling via `self.oracle.get_c()`)
4. **Can BiasConfig be unified with Oracle for feature ID access?** (Currently separate paths)
5. **Should task preparation data (root, num_constraints) be pre-computed and passed in?** (Currently queried from oracle on-demand)
