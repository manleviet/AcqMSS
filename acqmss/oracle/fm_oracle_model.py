"""
Oracle models for ConsistencyChecker integration.

FMOracleModel: Assumption-guarded FM validation (incremental checker).
OneShotModel: Baked unit clauses for one-shot SAT checks (non-incremental).

Both satisfy CheckerModel Protocol for use with CheckerFactory.create_from_model().
"""

from typing import Dict, List, Optional

from flamapy.metamodels.configuration_metamodel.models import Configuration

from explanation.models import DiagnosisTask, DescriptionProvider
from explanation.models.task_preparation import PreparationOutput, prepare_kb


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
        self.next_tseitin_var: int = 1000

        self.configuration: Optional[Configuration] = None

        # CheckerModel protocol attributes
        self._use_incremental: bool = True

        # Populated after prepare()
        self._start_id_assignments: int = 1
        self._pos_assignment_to_assumption: Dict[str, int] = {}
        self._neg_assignment_to_assumption: Dict[str, int] = {}
        # Populated after prepare()
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
    def start_id_assignments(self):
        return self._start_id_assignments

    def use_incremental(self, enabled: bool = True) -> 'FMOracleModel':
        """Set incremental solver mode."""
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

    def with_configuration(self, configuration: Configuration) -> 'FMOracleModel':
        """Convert feature config to list of assumption IDs to activate."""
        active_assumptions = []
        for feat, value in configuration.elements.items():
            assumption = self._pos_assignment_to_assumption[feat] if value else self._neg_assignment_to_assumption[feat]

            active_assumptions.append(assumption)

        step = 2
        set_c = [self._task.assumptions[i] for i in range(0, self.start_id_assignments, step)]
        set_c += active_assumptions

        self._task.set_c = set_c
        return self

    def prepare(self) -> DiagnosisTask:
        """Build set_kb + assumptions from constraint_map and variables."""
        output = OracleTaskPreparation.prepare(self)

        self._task = output.task
        self._description_provider = output.description_provider

        return self._task

    # TODO: remove
    @classmethod
    def from_fm_data(cls, constraint_map: Dict[str, List[List[int]]],
                     variables: Dict[str, int],
                     next_tseitin_var: int) -> 'FMOracleModel':
        """Factory: create from FM data and prepare."""
        model = cls()
        model.constraint_map = constraint_map
        model.variables = variables
        model.next_tseitin_var = next_tseitin_var
        # return model.prepare()
        return model

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
        fm_model = FmToDiagPysat(fm, create_negation=True).transform()

        self.constraint_map = fm_model.constraint_map
        self.negated_constraint_map = fm_model.negated_constraint_map

        self.variables = fm_model.variables
        self.next_tseitin_var = fm_model.next_tseitin_var

        self.prepare()

        return self



class OracleTaskPreparation:
    """Prepare assumption-guarded clauses for Oracle FM validation.

    FM constraints → direct in set_kb (always active).
    Feature assignments → assumption-guarded unit clauses.
    """

    @staticmethod
    def prepare(model: 'FMOracleModel') -> PreparationOutput:
        result = DiagnosisTask()
        provider = DescriptionProvider()

        # Use next_tseitin_var to avoid conflicts with Tseitin variables
        id_assumption = model.next_tseitin_var

        # Determine if negated forms should be used
        negated_constraint_map = model.negated_constraint_map

        # Step 1: FM constraints from constraint_map → direct in set_kb
        id_assumption = prepare_kb(
            result, provider, model.constraint_map, id_assumption, negated_constraint_map)

        # Step 2: Feature assignments → assumption-guarded
        model._start_id_assignments = len(result.assumptions)
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

        # Step 4: assign to set_c for consistency checks
        step = 2
        result.set_c = [result.assumptions[i] for i in range(0, model.start_id_assignments, step)]

        return PreparationOutput(
            task=result,
            description_provider=provider
        )


class OneShotModel:
    """Minimal CheckerModel for one-shot SAT checks.

    Bakes all clauses + unit assumptions into set_kb.
    Satisfies CheckerModel Protocol for CheckerFactory.
    """
    use_incremental = False

    def __init__(self, clauses: List[List[int]], unit_assumptions: List[int] = None):
        self._set_kb = list(clauses)
        if unit_assumptions:
            self._set_kb.extend([lit] for lit in unit_assumptions)

    def get_kb(self) -> List[List[int]]:
        return self._set_kb

    def get_assumptions(self) -> List[int]:
        return []
