# Deep Analysis: Oracle Module Classes

## Executive Summary

Three Oracle classes analyzed: **FeatureModelOracle**, **FMOracleModel**, **OracleTaskPreparation**. Found significant dead code, coupling issues, SRP violations, and performance inefficiencies suitable for optimization.

---

## Class Breakdown

### 1. FeatureModelOracle (fm_oracle.py:16-333)

**Dead Code (57 lines)**:
- Lines 59-77: Large commented block implementing old CNF/feature_ids approach (superseded by FMOracleModel)
- Lines 79-116: 38 unused method stubs (_extract_features, _build_cnf, _extract_leaf_features, etc.)
- Line 168-189: Commented get_valid_configuration method

**Key Issues**:
- **Circular responsibility**: Loads FM twice (line 57 for constraint extraction, implicit via FMOracleModel.build())
- **Tight coupling to FMOracleModel internals**: Lines 143, 152 directly access _oracle_model.variables, _oracle_model.task
- **SRP violation**: Handles both oracle interface + FM parsing + CTC description extraction (3 concerns)
- **Lazy CTX parsing**: _parse_ctc_to_description (lines 239-307) imported inside method (2 imports), called per-constraint
- **Redundant getters**: get_c(), get_kb(), get_assumptions() (lines 121-131) just delegate to _oracle_model.task

**Performance**:
- Lines 216-229: O(n) full FM traversal per get_constraint_descriptions() call (no caching)
- CTC parsing with nested AST checks (lines 253-307) could be slow for large feature models

### 2. FMOracleModel (fm_oracle_model.py:18-176)

**Issues**:
- **Unused dict**: negated_constraint_map (line 36) created in build() but never read after assignment
- **Coupling**: with_configuration (lines 105-130) tightly coupled to assumption structure, duplicates set_c computation logic
- **DRY violation**: Lines 126-127 duplicate DiagnosisTask set_c logic (same as OracleTaskPreparation line 233)
- **Incomplete builder**: set_incremental() returns self but forces build() later (lines 78-81, 160-176)
- **State inconsistency**: _task only populated after prepare() (lines 56-60) but prepare() called in build(), not constructor

**Design Problem**: Model acts as both config holder AND task builder—two responsibilities.

### 3. OracleTaskPreparation (fm_oracle_model.py:180-238)

**Issues**:
- **DRY**: Step numbering (lines 198, 202, 231) inconsistent ("Step 1/2/4" = missing 3)
- **Duplicate logic**: Lines 203-233 mirror exact assumption-to-description mapping as FeatureModelOracle internals
- **Unclear naming**: pos_assignment_to_assumption vs _pos_assignment_to_assumption (inconsistent underscoring)
- **Magic numbers**: Line 226 hardcoded step=2 (assumes pairs of pos/neg assumptions)
- **Hidden coupling**: Stores results directly into model instance (lines 228-229) rather than returning

---

## Key Findings

| Category | Issue | Impact |
|----------|-------|--------|
| **Dead Code** | ~100 lines commented code in FeatureModelOracle | Maintenance burden, confusion |
| **Coupling** | FeatureModelOracle → FMOracleModel internals | Hard to refactor, test independently |
| **DRY** | with_configuration() + OracleTaskPreparation both compute set_c | Risk of inconsistency |
| **SRP** | FeatureModelOracle handles 3 concerns | High cognitive load, hard to extend |
| **Performance** | get_constraint_descriptions() O(n) no cache | Slow for large FMs with repeated calls |
| **State** | FMOracleModel._task only valid after prepare() | Runtime errors if misused |

---

## Optimization Priorities

**High Impact**:
1. Remove 100+ lines dead code (cleanup + test)
2. Extract CTC parsing to dedicated class (reduce FeatureModelOracle scope)
3. Cache constraint descriptions (prevent O(n) re-parsing)

**Medium Impact**:
4. Decouple FeatureModelOracle from FMOracleModel internals (interface-based delegation)
5. Move with_configuration logic to OracleTaskPreparation or dedicated class
6. Consolidate set_c computation (1 source of truth)

**Low Impact**:
7. Remove negated_constraint_map if unused after optimization #1
8. Replace magic number 2 with named constant
9. Add prepare() state guard with clear error messages

---

## Unresolved Questions

- Is negated_constraint_map ever used elsewhere in codebase for bias constraint handling?
- Should get_constraint_descriptions() support filtering/caching strategy?
- Would constraint description extraction be better as external service?
