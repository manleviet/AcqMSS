---
phase: 9
title: B3 unify oracle contract
status: completed
priority: P1
effort: 1-2d
dependencies:
  - 1
---

# Phase 9: B3 — single Oracle contract

## Overview
Replace the fragmented Oracle surface (ABC with empty stubs + 20+ non-contractual `FeatureModelOracle` methods + a one-method `BGDataProvider` Protocol) with one `Oracle` Protocol/ABC that actually lists what consumers use. Drop empty stubs (incl. `get_variables()` which returns `None` and crashes `ExampleGenerator` for any non-FM oracle). Reclassify `ground_truth` (it is a `GroundTruthData` factory, not an Oracle).

## Safety-net FIRST (untested modules)
`conacq/oracle/cached.py`, `user_prompt.py`, `ground_truth.py` are untested. Write characterization tests for each (substitutability + the methods they actually implement) BEFORE changing the contract.

## Requirements
- Functional: one `Oracle` contract listing `ask`, `is_valid`, `get_bg_data`, `complete_configuration`, codec access (final list per consumer audit); `FeatureModelOracle`/`UserPromptOracle` conform; `cached` conforms; `ground_truth` reclassified out.
- Non-functional: no empty stubs returning None; conacq-side (`conacq/oracle/`).

## Architecture
- `conacq/oracle/base.py`: single `Oracle` Protocol/ABC. Audit consumer call-sites to define the real method set (grep `oracle.` usage in algorithms/runners/example_generators).
- `get_variables()`: either part of the contract (then all conformers implement) or removed and the FM-specific need met another way — decide from the ExampleGenerator usage (`example_generators/base.py:33`).

## Related Code Files (verified)
- Modify: `conacq/oracle/base.py` (stubs :32/:38-39/:41-42), `conacq/oracle/fm_oracle.py` (20+ methods :114-201), `conacq/oracle/cached.py`, `conacq/oracle/user_prompt.py`, `conacq/oracle/bg_data.py` (BGDataProvider :43-52)
- Reclassify: `conacq/oracle/ground_truth.py` (not an Oracle)
- Create: `tests/test_oracle_*.py` (safety-net for cached/user_prompt/ground_truth)

## Implementation Steps
1. Audit oracle call-sites; enumerate the real contract.
2. Write safety-net tests for cached/user_prompt/ground_truth.
3. Define the single contract; conform implementations; remove empty stubs; resolve `get_variables`.
4. Reclassify ground_truth; update its callers to use it as data, not oracle.
5. `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] One `Oracle` contract; no empty `pass` stubs
- [ ] cached/user_prompt conform; ground_truth reclassified (not Oracle)
- [ ] `get_variables` crash-path resolved (ExampleGenerator works for non-FM oracle, or contract makes it mandatory)
- [ ] Safety-net oracle tests exist (satisfies C3's safety-net prerequisite)
- [ ] Full suite green (≥351)

## Red-team adjustments (applied 260621)
- **ground_truth already done:** `conacq/oracle/ground_truth.py` is already `class GroundTruthData` (NOT an Oracle subclass) and consumers use it as data — "reclassify" is largely complete. Scope here = confirm no residual Oracle-substitution assumption + widen awareness.
- **CachedOracle / UserPromptOracle delegation gap:** both implement ONLY `is_valid` — they do NOT implement `get_variables`/`complete_configuration`. ADD delegation (forward to `base_oracle`) so they conform. Existing tests miss this (`test_quacq.py:147` only exercises `is_valid`) → the safety-net MUST include a substitutability test calling the FULL contract on both.
- **KEEP `get_variables` in the contract** (used by `ExampleGenerator` + apps `generate_examples.py:143`). This decision is BINDING on C5 (which keeps calling it) — record in both phase files.
- **Widen file list** (GroundTruthData importers): `conacq/eval/kb_comparator.py`, `conacq/eval/progressive_evaluation.py`, `conacq/eval/__init__.py`, `conacq/oracle/__init__.py`, `apps/run_evaluation.py`, `apps/run_compare.py`.

## Risk Assessment
- Defining the contract too narrow/loose → derive it strictly from real call-sites, not speculation.
- ground_truth reclassification may ripple into eval code → trace its importers before moving.
