---
title: "QuAcq Dependency Injection Refactor"
description: "Refactor QuAcq to use DI pattern matching ConGen: injected components, flat params, single learn() with mode"
status: complete
priority: P2
effort: 7h
branch: main
tags: [refactor, quacq, di, api]
created: 2026-02-28
completed: 2026-02-28
---

# QuAcq Dependency Injection Refactor

## Goal
Align QuAcq's API with ConGen's DI pattern: inject collaborators at construction, pass flat data at `learn()`, merge two learning methods into one with `mode` param. Eliminate QuAcqTask from algorithm internals entirely.

## Current State
- `QuAcq.__init__` creates `QueryGenerator` internally (no DI)
- `DiscriminatingGenerator` created inside `learn()` with full `QuAcqTask`
- Two separate methods: `learn()` + `learn_from_examples()`
- Both accept `QuAcqTask` object (not flat data)
- FindScope/FindC depend on QuAcqTask methods

## Target State
- `__init__` receives: `oracle`, `query_generator`, `example_provider`, `discriminating_generator`, `profiler`
- Factory class methods: `for_oracle()` (discrim_gen **required**), `for_examples()`
- Single `learn()` with `mode='oracle'|'example_only'|'example_first'` + flat raw data params
- FindScope/FindC refactored to accept raw params (NO internal QuAcqTask)
- QuAcqTask eliminated from algorithm package — only used by task_preparation for callers

## Phases

| # | Phase | File(s) | Effort | Status |
|---|-------|---------|--------|--------|
| 1 | [Refactor DiscriminatingGenerator](phase-01-refactor-discriminating-generator.md) | `discriminating_generator.py` | 30m | complete |
| 2 | [Refactor QueryGenerator](phase-02-refactor-query-generator.md) | `query_generator.py` | 45m | complete |
| 3 | [Refactor FindScope](phase-03-refactor-findscope.md) | `findscope.py` | 45m | complete |
| 4 | [Refactor FindC](phase-04-refactor-findc.md) | `findc.py` | 45m | complete |
| 5 | [Refactor QuAcq class](phase-05-refactor-quacq-class.md) | `quacq.py` | 1.5h | complete |
| 6 | [Update callers](phase-06-update-callers.md) | `quacq_runner.py`, `test_quacq.py` | 45m | complete |
| 7 | [Test and verify](phase-07-test-and-verify.md) | all | 45m | complete |

## Dependencies
- Phases 1-2 independent (parallel OK)
- Phases 3-4 independent (parallel OK), depend on Phase 1
- Phase 5 depends on 1+2+3+4
- Phase 6 depends on 5
- Phase 7 depends on 6

## Key Decisions
- `discrim_gen` **required** in `for_oracle()` — no auto-creation, fail fast
- FindScope/FindC refactored to raw params — NO internal QuAcqTask in algorithm
- Tests cover all 3 modes: oracle, example_only, example_first
- QuAcqRunner: per-run QuAcq construction (stateless, as current)

## Research Reports
- [QuAcq Internals](research/researcher-01-quacq-internals.md)
- [Callers & Tests](research/researcher-02-callers-tests.md)
- [Brainstorm](../reports/brainstorm-260228-0035-quacq-di-refactor.md)

## Validation Log

### Session 1 — 2026-02-28
**Trigger:** Initial plan creation validation
**Questions asked:** 5

#### Questions & Answers

1. **[Architecture]** Phase 3 Step 6: Nếu `self.discriminating_generator is None`, QuAcq tự tạo từ raw data. Điều này mâu thuẫn với factory pattern. Nên xử lý thế nào?
   - Options: Required in for_oracle() | Keep auto-create | Optional, warn if missing
   - **Answer:** Required in for_oracle()
   - **Rationale:** Consistent with factory pattern: inject all deps, fail fast if missing. Prevents hidden internal construction.

2. **[Architecture]** Plan xây dựng QuAcqTask nội bộ từ flat params trong learn(). Chấp nhận hay refactor FindScope/FindC luôn?
   - Options: Chấp nhận (Recommended) | Refactor FindScope/FindC
   - **Answer:** Refactor FindScope/FindC
   - **Rationale:** Eliminates QuAcqTask from algorithm entirely. Clean architecture — no hidden object reconstruction.

3. **[Scope]** Refactor FindScope/FindC tăng scope từ ~4h lên ~6-7h. Xác nhận?
   - Options: Xác nhận refactor full | Thu hẹp: chỉ bỏ QuAcqTask từ public API | Progressive: 2 PRs
   - **Answer:** Xác nhận refactor full
   - **Rationale:** One-shot refactor avoids intermediate inconsistencies. Worth the extra effort for clean result.

4. **[Testing]** Sau merge learn(), thêm test cho example modes?
   - Options: Thêm test cơ bản | Không thêm | Thêm đầy đủ 3 modes
   - **Answer:** Thêm đầy đủ 3 modes
   - **Rationale:** Coverage for all mode branches ensures no regressions. learn_from_examples had zero test coverage.

5. **[Architecture]** QuAcqRunner: tạo QuAcq mới per-run hay reuse?
   - Options: Per-run (Recommended) | Reuse in __init__
   - **Answer:** Per-run (Recommended)
   - **Rationale:** Stateless, simple, no side effects between runs. Matches current pattern.

#### Confirmed Decisions
- `discrim_gen` required in `for_oracle()` — fail fast, no auto-create
- FindScope/FindC refactored to raw params — full QuAcqTask elimination
- All 3 modes tested — oracle, example_only, example_first
- Per-run QuAcq construction in runner — unchanged pattern

#### Action Items
- [x] Add Phase 3 (FindScope refactor) and Phase 4 (FindC refactor)
- [x] Update Phase 5 (was 3): remove internal QuAcqTask, discrim_gen required
- [x] Update Phase 7 (was 5): add 3-mode test coverage
- [x] Update effort estimate: 4h → 7h
- [x] Renumber phases: 1-2 unchanged, 3-4 new, 5-7 renumbered

#### Impact on Phases
- Phase 3 (NEW): FindScope refactored to raw params — inline task methods as standalone functions
- Phase 4 (NEW): FindC refactored to raw params — same approach as FindScope
- Phase 5 (was 3): Remove internal QuAcqTask construction; discrim_gen required in for_oracle(); QuAcq.learn() passes raw data to FindScope/FindC directly
- Phase 7 (was 5): Add test coverage for all 3 modes (oracle, example_only, example_first)
