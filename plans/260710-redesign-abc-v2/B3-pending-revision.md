# B3 pending — passive-ConGen regen at the ConGen revision

**Why deferred:** B3 (`reduce.py` MSS-order fix, ADR-0017) changed ConGen's learned KB. The code + in-repo goldens landed on `feat/redesign-abc-v2`, but the passive-ConGen CV artifacts (`data/results/congen` → t9 golden → paper Tables 7/9/10/11) require a **multi-hour** pipeline run (REAL-FM-4 ≈ 734 s/cell × 3 folds). Doing it inline risked partial writes; doing it piecemeal now would also collide with the still-unseeded example mode (B1). So it is bundled into the ConGen revision.

**Loud marker (not green-that-lies):** `test_extraction_tables_are_byte_identical` in `tests/test_t9_metrics_safety_net.py` is `@pytest.mark.skip`ped (reason cites ADR-0017). Re-extracting stale data against a stale golden would pass while validating nothing — the skip keeps the debt visible.

## Checklist (run at the ConGen revision)

- [ ] **Regen CV data** — for each FM group (uncomment its `[[models]]` in `apps/conf/run_cv_config.toml`):
      `PYTHONPATH=. python -m apps.run_cv apps/conf/run_cv_config.toml`  → overwrites `data/results/congen/*.json` (19 files: REAL-FM-7, fqa, arcade, REAL-FM-4).
- [ ] **Re-extract** — `PYTHONPATH=. python -m apps.extract_results apps/conf/extract_results_config.toml` → refresh `paper/tables/results_tables.{md,tex}` and the frozen golden `tests/resources/t9_extraction_golden/results_tables.{md,tex}`.
- [ ] **Remove the skip** — delete the `@pytest.mark.skip(...)` on `test_extraction_tables_are_byte_identical` and its skip note.
- [ ] **Verify** — `PYTHONPATH=. pytest tests/test_t9_metrics_safety_net.py -v` → extraction byte-identical to the **new** golden; whole suite green.
- [ ] **Itemize the golden diff** (paper cells that moved: `n_kb`/`kb_reduction_ratio`/accuracy) and confirm each is the reduce-reorder effect, not a new bug — the Cowork review artifact.
- [ ] **Paper-regen note** — record the AcqMSS/ConGen number changes vs the old draft (memory `paper-regen-after-determinism-fixes`).
- [ ] **Flip ADR-0017** status note: passive regen done; skip removed.

## Bundled with this revision (do NOT regen piecemeal before it)

- **Interactive / iterative tables** (`data/results/interactive/*`, `tab:iterative_*` in `paper/evaluation.tex`) — a function of **B1 + B2 + B3**. Regenerate once, after B1 (example-pool per-fold seed, ADR-0015) lands, so the numbers are reproducible and not double-regenerated. Until then they carry the current (unseeded, pre-B1) example order.

## Landed already (this batch, `feat/redesign-abc-v2`)

- B2 (`quacq.py:140` bias order) + knob test + `layer23[.quacq]` regen — committed.
- B3 (`reduce.py:63` MSS order) + knob test + `layer23[.congen_*]` + `congen_runner.json` re-baseline — committed.
- `n_mss` (pre-reduce) unchanged throughout; QuAcq arm unaffected by B3 (empty KB on REAL-FM-7).

## Coverage gap to close at the revision — QuAcqRunner net (from the branch-parity audit)

The branch-parity audit (`plans/reports/branch-feature-parity-audit-260719-1439-…`) found **0 dropped features** but **1 coverage gap**: `QuAcqRunner.run()` is unpinned in v2 (ConGenRunner has `test_t11_congen_runner_net.py`; QuAcqRunner has nothing). Build `tests/test_t11_quacq_runner_net.py` at the ConGen/B1 revision — **with the interactive bundle**, since its golden depends on B1+B2+B3.

**Template — reference from `feat/redesign-abc:tests/test_runners_characterization.py::TestQuAcqRunnerCharacterization` (deleted branch; preserved here).** Structure only — **RE-RECORD every value on v2**: the ids are strings on v1 (`'c103'`) but ints in v2, and B1 (example seed) + B2 (`quacq.py:140` order) + B3 (`reduce.py` order) all move the example-mode counts.

```python
# _load_examples(): ExampleIO.load_json(REAL-FM-7 rs_1n) -> pos[:5], neg[:1] (small, <30s)
# Run QuAcqRunner once (class fixture), reuse across assertions:
runner = QuAcqRunner(BIAS_PATH, FM_PATH, query_mode='example_only')
result = runner.run(positive_examples=pos, negative_examples=neg, shuffle_seed=42)

# PINNED (v1 golden values — RE-RECORD on v2):
#   n_bias == 295            n_kb == 1                 n_queries == 17
#   convergence_reason == 'pool_exhausted'            consistency_checks == 17
#   is_consistent_calls == 1996   quacq_calls == 1    findscope_calls == 15
#   findc_calls == 1         dis_gen_calls == 0        reduce_calls == 1
#   sorted(kb_constraints) == ['c103']   len(kb_clauses) == 1   len(bg_clauses) == 1
#   n_kb == len(kb_constraints)
# NOT pinned (presence+type only): runtime_ms, memory_peak_mb, solver_time_ms  (> 0)
```

This is the example-mode path B2 (`quacq.py:140`) touches, so the net is what would guard B2 there — deferred to the revision because its golden rides the B1 bundle.
