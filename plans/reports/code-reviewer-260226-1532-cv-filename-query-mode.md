# Code Review: CV Filename Query Mode Suffix

**Date:** 2026-02-26
**Scope:** `apps/run_cv.py` lines 187-191 (4-line diff)
**Focus:** Filename change for interactive algorithm output

---

## Overall Assessment

The change is **correct and safe** for its immediate purpose (preventing overwrites between `example_only` and `example_first` runs). However, it introduces a **high-priority downstream compatibility issue** with `extract_results.py` that must be addressed.

---

## Check 1: `query_mode` Scope -- PASS

`query_mode` is defined at line 83 in the same `main()` function scope:
```python
query_mode = interactive_config.get('query_mode', 'example_only')
```
It is always in scope when the conditional at line 188 is reached. The conditional guards correctly -- `query_mode` is only used when `algorithm == 'interactive'`, which is the only case where it is meaningful.

## Check 2: Conditional Correctness -- PASS

The `if algorithm == 'interactive'` guard is correct:
- ConGen files keep the original pattern: `{name}_cv_{mode}.json`
- Interactive files get the extended pattern: `{name}_cv_{mode}_{query_mode}.json`
- No risk of `query_mode` leaking into ConGen filenames

## Check 3: Impact on `find_cv_files()` -- PASS (no issue)

`find_cv_files()` in `conacq/eval/config.py` (line 99) uses glob `*_cv_*.json`:
```python
return sorted(cv_path.glob('*_cv_*.json'))
```
The new filename `REAL-FM-7_rs_1n_cv_non-incremental_example_only.json` still matches `*_cv_*.json`. No breakage.

## Check 4: Impact on `run_compare.py` -- PASS (no issue)

`run_compare.py` iterates files from `find_cv_files()` and reads JSON content (line 116-117). It never parses the filename. File discovery uses the same glob above. No breakage.

---

## Critical Issue: `extract_results.py` `parse_filename()` Will Silently Ignore Interactive Files

**Severity: HIGH**

`extract_results.py:parse_filename()` (lines 92-108) expects filenames ending in exactly `_cv_incremental.json` or `_cv_non-incremental.json`:

```python
if not filename.endswith('_cv_incremental.json') and \
   not filename.endswith('_cv_non-incremental.json'):
    return None  # <-- interactive files will hit this and be silently skipped
```

A file named `REAL-FM-7_rs_1n_cv_non-incremental_example_only.json` does **not** end with `_cv_non-incremental.json`. It ends with `_example_only.json`. Therefore:

1. `parse_filename()` returns `None` for all interactive CV files
2. `load_cv_result()` returns `None` (line 113-115)
3. `load_all_results()` silently skips them (line 254)
4. Interactive results never appear in generated paper tables

This is a **silent data loss** -- no error, no warning, just missing rows.

### Recommended Fix

Update `parse_filename()` to handle the new pattern. Two options:

**Option A (minimal):** Strip known `query_mode` suffixes before matching:
```python
def parse_filename(filename: str) -> Optional[Tuple[str, str, str]]:
    # Strip query_mode suffix for interactive files
    for qm in ('_example_only', '_example_first'):
        if filename.endswith(f'{qm}.json'):
            filename = filename[:-len(f'{qm}.json')] + '.json'
            break
    # ... rest unchanged
```

**Option B (robust):** Use regex to extract mode, allowing optional trailing segments:
```python
import re
_CV_PATTERN = re.compile(r'^(.+)_cv_(incremental|non-incremental)(?:_.+)?\.json$')

def parse_filename(filename: str) -> Optional[Tuple[str, str, str]]:
    m = _CV_PATTERN.match(filename)
    if not m:
        return None
    base, mode = m.group(1), m.group(2)
    for strategy in STRATEGIES:
        if base.endswith(f'_{strategy}'):
            model = base[:-len(f'_{strategy}')]
            return (model, strategy, mode)
    return None
```

Option B is preferred -- it handles any future filename extensions without needing to enumerate suffixes.

---

## Medium Priority

### Consider storing `query_mode` in the output JSON

The interactive runner already records `query_mode` in result metadata (via `quacq.py` line 224). Confirm that `generate_unified_cv_dict` propagates this to the output JSON. If it does, `extract_results.py` could also use JSON content (not filename) to distinguish runs -- a more robust approach long-term.

---

## Low Priority

### Comment accuracy
The inline comment `# Include query_mode in filename for interactive to avoid overwrites` is accurate and helpful.

---

## Positive Observations

- Clean, minimal diff -- only changes what is needed
- Correct use of the `algorithm` guard to keep ConGen path untouched
- Good defensive approach to filename uniqueness

---

## Recommended Actions

1. **[HIGH]** Update `extract_results.py:parse_filename()` to handle the `_{query_mode}` suffix in interactive filenames (otherwise table generation silently drops interactive results)
2. **[MEDIUM]** Verify `generate_unified_cv_dict` includes `query_mode` in JSON metadata for content-based identification
3. **[LOW]** No action needed -- change is otherwise correct

---

## Unresolved Questions

1. Will `extract_results.py` need to distinguish between `example_only` and `example_first` results in tables, or should they be treated identically once parsed? (Affects whether `parse_filename` should return `query_mode` as a 4th tuple element.)
2. Are there any other downstream scripts that glob for `*_cv_*.json` and parse the filename?
