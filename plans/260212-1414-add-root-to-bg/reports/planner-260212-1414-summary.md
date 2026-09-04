# Plan Summary: Add Root [1] to Background Knowledge

**Date**: 2026-02-12
**Plan Directory**: `/Users/manleviet/Development/GitHub/AcqMSS/plans/260212-1414-add-root-to-bg/`
**Status**: Ready for implementation

## Problem Statement

Root constraint [1] exists in Oracle CNF but NOT in background knowledge (BG) in either CONGEN or QuAcq pipelines. This causes root to be counted as false negative in clause-based evaluation.

**Root Cause**: CONGENModel and InteractiveLearner bypass DiagnosisModel construction, which normally adds root to set_b. Both explicitly set BG to empty [].

## Solution Architecture

Three-phase implementation to propagate root [1] through both learning pipelines and fix evaluation:

### Phase 1: CONGEN Root Propagation (1.5h)
- Add `root_feature_id: Optional[int]` field to CONGENModel
- Modify `from_bias_and_examples()` to accept root_feature_id parameter
- Update IncrementalCONGENTaskPreparation: add [root_id] to set_b
- Update NonIncrementalCONGENTaskPreparation: add [[root_id]] to set_b
- Modify run_congen.py to extract root and pass to model

**Files**: `model.py`, `task_preparation.py`, `run_congen.py`

### Phase 2: QuAcq Root Propagation (1h)
- Modify `_build_task_from_bias()`: change background=[] to background=[1]
- Modify `from_bias()`: default bg_clauses to [1] if None
- Verify from_files() and from_examples() inherit fix via _build_task_from_bias()

**Files**: `interactive/learner.py`

### Phase 3: Evaluator BG Union (0.5h)
- Add `bg_clauses: List[List[int]]` to CONGENResultData
- Modify `_evaluate_by_clause()`: union kb_clauses with bg_clauses before comparison
- Update CONGEN.acquire() to populate bg_clauses in result
- Update InteractiveLearner.evaluate() to pass BG to evaluator

**Files**: `result_loader.py`, `evaluator.py`, `congen.py`, `interactive/learner.py`

## Key Design Decisions

1. **Backward Compatible**: root_feature_id=None → empty BG (current behavior)
2. **Root ID Extraction**: Use value 1 (default FM root), can enhance with flamapy introspection
3. **BG Format**:
   - Incremental: List[int] = [1]
   - Non-incremental: List[List[int]] = [[[1]]]
4. **Evaluator Access**: Add bg_clauses to CONGENResultData (cleanest, no API change)

## Success Metrics

- All 285 existing tests pass
- REAL-FM-7 clause-based eval: FN for root [1] disappears
- Type checking passes (mypy/pyright)
- set_b/background contains root in debug logs

## Files Modified (7 total)

1. `acqmss/algorithms/model.py` — Add root_feature_id field/param
2. `acqmss/algorithms/task_preparation.py` — Populate set_b with root
3. `apps/run_congen.py` — Extract and pass root_feature_id
4. `acqmss/algorithms/interactive/learner.py` — Set background=[1]
5. `acqmss/eval/result_loader.py` — Add bg_clauses to CONGENResultData
6. `acqmss/eval/evaluator.py` — Union BG in clause comparison
7. `acqmss/algorithms/congen.py` — Populate bg_clauses in result

## Testing Strategy

**Per Phase**:
- Phase 1: `pytest tests/test_congen.py -v`
- Phase 2: `pytest tests/test_interactive.py -v`
- Phase 3: `pytest tests/test_evaluation.py -v`

**Integration**:
- Full suite: `pytest tests/ -v` (all 285 tests)
- Manual: Run REAL-FM-7 with clause eval, verify root [1] in TP not FN

## Risk Mitigation

**Low Risk** overall (backward compatible, optional parameters):
- Root ID hardcoded to 1: Low risk for typical FMs, can enhance if needed
- BG format mismatch: Unit tests will catch immediately
- Missing BG in result: Defaults to [] preserve current behavior

## Implementation Order

Must proceed sequentially (dependencies):
1. Phase 1 first (CONGEN foundation)
2. Phase 2 parallel-eligible after Phase 1 concepts verified
3. Phase 3 last (depends on BG in both pipelines)

## Next Actions

1. Implement Phase 1 (CONGEN)
2. Run test_congen.py, verify set_b in debug logs
3. Implement Phase 2 (QuAcq)
4. Run test_interactive.py, verify background in debug logs
5. Implement Phase 3 (Evaluator)
6. Run full test suite
7. Test on REAL-FM-7, verify clause eval improvement

## References

- Pattern: `explanation/models/task_preparation.py:461-479` (original root handling)
- Oracle: `acqmss/testcases/oracle.py` (feature_ids source of truth)
- DiagnosisModel: Always adds root to set_b in original architecture
