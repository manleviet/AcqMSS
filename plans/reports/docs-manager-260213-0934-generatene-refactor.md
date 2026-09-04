# Documentation Update Report: GenerateNE Refactoring

**Date**: February 13, 2026 | **Task**: Update documentation to reflect GenerateNE refactoring

## Summary

Updated AcqMSS documentation to accurately reflect the refactoring that moved GenerateNE out of CONGEN's internal logic. GenerateNE is now called by callers before CONGEN, with results merged into the task via `merge_ne_into_task()`.

## Changes Made

### 1. system-architecture.md

**Lines 17-22** (Overview diagram):
- Updated CONGEN description from "GenerateNE → ACQMSS → REDUCE" to "ACQMSS → REDUCE (GenerateNE pre-computed)"
- Added explicit line: "GenerateNE: Create negated examples (called by caller)"

**Lines 74-82** (Algorithm descriptions):
- Modified CONGEN description: input now "Bias, E+, pre-computed NE" instead of "Bias, E+, E-"
- Updated process: "ACQMSS → REDUCE (NE pre-computed by caller)"
- Enhanced GenerateNE description: noted it's "Called by callers before CONGEN" and results are "merged into task via `merge_ne_into_task()`"

**Lines 196-210** (CONGENTask class):
- Added new field: `self.set_ne: list[int]` with description "Negated example (NE) assumption IDs (pre-computed by caller)"

**Lines 539-546** (CONGEN Learning Flow diagram):
- Moved GenerateNE step BEFORE CONGEN
- Annotated: "called BEFORE CONGEN"
- Added: "Merged into task via merge_ne_into_task()"

**Lines 264-273** (ConsistencyChecker docstring):
- Added annotation: "(immutable after construction)"
- Noted: "Checkers are read-only after creation. No add_clause/add_assumption mutations."
- Added: "GenerateNE runs separately before CONGEN, results merged via merge_ne_into_task()."

**Lines 564-567** (Mode-Agnostic Design section):
- Updated algorithm list: "CONGEN, ACQMSS, and REDUCE" (removed GenerateNE)
- Added: "GenerateNE is called separately by callers before CONGEN."

### 2. codebase-summary.md

**Lines 18-21** (File table):
- `congen.py`: Changed description from "GenerateNE → ACQMSS → REDUCE" to "ACQMSS → REDUCE with pre-computed NE"
- `generate_ne.py`: Changed description to clarify it's "called by caller, results merged via merge_ne_into_task"

### 3. code-standards.md

**No changes required** - code-standards.md does not contain specific CONGEN flow descriptions. Checker pattern descriptions remain valid (both checkers use identical assumption-based data).

## Key Points Updated

1. **Flow order**: GenerateNE now executes BEFORE task preparation and CONGEN
2. **Checker immutability**: ConsistencyChecker is now immutable (no add_clause/add_assumption methods)
3. **Task pre-population**: `task.set_ne` now populated by caller via `merge_ne_into_task()`
4. **API clarity**: New `merge_ne_into_task()` function exported from acqmss.algorithms

## Files Modified

- `/Users/manleviet/Development/GitHub/AcqMSS/docs/system-architecture.md` — 7 edits
- `/Users/manleviet/Development/GitHub/AcqMSS/docs/codebase-summary.md` — 1 edit

## Validation

All changes are minimal, focused updates that:
- Preserve existing documentation structure
- Maintain consistency with actual code implementation
- Use correct new API names (`merge_ne_into_task`)
- Don't introduce any breaking changes to documented patterns

Documentation now accurately reflects:
- Caller → GenerateNE → merge_ne_into_task() → task with set_ne
- task → CONGEN (with set_ne pre-populated)
- Immutable checker interface (no mutations after construction)
