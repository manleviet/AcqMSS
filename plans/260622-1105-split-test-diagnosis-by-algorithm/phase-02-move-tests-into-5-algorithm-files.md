---
phase: 2
title: Move tests into 5 algorithm files
status: completed
effort: ''
---

# Phase 2: Move tests into 5 algorithm files

## Overview
Relocate all 35 test functions VERBATIM from `test_diagnosis.py` into 5 algorithm-grouped files, each importing scaffolding from `tests.diagnosis_support`. Then delete `test_diagnosis.py`. Zero edits to test bodies, decorators, or assertions.

## Architecture
Each new file's preamble:
```python
from tests.diagnosis_support import (
    ENABLED_TESTS, STANDARD_PARAMS, SAT4J_ONLY_PARAMS, NO_SAT4J_PARAMS,
    Resources, create_checker, _skip_if_disabled, _profiler_preset,
    print_test_header, print_profiler_status,
)
# + the explanation imports each file's tests actually use (FastDiag, HSDAG builder, etc.)
```
Tests keep their `@pytest.mark.parametrize(...)` + `@_skip_if_disabled('key')` decorators unchanged — the `'key'` strings still resolve against the single `ENABLED_TESTS` in support.

## Related Code Files (Create / Delete)
- Create: `tests/test_diagnosis_fastdiag.py` — move funcs at lines 223, 269, 449-517, 627-647, 675-699 (FastDiag, FastDiagP, hsdag_fastdiag_{1diag,2diag,all,configuration,test_case}).
- Create: `tests/test_diagnosis_quickxplain.py` — lines 246, 524-624, 650-672, 702-725 (QuickXPlain, hsdag_quickxplain_{1cs,dfs,2cs,all,configuration,testcase}).
- Create: `tests/test_diagnosis_quickxplain_testcases.py` — lines 397-446, 971-1090 (QXTC direct ×2, hsdag_quickxplainwithtestcases ×4).
- Create: `tests/test_diagnosis_kbdiag.py` — lines 292-394, 731-965 (kbdiag ×4, hsdag_kbdiag ×8).
- Create: `tests/test_diagnosis_redundancy.py` — lines 1115-1278 (wipeoutr_fm, pysat_redundancy, wipeoutr_t).
- Delete: `tests/test_diagnosis.py`.

(Line numbers are the CURRENT pre-move positions — re-grep `^def test_` before cutting in case prior phases shifted them.)

## Implementation Steps
1. For each of the 5 files: add module docstring + the support import + per-file explanation imports, then paste the assigned test functions VERBATIM (incl. both decorators).
2. Per-file explanation imports: only what that file uses (e.g. fastdiag file imports `FastDiag`, `FastDiagP`, the HSDAG diagnosis builder; redundancy file imports the WipeOutR ops). Avoid a blanket star-import.
3. After all 5 written, delete `tests/test_diagnosis.py`.
4. Do NOT touch test bodies — if a paste needs an import the support module doesn't export, EXPORT it from support (Phase 1 surface), don't rewrite the test.

## Success Criteria
- [ ] 5 files created, `test_diagnosis.py` deleted.
- [ ] Each new file collects without import error (`pytest <file> --co -q`).
- [ ] Sum of test funcs across 5 files = 35; no test renamed.
- [ ] `git diff` of moved bodies = pure relocation (no intra-body changes).

## Risk Assessment
- Risk: per-file import omission → collection ImportError. Mitigation: collect each file individually in this phase; fix by adding the missing import to that file (or exporting from support).
- Risk: a test function accidentally duplicated or dropped during cut/paste. Mitigation: Phase 3 collected-count gate (206) catches both directions.
