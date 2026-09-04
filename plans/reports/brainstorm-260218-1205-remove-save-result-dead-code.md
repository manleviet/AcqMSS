# Brainstorm: Remove save_result & resolve Dead Code from ConGen/Learner

## Problem Statement
ConGen handles resolve assumption IDs → human-readable names and save result — violating SRP. These should be caller's responsibility (e.g., ConGenRunner).

## Key Finding
Both `ConGen.save_result()`, `resolve_congen_names()`, and `Learner.save_result()` are **dead code** with 0 external callers. ConGenRunner already handles resolution inline.

## Evaluated Approaches

### A: Delete Dead Code Only (RECOMMENDED)
- Remove `resolve_congen_names()` from `congen.py`
- Remove `ConGen.save_result()` from `congen.py`
- Remove `Learner.save_result()` from `learner.py`
- Update `__init__.py` exports
- **Pros**: Simplest, zero risk, KISS/YAGNI compliant
- **Cons**: None

### B: Delete + Extract Utility
- Same as A, plus extract resolve logic into utility function
- **Pros**: Reusable resolution
- **Cons**: YAGNI — no other callers need it; `description_provider.get_description()` already serves this purpose

### C: Create ResultFormatter Class
- Dedicated class for formatting/saving
- **Pros**: Extensible
- **Cons**: Over-engineered for 0 callers; `save_kb_result()` in `conacq/eval/report.py` already handles file I/O at app level

## Final Recommendation
**Approach A** — pure dead code removal. ConGenRunner.run() already correctly handles resolution (lines 202-213). File saving handled by `save_kb_result()` in `conacq/eval/report.py`.

## Files to Modify
| File | Action |
|---|---|
| `conacq/algorithms/acqmss/congen.py` | Remove `resolve_congen_names()` + `save_result()` |
| `conacq/algorithms/acqmss/__init__.py` | Remove `resolve_congen_names` export |
| `conacq/algorithms/__init__.py` | Remove `resolve_congen_names` export |
| `conacq/algorithms/interactive/learner.py` | Remove `save_result()` |

## Success Criteria
- All tests pass
- No broken imports
- ConGen and Learner only contain algorithm logic

## Risk: Low
Dead code removal, 0 callers affected.
