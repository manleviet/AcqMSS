# Brainstorm: QuAcq → ConGen Evaluation Pipeline

**Date**: 2026-02-26
**Status**: Agreed
**Goal**: Design evaluation proving ConGen learns better KB from QuAcq-generated queries

---

## Problem Statement

Current evaluation uses shared n-fold CV (same E+/E- splits). This compares algorithms on **identical data**.
New approach: use QuAcq's own **strategically generated queries** as ConGen's training data — proving ConGen extracts more information from same oracle budget.

## Agreed Design

### Pipeline

```
FM model (.uvl)
     │
     ├──► QuAcq (automated, FM oracle) → until convergence
     │         │
     │         ├──► Learned KB_quacq (final)
     │         └──► query_history [(config, yes/no), ...]
     │                    │
     │              For each checkpoint N:
     │                    │
     │                    ▼
     │              queries[:N] → yes→E+, no→E-
     │                    │
     │                    ▼
     ├──► ConGen(E+, E-) ──► KB_congen_at_N
     │
     ├──► GroundTruthData.from_uvl() ──► C_T
     │
     └──► Compare at each checkpoint:
           ├── KB_quacq_final vs C_T
           └── KB_congen_at_N vs C_T
```

### Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| QuAcq mode | Automated (FM oracle) | Reproducible, no human |
| Query type saved | Complete configs only | Main loop queries, not FindScope partials |
| Query → examples | yes→E+, no→E- | Direct mapping |
| Comparison | vs groundtruth (no CV) | Single-run, direct C_T comparison |
| Groundtruth metrics | Constraint set (desc+clause) + Semantic equivalence | Both structural and logical |
| Semantic check | Both directions (KB⊨C_T AND C_T⊨KB) | Full equivalence |
| Progressive analysis | ConGen at multiple N (query budget checkpoints) | Learning curve visualization |
| FM count | Configurable (1 or many) | TOML config driven |

### Progressive Analysis Design

**Checkpoints**: Run ConGen at query counts like [10%, 25%, 50%, 75%, 100%] of total QuAcq queries.

At each checkpoint N:
1. Slice `query_history[:N]`
2. Split: yes-answers → E+, no-answers → E-
3. Run ConGen(E+, E-) → KB_congen_at_N
4. Compare KB_congen_at_N vs C_T

QuAcq comparison: only **final KB** (intermediate snapshots not currently tracked — possible future enhancement).

**Expected result**: ConGen reaches near-equivalence with C_T at N << total_queries, while QuAcq's final KB may still miss constraints. This proves ConGen's superior information extraction.

## Existing Infrastructure

| Component | Status | File |
|---|---|---|
| `GroundTruthData.from_uvl()` | ✅ Exists | `conacq/oracle/ground_truth.py` |
| `KBComparator` (desc+clause) | ✅ Exists | `conacq/eval/kb_comparator.py` |
| `InteractiveRunner` (automated) | ✅ Exists | `conacq/runners/interactive_runner.py` |
| `ConGenRunner` | ✅ Exists | `conacq/runners/congen_runner.py` |
| `ExampleSet/Example` | ✅ Exists | `conacq/examples/data_structures.py` |
| `InteractiveTask.query_history` | ✅ Exists | Stores (config, oracle_answer) |
| Query export → ExampleSet | ❌ New | Utility to convert queries to E+/E- |
| query_history in RunResult | ❌ New | Expose queries from InteractiveRunResult |
| Semantic equivalence check | ❌ New | SAT-based entailment both directions |
| Progressive evaluation | ❌ New | Loop over checkpoints + ConGen |
| Evaluation script | ❌ New | Orchestrate full pipeline |
| TOML config | ❌ New | Configure FM paths, checkpoints, etc. |

## What Needs Building

### 1. Expose query_history from InteractiveRunner
- Add `query_history: List[Tuple[Dict[str, bool], bool]]` to `InteractiveRunResult`
- Extract from `learner.task.query_history` after run completes

### 2. Query → ExampleSet Converter
- New utility: `queries_to_examples(query_history) -> ExampleSet`
- yes-answers → `Example(type=POSITIVE)`
- no-answers → `Example(type=NEGATIVE)`

### 3. Semantic Equivalence Check
- New method in `KBComparator` or standalone module
- **KB ⊨ C_T**: For each constraint c in C_T, check `SAT(KB ∪ ¬c)`. If UNSAT → KB entails c.
- **C_T ⊨ KB**: For each constraint c in KB, check `SAT(C_T ∪ ¬c)`. If UNSAT → C_T entails c.
- Full equivalence: both directions hold for all constraints.

### 4. Progressive Evaluation Loop
- Configure checkpoints (percentages or absolute counts)
- For each checkpoint: slice queries → run ConGen → compare
- Collect results into learning curve data

### 5. Evaluation Script (`apps/run_evaluation.py` or similar)
- Load FM, bias, oracle from TOML config
- Run QuAcq automated → collect queries
- Progressive ConGen evaluation
- Compare all KBs vs groundtruth
- Output: JSON results + summary table

### 6. TOML Configuration
```toml
[evaluation]
fm_path = "data/fms/model.uvl"
bias_path = "data/bias/model.json"
checkpoints = [10, 25, 50, 75, 100]  # percentages
output_dir = "data/results/evaluation/"

[quacq]
mode = "automated"
shuffle_seed = 42

[comparison]
strategies = ["description", "clause", "semantic"]
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| QuAcq many queries → ConGen slow | High | Progressive analysis limits per-run examples; optional budget cap |
| Too few "no" answers | Medium | QuAcq typically gets many "no" (each finds 1 constraint) |
| Semantic check expensive for large FM | Medium | Can run description/clause first, semantic optionally |
| QuAcq doesn't converge | Low | Track convergence_reason; report partial results |

## Success Metrics

The evaluation succeeds if ConGen demonstrates ANY of:
1. **Higher constraint recovery** (precision/recall) at same query budget
2. **Faster convergence** — reaches near-equivalence at fewer queries
3. **Better semantic equivalence** — KB_congen ≡ C_T while KB_quacq ⊊ C_T
4. **Smaller KB** — fewer constraints with same or better coverage

## Next Steps

1. Create implementation plan with phases
2. Phase 1: Expose query_history + query→ExampleSet converter
3. Phase 2: Semantic equivalence check
4. Phase 3: Progressive evaluation loop
5. Phase 4: Evaluation script + TOML config
6. Phase 5: Test on single FM → validate approach

## Unresolved Questions

1. **QuAcq intermediate KB tracking**: Currently only final KB available. Progressive QuAcq KB comparison would require either (a) modifying QuAcq to save snapshots, or (b) tracking constraint addition order. Defer to future enhancement?
2. **Checkpoint granularity**: Fixed percentages [10,25,50,75,100] or adaptive (e.g., every 10 queries)?
3. **Multiple FM batch**: How to aggregate results across FMs? Average learning curves? Per-FM reports?
