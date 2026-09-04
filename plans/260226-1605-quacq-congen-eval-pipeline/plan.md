---
title: "QuAcq->ConGen Evaluation Pipeline"
description: "Evaluation proving ConGen learns better KB from QuAcq-generated queries via progressive analysis"
status: pending
priority: P1
effort: 6h
branch: main
tags: [evaluation, quacq, congen, comparison, progressive]
created: 2026-02-26
---

# QuAcq -> ConGen Evaluation Pipeline

## Goal

Prove ConGen extracts more knowledge from the same oracle query budget as QuAcq. Pipeline: run QuAcq (automated) -> collect query history -> feed subsets to ConGen at checkpoints -> compare both KBs against ground truth C_T using structural + semantic equivalence.

## Phases

| # | Phase | File | Status | Effort |
|---|-------|------|--------|--------|
| 1 | Expose Query History + Converter | [phase-01](phase-01-query-history-converter.md) | pending | 1h |
| 2 | Semantic Equivalence Check | [phase-02](phase-02-semantic-equivalence.md) | pending | 2h |
| 3 | Progressive Evaluation Engine | [phase-03](phase-03-progressive-evaluation.md) | pending | 1.5h |
| 4 | Evaluation Script + Config | [phase-04](phase-04-evaluation-script.md) | pending | 1.5h |

## Dependencies

- Phase 1 must complete before Phase 3 (converter needed for progressive eval)
- Phase 2 must complete before Phase 3 (semantic check used at each checkpoint)
- Phases 1 and 2 are independent (can parallelize)
- Phase 4 depends on all prior phases

## Architecture

```
FM (.uvl) + Bias (.json)
     |
     +---> InteractiveRunner(mode='automated') ---> InteractiveRunResult
     |         |                                        |
     |         +--- query_history [Phase 1]             +--- kb_clauses (QuAcq final)
     |                   |
     |       For each checkpoint N%:
     |                   |
     |          queries[:N] ---> queries_to_examples() [Phase 1]
     |                               |
     |                          E+, E- subsets
     |                               |
     +---> ConGenRunner.run(E+, E-) ---> ConGenRunResult
                                              |
                                         kb_clauses (ConGen at N)
                                              |
              KBComparator.compare() [description + clause]
              SemanticEquivalenceChecker.check() [Phase 2]
                                              |
                                    ProgressiveResult [Phase 3]
                                              |
                                    JSON output [Phase 4]
```

## Key Files (New)

| File | Phase | ~Lines |
|------|-------|--------|
| `conacq/examples/query_converter.py` | 1 | 50 |
| `conacq/eval/semantic_equivalence.py` | 2 | 100 |
| `conacq/eval/progressive_evaluation.py` | 3 | 150 |
| `apps/run_evaluation.py` | 4 | 150 |
| `apps/conf/run_evaluation_config.toml` | 4 | 30 |

## Key Files (Modified)

| File | Phase | Change |
|------|-------|--------|
| `conacq/runners/interactive_runner.py` | 1 | Add `query_history` field to `InteractiveRunResult` + propagate |
| `conacq/eval/kb_comparator.py` | 2 | Add `SEMANTIC` strategy enum value |
| `conacq/eval/__init__.py` | 2,3 | Export new modules |

## Research

- [Query Flow Research](research/researcher-01-query-flow.md)
- [Comparator/SAT Research](research/researcher-02-comparator-sat.md)
- [Brainstorm](../reports/brainstorm-260226-1605-quacq-congen-evaluation-pipeline.md)

## Key Files (Modified) — Updated

| File | Phase | Change |
|------|-------|--------|
| `conacq/runners/interactive_runner.py` | 1 | Add `query_history` field to `InteractiveRunResult` + propagate |
| `conacq/algorithms/interactive/task.py` | 1 | Add `source` param to `record_query()` |
| `conacq/algorithms/interactive/quacq.py` | 1 | Pass `source='main'` at main loop call |
| `conacq/algorithms/interactive/findc.py` | 1 | Pass `source='findc'` at FindC calls |
| `conacq/eval/kb_comparator.py` | 2 | Add `SEMANTIC` strategy enum value |
| `conacq/eval/__init__.py` | 2,3 | Export new modules |

