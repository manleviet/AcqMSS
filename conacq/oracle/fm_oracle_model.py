"""
Oracle models for ConsistencyChecker integration.

FMOracleModel: Assumption-guarded FM validation (incremental checker).
Exposes get_kb()/get_assumptions()/use_incremental + a prepared task for use
with build_checker().
"""

from typing import Dict, List, Optional

from conacq.kb_model import KBModel
from conacq.oracle.bg_data import BGData
from explanation.api import (
    DiagnosisTask,
    DescriptionProvider,
    AssignmentAssumptionMap,
    PreparedTask,
    prepare_kb,
    prepare_variable_assignments,
    slice_assumptions,
)


class FMOracleModel(KBModel):
    """Model for Oracle FM validation via ConsistencyChecker.

    Uses the constraint_map + name↔id catalog pattern (same as DiagnosisModel/ConGenModel).
    Exposes get_kb()/get_assumptions()/use_incremental + a prepared task after prepare().

    FM clauses go directly into set_kb (always active).
    Feature assignments become assumption-guarded unit clauses:
      [-a_pos_i, fid]  → if a_pos_i active, feature must be true
      [-a_neg_i, -fid] → if a_neg_i active, feature must be false
    """

    def __init__(self):
        super().__init__()
        self._fm_path: str = ""

        # Solver selection consumed by build_checker()
        self._use_incremental: bool = True

        # Populated after prepare()
        # Built once, so membership queries reuse it instead of rebuilding this
        # immutable map on every call (is_valid is a hot path).
        self.assignment_map: Optional[AssignmentAssumptionMap] = None
        self._bg_data: Optional[BGData] = None
        self._task: Optional[DiagnosisTask] = None
        self._description_provider: Optional[DescriptionProvider] = None

    @property
    def task(self) -> DiagnosisTask:
        """Get prepared task. Call prepare() first."""
        if self._task is None:
            raise RuntimeError("Call prepare() first")
        return self._task

    @property
    def description_provider(self) -> DescriptionProvider:
        """Get description provider. Call prepare() first."""
        if self._description_provider is None:
            raise RuntimeError("Call prepare() first")
        return self._description_provider

    @property
    def bg_data(self) -> BGData:
        """Root BG data for ConGen. Call prepare() first."""
        if self._bg_data is None:
            raise RuntimeError("Call prepare() first")
        return self._bg_data

    @property
    def use_incremental(self) -> bool:
        """Whether to use incremental solver."""
        return self._use_incremental

    def set_incremental(self, enabled: bool = True) -> 'FMOracleModel':
        """Set incremental solver mode (builder pattern)."""
        self._use_incremental = enabled
        return self

    # Convenience getters (delegate to result)
    def get_c(self) -> List:
        """Get the set of potentially faulty constraints."""
        return self.task.set_c

    def get_kb(self) -> List[List[int]]:
        """Get the full knowledge base with assumptions."""
        return self.task.set_kb

    def get_assumptions(self) -> List[int]:
        """Get the list of assumption literals."""
        return self.task.assumptions

    def get_fm_clauses(self) -> List[List[int]]:
        """Get FM CNF clauses (without assumption guards).

        Returns the original clauses from constraint_map, not the
        assumption-guarded versions stored in task.set_kb.
        """
        return [clause for clauses in self.constraint_map.values()
                for clause in clauses]

    def get_variables(self) -> set:
        """All feature names. The model owns the catalog; the oracle delegates."""
        return set(self.name_to_id.keys())

    def get_variable_ids(self) -> Dict[str, int]:
        """Feature name -> SAT variable id. The model owns the catalog."""
        return dict(self.name_to_id)

    def prepare(self) -> DiagnosisTask:
        """Build set_kb + assumptions from constraint_map and variables."""
        output = FMOracleTaskPreparation.prepare(self)

        self._task = output.task
        self._description_provider = output.describe

        return self._task

    @classmethod
    def from_fm(cls, fm_path: str) -> 'FMOracleModel':
        """Factory: create from FM and prepare."""
        builder = cls()
        builder._fm_path = fm_path
        return builder

    def build(self) -> 'FMOracleModel':
        """Convenience method for chaining: build and prepare."""
        from flamapy.metamodels.fm_metamodel.transformations import UVLReader
        from explanation.api import FmToDiagPysat

        fm = UVLReader(self._fm_path).transform()
        # FmToDiagPysat creates both constraint_map and negated_constraint_map for redundancy detection.
        fm_model = FmToDiagPysat(fm, create_negation=True).transform()

        self.constraint_map = fm_model.constraint_map
        self.negated_constraint_map = fm_model.negated_constraint_map

        self.name_to_id = fm_model.variables
        self.id_to_name = fm_model.features
        self.next_available_id = fm_model.next_available_id

        self.prepare()

        return self


class FMOracleTaskPreparation:
    """Prepare assumption-guarded clauses for Oracle FM validation.

    Shared Assumption ID Layout (Oracle owns Parts 1-4):
      Part 1: Feature variable IDs (1..n)               <- FmToDiagPysat
      Part 2: Tseitin vars (negated FM constraints)      <- FmToDiagPysat
      Part 3: FM constraint assumptions (paired)         <- This method
               [root, NOT(root), c2, NOT(c2), ...]
      Part 4: Variable assignment assumptions (paired)   <- This method
               [f1=true, f1=false, f2=true, ...]

    ConGen continues from Part 5 onward (see ConGenTaskPreparation).
    BGData extracts Part 3's first pair (root BG) + end-of-Part-4 ID.
    """

    @staticmethod
    def prepare(model: 'FMOracleModel') -> PreparedTask:
        provider = DescriptionProvider()

        # Use next_available_id to avoid conflicts with Tseitin variables
        id_assumption = model.next_available_id

        # Determine if negated forms should be used
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

        # The feature-assignment map, built once here — membership queries reuse
        # it (is_valid appends this query's assumptions to task.set_c locally).
        model.assignment_map = AssignmentAssumptionMap(
            pos_assignment_to_assumption, neg_assignment_to_assumption)

        # Step 3: FM constraint assumptions only (originals of the paired Part-3
        # layout, stride 2). Stored on the frozen task as set_c; is_valid reads it
        # directly and never rebinds it.
        set_c = slice_assumptions(assumptions, 0, assignments_start_index, 2)

        # Extract Part 4 data (assignment clauses added after Part 3)
        assignment_clauses = set_kb[assignment_kb_start:]
        assignment_assumptions = assumptions[assignments_start_index:]

        # Step 4: Extract root BG data for ConGen consumption (requires negated constraints)
        model._bg_data = BGData(
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

        # Build-then-freeze: construct the frozen task once (set_b unused by Oracle).
        task = DiagnosisTask(
            set_c=set_c, set_b=[], set_kb=set_kb,
            negation_map=negation_map, assumptions=assumptions)
        return PreparedTask(
            task=task,
            describe=provider
        )


