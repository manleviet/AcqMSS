# Planner Report: QuAcq->ConGen Evaluation Pipeline

**Date**: 2026-02-26
**Plan**: `plans/260226-1605-quacq-congen-eval-pipeline/`

## Summary

Created 4-phase implementation plan for evaluation pipeline proving ConGen learns better KB from QuAcq-generated queries. Total estimated effort: 6h.

## Phases

| Phase | Description | Effort | Dependencies |
|-------|-------------|--------|--------------|
| 1 | Expose query_history + converter utility | 1h | None |
| 2 | SAT-based semantic equivalence checker | 2h | None |
| 3 | Progressive evaluation engine | 1.5h | Phase 1, 2 |
| 4 | Evaluation script + TOML config | 1.5h | Phase 1, 2, 3 |

## New Files (5)

- `conacq/examples/query_converter.py` — query history -> ExampleSet converter
- `conacq/eval/semantic_equivalence.py` — bidirectional SAT entailment checker
- `conacq/eval/progressive_evaluation.py` — checkpoint-based ConGen evaluation loop
- `apps/run_evaluation.py` — orchestration script
- `apps/conf/run_evaluation_config.toml` — example config

## Modified Files (3)

- `conacq/runners/interactive_runner.py` — add `query_history` field to `InteractiveRunResult`
- `conacq/eval/kb_comparator.py` — add `SEMANTIC` strategy
- `conacq/eval/__init__.py` — export new modules

## Key Design Decisions

1. **Direct PySAT Solver** for semantic checks (not `IncrementalPySATChecker`) — simpler, context-managed, no checker model overhead
2. **Reuse ConGenRunner** across checkpoints (it already supports repeated `run()` calls with different examples)
3. **Bridge helper** `ConGenResultData` from run results — avoids changing `KBComparator.compare()` signature
4. **Percentage-based checkpoints** — flexible, config-driven, handles variable query counts

## Parallelization Opportunity

Phases 1 and 2 are independent — can be implemented in parallel by separate agents.

## Files Created

- `plans/260226-1605-quacq-congen-eval-pipeline/plan.md`
- `plans/260226-1605-quacq-congen-eval-pipeline/phase-01-query-history-converter.md`
- `plans/260226-1605-quacq-congen-eval-pipeline/phase-02-semantic-equivalence.md`
- `plans/260226-1605-quacq-congen-eval-pipeline/phase-03-progressive-evaluation.md`
- `plans/260226-1605-quacq-congen-eval-pipeline/phase-04-evaluation-script.md`
