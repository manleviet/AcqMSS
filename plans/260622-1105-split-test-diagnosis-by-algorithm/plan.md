---
title: Split test_diagnosis.py by algorithm
description: ''
status: completed
priority: P2
branch: feat/redesign-abc
tags: []
blockedBy: []
blocks: []
created: '2026-06-22T09:24:15.421Z'
createdBy: 'ck:plan'
source: skill
---

# Split test_diagnosis.py by algorithm

## Overview

Test-only refactor. Split `tests/test_diagnosis.py` (1278 L, 35 tests) BY ALGORITHM into 5 files + 1 shared support module. **PURE VERBATIM MOVE** — zero test-body edits; only scaffolding relocates. `explanation/` untouched.

Source: brainstorm `plans/reports/brainstorm-260622-1105-split-test-diagnosis-by-algorithm.md`.

**HELD (status: pending).** Execute only AFTER the FastDiagP-canary PR (commit `24afc1b`) merges to `main`.

**Acceptance gate (the whole point):** `test_diagnosis.py` currently collects **206 tests** (`pytest tests/test_diagnosis.py --co -q`). After the split, `pytest tests/test_diagnosis_*.py --co -q` MUST collect **206** — same number, just spread across 5 files. Full suite pass count unchanged (579). `git diff` shows pure relocation + new support module, 0 logic edits.

### Target layout
| New file | Tests | # |
|---|---|---|
| `tests/diagnosis_support.py` | shared scaffolding (no tests) | 0 |
| `tests/test_diagnosis_fastdiag.py` | FastDiag + FastDiagP + HSDAG-FastDiag | 7 |
| `tests/test_diagnosis_quickxplain.py` | QuickXPlain + HSDAG-QuickXPlain | 7 |
| `tests/test_diagnosis_quickxplain_testcases.py` | QXTC + HSDAG-QXTC | 6 |
| `tests/test_diagnosis_kbdiag.py` | KBDiag + HSDAG-KBDiag | 12 |
| `tests/test_diagnosis_redundancy.py` | WipeOutR_FM/_T + pysat redundancy | 3 |
| ~~`tests/test_diagnosis.py`~~ | DELETED | — |

### Out of scope
`ENABLED_TESTS`→pytest-marker migration · HSDAG boilerplate (`profiler_session`+builder-selection) extraction (deferred, YAGNI) · any production/`explanation/` change · renaming other test files.

### Task hydration
SKIPPED — plan is held/pending; Claude Tasks are session-scoped and won't survive to the post-merge execution session. Plan files are the source of truth.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Extract shared support module](./phase-01-extract-shared-support-module.md) | Completed |
| 2 | [Move tests into 5 algorithm files](./phase-02-move-tests-into-5-algorithm-files.md) | Completed |
| 3 | [Verify collected-count parity](./phase-03-verify-collected-count-parity.md) | Completed |

## Dependencies

- Execution gated on FastDiagP-canary commit `24afc1b` being merged to `main` (a commit, not a plan dir — no `blockedBy` plan ref).
- No overlap with other in-flight plans (test-only; touches only `tests/`).
