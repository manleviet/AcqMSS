"""
Oracle models for ConsistencyChecker integration.

FMOracleModel: Assumption-guarded FM validation (incremental checker).
Satisfies CheckerModel Protocol for use with CheckerFactory.create_from_model().
"""

from typing import Dict, List, Optional

from flamapy.metamodels.configuration_metamodel.models import Configuration

from conacq.oracle.bg_data import BGData
from explanation.models import DiagnosisTask, DescriptionProvider
from explanation.models.task_preparation import PreparationOutput, prepare_kb, _ASSUMPTION_PAIR_STRIDE


class FMOracleModel:
    """Model for Oracle FM validation via ConsistencyChecker.

    Uses constraint_map + variables pattern (same as DiagnosisModel/ConGenModel).
    Satisfies CheckerModel Protocol after prepare().

    FM clauses go directly into set_kb (always active).
    Feature assignments become assumption-guarded unit clauses:
      [-a_pos_i, fid]  → if a_pos_i active, feature must be true
      [-a_neg_i, -fid] → if a_neg_i active, feature must be false
    """

    def __init__(self):
        self._fm_path: str = ""

        # map clauses to relationships/constraint
        self.constraint_map: Dict[str, List[List[int]]] = {}
        # map negated clauses to relationships/constraint (for redundancy detection)
        self.negated_constraint_map: Dict[str, List[List]] = {}
        # map feature names to IDs (for debugging and description generation)
        self.variables: Dict[str, int] = {}
        # Used as starting ID for assumption literals to avoid conflicts.
        self.next_available_id: int = 1000

        self.configuration: Optional[Configuration] = None

        # CheckerModel protocol attributes
        self._use_incremental: bool = True

        # Populated after prepare()
        self._base_set_c: List = []
        self._pos_assignment_to_assumption: Dict[str, int] = {}
        self._neg_assignment_to_assumption: Dict[str, int] = {}
        # Populated after prepare()
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

    def _config_to_assumptions(self, configuration) -> list:
        """Convert feature config to assignment assumption IDs.

        Args:
            configuration: Dict[str, bool] or Configuration object

        Returns:
            List of assumption IDs for the given feature assignments
        """
        items = configuration.elements.items() if hasattr(configuration, 'elements') else configuration.items()
        return [self._pos_assignment_to_assumption[feat] if value else self._neg_assignment_to_assumption[feat]
                for feat, value in items]

    def with_configuration(self, configuration) -> 'FMOracleModel':
        """Apply feature config: updates set_c with base + assignment assumptions.

        Args:
            configuration: Dict[str, bool] or Configuration object

        Returns:
            self (for fluent chaining)
        """
        self.task.set_c = self._base_set_c + self._config_to_assumptions(configuration)
        return self

    def prepare(self, configuration=None) -> DiagnosisTask:
        """Build set_kb + assumptions from constraint_map and variables.

        Args:
            configuration: Optional Dict[str, bool] or Configuration to apply immediately
        """
        output = FMOracleTaskPreparation.prepare(self, configuration)

        self._task = output.task
        self._description_provider = output.description_provider

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
        from explanation.transformations.fm_to_diag_pysat import FmToDiagPysat

        fm = UVLReader(self._fm_path).transform()
        # FmToDiagPysat creates both constraint_map and negated_constraint_map for redundancy detection.
        fm_model = FmToDiagPysat(fm, create_negation=True).transform()

        self.constraint_map = fm_model.constraint_map
        self.negated_constraint_map = fm_model.negated_constraint_map

        self.variables = fm_model.variables
        self.next_available_id = fm_model.next_available_id

        self.prepare(configuration=self.configuration)

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
        neg_assumption_to_assumption = {}

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
            neg_assumption_to_assumption[name] = a_neg
            id_assumption += 1

        model._pos_assignment_to_assumption = pos_assignment_to_assumption
        model._neg_assignment_to_assumption = neg_assumption_to_assumption

        # Step 3: compute and cache base set_c (FM constraint assumptions only)
        model._base_set_c = [result.assumptions[i]
                             for i in range(0, assignments_start_index, _ASSUMPTION_PAIR_STRIDE)]
        result.set_c = list(model._base_set_c)

        # Step 3b: apply configuration if provided
        if configuration is not None:
            result.set_c = model._base_set_c + model._config_to_assumptions(configuration)

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
            neg_assignment_to_assumption=dict(neg_assumption_to_assumption),
        )

        return PreparationOutput(
            task=result,
            description_provider=provider
        )


