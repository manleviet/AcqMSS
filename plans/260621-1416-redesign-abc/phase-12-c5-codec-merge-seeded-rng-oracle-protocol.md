---
phase: 12
title: C5 codec merge + seeded RNG + oracle protocol
status: completed
priority: P1
effort: 1-2d
dependencies:
  - 9
  - 11
---

# Phase 12: C5 — codec merge + seeded RNG + ExampleGenerator on Oracle Protocol

## Overview
Start Phase C with the small, high-value items: fold the 3rd config↔literal encoder into `VariableCodec`; introduce ONE seeded RNG source for all generators (closes the reproducibility hole — critical for a benchmark codebase); make `ExampleGenerator` depend on the `Oracle` Protocol (B3) not the concrete `FeatureModelOracle`, and extract the shared valid-config helper.

## Requirements
- Functional: `Example.to_literals` logic lives in `VariableCodec`; every generator uses `random.Random(seed)` instances (no global `random.seed`/`random.shuffle`); ExampleGenerator typed against `Oracle`; one `_generate_valid_config` helper.
- Non-functional: reproducibility test proves identical output for identical seed; codec change framework-isolated.

## Architecture
- Codec: add the encode path `to_literals` currently in `examples/data_structures.py:81` (note: the working-tree fix already routed `_model_to_config`→codec, so codec is already the decode source — this adds the remaining encode duplicate).
- RNG: a single seeded-RNG accessor (mirroring the correct pattern in `eval/folds.py:46` / `cross_validation.py:194`); thread a `random.Random(seed)` instance through generators.
- ExampleGenerator: param typed `Oracle` (Protocol from B3); shared valid-config helper folds `base._generate_valid_config` + `feature_frequency._generate_valid_config_for_coverage`.

## Related Code Files (verified)
- Modify: `explanation/models/codec.py` (absorb encode), `conacq/examples/data_structures.py` (`to_literals` :81 → delegate/remove)
- Modify (RNG): `conacq/example_generators/base.py` (:71/:73/:74), `feature_frequency.py` (global seed :49; shuffle :186/:192/:222; choice :195/:219), `random_sampling.py` (global seed :45/:102/:224; choice :57/:140/:266), `query_provider.py` (:65 — already partly seeded)
- Modify: `conacq/example_generators/base.py` (:11 concrete FeatureModelOracle import → Oracle Protocol; :33 get_variables call)
- Create: `tests/test_rng_reproducibility_*.py`

## Implementation Steps
1. Move encode into codec; re-point `to_literals` users; delete the duplicate.
2. Introduce seeded-RNG source; replace every global `random.*` in generators with instance calls.
3. Add reproducibility test (same seed → identical examples).
4. Re-type ExampleGenerator on Oracle Protocol; extract shared valid-config helper.
5. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] One config↔literal encoder (in codec); `to_literals` duplicate gone
- [ ] No global `random.seed`/`random.shuffle`/`random.choice` in generators; reproducibility test green
- [ ] ExampleGenerator typed against `Oracle`; one valid-config helper
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **Safety-net FIRST (untested generators — CRITICAL gap):** content-pinning characterization tests for `RandomSampling` + `FeatureFrequency` — with a fixed seed assert the EXACT generated example set BEFORE the refactor, then re-pin to the new seeded stream after. The same-seed-twice reproducibility test is necessary but NOT sufficient (passes by construction even if distribution/coverage logic broke). Only `QueryProvider` has any test today, and it asserts pool state, not order.
- **Downstream coupling:** grep tests for assertions on specific generated configs/example counts (KB-acquisition tests fed by generators) and re-baseline within-stage.
- **Depends on B3 keeping `get_variables`** in the Oracle contract (confirmed in B3) — `ExampleGenerator.__init__` keeps calling it.

## Risk Assessment
- Switching from global to instance RNG changes value streams → expect to re-baseline any test asserting specific random outputs; assert reproducibility (same seed twice), not specific legacy values.
