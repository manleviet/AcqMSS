"""
Task preparation for ConGen algorithm.

Contains ConGenTask dataclass and ConGenTaskPreparation strategy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from explanation.models.task_preparation import (
    TestCaseTask,
    TestCaseTaskPreparationStrategy,
    DescriptionProvider,
    PreparationOutput, prepare_testsuite_with_negation,
    prepare_kb,
)

if TYPE_CHECKING:
    from .congen_model import ConGenModel


@dataclass
class ConGenTask(TestCaseTask):
    """Task for ConGen algorithm.

    Inherits from TestCaseTask with mapping:
    - set_c: Bias constraints (B) - assumption IDs
    - set_b: Background knowledge (BG) - assumption IDs
    - set_kb: Full KB with assumptions (clauses with assumption literals)
    - neg_c_map: Dict[int, int] - negation map for REDUCE
    - assumptions: List of all assumption IDs (for reference)
    - set_tc: Positive examples (E+) - assumption IDs
    - set_tv: Negative examples (E-) - assumption IDs
    - set_neg_tv: Negated negative examples (NE) - populated by GenerateNE
    - neg_tc_map: Dict[int, int] - negation map for examples
    Inherited from TestCaseTask (unused by ConGen):
    - set_neg_tc

    Additional ConGen-specific fields:
    - e_neg_literals: Raw E⁻ literals for GenerateNE (List of [l1, l2, ...])
    - assumption_to_constraint: Maps assumption ID to constraint name
    - constraint_to_assumption: Maps constraint name to assumption ID
    - next_assumption_id: Next available assumption ID for GenerateNE
    """
    # e_neg_literals: List[List[int]] = field(default_factory=list)
    assumption_to_constraint: Dict[int, str] = field(default_factory=dict)
    constraint_to_assumption: Dict[str, int] = field(default_factory=dict)
    # next_assumption_id: int = 1000

    def get_constraint_name(self, element: Any) -> str:
        """Get constraint name from assumption ID."""
        if isinstance(element, int):
            return self.assumption_to_constraint.get(element, f'unknown_{element}')
        return f'unknown_{element}'


def _build_constraint_maps(
        result: ConGenTask,
        constraint_map: Dict[str, List[List[int]]],
        negated_constraint_map: Optional[Dict[str, List[List[int]]]],
        start_id: int
) -> None:
    """Build bidirectional constraint-assumption maps from sequential IDs.

    Must mirror prepare_kb's ID assignment: +1 per constraint, +1 per negated form.
    """
    aid = start_id
    for name in constraint_map:
        result.constraint_to_assumption[name] = aid
        result.assumption_to_constraint[aid] = name
        aid += 1
        # Skip negated form's ID if it exists
        if negated_constraint_map is not None:
            negated_key = f"NOT({name})"
            if negated_key in negated_constraint_map:
                aid += 1


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
        result.neg_c_map[original_id] = negated_id
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
    - neg_c_map: Negation map for REDUCE
    """

    def __init__(self, mode_name: str = "congen"):
        self._mode_name = mode_name

    @property
    def mode_name(self) -> str:
        return self._mode_name

    def prepare(self, model: 'ConGenModel') -> PreparationOutput:
        """Prepare ConGen task from model.

        Args:
            model: ConGenModel with constraint_map, variables, task_input, etc.

        Returns:
            PreparationOutput with ConGenTask
        """
        result = ConGenTask()
        provider = DescriptionProvider()

        task_input = model.task_input

        # Start assumption IDs after Tseitin variables
        id_assumption = model.next_tseitin_var

        # Step 0: Prepare background knowledge (BG) - root constraints
        id_assumption = _prepare_bg(result, provider, model.variables, model.root_feature, id_assumption)

        # Reserve IDs for fm constraints and their negations
        id_assumption = id_assumption + model.num_fm_constraints * 2
        # Reserve IDs for all possible variable assignments
        id_assumption = id_assumption + len(model.variables) * 2

        # Step 1: Prepare bias constraints as set_c (with negated forms for REDUCE)
        bias_start_id = id_assumption
        id_assumption = prepare_kb(
            result, provider, model.constraint_map,
            id_assumption, model.negated_constraint_map)
        _build_constraint_maps(
            result, model.constraint_map,
            model.negated_constraint_map, bias_start_id)

        # Step 2: Prepare E+ as set_tc
        start_id_tc = len(result.assumptions)
        id_assumption = prepare_testsuite_with_negation(
            result, provider, model.variables, task_input.positive_test_cases, id_assumption, is_negative=False)

        # Step 3: Prepare E- as set_tv
        start_id_tv = len(result.assumptions)
        if task_input.negative_test_cases is not None:
            id_assumption = prepare_testsuite_with_negation(
                result, provider, model.variables, task_input.negative_test_cases, id_assumption, is_negative=True)

        self._assign_sets(result, bias_start_id, start_id_tc, start_id_tv, task_input.negative_test_cases is not None)

        # Store next available assumption ID for GenerateNE
        model.next_tseitin_var = id_assumption

        logging.debug('<<< ConGenTaskPreparation: set_c=%d, set_tc=%d, e_neg=%d',
                      len(result.set_c), len(result.set_tc), len(result.e_neg_literals))

        return PreparationOutput(result, provider)

    def _assign_sets(self, result: ConGenTask,
                     bias_start_id: int,
                     start_id_tc: int, start_id_tv: int,
                     has_negative_test_cases: bool) -> None:
        """Assign sets from assumptions.

        Each test case has two assumptions (original + negated),
        so extract only the original assumptions for set_tc and set_tv.
        """
        step = 2

        result.set_b = [result.assumptions[0]]
        result.set_c = result.assumptions[bias_start_id:start_id_tc:step]

        tc_tv_assumptions = result.assumptions[start_id_tc:]
        original_tc_tv = [tc_tv_assumptions[i] for i in range(0, len(tc_tv_assumptions), step)]

        num_tc_original = (start_id_tv - start_id_tc) // step
        result.set_tc = original_tc_tv[:num_tc_original]
        result.set_tv = original_tc_tv[num_tc_original:] if has_negative_test_cases else []