## Success Criteria

ConGen demonstrates ANY of:
1. Higher precision/recall at same query budget
2. Faster convergence (near-equivalence at fewer queries)
3. Better semantic equivalence (KB_congen equiv C_T while KB_quacq subset C_T)
4. Smaller KB with same or better coverage

## Validation Log

### Session 1 — 2026-02-26
**Trigger:** Initial plan creation validation
**Questions asked:** 6

#### Questions & Answers

1. **[Scope]** Phase 1 notes that `query_history` contains ALL queries from FindC sub-routine and main QuAcq loop. FindC creates discriminating queries (possibly partial). How to filter for ConGen input?
   - Options: All queries (no filter) | Filter: only complete configs | Tag source in history
   - **Answer:** Only main_loop queries
   - **Custom input:** "chỉ lấy queries ở main_loop"
   - **Rationale:** ConGen should receive only the strategically-generated top-level queries, not FindC discriminating sub-queries which are partial and serve a different purpose.

2. **[Architecture]** Phase 2 semantic equivalence: BG clauses present in both KB and C_T. Should BG be excluded from entailment target to avoid false negatives?
   - Options: Include BG in source only (Recommended) | Include BG both sides | Exclude BG entirely
   - **Answer:** Include BG in source only
   - **Rationale:** KB⊨C_T: check SAT(KB+BG+¬c). C_T⊨KB: check SAT(C_T+¬c) but only check KB clauses (exclude BG from target). Cleanest approach avoids double-counting.

3. **[Risk]** Phase 3: Small checkpoints may yield only positive or only negative queries. ConGen needs both E+ and E-. Skip or run anyway?
   - Options: Skip + log warning (Recommended) | Require minimum examples | Always run, let ConGen handle
   - **Answer:** Always run, let ConGen handle
   - **Rationale:** Even edge case results are valid data points for the learning curve.

4. **[Scope]** Phase 4 output: Besides JSON, need additional formats for paper analysis?
   - Options: JSON only (extend later) | JSON + CSV summary | JSON + LaTeX table
   - **Answer:** JSON only (extend later)
   - **Rationale:** Keep scope minimal. Visualization scripts can be added separately.

5. **[Architecture]** Mechanism to distinguish main_loop vs FindC queries in query_history?
   - Options: Separate list in InteractiveTask | Tag source in record_query() | Record only in main loop
   - **Answer:** Tag source in record_query()
   - **Custom input:** Add `source='main'|'findc'` param to `record_query()`
   - **Rationale:** Preserves all data for future analysis while enabling filtering at conversion time.

6. **[Assumptions]** ConGen with empty E-: User corrected assumption that AcqMSS returns full bias with empty set_neg_tv.
   - Options: Yes always run | Skip if E- empty | Require min 1 of each
   - **Answer:** Always run — AcqMSS works correctly with empty E-
   - **Custom input:** "kiểm tra lại AcqMSS, nó phải hoạt động ngay cả khi set_neg_tv là empty và lúc đó kết quả phụ thuộc vào E+, không thể nào trả về toàn bộ bias được"
   - **Rationale:** AcqMSS depends on E+ to filter bias even without E-. Result is valid.

#### Confirmed Decisions
- Query source tagging: `record_query(config, answer, source)` — filter `source='main'` for ConGen
- BG in semantic: include as source-side only, exclude from entailment targets
- Empty examples: always run ConGen, no skipping
- Output: JSON only for now

#### Action Items
- [ ] Phase 1: Add `source` param to `record_query()` in `task.py`
- [ ] Phase 1: Update `quacq.py` main loop call with `source='main'`
- [ ] Phase 1: Update `findc.py` calls with `source='findc'`
- [ ] Phase 1: Filter by `source='main'` in `queries_to_examples()` / `queries_to_assignment_lists()`
- [ ] Phase 2: BG only in source formula, not in target clauses for entailment check
- [ ] Phase 3: Remove "skip if empty" guards — always run ConGen

#### Impact on Phases
- Phase 1: Add source tagging to `record_query()`, update callers, filter in converter
- Phase 2: Clarify BG handling in `_check_entails()` — add BG to source only
- Phase 3: Remove skip-on-empty logic, always run checkpoint
