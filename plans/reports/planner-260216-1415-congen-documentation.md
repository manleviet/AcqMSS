# Planner Report: ConGen Documentation

**Date**: 2026-02-16
**Plan**: `plans/260216-1415-congen-documentation/`

## Summary

Created a 2-phase implementation plan for writing comprehensive ConGen algorithm documentation in `docs/congen.md`.

## Research Findings

### Paper Analysis (paper/AcqMSS.pdf, 7 pages)
- ConGen = passive/batch constraint acquisition via MSS of constraint bias
- 3 sub-algorithms: GenerateNE (negate E- via QuickXPlain), AcqMSS (divide-and-conquer MSS), REDUCE (redundancy elimination via entailment)
- 6 formal definitions (vocabulary, constraint theory, target, language, bias, acquisition problem)
- Detailed working example: 3 Boolean variables, 18 bias constraints, traces through AcqMSS execution tree (Figure 1)
- Complexity: AcqMSS worst-case 2*gamma*log2(n/gamma)+2*gamma checks; best-case log2(n/gamma)+2*gamma
- Correctness (Theorem 1) + Completeness (Theorem 2) proven
- Experimental tables marked TBD in paper draft

### Codebase Mapping
- 7 core implementation files (~1,458 LOC total in algorithms/)
- ConGen pipeline: ConGenModelBuilder -> ConGenModel.prepare() (runs GenerateNE internally) -> CheckerFactory -> ConGen.acquire() (AcqMSS + REDUCE)
- Evaluation: cross_validation.py (504 LOC), congen_runner.py (228 LOC), accuracy.py (170 LOC)
- Implementation adds: builder pattern, assumption-based representation, negation_map, Tseitin encoding, CV fold reuse

### Style Reference
- `docs/quacq.md` (194 lines): Overview -> Sub-algorithms -> Complexity table -> Experimental Results table -> Key Advantages list -> Relation to Codebase file table -> Shared Infrastructure -> CV Support with code example

## Plan Structure

| Phase | Description | Effort |
|-------|-------------|--------|
| Phase 1 | Research paper and code (completed in this planning session) | 45m |
| Phase 2 | Write docs/congen.md | 1h15m |

## Files Created

- `plans/260216-1415-congen-documentation/plan.md` - Overview (50 lines)
- `plans/260216-1415-congen-documentation/phase-01-research-paper-and-code.md` - Full research summary with algorithms, definitions, code mapping (170 lines)
- `plans/260216-1415-congen-documentation/phase-02-write-congen-documentation.md` - Writing plan with target structure, steps, success criteria (140 lines)

## Unresolved Questions

1. **Paper experimental results**: Tables 7-12 all show TBD values. Document methodology but note results pending, or omit tables entirely?
2. **docs/README.md**: Need to check if it has a documentation index to update with congen.md link.
