"""
Task preparation for QuAcq interactive constraint acquisition.

Prepares QuAcqTask from bias + oracle. No E+/E- needed (unlike ConGen).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from explanation.models.task_preparation import (
    DescriptionProvider,
    PreparationOutput,
    prepare_kb,
    _ASSUMPTION_PAIR_STRIDE,
)
from explanation.operations.algorithms.utils import negate_cnf_tseitin

from .quacq_task import QuAcqTask

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle
    from .quacq_model import QuAcqModel


class QuAcqTaskPreparation:
    """Prepare QuAcqTask from bias + oracle. No E+/E-.

    Assumption ID layout (QuAcq owns Parts 5-6):
      Parts 1-4: Owned by Oracle (see OracleTaskPreparation)
      Part 5:    Tseitin vars (negated bias constraints)   <- This method
      Part 6:    Bias constraint assumptions (paired)      <- This method
    """

    def prepare(self, model: 'QuAcqModel',
                oracle: FeatureModelOracle) -> PreparationOutput:
        """Prepare QuAcqTask from model and oracle.

        Args:
            model: InteractiveModel with bias constraint_map
            oracle: FeatureModelOracle for BG data and feature IDs

        Returns:
            PreparationOutput with QuAcqTask and DescriptionProvider
        """
        result = QuAcqTask()
        provider = DescriptionProvider()

        # Step 0: Copy BG data from Oracle (root constraint pair)
        bg_data = oracle.get_bg_data()
        result.set_kb.extend(bg_data.set_kb)
        result.assumptions.extend(list(bg_data.assumptions))
        result.negation_map.update(bg_data.negation_map)
        for aid, desc in bg_data.descriptions.items():
            provider.add_constraint_description(aid, desc)
        result.set_b = list(bg_data.assumptions)
        id_assumption = bg_data.next_available_id

        # Store raw BG clauses (without assumption guards) for _find_conflict
        result.background_clauses = oracle.get_root_clauses()

        # Step 1: Negate bias constraints using Tseitin transformation
        next_tseitin_var = id_assumption
        for key, c in model.constraint_map.items():
            neg_clauses, next_tseitin_var = negate_cnf_tseitin(c, next_tseitin_var)
            model.negated_constraint_map[f"NOT({key})"] = neg_clauses

        # Step 2: Assign assumption IDs via prepare_kb()
        id_assumption = next_tseitin_var
        bias_start_pos = len(result.assumptions)
        id_assumption = prepare_kb(
            result, provider, model.constraint_map,
            id_assumption, model.negated_constraint_map)

        # Step 3: Extract bias assumption IDs (stride=2: original, not negated)
        result.bias = set(
            result.assumptions[bias_start_pos::_ASSUMPTION_PAIR_STRIDE])

        # Step 4: Build constraint_clauses and negated_clauses mappings
        for aid in result.bias:
            name = provider.get_description(aid)
            if name in model.constraint_map:
                result.constraint_clauses[aid] = model.constraint_map[name]
            neg_key = f"NOT({name})"
            if neg_key in model.negated_constraint_map:
                result.negated_clauses[aid] = model.negated_constraint_map[neg_key]

        # Step 5: Populate feature_ids/id_to_feature from oracle
        fm_data = oracle.get_fm_data()
        result.feature_ids = fm_data.feature_ids
        result.id_to_feature = {v: k for k, v in fm_data.feature_ids.items()}

        return PreparationOutput(result, provider)


# Backward-compat alias
InteractiveTaskPreparation = QuAcqTaskPreparation
