"""Shared base mixin for task preparations that consume BGData from an oracle.

Both ConGenTaskPreparation and QuAcqTaskPreparation start by copying BG data
from the oracle into a fresh result Task. This mixin factors out that common
copy into one place so the logic lives in exactly one location.

Divergence between the two preparations:
  - Part 3 (set_kb, assumptions, negation_map, descriptions): BOTH copy this.
  - Part 4 (assignment_clauses, assignment_assumptions): ONLY QuAcq copies this.

The mixin therefore provides:
  _copy_bg_data_part3(result, provider, bg_data) -- common to both
  _copy_bg_data_part4(result, bg_data)           -- QuAcq only

ConGenTaskPreparation calls _copy_bg_data_part3 only (Part 4 is not consumed
by ConGen because it does not use feature-assignment assumption pruning).
QuAcqTaskPreparation calls _copy_bg_data_part3 then _copy_bg_data_part4.
"""

from conacq.oracle.bg_data import BGData
from explanation.models.task_preparation import DescriptionProvider, DiagnosisTask


class OracleAwareTaskPreparation:
    """Mixin supplying protected BG-copy helpers for oracle-aware task preparations.

    Intended as a plain cooperative mixin — no __init__ arguments, no abstract
    methods. Inherit alongside the preparation's existing strategy base class.
    """

    @staticmethod
    def _copy_bg_data_part3(
        result: DiagnosisTask,
        provider: DescriptionProvider,
        bg_data: BGData,
    ) -> None:
        """Copy Part 3 BG data (root constraint pair) into result and provider.

        Performs, in order:
          1. Extend result.set_kb with bg_data.set_kb (assumption-guarded clauses).
          2. Extend result.assumptions with bg_data.assumptions (root + negated root IDs).
          3. Update result.negation_map with bg_data.negation_map.
          4. Register each description with the provider.

        Ordering matches the original inline code in both preparations verbatim.
        """
        result.set_kb.extend(bg_data.set_kb)
        result.assumptions.extend(list(bg_data.assumptions))
        result.negation_map.update(bg_data.negation_map)
        for aid, desc in bg_data.descriptions.items():
            provider.add_constraint_description(aid, desc)

    @staticmethod
    def _copy_bg_data_part4(
        result: DiagnosisTask,
        bg_data: BGData,
    ) -> None:
        """Copy Part 4 BG data (feature assignment assumptions) into result.

        Extends result.set_kb with assignment_clauses, then result.assumptions
        with assignment_assumptions. Ordering matches the original QuAcq inline
        code verbatim.

        Called by QuAcqTaskPreparation only — ConGen does not use Part 4.
        """
        result.set_kb.extend(bg_data.assignment_clauses)
        result.assumptions.extend(bg_data.assignment_assumptions)
