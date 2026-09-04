# Phase 4: DRY Cleanup `extract_results.py`

**Parent**: [plan.md](plan.md) | **Depends on**: Phase 3
**Priority**: Low | **Status**: pending | **Effort**: 30m

## Overview

`extract_results.py` has 16 table generator functions where each table has MD + LaTeX variants that are ~90% identical. Abstract the format layer to reduce duplication.

## Key Insights

Pattern in every pair:
- Same data iteration (KB1-KB4, strategies, modes)
- Same cell values
- Only differs in: delimiters (`|` vs `&`), line endings (`|` vs `\\\\`), header format, table wrapper

## Related Code Files

- `apps/extract_results.py` — 1016 lines, target ~400 lines after

## Implementation Steps

1. Create `TableFormat` enum or class with MD and LaTeX variants:
   - Row separator, column separator, line ending
   - Header/footer templates
   - Cell formatting helpers

2. Refactor each table pair into single function with `format` parameter:
   - `generate_accuracy_table(results, mode, format='md')` → replaces both `_md` and `_latex`
   - Same for all other pairs

3. Keep paper-specific tables (Table 7, 9, 10, 11) as they have unique layouts

4. Update `main()` to call unified functions with format parameter

## Todo

- [ ] Create `TableFormat` abstraction
- [ ] Merge MD/LaTeX pairs into single functions
- [ ] Update `main()` calls
- [ ] Verify output identical to before refactoring

## Success Criteria

- Same output files (bit-identical or semantically identical)
- ~50% fewer table generator functions
- File under 600 lines

## Risk

- LaTeX has quirks (escaping `%`, `\\`, `$`...) that may resist simple abstraction
- Paper tables (7, 9-11) have unique enough formats that may not merge cleanly
- Mitigation: keep paper tables separate, only merge generic tables
