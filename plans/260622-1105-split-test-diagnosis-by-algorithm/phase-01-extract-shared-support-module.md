---
phase: 1
title: Extract shared support module
status: completed
effort: ''
---

# Phase 1: Extract shared support module

## Overview
Create `tests/diagnosis_support.py` holding ALL scaffolding the 35 tests share (currently `test_diagnosis.py` lines ~1-220), so the 5 algorithm files import it instead of duplicating. Plain module, NOT `conftest.py` (these are import-time helpers/decorators, not fixtures).

## Architecture
- Single source of truth for the `ENABLED_TESTS` toggle map — one map, imported by all 5 files (NOT fragmented per file). Same for `ENABLED_PARAMS`.
- `_skip_if_disabled` closes over the module-global `ENABLED_TESTS` in `diagnosis_support` → the closure keeps working once imported.
- Existing `tests/conftest.py` (conacq bias/oracle fixtures) is UNTOUCHED.

## Related Code Files
- Create: `tests/diagnosis_support.py`
- Read (source of moved code): `tests/test_diagnosis.py` lines 1-220
- Do NOT modify: `tests/conftest.py`, anything in `explanation/`

## Implementation Steps
1. Create `tests/diagnosis_support.py`. Move VERBATIM from `test_diagnosis.py` header:
   - imports needed by scaffolding (os, pytest, flamapy ConfigurationBasicReader, the explanation builders/algorithms used by helpers — copy the import block, prune later only if unused).
   - `ENABLED_TESTS` dict, `ENABLED_PARAMS` dict.
   - `_get_standard_params` / `_get_sat4j_only_params` / `_get_no_sat4j_params` + `STANDARD_PARAMS` / `SAT4J_ONLY_PARAMS` / `NO_SAT4J_PARAMS` module constants.
   - `TEST_DIR`, `RESOURCES_DIR`, `Resources` class.
   - `_profiler_preset`, `print_test_header`, `print_profiler_status`, `create_checker`, `_skip_if_disabled`.
2. Keep symbol NAMES identical (the 5 files import them unchanged) → minimizes Phase 2 diff.
3. Sanity import: `python -c "import tests.diagnosis_support"` resolves with no error.

## Success Criteria
- [ ] `tests/diagnosis_support.py` created; imports resolve (`uv run --no-sync python -c "import tests.diagnosis_support"`).
- [ ] Single `ENABLED_TESTS` + `ENABLED_PARAMS` live here (no copies elsewhere).
- [ ] `tests/conftest.py` and `explanation/` byte-unchanged.

## Risk Assessment
- Risk: a helper silently depends on a symbol left behind in `test_diagnosis.py`. Mitigation: Phase 2 moves the tests too; run collection after Phase 2, not in isolation. Keep the import block whole during the move; prune unused imports only at the end with a lint pass.
