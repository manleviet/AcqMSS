# Code Review: `python -m apps.X` Invocation Refactoring

**Date**: 2026-02-25
**Scope**: Documentation/docstring-only migration from `PYTHONPATH=. python apps/X.py` to `python -m apps.X`
**Verdict**: PASS with 2 issues (1 high, 1 low)

---

## Scope

- **Files reviewed**: 22 changed files (8 `.py`, 8 `.toml`, 4 `.md`, 1 new `__init__.py`, 1 new `config.py`)
- **Focus**: Verify pattern consistency, no stale references, no unintended logic changes

## Overall Assessment

The migration is well-executed. All non-plan, non-historical files in the working tree are clean -- zero remaining `PYTHONPATH=. python apps/` references. The `PYTHONPATH=. pytest` pattern is correctly left untouched (pytest still requires it). The `apps/__init__.py` is correctly empty.

---

## Issues Found

### HIGH: `README.md` references deleted script `run_congen_eval`

**File**: `/Users/manleviet/Development/GitHub/AcqMSS/README.md`, line 41

```
python -m apps.run_congen_eval apps/conf/run_congen_eval_config.toml -v
```

`run_congen_eval.py` is deleted (git status shows `D apps/run_congen_eval.py`). The invocation pattern was correctly updated to `python -m`, but the script no longer exists. This will confuse users following the Quick Start.

**Fix**: Replace with `python -m apps.run_cv` or `python -m apps.run_compare` depending on intent (CV vs comparison), and reference the correct TOML config. The Quick Start step 4 ("Evaluate results") should now reference the new pipeline.

Similarly, `apps/conf/test_eval_config.toml` line 2 references:
```
# Run with: python -m apps.run_congen_eval apps/conf/test_eval_config.toml -v
```
This config's runner no longer exists.

### LOW: `.serena/memories/` contain stale references

**Files**: `.serena/memories/project_overview.md` (lines 31-33), `.serena/memories/suggested_commands.md` (lines 14-19)

These still use `PYTHONPATH=. python apps/X.py` and reference deleted scripts (`run_congen_eval.py`, `run_interactive_eval.py`). Not tracked by git, but will mislead Serena-based agents.

---

## Observations Beyond Docstring Scope

The changeset includes logic changes beyond the stated docstring/comment migration:

| File | Change |
|------|--------|
| `apps/run_congen.py` | Replaced inline `ModelConfig`/`load_config`/`parse_models` with shared `conacq.eval.config` imports; renamed `is_incremental` -> `use_incremental`; added `bg_clauses` to `save_kb_result`; changed model field `path` -> `oracle` |
| `apps/conf/run_congen_config.toml` | Structural change: `path` -> `oracle` + `name` field added |
| `apps/extract_results.py` | Added `load_eval_result()`, `_find_matching_eval()` (58 new LOC); modified `load_all_results()` to merge external eval files |
| `conacq/eval/config.py` | Added `kb_dir` field to `ModelConfig`; added to `parse_models()` |
| `conacq/eval/__init__.py` | Added exports for `config.py` symbols |
| `conacq/eval/report.py` | Added `bg_clauses` parameter to `save_kb_result()` |

These are coherent with the broader pipeline refactor (new `run_cv.py`/`run_compare.py`/`describe_kb.py` replacing old `run_congen_eval.py`/`run_interactive_eval.py`). No issues with the logic changes themselves -- they are clean and backward-compatible via the `Optional` fields.

---

## Staging State Note

The staged index for new files (`describe_kb.py`, `run_compare.py`, `run_cv.py`, `run_interactive.py`, and 4 TOML configs) still contains old `PYTHONPATH=.` patterns in argparse epilog strings. The unstaged diff corrects these. Before committing, ensure all changes are staged (`git add`) so the final commit contains the clean versions.

---

## Verification Summary

| Check | Result |
|-------|--------|
| No stale `PYTHONPATH=. python apps/` in non-plan files | PASS (working tree) |
| `PYTHONPATH=. pytest` intentionally preserved | PASS |
| New `python -m apps.X` pattern consistent across all 8 scripts | PASS |
| New `python -m apps.X` pattern consistent across all 8 TOML configs | PASS |
| Docs updated (`README.md`, `CLAUDE.md`, `codebase-summary.md`, `data/examples/README.md`) | PASS |
| `apps/__init__.py` exists and is empty | PASS |
| No logic changes in docstring-only files | PARTIAL (see observations above) |
| References to deleted scripts cleaned up | FAIL (`README.md:41`, `test_eval_config.toml:2`) |
| Historical files (`plans/`) untouched | PASS |

---

## Recommended Actions

1. **Fix `README.md` line 41** -- replace `run_congen_eval` reference with the correct new pipeline command (e.g., `python -m apps.run_compare` or `python -m apps.run_cv`)
2. **Fix `apps/conf/test_eval_config.toml` line 2** -- update the comment to reference the correct runner, or delete the file if `run_congen_eval.py` is fully replaced
3. **Stage all changes** before committing -- the staged index still has old patterns in new files
4. **Optional**: Update `.serena/memories/` to reflect new invocation pattern

## Unresolved Questions

- Is `test_eval_config.toml` still needed now that `run_congen_eval.py` is deleted? If so, which runner should it reference?
- Should `docs/project-overview-pdr.md` (lines 212-213) be updated to reflect the new file structure, or is it considered historical?
