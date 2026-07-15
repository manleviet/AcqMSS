"""
Task preparation for the FM oracle (job ①/② provisioning).

FMOracleTaskPreparation builds the assumption-guarded task once (pure) and exposes
two views of it: the oracle's frozen provisioning snapshot (``prepare`` -> OracleData,
job ②) and the plain PreparedTask (``prepare_task``). The oracle *receives* its
OracleData; it does not assemble what it provides (ADR-0009).
"""

from typing import TYPE_CHECKING, Dict, List, Tuple

from conacq.oracle.bg_data import BGData
from conacq.oracle.oracle_data import OracleData
from explanation.api import (
    DiagnosisTask,
    DescriptionProvider,
    AssignmentAssumptionMap,
    PreparedTask,
    prepare_kb,
    prepare_variable_assignments,
    slice_assumptions,
)

if TYPE_CHECKING:
    from conacq.oracle.fm.model import FMOracleModel


class FMOracleTaskPreparation:
    """Prepare assumption-guarded clauses + BGData for Oracle FM validation.

    Shared Assumption ID Layout (Oracle owns Parts 1-4):
      Part 1: Feature variable IDs (1..n)               <- FmToDiagPysat
      Part 2: Tseitin vars (negated FM constraints)      <- FmToDiagPysat
      Part 3: FM constraint assumptions (paired)         <- This method
               [root, NOT(root), c2, NOT(c2), ...]
      Part 4: Variable assignment assumptions (paired)   <- This method
               [f1=true, f1=false, f2=true, ...]

    ConGen continues from Part 5 onward (see ConGenTaskPreparation).
    BGData extracts Part 3's first pair (root BG) + end-of-Part-4 ID.

    Pure: builds everything into locals; the model is never mutated. Two public
    views over the same preparation — ``prepare`` (OracleData, job ②) and
    ``prepare_task`` (PreparedTask).
    """

    @staticmethod
    def _prepare(
        model: 'FMOracleModel'
    ) -> Tuple[DiagnosisTask, DescriptionProvider, AssignmentAssumptionMap, BGData, List[List[int]]]:
        """Core preparation (pure). Returns the task, its DescriptionProvider, the
        feature-assignment map, the root BGData, and the raw root clauses."""
        provider = DescriptionProvider()

        # Use next_available_id to avoid conflicts with Tseitin variables
        id_assumption = model.next_available_id
        negated_constraint_map = model.negated_constraint_map

        # Local accumulation (build-then-freeze)
        set_kb: List[List[int]] = []
        assumptions: List[int] = []
        negation_map: Dict[int, int] = {}

        # Step 1: FM constraints from constraint_map → set_kb with assumptions
        id_assumption = prepare_kb(
            set_kb, assumptions, negation_map, provider,
            model.constraint_map, id_assumption, negated_constraint_map)

        # Step 2: Feature assignments → assumption-guarded (paired true/false)
        assignments_start_index = len(assumptions)
        assignment_kb_start = len(set_kb)
        id_assumption, pos_assignment_to_assumption, neg_assignment_to_assumption = (
            prepare_variable_assignments(
                set_kb, assumptions, provider, model.name_to_id, id_assumption))

        # The feature-assignment map, returned on the PreparedTask / OracleData;
        # membership queries reuse it locally (is_valid appends this query's
        # assumptions to set_c). The model is never mutated.
        assignment_map = AssignmentAssumptionMap(
            pos_assignment_to_assumption, neg_assignment_to_assumption)

        # Step 3: FM constraint assumptions only (originals of the paired Part-3
        # layout, stride 2). Stored on the frozen task as set_c.
        set_c = slice_assumptions(assumptions, 0, assignments_start_index, 2)

        # Extract Part 4 data (assignment clauses added after Part 3)
        assignment_clauses = set_kb[assignment_kb_start:]
        assignment_assumptions = assumptions[assignments_start_index:]

        # Step 4: Extract root BG data for ConGen consumption (requires negated constraints)
        bg_data = BGData(
            set_kb=set_kb[:2],  # first pair of assumptions for root constraint
            assumptions=(assumptions[0], assumptions[1]),
            negation_map={assumptions[0]: assumptions[1]},
            descriptions=provider.get_descriptions_for(
                [assumptions[0], assumptions[1]]),
            next_available_id=id_assumption,
            # Part 4
            assignment_clauses=assignment_clauses,
            assignment_assumptions=assignment_assumptions,
            pos_assignment_to_assumption=dict(pos_assignment_to_assumption),
            neg_assignment_to_assumption=dict(neg_assignment_to_assumption),
        )

        # The root constraint is, by construction, the FIRST entry in constraint_map
        # (FmToDiagPysat traverses the FM tree root-first — the same invariant the
        # bg_data root pair relies on). Its raw clauses are the background clauses
        # ConGen/QuAcq report.
        root_clauses = list(model.constraint_map[next(iter(model.constraint_map))])

        # Build-then-freeze: construct the frozen task once (set_b unused by Oracle).
        task = DiagnosisTask(
            set_c=set_c, set_b=[], set_kb=set_kb,
            negation_map=negation_map, assumptions=assumptions)
        return task, provider, assignment_map, bg_data, root_clauses

    @staticmethod
    def prepare(model: 'FMOracleModel') -> OracleData:
        """Assemble the oracle's frozen provisioning snapshot (job ②).

        The oracle receives this; it does not build what it provides (ADR-0009).
        """
        task, _provider, assignment_map, bg_data, root_clauses = (
            FMOracleTaskPreparation._prepare(model))
        return OracleData(
            task=task,
            bg_data=bg_data,
            root_clauses=root_clauses,
            assignment_map=assignment_map,
            next_available_id=model.next_available_id,
        )

    @staticmethod
    def prepare_task(model: 'FMOracleModel') -> PreparedTask:
        """The plain PreparedTask view (task + describe + assignment_map), for
        FMOracleModel.prepare_task and preparation-layout tests."""
        task, provider, assignment_map, _bg_data, _root_clauses = (
            FMOracleTaskPreparation._prepare(model))
        return PreparedTask(
            task=task, describe=provider, assignment_map=assignment_map)
