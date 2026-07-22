"""Task preparation for ConMin (P1: Stage-1 fields, delegated to ConGen prep).

ConMin's Stage-1 task is identical to ConGen's, so ``ConMinTaskPreparation`` reuses
``ConGenTaskPreparation`` by composition. Reusing the exact same assumption-ID
allocation makes the ConMin task fields byte-identical to a ConGen task built from
the same inputs — Stage-1 ID parity holds by construction, not by hope.

This is a P1-local choice, NOT the arc endpoint: the delegated prep is a black box
that discards the per-e- NE assignment-assumption IDs that P3's ``neg_encodings``
(design brief §2) will need. P3 re-decides this seam (subclass the already-factored
``ConGenTaskPreparation._prepare_negative_examples`` hook, and/or surface those IDs
out of ``GenerateNE``). Until then, delegation is the zero-baseline-risk minimum.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Dict, Optional

from explanation.api import (
    TestCaseTask,
    TaskPreparationStrategy,
    PreparedTask,
    TestSuite,
)
from conacq.algorithms.acqmss import ConGenTaskInput, ConGenTaskPreparation

if TYPE_CHECKING:
    from conacq.oracle import OracleData
    from .conmin_model import ConMinModel


@dataclass(frozen=True)
class ConMinTaskInput:
    """Per-preparation input for ``ConMinModel.prepare_task``: the oracle's frozen
    provisioning snapshot plus this fold's examples.

    ConMin's own input type (the ``prepare_task`` signature is unified across models,
    the input TYPE is not — ADR-0006). The fields mirror ``ConGenTaskInput`` because
    P1's Stage-1 preparation is delegated to ConGen's; the prep reads this input only
    by attribute, so it is passed straight through (no clone/convert).
    """

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
        """Build a ConMinTaskInput from raw example dicts ({feature: bool}).

        Reuses ConGen's example→TestSuite normalisation (missing E+/E- become empty
        TestSuites) rather than duplicating it.
        """
        ci = ConGenTaskInput.from_examples(
            oracle_data, positive_examples, negative_examples)
        return cls(ci.oracle_data, ci.positive_test_cases, ci.negative_test_cases)


@dataclass(frozen=True)
class ConMinTask(TestCaseTask):
    """Immutable ConMin task.

    P1 carries exactly the Stage-1 fields inherited from ``TestCaseTask`` (same set as
    ``ConGenTask``). P3 adds ``neg_encodings`` and ``support_count`` (with defaults).
    """

    pass  # No additional fields in P1.


class ConMinTaskPreparation(TaskPreparationStrategy):
    """Prepare a ConMin Stage-1 task by delegating to ``ConGenTaskPreparation``.

    Byte-identical assumption-ID layout to ConGen (same oracle snapshot, same
    allocation order) → Stage-1 parity by construction.
    """

    def prepare(self, model: "ConMinModel", task_input: ConMinTaskInput) -> PreparedTask:
        # Pass task_input straight in: ConGenTaskPreparation.prepare reads it only by
        # attribute (.oracle_data / .positive_test_cases / .negative_test_cases), all
        # present on ConMinTaskInput. Duck-typed on both model and input — the prep
        # touches only KBModel-level model fields, and a ConMinModel is a KBModel.
        prepared = ConGenTaskPreparation().prepare(model, task_input)
        ct = prepared.task
        task = ConMinTask(
            set_c=ct.set_c, set_b=ct.set_b, set_kb=ct.set_kb,
            negation_map=ct.negation_map, assumptions=ct.assumptions,
            set_tc=ct.set_tc, set_tv=ct.set_tv,
            set_neg_tv=ct.set_neg_tv, set_neg_tc=ct.set_neg_tc)
        return PreparedTask(task, prepared.describe)
