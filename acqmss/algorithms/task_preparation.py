"""
Task preparation strategies for CONGEN algorithm.

Prepares CONGENTask from bias constraints and examples.
Supports both incremental and non-incremental modes.
"""

import logging
from typing import TYPE_CHECKING, Dict, List, Tuple

from explanation.models.task_preparation import (
    TestCaseTaskPreparationStrategy,
    DescriptionProvider,
    PreparationOutput
)
from explanation.models.testsuite import TestSuite
from explanation.operations.algorithms.utils import negate_cnf_tseitin

from .task import IncrementalCONGENTask, NonIncrementalCONGENTask
from .model import CONGENModel


class IncrementalCONGENTaskPreparation(TestCaseTaskPreparationStrategy):
    """Prepare CONGEN task for incremental mode.

    Pattern follows IncrementalTestCaseTaskPreparation.

    Data mapping:
    - set_c: Bias constraints (B) with individual assumptions
    - set_b: Background knowledge (BG) - empty or FM root
    - set_tc: Positive examples (E+) with assumptions
    - set_tv: Negative examples (E-) with assumptions
    - set_neg_tv: Negated negative examples (NE)
    - neg_c_map: Negation map for REDUCE
    """

    @property
    def mode_name(self) -> str:
        return "incremental-congen"

    def prepare(self, model: CONGENModel) -> PreparationOutput:
        """Prepare CONGEN task from model.

        Args:
            model: DiagnosisModel with:
                - constraint_map: Bias constraints {name: clauses}
                - negated_constraint_map: Negated bias constraints
                - variables: Feature name to variable ID mapping
                - task_input.positive_test_cases: E+
                - task_input.negative_test_cases: E-
                - next_tseitin_var: Starting assumption ID

        Returns:
            PreparationOutput with IncrementalCONGENTask
        """
        result = IncrementalCONGENTask()
        provider = DescriptionProvider()
        task_input = model.task_input

        # Start assumption IDs after Tseitin variables
        id_assumption = model.next_tseitin_var

        logging.debug('>>> IncrementalCONGENTaskPreparation.prepare()')

        # Step 1: Prepare bias constraints as set_c (with negated forms for REDUCE)
        id_assumption = self._prepare_bias_constraints(
            result, provider, model.constraint_map,
            model.negated_constraint_map, id_assumption)

        # Step 2: Prepare E+ as set_tc
        id_assumption = self._prepare_examples(
            result, provider, model.variables,
            task_input.positive_test_cases, id_assumption, is_negative=False)

        # Step 3: Prepare E- (store literals in e_neg_literals)
        # Note: NE generation is done by GenerateNE in CONGEN.acquire()
        if task_input.negative_test_cases is not None:
            id_assumption = self._prepare_examples(
                result, provider, model.variables,
                task_input.negative_test_cases, id_assumption, is_negative=True)

        # set_b (BG) is empty for CONGEN (no FM background)
        # Can be extended to include FM if needed

        # Store next available assumption ID for GenerateNE
        result.next_assumption_id = id_assumption

        logging.debug('<<< IncrementalCONGENTaskPreparation: set_c=%d, set_tc=%d, e_neg=%d',
                      len(result.set_c), len(result.set_tc), len(result.e_neg_literals))

        return PreparationOutput(result, provider)

    def _prepare_bias_constraints(
            self,
            result: IncrementalCONGENTask,
            provider: DescriptionProvider,
            constraint_map: Dict[str, List[List[int]]],
            negated_constraint_map: Dict[str, List[List[int]]],
            id_assumption: int
    ) -> int:
        """Prepare bias constraints with assumptions.

        Each bias constraint gets an assumption ID. Negated forms are also
        prepared for REDUCE algorithm.

        Args:
            result: Task to populate
            provider: Description provider
            constraint_map: {constraint_name: clauses}
            negated_constraint_map: {negated_name: negated_clauses}
            id_assumption: Starting assumption ID

        Returns:
            Next available assumption ID
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
            result: IncrementalCONGENTask,
            provider: DescriptionProvider,
            variables: Dict[str, int],
            examples: TestSuite,
            id_assumption: int,
            is_negative: bool
    ) -> int:
        """Prepare examples with assumptions.

        Each example gets an assumption ID. For negative examples,
        stores literals in e_neg_literals for GenerateNE (called in CONGEN).

        Note: NE generation is NOT done here. It's done by GenerateNE
        in CONGEN.acquire() to match the paper algorithm.

        Args:
            result: Task to populate
            provider: Description provider
            variables: {feature_name: variable_id}
            examples: TestSuite with test cases
            id_assumption: Starting assumption ID
            is_negative: Whether these are negative examples

        Returns:
            Next available assumption ID
        """
        for testcase in examples.testcases:
            original_id = id_assumption
            desc_parts = []
            literals = []

            # Build clauses for example: assumption → (l1 ∧ l2 ∧ ...)
            for assignment in testcase.assignments:
                if assignment.feature not in variables:
                    raise KeyError(f'Feature {assignment.feature} is not in the model.')

                desc_parts.append(f'{assignment.feature}={"true" if assignment.value else "false"}')
                var = variables[assignment.feature] if assignment.value else -variables[assignment.feature]
                literals.append(var)
                # Add clause: (var ∨ ¬assumption)
                result.set_kb.append([var, -original_id])

            result.assumptions.append(original_id)
            desc = ' & '.join(desc_parts)
            provider.add_test_case_description(original_id, desc)

            if is_negative:
                result.set_tv.append(original_id)
                # Store E⁻ literals for GenerateNE (called in CONGEN.acquire)
                result.e_neg_literals.append(literals)
            else:
                result.set_tc.append(original_id)

            id_assumption += 1

        return id_assumption


class NonIncrementalCONGENTaskPreparation(TestCaseTaskPreparationStrategy):
    """Prepare CONGEN task for non-incremental mode.

    Pattern follows NonIncrementalTestCaseTaskPreparation.
    All sets are List[List[int]] (clauses) instead of assumption IDs.
    """

    @property
    def mode_name(self) -> str:
        return "non-incremental-congen"

    def prepare(self, model: CONGENModel) -> PreparationOutput:
        """Prepare CONGEN task for non-incremental mode.

        Args:
            model: DiagnosisModel with constraint_map, variables, task_input

        Returns:
            PreparationOutput with NonIncrementalCONGENTask
        """
        result = NonIncrementalCONGENTask()
        provider = DescriptionProvider()
        task_input = model.task_input

        logging.debug('>>> NonIncrementalCONGENTaskPreparation.prepare()')

        # Step 1: Prepare bias constraints as set_c (clauses)
        self._prepare_bias_constraints(
            result, provider, model.constraint_map, model.negated_constraint_map)

        # Step 2: Prepare E+ as set_tc
        self._prepare_examples(
            result, provider, model.variables,
            task_input.positive_test_cases, is_negative=False)

        # Step 3: Prepare E- (store literals in e_neg_literals)
        # Note: NE generation is done by GenerateNE in CONGEN.acquire()
        if task_input.negative_test_cases is not None:
            self._prepare_examples(
                result, provider, model.variables,
                task_input.negative_test_cases, is_negative=True)

        logging.debug('<<< NonIncrementalCONGENTaskPreparation: set_c=%d, set_tc=%d, e_neg=%d',
                      len(result.set_c), len(result.set_tc), len(result.e_neg_literals))

        return PreparationOutput(result, provider)

    def _prepare_bias_constraints(
            self,
            result: NonIncrementalCONGENTask,
            provider: DescriptionProvider,
            constraint_map: Dict[str, List[List[int]]],
            negated_constraint_map: Dict[str, List[List[int]]]
    ) -> None:
        """Prepare bias constraints as clause lists."""
        tseitin_var = max(
            max(abs(lit) for clause in clauses for lit in clause)
            for clauses in constraint_map.values()
        ) + 1 if constraint_map else 1

        for name, clauses in constraint_map.items():
            result.set_c.append(clauses)
            result.set_kb.append(clauses)
            provider.add_constraint_description(clauses, name)

            # Store clause-to-name mapping
            clauses_key = tuple(tuple(c) for c in clauses)
            result.clauses_to_name[clauses_key] = name
            result.name_to_clauses[name] = clauses

            # Prepare negated form
            negated_key = f"NOT({name})"
            if negated_constraint_map and negated_key in negated_constraint_map:
                negated_clauses = negated_constraint_map[negated_key]
            else:
                negated_clauses, tseitin_var = negate_cnf_tseitin(clauses, tseitin_var)

            result.neg_c_map[clauses_key] = negated_clauses
            provider.add_constraint_description(negated_clauses, negated_key)

    def _prepare_examples(
            self,
            result: NonIncrementalCONGENTask,
            provider: DescriptionProvider,
            variables: Dict[str, int],
            examples: TestSuite,
            is_negative: bool
    ) -> None:
        """Prepare examples as clause lists.

        Note: NE generation is NOT done here. It's done by GenerateNE
        in CONGEN.acquire() to match the paper algorithm.
        """
        for testcase in examples.testcases:
            desc_parts = []
            literals = []

            for assignment in testcase.assignments:
                if assignment.feature not in variables:
                    raise KeyError(f'Feature {assignment.feature} is not in the model.')

                desc_parts.append(f'{assignment.feature}={"true" if assignment.value else "false"}')
                var = variables[assignment.feature] if assignment.value else -variables[assignment.feature]
                literals.append(var)

            # Example as clauses: [[l1], [l2], ...]
            example_clauses = [[lit] for lit in literals]
            desc = ' & '.join(desc_parts)
            provider.add_test_case_description(example_clauses, desc)

            if is_negative:
                result.set_tv.append(example_clauses)
                # Store E⁻ literals for GenerateNE (called in CONGEN.acquire)
                result.e_neg_literals.append(literals)
            else:
                result.set_tc.append(example_clauses)
