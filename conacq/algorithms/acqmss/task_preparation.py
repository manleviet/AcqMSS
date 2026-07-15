"""
Task preparation for ConGen algorithm.

Contains ConGenTask dataclass and ConGenTaskPreparation strategy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from explanation.api import (
    Assignment,
    AssumptionIdAllocator,
    TestCase,
    TaskPreparationStrategy,
    TestCaseTask,
    TestSuite,
    DescriptionProvider,
    PreparedTask, prepare_testsuite_with_negation,
    prepare_kb,
)
from .generate_ne import GenerateNE

if TYPE_CHECKING:
    from .congen_model import ConGenModel
    from conacq.oracle import OracleData


@dataclass(frozen=True)
class ConGenTaskInput:
    """Per-preparation input for ConGenModel.prepare_task: the oracle's frozen
    provisioning snapshot plus this fold's examples. ConGen's own input type — the
    prepare_task signature is unified across models, the input TYPE is not (a shared
    union would be the fat-container anti-pattern removed at T9, ADR-0006).

    ``negative_test_cases`` is an empty TestSuite (not None) when there is no E-, so
    the prep's ``is not None`` set-assignment behaves exactly as the old mailbox did.
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
    ) -> "ConGenTaskInput":
        """Build a ConGenTaskInput from raw example dicts ({feature: bool}).

        Missing E+/E- become empty TestSuites — the same normalisation the model's
        prepare() used to do internally before the mailbox was cut.
        """
        return cls(
            oracle_data,
            _examples_to_testsuite(positive_examples or []),
            _examples_to_testsuite(negative_examples or []),
        )


def _examples_to_testsuite(examples: List[Dict[str, bool]]) -> TestSuite:
    """Convert a list of example dicts ({feature: bool}) to a TestSuite."""
    testcases = []
    for example in examples:
        assignments = [
            Assignment(feature=name, value=value)
            for name, value in example.items()
        ]
        testcases.append(TestCase(assignments=assignments))
    return TestSuite(testcases=testcases)


@dataclass(frozen=True)
class ConGenTask(TestCaseTask):
    """Immutable task for ConGen algorithm.

    Inherits from TestCaseTask with mapping:
    - set_c: Bias constraints (B) - assumption IDs
    - set_b: Background knowledge (BG) - assumption IDs
    - set_kb: Full KB with assumptions (clauses with assumption literals)
    - negation_map: Dict[int, int] - negation map for REDUCE
    - assumptions: List of all assumption IDs (for reference)
    - set_tc: Positive examples (E+) - assumption IDs
    - set_tv: Negative examples (E-) - assumption IDs
    - set_neg_tv: Negated negative examples (NE) - populated by GenerateNE
    Inherited from TestCaseTask (unused by ConGen):
    - set_neg_tc

    Naming: Use DescriptionProvider (from PreparedTask) to map assumption IDs
    to human-readable names. It covers all assumptions (bias, root, test cases, NE).
    """
    pass  # No additional fields needed


