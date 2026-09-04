# FM Reading & Data Flow: Duplication Analysis

## Executive Summary

FM reading logic is **partially duplicated** across 3 primary layers, each reading/transforming FM differently. Core duplication center: **UVLReader invocations** (6 independent calls) and **CNF transformation** (2 separate paths). No "bad" duplication—each layer justified—but consolidation points exist.

## FM Reading Locations

### Layer 1: Bias Generation (apps/generate_bias_config.py)
- **When**: Offline, one-time generation of bias constraints
- **What**: Extracts hierarchical candidates, cross-tree features, leaf features
- **How**: `UVLReader(fm_path).transform()` → Direct flamapy FeatureModel API
- **Returns**: Structured YAML bias config (hierarchical_candidates, cross_tree_features)
- **DRY Score**: 🔴 Independent FM reading (duplication #1)

### Layer 2: Oracle Stack (acqmss/oracle/)
**Two parallel read paths:**

#### Path 2a: FeatureModelOracle (fm_oracle.py)
- **When**: Runtime validation during learning
- **What**: Loads FM once, delegates to FMOracleModel for CNF conversion
- **Flow**:
  1. `FMOracleModel.from_fm(path)` → stores path
  2. `.build()` → `UVLReader(path).transform()` + `FmToDiagPysat` → CNF
  3. Creates CheckerFactory-compatible model with set_kb + assumptions
- **Returns**: CheckerModel protocol (get_kb(), get_assumptions(), get_c())
- **Lazy FM loading**: `.fm` property loads raw FM for description extraction (cached)
- **DRY Score**: 🟠 Independent UVL read in build() (duplication #2)

#### Path 2b: OracleData.from_uvl() (extractor.py)
- **When**: Evaluation, batch comparison
- **What**: Extracts descriptions + CNF clauses for evaluation metrics
- **Flow**:
  1. Creates FeatureModelOracle(str(path)) → triggers full FM read + CNF conversion
  2. Extracts: descriptions, clauses, feature_map, root_feature
  3. Cleans up oracle
- **Returns**: Dataclass with descriptions, clauses, feature_map
- **DRY Score**: 🟠 Reuses FeatureModelOracle but requires instantiation overhead (duplication #3)

### Layer 3: Explanation (explanation/)
**Diagnosis model FM reading:**

#### Path 3a: DiagnosisModelBuilder.from_uvl()
- **When**: Diagnosis algorithms, testing
- **What**: Creates DiagnosisModel (not CheckerModel) for SAT-based diagnosis
- **Flow**:
  1. `UVLReader(path).transform()` → flamapy FeatureModel
  2. `FmToDiagPysat(fm, create_negation=needs_negation).transform()` → DiagnosisModel
  3. Returns model with constraint_map, negated_constraint_map, variables
- **Returns**: DiagnosisModel (different API than FMOracleModel)
- **DRY Score**: 🔴 Independent UVL read + separate FmToDiagPysat call (duplication #4)

#### Path 3b: FmToDiagPysat (fm_to_diag_pysat.py)
- **When**: Transforms raw FeatureModel to SAT CNF
- **What**: Converts relations + constraints → clauses + negated forms (Tseitin)
- **Shared Logic**: Inherits from flamapy's FmToPysat
- **Returns**: DiagnosisModel with constraint_map, negated_constraint_map, next_tseitin_var

### Constraint Description Extraction (acqmss/oracle/constraint_description.py)
- **Function**: `extract_constraint_descriptions(fm)`
- **Called by**: FeatureModelOracle.get_constraint_descriptions()
- **What**: Parses hierarchical relations + CTCs → human-readable strings
- **Patterns recognized**: requires, excludes, alternative, or, mandatory, optional
- **DRY Score**: 🟢 Centralized, single call site

## Data Flow Diagram

```
.uvl file
    ↓
UVLReader (6 independent calls)
    ├─→ [1] generate_bias_config.py (standalone)
    ├─→ [2] fm_oracle_model.py.build()
    ├─→ [3] test_congen.py, test_interactive.py (tests)
    ├─→ [4] test_diagnosis.py (tests)
    └─→ [5] diagnosis_model_builder.py.from_uvl()

flamapy FeatureModel object
    ├─→ FmToDiagPysat (2 callers)
    │   ├─→ [A] FMOracleModel.build() → constraint_map + variables
    │   └─→ [B] DiagnosisModelBuilder.from_uvl() → constraint_map
    │
    ├─→ constraint_description extraction (1 caller)
    │   └─→ FeatureModelOracle.get_constraint_descriptions()
    │
    └─→ Direct flamapy API calls (3 callers)
        ├─→ generate_bias_config.py (fm.get_features(), fm.get_relations(), etc.)
        ├─→ FeatureModelOracle lazy .fm property
        └─→ test_* files
```

## Duplication Map

| Logic | Location A | Location B | Impact | Recommendation |
|-------|-----------|-----------|--------|-----------------|
| **UVLReader invocation** | fm_oracle_model.build() | diagnosis_model_builder.from_uvl() | 2 independent file reads | **Share**: Extract FMFileLoader utility |
| **UVLReader (bias)** | generate_bias_config.py | (standalone) | Separate workflow | **Keep separate**: One-time offline script |
| **FmToDiagPysat call** | FMOracleModel.build() | DiagnosisModelBuilder.from_uvl() | Different return types (CheckerModel vs DiagnosisModel) | **Keep separate**: Different purposes, incompatible interfaces |
| **Constraint map building** | FmToDiagPysat.transform() | (single source) | Central, no duplication | **Already DRY** |
| **Negated form creation** | FmToDiagPysat._create_negated_forms() | (single source) | Central via Tseitin transform | **Already DRY** |
| **Feature ID mapping** | constraint_description.py | fm_oracle.py.get_root_feature() | Both query flamapy API | **Keep separate**: Different purposes |
| **Constraint descriptions** | extract_constraint_descriptions() | (single caller) | Centralized | **Already DRY**: Factory pattern handles both |
| **OracleData creation** | OracleData.from_uvl() | OracleData.from_oracle() | Two entry points, same extraction | **Already DRY**: Factory pattern handles both |

## Identified Pain Points

1. **6 independent UVLReader calls**: 2 in runtime paths (fm_oracle_model, diagnosis_model_builder), 4 in tests
   - **Problem**: Each re-reads file, no reuse
   - **Severity**: Low (only once per application lifecycle)
   - **Solution**: Extract FMFileCache utility (lazy singleton pattern)

2. **Two CheckerModel builders** (FMOracleModel vs OneShotModel)
   - **Problem**: Similar structures, different semantics
   - **Severity**: Low (rare to build OneShotModel)
   - **Solution**: Justify separation in codebase comments (KISS: simpler than unifying)

3. **OracleData + FeatureModelOracle dual API**
   - **Problem**: OracleData.from_uvl() wraps FeatureModelOracle instantiation
   - **Severity**: Medium (evaluation code creates oracle just for extraction)
   - **Solution**: Add OracleData.extract_direct(path) static method to skip oracle overhead

4. **Feature extraction scattered**
   - `get_leaf_features()` (fm_oracle.py)
   - `extract_leaf_features()` (generate_bias_config.py)
   - Both call flamapy API, same logic
   - **Severity**: Low (small functions, clear intent)
   - **Solution**: Consolidate in shared utilities module

## Data Flow Summary

1. **Offline (one-time)**: generate_bias_config.py reads FM → extracts bias → YAML
2. **Runtime (many times per app instance)**:
   - FeatureModelOracle reads FM → FmToDiagPysat → CNF clauses + assumptions
   - CheckerFactory creates solver from model → consistent validation
3. **Evaluation**: OracleData reads via FeatureModelOracle → comparison metrics
4. **Testing/Diagnosis**: DiagnosisModelBuilder reads FM → separate DiagnosisModel for algorithms

## Unresolved Questions

1. Should OracleData cache extracted data to avoid re-reading same file multiple times in eval runs?
2. Is FMFileCache utility worth ~50 lines of code vs. current duplication overhead?
3. Should constraint_description extraction be moved to FmToDiagPysat output (store descriptions in constraint_map)?
