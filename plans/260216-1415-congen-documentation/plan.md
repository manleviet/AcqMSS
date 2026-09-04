---
title: "ConGen Algorithm Documentation"
description: "Write comprehensive documentation for ConGen algorithm based on paper and source code"
status: complete
priority: P2
effort: 2h30m
branch: main
tags: [documentation, congen, algorithm]
created: 2026-02-16
completed: 2026-02-16
---

# ConGen Algorithm Documentation Plan

## Objective

Create `docs/congen.md` documenting the ConGen (Constraint Acquisition With Maximum Satisfiable Subsets) algorithm. Follow `docs/quacq.md` style exactly.

## Phases

| # | Phase | Status | Effort |
|---|-------|--------|--------|
| 1 | [Research paper and code](phase-01-research-paper-and-code.md) | complete | 45m |
| 2 | [Write docs/congen.md](phase-02-write-congen-documentation.md) | complete | 1h15m |
| 3 | [Cross-link docs](phase-03-cross-link-documentation.md) | complete | 30m |

## Key Dependencies

- Paper: `paper/AcqMSS.pdf` (7 pages)
- Template: `docs/quacq.md` (194 lines)
- Source: `acqmss/algorithms/` (congen.py, acqmss.py, reduce.py, generate_ne.py, task_preparation.py, congen_model.py, congen_model_builder.py)
- Eval: `acqmss/eval/` (cross_validation.py, congen_runner.py)

## Target Output

Single file: `docs/congen.md` (~400-600 lines), covering:
- Algorithm overview and motivation (paper Sections 1-2)
- Three sub-algorithms: GenerateNE, AcqMSS, REDUCE (paper Algorithms 1-3)
- Complexity analysis and correctness theorems (paper Section "Analysis and Evaluation")
- Working example walkthrough (paper Tables 1-6, Figure 1)
- Codebase mapping (files, LOC, patterns)
- Shared infrastructure with QuAcq
- Cross-validation and evaluation support

## Success Criteria

- [x] Follows docs/quacq.md format exactly
- [x] All 3 algorithms documented with pseudocode
- [x] Paper theorems/proofs summarized
- [x] Working example from paper included
- [x] Source files mapped with LOC
- [x] Under 800 lines (383 lines)
- [x] CLAUDE.md updated with congen.md reference
- [x] README.md documentation table includes congen.md
- [x] docs/README.md fully cross-linked (section, stats, flow diagram, roles)
