"""
Task preparation for ConGen algorithm.

Contains ConGenTask dataclass and ConGenTaskPreparation strategy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Tuple

from explanation.models.task_preparation import (
    TestCaseTask,
    TestCaseTaskPreparationStrategy,
    DescriptionProvider,
    PreparationOutput, prepare_testsuite_with_negation,
    prepare_kb,
    _ASSUMPTION_PAIR_STRIDE,
)
from explanation.operations.algorithms.utils import negate_cnf_tseitin
from .generate_ne import GenerateNE

if TYPE_CHECKING:
    from explanation.models.testsuite import TestSuite
    from .congen_model import ConGenModel


@dataclass
class ConGenTask(TestCaseTask):
    """Task for ConGen algorithm.

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

    Naming: Use DescriptionProvider (from PreparationOutput) to map assumption IDs
    to human-readable names. It covers all assumptions (bias, root, test cases, NE).
    """
    pass  # No additional fields needed


def _prepare_bg(
        result: ConGenTask,
        provider: DescriptionProvider,
        variables: Dict[str, int],
        root_feature: str,
        id_assumption: int
) -> int:
    # Adds root clauses and negated clauses to knowledgebase
    if root_feature is not None and root_feature in variables:
        root_id = variables[root_feature]

        # root clause
        key = f'{root_feature}=true'
        original_id = id_assumption

        result.set_kb.append([root_id, -original_id])

        result.assumptions.append(original_id)
        provider.add_constraint_description(original_id, key)
        id_assumption += 1

        # negated root clause for REDUCE
        negated_key = f'NOT({root_feature}=true)'
        negated_id = id_assumption

        result.set_kb.append([-root_id, -negated_id])

        result.assumptions.append(negated_id)
        result.negation_map[original_id] = negated_id
        provider.add_constraint_description(negated_id, negated_key)
        id_assumption += 1

    return id_assumption


class ConGenTaskPreparation(TestCaseTaskPreparationStrategy):
    """Prepare ConGen task using assumptions.

    Data mapping:
    - set_c: Bias constraints (B) with individual assumptions
    - set_b: Background knowledge (BG) - empty or FM root
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

    def prepare(self, model: ConGenModel) -> PreparationOutput:
        """Prepare ConGen task from model."""
        result = ConGenTask()
        provider = DescriptionProvider()
        task_input = model.task_input

        # Start assumption IDs after Tseitin variables
        id_assumption = model.next_tseitin_var

        # Step 0: Prepare background knowledge (BG) - root constraints
        id_assumption = _prepare_bg(result, provider, model.variables, model.root_feature, id_assumption)

        # Reserve IDs for fm constraints and their negations + variable assignments
        id_assumption = id_assumption + (model.num_fm_constraints - 1) * _ASSUMPTION_PAIR_STRIDE
        id_assumption = id_assumption + len(model.variables) * _ASSUMPTION_PAIR_STRIDE

        # Step 1: Prepare bias constraints as set_c (with negated forms for REDUCE)
        bias_start_pos = len(result.assumptions)
        next_tseitin_var = id_assumption
        for key, c in model.constraint_map.items():
            neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
            model.negated_constraint_map[f"NOT({key})"] = neg_clauses

        id_assumption = next_tseitin_var
        id_assumption = prepare_kb(
            result, provider, model.constraint_map,
            id_assumption, model.negated_constraint_map)
        # Step 2: Prepare E+ as set_tc
        tc_start_pos = len(result.assumptions)
        id_assumption = prepare_testsuite_with_negation(
            result, provider, model.variables, task_input.positive_test_cases, id_assumption, is_negative=False)

        tv_start_pos = len(result.assumptions)
        self._assign_sets(result, bias_start_pos, tc_start_pos, tv_start_pos, task_input.negative_test_cases is not None)

        # Step 3: Prepare E- as NE via GenerateNE
        testsuite = task_input.negative_test_cases
        if testsuite is not None and len(testsuite.testcases) > 0:
            id_assumption = self._prepare_negative_examples(
                result, provider, model, testsuite, id_assumption)

        # Store next available assumption ID
        model.next_tseitin_var = id_assumption

        logging.debug('<<< ConGenTaskPreparation: set_c=%d, set_tc=%d, set_tv=%d',
                      len(result.set_c), len(result.set_tc), len(result.set_tv))

        return PreparationOutput(result, provider)

    def _prepare_negative_examples(
            self,
            result: ConGenTask,
            provider: DescriptionProvider,
            model: ConGenModel,
            testsuite: TestSuite,
            id_assumption: int
    ) -> int:
        """Step 3: Generate NE from negative examples.

        Orchestrates: GenerateNE -> combine -> negate -> populate task.
        """
        oracle = model.oracle
        if oracle is None:
            raise ValueError("Oracle required for NE generation from negative examples")

        generate_ne = GenerateNE(oracle)
        ne_results, id_assumption = generate_ne.generate(
            testsuite, model.variables, result.set_kb, result.assumptions, id_assumption)

        neg_tv_ids = [ne.ne_id for ne in ne_results]
        descs = [ne.desc for ne in ne_results]

        ne_id, id_assumption = self._combine_ne_constraints(
            result, provider, neg_tv_ids, descs, id_assumption)

        negated_ne_id, id_assumption = self._create_negated_ne(
            result, provider, ne_id, neg_tv_ids, id_assumption)

        result.negation_map[ne_id] = negated_ne_id
        return id_assumption

    @staticmethod
    def _combine_ne_constraints(
            result: ConGenTask,
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
                result.set_kb.append([neg_tv_id, -ne_id])
            result.assumptions.append(ne_id)
            provider.add_test_case_description(ne_id, f"({' AND '.join(descs)})")
            result.set_neg_tv.append(ne_id)
            id_assumption += 1
        else:
            ne_id = neg_tv_ids[0]
            result.assumptions.append(ne_id)
            provider.add_test_case_description(ne_id, descs[0])
            result.set_neg_tv.append(ne_id)

        return ne_id, id_assumption

    @staticmethod
    def _create_negated_ne(
            result: ConGenTask,
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
                result.set_kb.append([-neg_tv_id, -negated_ne_id])
                negated_ne_ids.append(negated_ne_id)
                id_assumption += 1
            negated_ne_id = id_assumption
            result.set_kb.append(negated_ne_ids + [-negated_ne_id])
        else:
            negated_ne_id = id_assumption
            result.set_kb.append([-ne_id, -negated_ne_id])

        result.assumptions.append(negated_ne_id)
        provider.add_test_case_description(negated_ne_id, f"NOT({provider.get_description(ne_id)})")
        id_assumption += 1

        return negated_ne_id, id_assumption

    def _assign_sets(self, result: ConGenTask,
                     bias_start_id: int,
                     start_id_tc: int, start_id_tv: int,
                     has_negative_test_cases: bool) -> None:
        """Assign sets from assumptions.

        Each test case has two assumptions (original + negated),
        so extract only the original assumptions for set_tc and set_tv.
        """
        result.set_b = [result.assumptions[0]]
        result.set_c = result.assumptions[bias_start_id:start_id_tc:_ASSUMPTION_PAIR_STRIDE]

        tc_tv_assumptions = result.assumptions[start_id_tc:]
        original_tc_tv = [tc_tv_assumptions[i] for i in range(0, len(tc_tv_assumptions), _ASSUMPTION_PAIR_STRIDE)]

        num_tc_original = (start_id_tv - start_id_tc) // _ASSUMPTION_PAIR_STRIDE
        result.set_tc = original_tc_tv[:num_tc_original]
        result.set_tv = original_tc_tv[num_tc_original:] if has_negative_test_cases else []
