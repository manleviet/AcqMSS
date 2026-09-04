# Phase 2: Write ConGen Documentation

## Priority
P2

## Status
complete

## Overview
Write `docs/congen.md` following the exact style/format of `docs/quacq.md`. Uses research summary from Phase 1 as source material.

## Context Links
- Phase 1 research: `plans/260216-1415-congen-documentation/phase-01-research-paper-and-code.md`
- Style template: `docs/quacq.md` (194 lines)
- Paper: `paper/AcqMSS.pdf`

## Key Insights
- `docs/quacq.md` structure: Overview -> Implementation Modes -> Sub-algorithms -> Complexity -> Experimental Results -> Key Advantages -> Relation to Codebase -> Shared Infrastructure -> CV Support
- ConGen is simpler than QuAcq (one mode: passive/batch), so doc should be shorter
- Paper has a detailed working example (Tables 1-6, Figure 1) worth including
- Implementation has details beyond paper: builder pattern, prepare(), assumption-based representation

## Requirements

### Functional
- Document all 3 algorithms with pseudocode blocks
- Include paper's formal definitions (vocabulary, bias, constraint acquisition problem)
- Include working example walkthrough
- Map every algorithm to source file with LOC
- Include complexity analysis and correctness theorems
- Document evaluation methodology (sampling, CV, accuracy formula)

### Non-Functional
- Under 800 lines total
- Follow `docs/quacq.md` format exactly (headers, tables, code blocks)
- Sacrifice grammar for concision
- Use same table formatting as quacq.md

## Target Document Structure

```markdown
# ConGen - Constraint Acquisition With Maximum Satisfiable Subsets

**Last Updated**: 2026-02-16
**Paper:** [citation]

## Overview
- What ConGen does (passive/batch constraint acquisition via MSS)
- Problem definition (Definition 6 from paper)
- Key idea: MSS of bias B that accepts E+ and rejects E-

## Formal Definitions
- Definition 1-5 from paper (vocabulary, constraint theory, target, language, bias)
- Definition 6: Constraint Acquisition Problem

## Working Example
- Variables (Table 1), Target C_T (Table 2), Training Set (Table 4)
- Bias B (Table 3), Background Knowledge BG (Table 5)
- Step-by-step walkthrough showing B' derivation (Table 6)

## Algorithm Pipeline
- High-level: GenerateNE -> IsConsistent check -> AcqMSS -> REDUCE
- Algorithm 1 pseudocode

## GenerateNE
- Purpose: negate E- into NE constraints
- QuickXPlain for minimal conflict per e-
- Subset minimality requirement

## AcqMSS (Algorithm 2)
- Divide-and-conquer MSS finding
- Pseudocode
- IsConsistent/TestC role
- Recursive split strategy

## REDUCE (Algorithm 3)
- Redundancy elimination via logical entailment
- c redundant if BG U (KB - {c}) |= c
- Pseudocode

## Complexity Analysis
- AcqMSS worst/best case (table)
- Conflict determination complexity
- Comparison note with HSDAG

## Correctness and Completeness
- Theorem 1 (Correctness): B' accepts all E+
- Theorem 2 (Completeness): ConGen returns B' subset of B
- Corollary 1: Failure condition
- Remark 1: Empty B' case

## Experimental Setup
- Oracle-based evaluation (FM knowledge bases)
- Sampling methods: RS, 2-COV, FF
- n-fold cross-validation
- Accuracy formula

## Key Advantages
1. Passive learning (no user interaction)
2. Partial examples supported
3. Divide-and-conquer efficiency
4. MSS guarantees (accepts all E+)
5. Redundancy elimination via REDUCE
6. Oracle integration for automated evaluation

## Relation to Codebase
- Table: file -> LOC -> purpose (same format as quacq.md)
- Core implementation files
- Evaluation support files

## Implementation Details Beyond Paper
- ConGenModel.prepare() internalizes GenerateNE
- Builder pattern (ConGenModelBuilder)
- Assumption-based representation (mode-agnostic)
- negation_map for REDUCE
- Tseitin encoding for clause negation
- CV fold reuse

## Shared Infrastructure with QuAcq
- Same SAT solvers
- Same FM representation
- Same bias generation pipeline
- Same evaluation framework
- Shared CV folds (fold_io.py)

## Cross-Validation Support
- Code example (same style as quacq.md)
- Key features: per-fold bias shuffling, shared folds
```

## Related Code Files

### Files to Read (already read in Phase 1)
- `acqmss/algorithms/congen.py` (228 LOC)
- `acqmss/algorithms/acqmss.py` (104 LOC)
- `acqmss/algorithms/reduce.py` (155 LOC)
- `acqmss/algorithms/generate_ne.py` (193 LOC)
- `acqmss/algorithms/task_preparation.py` (435 LOC)
- `acqmss/algorithms/congen_model.py` (186 LOC)
- `acqmss/algorithms/congen_model_builder.py` (157 LOC)

### File to Create
- `docs/congen.md`

## Implementation Steps

1. Create `docs/congen.md` with header matching quacq.md style
2. Write Overview section (paper abstract + introduction summary)
3. Write Formal Definitions section (Definitions 1-6)
4. Write Working Example section (Tables 1-6 from paper)
5. Write Algorithm Pipeline section (Algorithm 1 with pseudocode)
6. Write GenerateNE section (NE generation + QuickXPlain)
7. Write AcqMSS section (Algorithm 2 with pseudocode)
8. Write REDUCE section (Algorithm 3 with pseudocode)
9. Write Complexity Analysis section (table format)
10. Write Correctness and Completeness section (Theorems 1-2)
11. Write Experimental Setup section (sampling, CV, accuracy)
12. Write Key Advantages section (numbered list)
13. Write Relation to Codebase section (file table)
14. Write Implementation Details section (beyond paper)
15. Write Shared Infrastructure section
16. Write Cross-Validation Support section (code example)
17. Review: verify under 800 lines, matches quacq.md style
18. Update `docs/README.md` to include congen.md link (if README has doc index)

## Todo

- [x] Write docs/congen.md header + Overview
- [x] Write Formal Definitions
- [x] Write Working Example
- [x] Write Algorithm Pipeline + GenerateNE + AcqMSS + REDUCE
- [x] Write Complexity Analysis + Correctness
- [x] Write Experimental Setup + Key Advantages
- [x] Write Relation to Codebase + Implementation Details
- [x] Write Shared Infrastructure + CV Support
- [x] Verify line count < 800
- [x] Update docs/README.md if needed

## Success Criteria
- [x] File exists at `docs/congen.md`
- [x] Format matches `docs/quacq.md` exactly
- [x] All 3 algorithms have pseudocode blocks
- [x] Paper theorems summarized
- [x] Working example included
- [x] Source files mapped with LOC
- [x] Under 800 lines
- [x] `docs/README.md` updated if it has a doc index

## Risk Assessment
- **Line count risk**: Working example + 3 algorithms + definitions could exceed 800 lines
  - Mitigation: Keep working example compact (merge tables), use concise descriptions
- **Paper TBD tables**: Experimental results tables are TBD in paper draft
  - Mitigation: Document methodology and formula, note results as TBD
