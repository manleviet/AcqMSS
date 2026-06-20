"""
Oracle model for FM validation via SAT solver.

FMOracleModel: Immutable KB container for FM constraints + feature variables.
Satisfies ModelProtocol. Provides prepare_task() returning a DiagnosisTask
with attached VariableCodec (id_to_name + pos/neg assignment maps from Part 4).

FMOracleTaskPreparation: static preparation logic (unchanged structure).
"""

from typing import Dict, List, Optional

from conacq.oracle.bg_data import BGData
from explanation.models import DiagnosisTask, DescriptionProvider
from explanation.models.codec import VariableCodec
from explanation.models.task_preparation import (
    PreparationOutput,
    prepare_kb,
    _ASSUMPTION_PAIR_STRIDE,
)


class FMOracleModel:
    """Thin KB container for Oracle FM validation.

    Holds FM constraint_map, variables, and negated_constraint_map (for
    redundancy detection).  Satisfies ModelProtocol so preparation
    strategies can read it directly.

    Call prepare_task() to obtain a fresh DiagnosisTask with attached
    VariableCodec (codec).  The returned task is self-contained; the
    model itself carries no per-task mutable state.
    """

    def __init__(self):
        self._fm_path: str = ""

        # ModelProtocol fields -------------------------------------------------
        # constraint_map: FM constraint name -> raw CNF clauses
        self.constraint_map: Dict[str, List[List[int]]] = {}
        # negated_constraint_map: "NOT(name)" -> negated CNF clauses
        self.negated_constraint_map: Dict[str, List[List]] = {}
        # variables: feature name -> SAT variable ID
        self.variables: Dict[str, int] = {}
        # next_available_id: first ID safe for new assumption literals
        self.next_available_id: int = 1000

        # Internal state set by prepare_task (for BG extraction) ---------------
        self._bg_data: Optional[BGData] = None

    @property
    def bg_data(self) -> BGData:
        """Root BG data for ConGen. Call prepare_task() first."""
        if self._bg_data is None:
            raise RuntimeError("Call prepare_task() first")
        return self._bg_data

    def prepare_task(self, configuration=None) -> DiagnosisTask:
        """Build a fresh DiagnosisTask from the FM constraint_map.

        Attaches a VariableCodec (codec) with:
          - id_to_name: {var_id: feature_name}
          - pos_assignment_to_assumption: {name: assumption_id for feature=true}
          - neg_assignment_to_assumption: {name: assumption_id for feature=false}

        Also populates self._bg_data for ConGen/BG extraction.

        Args:
            configuration: Optional Dict[str, bool] or Configuration to
                apply immediately (sets task.set_c to base FM assumptions
                + per-feature assignment assumptions).

        Returns:
            Fresh DiagnosisTask with task.codec attached.
        """
        output = FMOracleTaskPreparation.prepare(self, configuration)
        task = output.task

        # Build codec from Part 4 maps created during preparation
        codec = VariableCodec(
            id_to_name={vid: name for name, vid in self.variables.items()},
            pos_assignment_to_assumption=dict(self._pos_assignment_to_assumption),
            neg_assignment_to_assumption=dict(self._neg_assignment_to_assumption),
        )
        task.codec = codec
        task.describe = output.description_provider

        return task

    # -------------------------------------------------------------------------
    # Convenience helpers (used by FeatureModelOracle)
    # -------------------------------------------------------------------------

    def get_fm_clauses(self) -> List[List[int]]:
        """Raw FM CNF clauses (without assumption guards)."""
        return [clause for clauses in self.constraint_map.values()
                for clause in clauses]

    # -------------------------------------------------------------------------
    # Factory / builder methods
    # -------------------------------------------------------------------------

    @classmethod
    def from_fm(cls, fm_path: str) -> 'FMOracleModel':
        """Factory: create model from FM path (not yet built)."""
        obj = cls()
        obj._fm_path = fm_path
        return obj

    def build(self) -> 'FMOracleModel':
        """Load FM from file, populate constraint_map/variables, call prepare_task()."""
        from flamapy.metamodels.fm_metamodel.transformations import UVLReader
        from explanation.transformations.fm_to_diag_pysat import FmToDiagPysat

        fm = UVLReader(self._fm_path).transform()
        fm_model = FmToDiagPysat(fm, create_negation=True).transform()

        self.constraint_map = fm_model.constraint_map
        self.negated_constraint_map = fm_model.negated_constraint_map
        self.variables = fm_model.variables
        self.next_available_id = fm_model.next_available_id

        # Prepare task to populate _bg_data (needed by oracle before any query)
        self.prepare_task()

        return self

    # Populated by FMOracleTaskPreparation during prepare_task(): the FM-constraint
    # base assumptions and the Part-4 assignment-assumption maps the codec is built from.
    _pos_assignment_to_assumption: Dict[str, int]
    _neg_assignment_to_assumption: Dict[str, int]
    _base_set_c: List[int]


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
    def prepare(model: 'FMOracleModel', configuration=None) -> PreparationOutput:
        result = DiagnosisTask()
        provider = DescriptionProvider()

        # Use next_available_id to avoid conflicts with Tseitin variables
        id_assumption = model.next_available_id

        # Determine if negated forms should be used
        negated_constraint_map = model.negated_constraint_map

        # Step 1: FM constraints from constraint_map → set_kb with assumptions
        id_assumption = prepare_kb(
            result, provider, model.constraint_map, id_assumption, negated_constraint_map)

        # Step 2: Feature assignments → assumption-guarded
        assignments_start_index = len(result.assumptions)
        assignment_kb_start = len(result.set_kb)
        pos_assignment_to_assumption = {}
        neg_assignment_to_assumption = {}

        for name, fid in model.variables.items():
            # a_pos: if active → feature must be true
            a_pos = id_assumption
            desc = f'{name}=true'
            result.set_kb.append([-a_pos, fid])

            result.assumptions.append(a_pos)
            provider.add_configuration_description(a_pos, desc)
            pos_assignment_to_assumption[name] = a_pos
            id_assumption += 1

            # a_neg: if active → feature must be false
            a_neg = id_assumption
            desc = f'{name}=false'
            result.set_kb.append([-a_neg, -fid])

            result.assumptions.append(a_neg)
            provider.add_configuration_description(a_neg, desc)
            neg_assignment_to_assumption[name] = a_neg
            id_assumption += 1

        # Store Part 4 maps on the model so prepare_task() can build codec
        model._pos_assignment_to_assumption = pos_assignment_to_assumption
        model._neg_assignment_to_assumption = neg_assignment_to_assumption

        # Step 3: compute and cache base set_c (FM constraint assumptions only)
        model._base_set_c = [result.assumptions[i]
                             for i in range(0, assignments_start_index, _ASSUMPTION_PAIR_STRIDE)]
        result.set_c = list(model._base_set_c)

        # Step 3b: apply configuration if provided
        if configuration is not None:
            items = (configuration.elements.items()
                     if hasattr(configuration, 'elements') else configuration.items())
            config_assumptions = [
                pos_assignment_to_assumption[feat] if value
                else neg_assignment_to_assumption[feat]
                for feat, value in items
            ]
            result.set_c = model._base_set_c + config_assumptions

        # Extract Part 4 data (assignment clauses added after Part 3)
        assignment_clauses = result.set_kb[assignment_kb_start:]
        assignment_assumptions = result.assumptions[assignments_start_index:]

        # Step 4: Extract root BG data for ConGen consumption (requires negated constraints)
        model._bg_data = BGData(
            set_kb=result.set_kb[:2],  # first pair of assumptions for root constraint
            assumptions=(result.assumptions[0], result.assumptions[1]),
            negation_map={result.assumptions[0]: result.assumptions[1]},
            descriptions=provider.get_descriptions_for(
                [result.assumptions[0], result.assumptions[1]]),
            next_available_id=id_assumption,
            # Part 4
            assignment_clauses=assignment_clauses,
            assignment_assumptions=assignment_assumptions,
            pos_assignment_to_assumption=dict(pos_assignment_to_assumption),
            neg_assignment_to_assumption=dict(neg_assignment_to_assumption),
        )

        return PreparationOutput(
            task=result,
            description_provider=provider
        )
