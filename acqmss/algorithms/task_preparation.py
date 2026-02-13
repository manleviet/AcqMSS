"""
Task preparation for CONGEN algorithm.

Prepares CONGENTask from bias constraints and examples.
"""

import logging
from typing import Dict, List

from explanation.models.task_preparation import (
    TestCaseTaskPreparationStrategy,
    DescriptionProvider,
    PreparationOutput
)
from explanation.models.testsuite import TestSuite
from explanation.operations.algorithms.utils import negate_cnf_tseitin

from .task import CONGENTask
from .model import CONGENModel


class CONGENTaskPreparation(TestCaseTaskPreparationStrategy):
    """Prepare CONGEN task using assumptions.

    Data mapping:
    - set_c: Bias constraints (B) with individual assumptions
    - set_b: Background knowledge (BG) - empty or FM root
    - set_tc: Positive examples (E+) with assumptions
    - set_tv: Negative examples (E-) with assumptions
    - set_neg_tv: Negated negative examples (NE)
    - neg_c_map: Negation map for REDUCE
    """

    def __init__(self, mode_name: str = "congen"):
        self._mode_name = mode_name

    @property
    def mode_name(self) -> str:
        return self._mode_name

    def prepare(self, model: CONGENModel) -> PreparationOutput:
        """Prepare CONGEN task from model.

        Args:
            model: CONGENModel with constraint_map, variables, task_input, etc.

        Returns:
            PreparationOutput with CONGENTask
        """
        result = CONGENTask()
        provider = DescriptionProvider()
        task_input = model.task_input

        # Start assumption IDs after Tseitin variables
        id_assumption = model.next_tseitin_var

        logging.debug('>>> CONGENTaskPreparation.prepare() [%s]', self._mode_name)

        # Step 1: Prepare bias constraints as set_c (with negated forms for REDUCE)
        id_assumption = self._prepare_bias_constraints(
            result, provider, model.constraint_map,
            model.negated_constraint_map, id_assumption)

        # Step 2: Prepare E+ as set_tc
        id_assumption = self._prepare_examples(
            result, provider, model.variables,
            task_input.positive_test_cases, id_assumption, is_negative=False)

        # Step 3: Prepare E- (store literals in e_neg_literals)
        if task_input.negative_test_cases is not None:
            id_assumption = self._prepare_examples(
                result, provider, model.variables,
                task_input.negative_test_cases, id_assumption, is_negative=True)

        # Add background knowledge literals
        if model.background_knowledge:
            result.set_b.extend(model.background_knowledge)

        # Store next available assumption ID for GenerateNE
        result.next_assumption_id = id_assumption

        logging.debug('<<< CONGENTaskPreparation: set_c=%d, set_tc=%d, e_neg=%d',
                      len(result.set_c), len(result.set_tc), len(result.e_neg_literals))

        return PreparationOutput(result, provider)

    def _prepare_bias_constraints(
            self,
            result: CONGENTask,
            provider: DescriptionProvider,
            constraint_map: Dict[str, List[List[int]]],
            negated_constraint_map: Dict[str, List[List[int]]],
            id_assumption: int
    ) -> int:
        """Prepare bias constraints with assumptions.

        Each bias constraint gets an assumption ID. Negated forms are also
        prepared for REDUCE algorithm.
        """
        for name, clauses in constraint_map.items():
            original_id = id_assumption

            # Add clauses with assumption: (clause ∨ ¬a)
            for clause in clauses:
                result.set_kb.append(clause + [-original_id])

            result.assumptions.append(original_id)
            result.set_c.append(original_id)
            result.constraint_to_assumption[name] = original_id
            result.assumption_to_constraint[original_id] = name
            provider.add_constraint_description(original_id, name)

            id_assumption += 1

            # Prepare negated form for REDUCE
            negated_id = id_assumption
            negated_key = f"NOT({name})"

            if negated_constraint_map and negated_key in negated_constraint_map:
                negated_clauses = negated_constraint_map[negated_key]
            else:
                # Generate negated form using Tseitin
                negated_clauses, id_assumption = negate_cnf_tseitin(clauses, id_assumption)
                negated_id = id_assumption
                id_assumption += 1

            for neg_clause in negated_clauses:
                result.set_kb.append(neg_clause + [-negated_id])

            result.assumptions.append(negated_id)
            result.neg_c_map[original_id] = negated_id
            provider.add_constraint_description(negated_id, negated_key)

            id_assumption += 1

        return id_assumption

    def _prepare_examples(
            self,
            result: CONGENTask,
            provider: DescriptionProvider,
            variables: Dict[str, int],
            examples: TestSuite,
            id_assumption: int,
            is_negative: bool
    ) -> int:
        """Prepare examples with assumptions.

        Each example gets an assumption ID. For negative examples,
        stores literals in e_neg_literals for GenerateNE.
        """
        for testcase in examples.testcases:
            original_id = id_assumption
            desc_parts = []
            literals = []

            for assignment in testcase.assignments:
                if assignment.feature not in variables:
                    raise KeyError(f'Feature {assignment.feature} is not in the model.')

                desc_parts.append(f'{assignment.feature}={"true" if assignment.value else "false"}')
                var = variables[assignment.feature] if assignment.value else -variables[assignment.feature]
                literals.append(var)
                result.set_kb.append([var, -original_id])

            result.assumptions.append(original_id)
            desc = ' & '.join(desc_parts)
            provider.add_test_case_description(original_id, desc)

            if is_negative:
                result.set_tv.append(original_id)
                result.e_neg_literals.append(literals)
            else:
                result.set_tc.append(original_id)

            id_assumption += 1

        return id_assumption
