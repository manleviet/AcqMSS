# Red-team review — AcqMSS redesign A+B+C plan

**Date:** 2026-06-21 · **Plan:** `plans/260621-1416-redesign-abc/` · **Branch:** `feat/redesign-abc` · **Baseline:** 352 tests collected
**Method:** 3 hostile reviewers (sequencing / test-safety / regression), each verified findings vs live code. Highest-impact claims re-verified by planner before applying.
**Scope frame:** locked = A+B+C all items, no back-compat, pins frozen, staged green gate, framework isolated in `explanation/`. Reviewers could not recommend cutting scope — only correctness/sequencing/test/regression fixes.

> All actionable findings applied to phase files as `## Red-team adjustments (applied 260621)`. This report = durable record + dispositions.

## Verified-and-applied (CRITICAL/HIGH)

| ID | Sev | Phase | Finding | Disposition |
|----|-----|-------|---------|-------------|
| SEQ-1 | CRIT | A7,A3,B2,C7,C3 | test_diagnosis migration unowned; A3 deletes sat4j classes it imports via `pysat_explanation_builder` → suite red at end of A3 (C7/C3/B2 also touch its symbols) | A7 deferral removed; each diagnosis-touching phase updates test_diagnosis in-stage; pytest migration owned by C7. Verified: test_diagnosis sat4j params :111-152. |
| REG-1 | CRIT | B4 | Map-move off model collides w/ landed `_model_to_config→codec` fix (ordering cycle); `fm_oracle.py` + `test_oracle_model.py` reads omitted | phase-10 file list widened (fm_oracle.py :104/106/178/192, 4 tests, quacq/__init__); structural step + byte-identical assert added. Verified. |
| REG-2 | CRIT/HIGH | A1 | 5th slice site `fm_oracle_model.py:197` (uses `_ASSUMPTION_PAIR_STRIDE`) omitted | added to A1 file list; routed through slicer. Verified. |
| REG-7 | HIGH | C2 | brief's `progressive_evaluation.py:315-325` inline path does not exist | corrected to real sites kb_comparator:163/319, metrics:144, accuracy:117; re-scout mandated. Verified (no `EvaluationMetrics(` in progressive_evaluation). |
| TEST-2/REG-6 | CRIT/HIGH | C2 | 28 field-coupled assertions + `ConGenResultData` force-rewritten; safety-net too weak → silent value drift | frozen-reference-dict pinning + mandatory export byte-compare; importer list widened; keep `BaseRunResult` inheritance; from_json round-trip test. Verified 28 `agg.` refs. |
| REG-4 | HIGH | C7→C2 | twin-merge collapses distinct `@measure_time`/`@count_calls` keys C2 reads by name → zeroed aggregates | C7 must preserve both key sets (param-selected label); C2 pins per-algo metrics. Verified key names. |
| REG-5/REG-3 | HIGH | C7,A1 | wipeoutr_fm vs _t structurally different (for vs while+pop); 4 `_assign_sets` divergent semantics | "behavior-preserving" qualified: keep loop bodies separate if iteration order changes; A1 pins ALL branches/stride modes. Verified bodies. |
| TEST-1 | CRIT | C5 | RNG'd generators have ZERO covering tests; reproducibility test passes by construction | content-pinning safety-net (exact generated set) added before refactor. Verified only QueryProvider tested. |
| SEQ-3 | HIGH | A2 | base location waffly → B1 rework risk | hard requirement: `explanation/models/abstract_model_builder.py` + re-export this phase. |
| SEQ-7 | MED/HIGH | B2 | profiler split must keep `__init__` re-exports (34 sites + 4 tests; AbstractProfiler vs Profiler) | explicit re-export success criterion added. Verified import surface. |
| SEQ-4 | MED | B3 | CachedOracle/UserPromptOracle don't implement get_variables/complete_configuration; existing tests miss it | add delegation + substitutability test; keep get_variables in contract. Verified cached/user_prompt impls. |
| TEST-4/REG-11 | HIGH | A6 | atomic-JSON proven only by manual smoke-run; run_compare is RMW same-file; same-fs temp | automated round-trip + fault-injection test; temp in target dir; build dict before truncate. Verified run_compare:125→151. |
| TEST-3 | HIGH | A1 | `oracle_aware_task_preparation.py` untested, mutated indirectly | integration-characterization safety-net added. |
| REG-10 | MED | A3 | sat4j not byte-identical (extra `_create_checker`); real caller `pysat_explanation_builder` omitted | added to file list; diff incl. `_create_checker`; confirm for_*_sat4j tested before delete. Verified. |
| REG-9 | MED | B3 | ground_truth reclassification ripples to 7 importers | file list widened; noted reclassify largely DONE (already `GroundTruthData`). Verified. |
| TEST-5 | MED | B1,C6 | `dimacs_to_configuration.py` is dead (0 importers) — characterizing it blocks deletion | B1 skips it; C6 deletes it. Verified zero importers. |

## Applied (MED/LOW polish)
- **SEQ-2** A1: slicer takes plain-int stride → conacq stops importing the private const immediately.
- **SEQ-5** B3↔C5: get_variables keep-decision cross-referenced (binding on C5).
- **SEQ-6** A4→C2: metric map must not bake `PerformanceMetrics` field names.
- **TEST-6** A7: stale line fixed (`Resources` at :102, not :160-180).
- **TEST-8** A4: split assertion policy — pin counts exactly, timing/memory presence+type only.
- **TEST-9** A5: logging-only edits to untested oracles (no control-flow change before B3).
- **C7** qxtc labeler arity (`find_conflict_set` vs `find_conflict`) preserved in template base.

## Verdict
Plan structure & A→B→C order are sound; sequential dependencies point the right way. The fixes are all additive (steps/files/assertions/cross-refs) within the locked scope — no scope cut, no design reversal. After applying, the highest residual risk is **B4** (oracle map-move vs codec fix); its phase now carries the widened file list + ordering-cycle step + byte-identical guard.

## Unresolved questions (for user)
1. **B4 intent:** should `prepare()` keep writing maps to the model then copy to Task, or fully restructure to hand maps directly to `prepare_task()`? (Two very different blast radii on `fm_oracle.py`.) Recommend the full restructure (kills the cycle) — confirm.
2. **C2 5th-path:** the real metrics duplication is in `kb_comparator`/`accuracy`, not `progressive_evaluation`. Confirm the intended "single source of truth" target before C2 (the brief mislabeled the file).
3. **dimacs_to_configuration.py:** confirmed dead in-repo — OK to delete in C6, or is it kept for an out-of-repo/plugin consumer?