class ConGenTaskPreparation(TaskPreparationStrategy):
    """Prepare ConGen task using assumptions.

    Data mapping:
    - set_c: Bias constraints (B) with individual assumptions
    - set_b: Background knowledge (BG) - root from Oracle via BGData
    - set_tc: Positive examples (E+) with assumptions
    - set_tv: Negative examples (E-) with assumptions
    - set_neg_tv: Negated negative examples (NE)
    - negation_map: Negation map for REDUCE
    """

    def prepare(self, model: ConGenModel, task_input: "ConGenTaskInput") -> PreparedTask:
        """Prepare ConGen task from model + task input.

        BG + KB come from the frozen OracleData snapshot carried on the task input;
        E+/E- come from the same input. The model is a pure KB — it no longer holds
        the task input, so it is passed in explicitly (was ``model.task_input``).

        Shared Assumption ID Layout (ConGen owns Parts 5-8):
          Parts 1-4: Owned by Oracle (see OracleTaskPreparation)
          Part 5: Tseitin vars (negated bias constraints)    <- This method
          Part 6: Bias constraint assumptions (paired)       <- This method
          Part 7: Positive test case assumptions (paired)    <- This method
          Part 8: NE + negated NE                            <- This method

        ConGen starts from bg_data.next_available_id (end of Oracle Part 4).
        Root BG (Part 3 first pair) is copied from Oracle via BGData.

        Build-then-freeze: every field accumulates into a local, then the frozen
        ConGenTask is constructed once at the end.
        """
        provider = DescriptionProvider()
        oracle_data = task_input.oracle_data

        # Local accumulation
        set_kb: List[List[int]] = []
        assumptions: List[int] = []
        negation_map: Dict[int, int] = {}
        set_neg_tv: List[int] = []
        set_neg_tc: List[int] = []

        # Step 0: Copy BG data from Oracle (root constraint pair from Part 3)
        bg_data = oracle_data.get_bg_data()
        set_kb.extend(bg_data.set_kb)
        assumptions.extend(list(bg_data.assumptions))
        negation_map.update(bg_data.negation_map)
        for aid, desc in bg_data.descriptions.items():
            provider.add_constraint_description(aid, desc)

        # Step 1: bias constraints → set_c (exactly the originals prepare_kb emitted,
        # returned directly). set_b is the BG root (first assumption, Part 3).
        alloc = AssumptionIdAllocator(model.next_available_id)
        set_c = prepare_kb(
            set_kb, assumptions, negation_map, provider,
            model.constraint_map, alloc, model.negated_constraint_map)
        set_b = [assumptions[0]]

        # Step 2: E+ → set_tc (the originals); its negated forms populate the
        # ConGen-unused set_neg_tc, preserved for task-content parity.
        set_tc, pos_negated_ids = prepare_testsuite_with_negation(
            set_kb, assumptions, negation_map, provider, model.name_to_id,
            task_input.positive_test_cases, alloc)
        set_neg_tc.extend(pos_negated_ids)

        # E- is transformed into NE (set_neg_tv) below, never stored as set_tv.
        set_tv: List[int] = []

        # Step 3: Prepare E- as NE via GenerateNE (appends to set_kb/assumptions/set_neg_tv)
        testsuite = task_input.negative_test_cases
        if testsuite is not None and len(testsuite.testcases) > 0:
            self._prepare_negative_examples(
                set_kb, assumptions, negation_map, set_neg_tv,
                provider, model, oracle_data, testsuite, alloc)

        # NOTE: Do NOT update model.next_available_id here.
        # model.next_available_id was set by the builder at build time and should remain fixed.
        # Updating it here would cause subsequent prepare() calls to allocate IDs from wrong range.

        logging.debug('<<< ConGenTaskPreparation: set_c=%d, set_tc=%d, set_tv=%d',
                      len(set_c), len(set_tc), len(set_tv))

        task = ConGenTask(
            set_c=set_c, set_b=set_b, set_kb=set_kb,
            negation_map=negation_map, assumptions=assumptions,
            set_tc=set_tc, set_tv=set_tv,
            set_neg_tv=set_neg_tv, set_neg_tc=set_neg_tc)
        return PreparedTask(task, provider)

    def _prepare_negative_examples(
            self,
            set_kb: List[List[int]],
            assumptions: List[int],
            negation_map: Dict[int, int],
            set_neg_tv: List[int],
            provider: DescriptionProvider,
            model: ConGenModel,
            oracle_data: "OracleData",
            testsuite: TestSuite,
            alloc: AssumptionIdAllocator
    ) -> None:
        """Step 3: Generate NE from negative examples.

        Orchestrates: GenerateNE -> combine -> negate -> populate locals.
        """

        generate_ne = GenerateNE(oracle_data)
        ne_results = generate_ne.generate(
            testsuite, model.name_to_id, set_kb, assumptions, alloc)

        neg_tv_ids = [ne.ne_id for ne in ne_results]
        descs = [ne.desc for ne in ne_results]

        ne_id = self._combine_ne_constraints(
            set_kb, assumptions, set_neg_tv, provider, neg_tv_ids, descs, alloc)

        negated_ne_id = self._create_negated_ne(
            set_kb, assumptions, provider, ne_id, neg_tv_ids, alloc)

        negation_map[ne_id] = negated_ne_id

    @staticmethod
    def _combine_ne_constraints(
            set_kb: List[List[int]],
            assumptions: List[int],
            set_neg_tv: List[int],
            provider: DescriptionProvider,
            neg_tv_ids: List[int],
            descs: List[str],
            alloc: AssumptionIdAllocator
    ) -> int:
        """Combine NEs into single assumption for set_neg_tv.

        Single NE: use directly. Multiple NEs: conjunction via implication clauses.
        Returns: ne_id
        """
        if len(neg_tv_ids) > 1:
            ne_id = alloc.allocate()
            for neg_tv_id in neg_tv_ids:
                set_kb.append([neg_tv_id, -ne_id])
            assumptions.append(ne_id)
            provider.add_test_case_description(ne_id, f"({' AND '.join(descs)})")
            set_neg_tv.append(ne_id)
        else:
            ne_id = neg_tv_ids[0]
            assumptions.append(ne_id)
            provider.add_test_case_description(ne_id, descs[0])
            set_neg_tv.append(ne_id)

        return ne_id

    @staticmethod
    def _create_negated_ne(
            set_kb: List[List[int]],
            assumptions: List[int],
            provider: DescriptionProvider,
            ne_id: int,
            neg_tv_ids: List[int],
            alloc: AssumptionIdAllocator
    ) -> int:
        """Create negated form of NE for REDUCE.

        not(not(e1) and not(e2) and ...) = (e1 or e2 or ...)
        Returns: negated_ne_id
        """
        if len(neg_tv_ids) > 1:
            negated_ne_ids = []
            for neg_tv_id in neg_tv_ids:
                negated_ne_id = alloc.allocate()
                set_kb.append([-neg_tv_id, -negated_ne_id])
                negated_ne_ids.append(negated_ne_id)
            negated_ne_id = alloc.allocate()
            set_kb.append(negated_ne_ids + [-negated_ne_id])
        else:
            negated_ne_id = alloc.allocate()
            set_kb.append([-ne_id, -negated_ne_id])

        assumptions.append(negated_ne_id)
        provider.add_test_case_description(negated_ne_id, f"NOT({provider.get_description(ne_id)})")

        return negated_ne_id
