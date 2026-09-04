---
phase: 6
title: A6 apps CLI harness + atomic JSON
status: completed
priority: P1
effort: 2d
dependencies:
  - 1
  - 5
---

# Phase 6: A6 — apps/ CLI harness + atomic JSON writes

## Overview
`apps/` (11 scripts, ~3.2k LOC) is the single largest hygiene gap: 254 `print()`, config-loading cloned 4×, runner setup cloned, FM-oracle init cloned, string-based dispatch, and — highest severity — in-place JSON writes that corrupt the unified CV JSON on a mid-write crash. Build one shared CLI/config harness + a runner-factory + logging; make CV-JSON writes atomic.

## Requirements
- Functional: one config-loader (`load_pipeline_config` + section extraction), one runner-factory, logging instead of print; CV-JSON writes via temp-file + `os.replace` (atomic).
- Non-functional: data-loss risk closed; batch runs silenceable/redirectable; depends on A4's runner base for the factory.

## Architecture
- `apps/_harness.py` (or similar): shared `load_config`, `make_runner`, logging setup.
- Atomic write helper: write to `*.tmp` then `os.replace(tmp, final)`.

## Related Code Files (verified)
- Create: `apps/<shared harness module>.py`
- Modify: `apps/run_congen.py` (cfg :152), `apps/run_cv.py` (cfg :65; JSON :193), `apps/run_quacq.py` (cfg :144), `apps/run_evaluation.py` (cfg :216; reach-in `runner.model.constraint_map`/`runner.feature_ids`), `apps/run_compare.py` (JSON :129-152), `apps/generate_*` (argparse + FM-oracle init clones), `apps/generate_bias_config.py` (`os.chdir` workaround :30-33)
- 254 `print()` across all 11 scripts → logging

## Implementation Steps
1. Extract shared config-loader + runner-factory (uses A4 base) + logging config.
2. Add atomic-write helper; route `run_compare`/`run_cv` JSON writes through it.
3. Replace 254 `print()` with module loggers (keep CLI UX: a logging handler to stdout).
4. Dedup argparse + FM-oracle init; remove `os.chdir` workaround.
5. Note the `run_evaluation` reach-in for B1 (don't fix the boundary here; just record).
6. Manually smoke-run one app end-to-end (`python -m apps.run_congen ...`); `PYTHONPATH=. pytest tests/ -v` → green.

## Success Criteria
- [ ] `print()` = 0 in `apps/` (logging only)
- [ ] One config-loader + one runner-factory; argparse/FM-oracle init deduped
- [ ] CV-JSON writes atomic (temp + `os.replace`)
- [ ] `os.chdir` workaround removed
- [ ] One app smoke-run verified; full suite green (≥351)

## Red-team adjustments (applied 260621)
- **Automated atomic-write test (not just manual smoke-run):** (a) round-trip — write dict → read back → assert equal + temp file gone; (b) fault-injection — mock `os.replace` to raise → assert ORIGINAL file untouched. "Atomic" is exactly the property a green suite won't otherwise prove.
- **`run_compare.py` is read-modify-write of the SAME file** (`json.load(cv_file)` :125 → `open(cv_file,'w')` :151) — highest data-loss path. Build the full in-memory dict BEFORE opening the temp; never truncate the source first.
- **Same-filesystem temp:** `os.replace` is atomic only if temp is on the target's filesystem — write the temp in `cv_file.parent`, then `os.replace(tmp, cv_file)` after `json.dump` flushes/closes.
- **Config-loader unit test:** assert the extracted sections equal what the 4 old inline loaders produced on a real TOML (apps/ is otherwise untested).

## Risk Assessment
- apps/ is thinly covered by the suite → rely on a manual smoke-run per touched entry point + the A4 runner tests.
- Logging that breaks `-v` CLI UX → add a stdout handler so verbose output is preserved.
