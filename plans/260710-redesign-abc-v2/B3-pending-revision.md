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
