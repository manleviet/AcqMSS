---
phase: 3
title: Verify collected-count parity
status: completed
effort: ''
---

# Phase 3: Verify collected-count parity

## Overview
Prove the split lost/added/renamed nothing and changed no behavior. The hard gate is collected-count identity (206) plus an unchanged full-suite pass count and a pure-relocation diff.

## Implementation Steps
1. **Collected-count parity (primary gate):**
   `PYTHONPATH=. uv run --no-sync pytest tests/test_diagnosis_*.py --co -q | tail -1` → MUST read `206 tests collected` (same as pre-split `test_diagnosis.py`).
2. **Optional name-level identity (stronger):** compare the SET of collected test node ids (basename after `::`, ignoring file path) pre vs post — must be identical. Capture pre-split list from git: `git show HEAD:tests/test_diagnosis.py | grep -oE 'def test_[a-z0-9_]+'` vs the 5 new files.
3. **Full suite:** `PYTHONPATH=. uv run --no-sync pytest tests/ -q` → same pass count as before the split (**579**, incl. the FastDiagP canary once merged).
4. **Purity check:** `git diff --stat` shows only `tests/` (5 new + support + deleted original); `git status --porcelain explanation/` clean. Spot-check 2-3 moved bodies with a diff to confirm verbatim.
5. **Lint pass:** prune any now-unused imports left in `diagnosis_support.py` / the 5 files (`ruff check tests/` if available); re-run step 1 after.

## Success Criteria
- [ ] `pytest tests/test_diagnosis_*.py --co -q` == **206 tests collected**.
- [ ] Set of test function names identical pre/post (none lost/renamed/added).
- [ ] Full suite pass count unchanged (579).
- [ ] `explanation/` byte-unchanged; diff is pure relocation + new support module.
- [ ] `test_diagnosis.py` no longer exists.

## Risk Assessment
- Risk: count matches but a param combo silently changed (e.g. a file lost a `SAT4J_ONLY_PARAMS` import and fell back). Mitigation: step 2 name-level set comparison + step 3 full-suite run catch divergence; the param decorators are moved verbatim so combos are preserved.
- Risk: pruning imports (step 5) removes one a test needs at runtime. Mitigation: re-collect AND run the suite after pruning, not just collect.
