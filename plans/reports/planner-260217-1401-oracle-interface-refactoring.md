# Planner Report: Oracle Interface Refactoring

**Date:** 2026-02-17
**Plan:** `/Users/manleviet/Development/GitHub/AcqMSS/plans/260217-1358-oracle-interface-refactoring/`

## Summary

Created 7-phase implementation plan to slim Oracle ABC to core membership query (`is_valid`/`ask` only) and extract all non-Oracle concerns (FM metadata, SAT capabilities, ground truth data).

## Key Design Decisions

1. **FMData frozen dataclass** (`acqmss/oracle/fm_data.py`) — holds features, feature_ids, root_feature, num_constraints, next_tseitin_var. Created from FeatureModelOracle via `get_fm_data()`.
2. **complete_configuration stays on FeatureModelOracle** as concrete method — callers already know the type.
3. **GenerateNE decoupled** — receives oracle KB/assumptions/set_c as explicit params. Zero oracle import.
4. **OracleData renamed to GroundTruthData** — reads FM directly via UVLReader+FmToDiagPysat (no solver instantiation).

## Phase Summary

| Phase | Effort | Description |
|-------|--------|-------------|
| 1 | 1.5h | Slim Oracle ABC, create FMData dataclass |
| 2 | 1h | Refactor ExampleGenerator (type FeatureModelOracle, use FMData) |
| 3 | 1.5h | Refactor InteractiveLearner + ConGenTaskPreparation (FMData for metadata) |
| 4 | 1h | Refactor GenerateNE (explicit params, no oracle dependency) |
| 5 | 1h | OracleData → GroundTruthData (direct FM reading) |
| 6 | 1h | Clean up FeatureModelOracle + wrappers (remove dead code) |
| 7 | 1h | Update tests (fix broken calls, add FMData tests) |
| **Total** | **8h** | |

## Files Affected

### Created (1 file)
- `acqmss/oracle/fm_data.py` — FMData frozen dataclass

### Modified (13 files)
- `acqmss/oracle/base.py` — slim to 1 abstract method
- `acqmss/oracle/fm_oracle.py` — add get_fm_data(), update __repr__
- `acqmss/oracle/user_prompt.py` — remove non-Oracle methods
- `acqmss/oracle/cached.py` — remove delegated non-Oracle methods
- `acqmss/oracle/extractor.py` — OracleData → GroundTruthData, direct FM reading
- `acqmss/oracle/__init__.py` — update exports
- `acqmss/example_generators/base.py` — type to FeatureModelOracle, use FMData
- `acqmss/algorithms/interactive/learner.py` — FMData in _build_task_from_bias
- `acqmss/algorithms/task_preparation.py` — FMData param for metadata
- `acqmss/algorithms/generate_ne.py` — remove oracle, explicit params
- `acqmss/algorithms/congen_model.py` — create FMData, pass through
- `acqmss/eval/evaluator.py` — GroundTruthData import
- `acqmss/eval/__init__.py` — GroundTruthData export

### Tests Modified (3 files)
- `tests/test_interactive.py` — fix get_feature_count, CachedOracle tests
- `tests/test_congen.py` — minimal updates
- `tests/test_evaluation.py` — OracleData → GroundTruthData

## Dependency Order
Phases 2-4 depend on Phase 1. Phase 5 independent. Phase 6 after 1-5. Phase 7 last.

## Unresolved Questions
1. Should CachedOracle be removed entirely? (Currently kept — still caches is_valid)
2. Should `get_leaf_features()` be removed? (Needs grep verification — likely dead code)
3. `get_constraint_descriptions()` has a lazy FM load (`self.fm` property) — if kept, the lazy load stays. If only GroundTruthData.from_uvl() is used, both can be removed.
