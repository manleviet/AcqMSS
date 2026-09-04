# Brainstorm — split `test_diagnosis.py` by algorithm

**Date:** 2026-06-22 · **Branch:** `feat/redesign-abc` · **Type:** test-only refactor (advisory; not implemented) · **Status: design APPROVED, ready for plan.**

## Problem
`tests/test_diagnosis.py` = **1278 L, 35 tests** — biggest test file, ~2× the next (`test_quacq` 705), **6× the ~200 L Python threshold**. Hurts LLM-tooling (Grep/Glob/context) + locality when touching one engine. Split warranted.

## Decision (user-approved)
Split **BY ALGORITHM** (vertical cohesion: each engine's direct + HSDAG-variant tests together) into **5 files + 1 shared support module**. Mirrors source layout (one file per algorithm module).

| New file | Tests (from test_diagnosis.py) | # | ~L |
|---|---|---|---|
| `tests/test_diagnosis_fastdiag.py` | `test_fastdiag_1diag`, `test_fastdiagp_1diag`, `hsdag_fastdiag_{1diag,2diag,all,configuration,test_case}` | 7 | ~300 |
| `tests/test_diagnosis_quickxplain.py` | `test_quickxplain_1cs`, `hsdag_quickxplain_{1cs,dfs,2cs,all,configuration,testcase}` | 7 | ~300 |
| `tests/test_diagnosis_quickxplain_testcases.py` | `test_quickxplainwithtestcases_{1cs_1,1diag_1_neg}`, `hsdag_quickxplainwithtestcases_{1diag_1,1diag_1_neg,all_1,all_1_neg}` | 6 | ~300 |
| `tests/test_diagnosis_kbdiag.py` | 4× `test_kbdiag_*`, 8× `hsdag_kbdiag_*` | 12 | ~450 |
| `tests/test_diagnosis_redundancy.py` | `wipeoutr_fm_redundancy`, `pysat_redundancy_constraints`, `wipeoutr_t_redundancy` | 3 | ~200 |
| `tests/diagnosis_support.py` (shared) | Resources, STANDARD/SAT4J/NO_SAT4J params + builders, **single `ENABLED_TESTS`** + `ENABLED_PARAMS`, `create_checker`, `_skip_if_disabled`, `_profiler_preset`, `print_test_header`, `print_profiler_status` | — | ~200 |

`test_diagnosis.py` is **deleted** (no residual). Total tests preserved: 7+7+6+12+3 = **35**.

## Approaches evaluated
1. **By algorithm, 5 files + support (CHOSEN).** Source-mirroring, vertical cohesion, HSDAG builder factory is algorithm-specific so stays uniform per file. Con: 5 files; KBDiag file ~450 L (still cohesive — accepted, no over-split).
2. By layer, 3 files (direct / hsdag / redundancy) — REJECTED: splits one engine across files; horizontal cut scatters algorithm-specific HSDAG builder usage.
3. One file per individual algorithm-test — REJECTED: FastDiag/FastDiagP/QuickXPlain are 1 direct test each → 1-test files = noise.
4. Classes-in-one-file — REJECTED: file stays 1278 L → doesn't solve the LLM-size rationale.

## Key design points
- **Single `ENABLED_TESTS` panel** lives in `diagnosis_support.py`, imported by all 5 files — preserves the documented "toggle map" convention; NOT fragmented per file.
- Shared helpers go in a **plain module `diagnosis_support.py`, NOT `conftest.py`** — they are import-time helpers/decorators (`_skip_if_disabled` returns a `skipif` mark at collection), not fixtures. Existing `conftest.py` (conacq bias/oracle fixtures) is untouched.
- **PURE MOVE, verbatim.** Tests relocate with ZERO body edits; only scaffolding moves to support. Behavior byte-identical.
- **Boilerplate-DRY deferred.** The repeated `profiler_session` + `PySATDiagnosisBuilder.for_…() if use_sat4j else …` + print/assert is a real DRY smell, but extraction is a SEPARATE later pass (YAGNI now; keeps this PR low-risk).

## Acceptance criteria
- `pytest tests/ --co -q | wc -l` **identical** before/after (proves no test lost/renamed/added).
- Full suite same pass count (579 incl. the FastDiagP canary).
- `git diff` shows pure relocation + new support module — **0 logic edits**, `explanation/` untouched.

## Risks / mitigations
- Import breakage → explicit exports in `diagnosis_support.py`; run collection first.
- `ENABLED_TESTS` drift → single map in support, no per-file copies.
- Collected-count drift → the `--co` diff gate above is the hard check.

## Sequencing & scope
- **AFTER** the held FastDiagP-canary PR merges. Separate **test-only** PR.
- OUT of scope: `ENABLED_TESTS`→pytest-marker migration; HSDAG boilerplate extraction; any production/`explanation/` change; naming migration of other test files.

## Unresolved questions
1. Filename convention defaulted to `test_diagnosis_<algo>.py` (grouped prefix). Flag if flat `test_<algo>.py` preferred.
