"""
Task preparation for ConGen algorithm.

Contains ConGenTask dataclass and ConGenTaskPreparation strategy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Tuple

from explanation.api import (
    TestCaseTask,
    TestCaseTaskPreparationStrategy,
    DescriptionProvider,
    PreparedTask, prepare_testsuite_with_negation,
    prepare_kb,
    slice_assumptions,
)
from .generate_ne import GenerateNE

if TYPE_CHECKING:
    from explanation.api import TestSuite
    from .congen_model import ConGenModel
    from conacq.oracle import FeatureModelOracle


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


class ConGenTaskPreparation(TestCaseTaskPreparationStrategy):
    """Prepare ConGen task using assumptions.

    Data mapping:
    - set_c: Bias constraints (B) with individual assumptions
    - set_b: Background knowledge (BG) - root from Oracle via BGData
    - set_tc: Positive examples (E+) with assumptions
    - set_tv: Negative examples (E-) with assumptions
    - set_neg_tv: Negated negative examples (NE)
    - negation_map: Negation map for REDUCE
    """

    def __init__(self, mode_name: str = "congen"):
        self._mode_name = mode_name

    @property
    def mode_name(self) -> str:
        return self._mode_name

    def prepare(self, model: ConGenModel, oracle: FeatureModelOracle) -> PreparedTask:
        """Prepare ConGen task from model. BG from Oracle, oracle for GenerateNE.

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
        task_input = model.task_input

        # Local accumulation
        set_kb: List[List[int]] = []
        assumptions: List[int] = []
        negation_map: Dict[int, int] = {}
        set_neg_tv: List[int] = []
        set_neg_tc: List[int] = []

        # Step 0: Copy BG data from Oracle (root constraint pair from Part 3)
        bg_data = oracle.get_bg_data()
        set_kb.extend(bg_data.set_kb)
        assumptions.extend(list(bg_data.assumptions))
        negation_map.update(bg_data.negation_map)
        for aid, desc in bg_data.descriptions.items():
            provider.add_constraint_description(aid, desc)

        # Step 1: Prepare bias constraints as set_c (negated forms from builder)
        bias_start_pos = len(assumptions)
        id_assumption = model.next_available_id
        id_assumption = prepare_kb(
            set_kb, assumptions, negation_map, provider,
            model.constraint_map, id_assumption, model.negated_constraint_map)

        # Step 2: Prepare E+ as set_tc (its negated forms populate the
        # ConGen-unused set_neg_tc, preserved for task-content parity)
        tc_start_pos = len(assumptions)
        id_assumption, pos_negated_ids = prepare_testsuite_with_negation(
            set_kb, assumptions, negation_map, provider, model.name_to_id,
            task_input.positive_test_cases, id_assumption)
        set_neg_tc.extend(pos_negated_ids)

        tv_start_pos = len(assumptions)
        set_b, set_c, set_tc, set_tv = self._assign_sets(
            assumptions, bias_start_pos, tc_start_pos, tv_start_pos,
            task_input.negative_test_cases is not None)

        # Step 3: Prepare E- as NE via GenerateNE (appends to set_kb/assumptions/set_neg_tv)
        testsuite = task_input.negative_test_cases
        if testsuite is not None and len(testsuite.testcases) > 0:
            id_assumption = self._prepare_negative_examples(
                set_kb, assumptions, negation_map, set_neg_tv,
                provider, model, oracle, testsuite, id_assumption)

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
            oracle: FeatureModelOracle,
            testsuite: TestSuite,
            id_assumption: int
    ) -> int:
        """Step 3: Generate NE from negative examples.

        Orchestrates: GenerateNE -> combine -> negate -> populate locals.
        """

        generate_ne = GenerateNE(oracle)
        ne_results, id_assumption = generate_ne.generate(
            testsuite, model.name_to_id, set_kb, assumptions, id_assumption)

        neg_tv_ids = [ne.ne_id for ne in ne_results]
        descs = [ne.desc for ne in ne_results]

        ne_id, id_assumption = self._combine_ne_constraints(
            set_kb, assumptions, set_neg_tv, provider, neg_tv_ids, descs, id_assumption)

        negated_ne_id, id_assumption = self._create_negated_ne(
            set_kb, assumptions, provider, ne_id, neg_tv_ids, id_assumption)

        negation_map[ne_id] = negated_ne_id
        return id_assumption

    @staticmethod
    def _combine_ne_constraints(
            set_kb: List[List[int]],
            assumptions: List[int],
            set_neg_tv: List[int],
            provider: DescriptionProvider,
            neg_tv_ids: List[int],
            descs: List[str],
            id_assumption: int
    ) -> Tuple[int, int]:
        """Combine NEs into single assumption for set_neg_tv.

        Single NE: use directly. Multiple NEs: conjunction via implication clauses.
        Returns: (ne_id, id_assumption)
        """
        if len(neg_tv_ids) > 1:
            ne_id = id_assumption
            for neg_tv_id in neg_tv_ids:
                set_kb.append([neg_tv_id, -ne_id])
            assumptions.append(ne_id)
            provider.add_test_case_description(ne_id, f"({' AND '.join(descs)})")
            set_neg_tv.append(ne_id)
            id_assumption += 1
        else:
            ne_id = neg_tv_ids[0]
            assumptions.append(ne_id)
            provider.add_test_case_description(ne_id, descs[0])
            set_neg_tv.append(ne_id)

        return ne_id, id_assumption

    @staticmethod
    def _create_negated_ne(
            set_kb: List[List[int]],
            assumptions: List[int],
            provider: DescriptionProvider,
            ne_id: int,
            neg_tv_ids: List[int],
            id_assumption: int
    ) -> Tuple[int, int]:
        """Create negated form of NE for REDUCE.

        not(not(e1) and not(e2) and ...) = (e1 or e2 or ...)
        Returns: (negated_ne_id, id_assumption)
        """
        if len(neg_tv_ids) > 1:
            negated_ne_ids = []
            for neg_tv_id in neg_tv_ids:
                negated_ne_id = id_assumption
                set_kb.append([-neg_tv_id, -negated_ne_id])
                negated_ne_ids.append(negated_ne_id)
                id_assumption += 1
            negated_ne_id = id_assumption
            set_kb.append(negated_ne_ids + [-negated_ne_id])
        else:
            negated_ne_id = id_assumption
            set_kb.append([-ne_id, -negated_ne_id])

        assumptions.append(negated_ne_id)
        provider.add_test_case_description(negated_ne_id, f"NOT({provider.get_description(ne_id)})")
        id_assumption += 1

        return negated_ne_id, id_assumption

    def _assign_sets(self, assumptions: List[int],
                     bias_start_id: int,
                     start_id_tc: int, start_id_tv: int,
                     has_negative_test_cases: bool
                     ) -> Tuple[List[int], List[int], List[int], List[int]]:
        """Compute (set_b, set_c, set_tc, set_tv) from assumptions.

        Each test case has two assumptions (original + negated),
        so extract only the original assumptions for set_tc and set_tv.
        Invariant: (start_id_tv - start_id_tc) is even (whole original+negated
        pairs), so slicing originals directly from each sub-region is exact.
        """
        set_b = [assumptions[0]]
        set_c = slice_assumptions(assumptions, bias_start_id, start_id_tc, 2)

        # Each test case is stored as an (original, negated) pair; stride by 2 to
        # keep only the originals, sliced directly from each sub-region.
        set_tc = slice_assumptions(assumptions, start_id_tc, start_id_tv, 2)
        set_tv = (slice_assumptions(assumptions, start_id_tv, None, 2)
                  if has_negative_test_cases else [])
        return set_b, set_c, set_tc, set_tv
