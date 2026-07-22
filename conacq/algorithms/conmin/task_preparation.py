"""Task preparation for ConMin.

ConMin's Stage-1 task is identical to ConGen's, so ``ConMinTaskPreparation``
**subclasses** ``ConGenTaskPreparation`` and reuses all of ``prepare`` (same
assumption-ID allocation → Stage-1 golden unchanged), overriding just two hooks:

- ``_prepare_negative_examples`` — additive: run ``GenerateNE`` with
  ``capture_assignments`` so each ``e⁻`` keeps its full-config assignment aids
  (design brief §2), and **register a ``negation_map`` entry per ``e⁻``** so the
  ``¬e⁻`` fallbacks are Reduce-able (the combined-NE prep leaves the per-``e⁻``
  negated forms built but unregistered — ``reduce.py`` would silently skip them).
  No new ids are allocated, so the Stage-1 golden `d13274bc…` is preserved.
- ``_make_task`` — return a ``ConMinTask`` carrying ``neg_encodings``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Dict, List, Mapping, Optional, Tuple

from explanation.api import (
    AssumptionIdAllocator,
    DescriptionProvider,
    PreparedTask,
    TestCaseTask,
    TestSuite,
)
from conacq.algorithms.acqmss import ConGenTaskInput, ConGenTaskPreparation
from conacq.algorithms.acqmss.generate_ne import GenerateNE

from .acqmincover import NegEncoding
from .support import build_support_count

if TYPE_CHECKING:
    from conacq.oracle import OracleData
    from .conmin_model import ConMinModel


@dataclass(frozen=True)
class ConMinTaskInput:
    """Per-preparation input for ``ConMinModel.prepare_task`` (ConMin's own type,
    ADR-0006). Fields mirror ``ConGenTaskInput``; ``from_examples`` reuses ConGen's
    example→TestSuite normalisation."""

    oracle_data: "OracleData"
    positive_test_cases: TestSuite
    negative_test_cases: Optional[TestSuite] = None

    @classmethod
    def from_examples(
            cls,
            oracle_data: "OracleData",
            positive_examples: Optional[List[Dict[str, bool]]],
            negative_examples: Optional[List[Dict[str, bool]]],
    ) -> "ConMinTaskInput":
        ci = ConGenTaskInput.from_examples(
            oracle_data, positive_examples, negative_examples)
        return cls(ci.oracle_data, ci.positive_test_cases, ci.negative_test_cases)


@dataclass(frozen=True)
class ConMinTask(TestCaseTask):
    """Immutable ConMin task. Adds ``neg_encodings`` (one per ``e⁻``, each carrying
    that ``e⁻``'s full-config assignment-assumption IDs for AcqMinCover's rejection
    test) and ``support_count`` (bias-aid → support⁺ over E⁺, precomputed at prep)."""

    neg_encodings: Tuple[NegEncoding, ...] = ()
    support_count: Mapping[int, int] = field(default_factory=dict)


class ConMinTaskPreparation(ConGenTaskPreparation):
    """Prepare a ConMin task; subclass of ConGen's prep (byte-identical Stage-1 IDs)."""

    def prepare(self, model: "ConMinModel", task_input: ConMinTaskInput) -> PreparedTask:
        """Reuse ConGen's Stage-1 prep, then attach the precomputed support⁺ counts
        (structural, solver-free) over the bias against this fold's E⁺."""
        # Reset the per-call neg_encodings hand-off (defensive: a fold with zero
        # negatives skips _prepare_negative_examples, so without this a reused prep
        # instance could leak the previous fold's encodings into _make_task).
        self._neg_encodings: Tuple[NegEncoding, ...] = ()
        prepared = super().prepare(model, task_input)
        task = prepared.task
        support_count = build_support_count(
            task.set_c, prepared.describe, model.constraint_map,
            model.name_to_id, task_input.positive_test_cases)
        task = replace(task, support_count=support_count)
        return PreparedTask(task, prepared.describe)

    def _prepare_negative_examples(
            self,
            set_kb: List[List[int]],
            assumptions: List[int],
            negation_map: Dict[int, int],
            set_neg_tv: List[int],
            provider: DescriptionProvider,
            model: "ConMinModel",
            oracle_data: "OracleData",
            testsuite: TestSuite,
            alloc: AssumptionIdAllocator,
    ) -> None:
        """ConMin NE step: same allocations as ConGen, plus per-e⁻ negation
        registration and neg_encodings capture (additive)."""
        generate_ne = GenerateNE(oracle_data)
        ne_results = generate_ne.generate(
            testsuite, model.name_to_id, set_kb, assumptions, alloc,
            capture_assignments=True)

        neg_tv_ids = [ne.ne_id for ne in ne_results]
        descs = [ne.desc for ne in ne_results]

        ne_id = self._combine_ne_constraints(
            set_kb, assumptions, set_neg_tv, provider, neg_tv_ids, descs, alloc)

        per_e_negations: Dict[int, int] = {}
        negated_ne_id = self._create_negated_ne(
            set_kb, assumptions, provider, ne_id, neg_tv_ids, alloc,
            per_e_negations_out=per_e_negations)
        negation_map[ne_id] = negated_ne_id

        # Critical fix: register each per-e⁻ ne_id's (already-built) negated form so a
        # ¬e⁻ fallback for an uncoverable e⁻ is Reduce-able (no id allocated here).
        for per_e_ne_id, per_e_neg in per_e_negations.items():
            negation_map[per_e_ne_id] = per_e_neg

        # Capture one NegEncoding per e⁻ (full-config assignment aids) for AcqMinCover.
        self._neg_encodings = tuple(
            NegEncoding(neg_id=ne.ne_id, assumption_ids=tuple(ne.assignment_aids))
            for ne in ne_results)

    def _make_task(self, **fields) -> TestCaseTask:
        return ConMinTask(**fields, neg_encodings=getattr(self, "_neg_encodings", ()))
