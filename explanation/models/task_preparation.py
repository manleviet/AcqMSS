"""Task preparation strategies and utilities for diagnosis.

This module provides strategy pattern implementations for preparing diagnosis tasks.

Strategy hierarchy:
- DiagnosisTaskPreparationStrategy: For diagnosis/conflict operations
  - IncrementalDiagnosisTaskPreparation
  - NonIncrementalDiagnosisTaskPreparation
- TestCaseTaskPreparationStrategy: For operations with test cases (KBDiag, WipeOutR_T)
  - IncrementalTestCaseTaskPreparation
  - NonIncrementalTestCaseTaskPreparation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Union, TYPE_CHECKING

from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.fm_metamodel.models.feature_model import Feature

from explanation.models.testsuite import TestSuite
from explanation.operations.algorithms.utils import get_hashcode

if TYPE_CHECKING:
    from .pysat_diagnosis_model import DiagnosisModel


# === INPUT DATA CLASS ===

@dataclass
class TaskInput:
    """Input parameters for task preparation.

    Single source of truth for user inputs passed through:
    DiagnosisModelBuilder → DiagnosisModel → TaskPreparation

    Use Cases Mapping:
    ==================
    1. Configuration diagnosis: configuration is set
    2. Config + FM diagnosis: configuration + with_cf_in_c=True
    3. FM diagnosis: no inputs (defaults)
    4. Error diagnosis: test_case is set
    5. KBDiag: positive_test_cases (+ optional negative_test_cases)
    6. WipeOutR_T: positive_test_cases + for_redundancy=True
    7. WipeOutR_FM: for_redundancy=True
    8. CXPlain (future): requirement + configuration + sub_configuration
    """
    # Diagnosis inputs
    configuration: Optional[Configuration] = None
    test_case: Optional[Configuration] = None
    with_cf_in_c: bool = False

    # Test case inputs
    positive_test_cases: Optional[TestSuite] = None
    negative_test_cases: Optional[TestSuite] = None

    # Redundancy detection
    for_redundancy: bool = False

    # CXPlain inputs (future)
    requirement: Optional[Configuration] = None
    sub_configuration: Optional[Configuration] = None

    def is_testcase_task(self) -> bool:
        """Check if this input is for a test case task."""
        return self.positive_test_cases is not None


# === UTILITIES ===

def convert_keys_to_features(configuration: Configuration) -> Configuration:
    """Convert string keys to Feature objects."""
    new_elements = {Feature(key) if isinstance(key, str) else key: value
                    for key, value in configuration.elements.items()}
    return Configuration(new_elements)


# === RESULT DATA CLASSES (Core data only) ===

@dataclass
class DiagnosisTask(ABC):
    """Base class for a diagnosis task.

    Contains only core data needed by algorithms.
    """
    # set of constraints which could be faulty
    set_c: List = field(default_factory=list)
    # background knowledge (i.e., the knowledge that is known to be true)
    set_b: List = field(default_factory=list)
    # set of all CNF with added assumptions
    set_kb: List = field(default_factory=list)
    # mapping: (for redundancy detection)
    # incremental: constraint ID -> negated constraint ID
    # non-incremental: constraint clauses -> negated constraint clauses
    neg_c_map: Dict = field(default_factory=dict)

    def get_cf(self) -> List:
        """Get all constraints (C ∪ B)."""
        return self.set_b + self.set_c


@dataclass
class IncrementalDiagnosisTask(DiagnosisTask):
    """Data for incremental mode.

    Contains assumptions needed by IncrementalPySATChecker.
    """
    # list of assumptions
    assumptions: List = field(default_factory=list)


@dataclass
class NonIncrementalDiagnosisTask(DiagnosisTask):
    """Data for non-incremental mode.

    No additional fields needed - uses only base class data.
    """
    pass


@dataclass
class TestCaseTask(DiagnosisTask):
    """Base class for tasks with test cases.

    Contains common fields for both incremental and non-incremental modes.
    Used by KBDiag algorithm with positive/negative test cases,
    and WipeOutR_T for test case redundancy detection.
    """
    # positive test cases (original form)
    set_tc: List = field(default_factory=list)
    # negative test cases (original form)
    set_tv: List = field(default_factory=list)
    # negated negative test cases (for KBDiag: B = B ∪ neg_Tν)
    set_neg_tv: List = field(default_factory=list)
    # negated positive test cases (for WipeOutR)
    set_neg_tc: List = field(default_factory=list)
    # mapping: (for WipeOutR_T)
    # incremental: test case ID -> negated test case ID
    # non-incremental: test case clauses -> negated test case clauses
    neg_tc_map: Dict = field(default_factory=dict)


@dataclass
class IncrementalTestCaseTask(TestCaseTask):
    """Test case task for incremental mode.

    Contains assumptions needed by IncrementalPySATChecker.
    """
    # list of assumptions
    assumptions: List = field(default_factory=list)


@dataclass
class NonIncrementalTestCaseTask(TestCaseTask):
    """Test case task for non-incremental mode.

    No assumptions needed - uses clause-based consistency checking.
    """
    pass


# Type alias for tasks with assumptions (used by IncrementalKBPreparator)
IncrementalTaskType = Union[IncrementalDiagnosisTask, IncrementalTestCaseTask]


# === DESCRIPTION PROVIDERS (For formatting only) ===

class DescriptionProvider:
    """Maps keys to descriptions, separated by category.

    Automatically handles both key types:
    - int keys (Incremental mode) → used directly
    - list keys (NonIncremental mode) → hashed via get_hashcode()

    Used only for formatting diagnosis results, not for algorithm logic.
    """

    def __init__(self):
        self.constraint_map: Dict = {}
        self.configuration_map: Dict = {}
        self.test_case_map: Dict = {}

    def _to_key(self, item):
        """Auto-detect key type and transform accordingly."""
        if isinstance(item, int):
            return item
        return get_hashcode(item)

    def get_description(self, item) -> str:
        """Get description, searching in order: constraint -> configuration -> test_case."""
        key = self._to_key(item)
        if key in self.constraint_map:
            return self.constraint_map[key]
        if key in self.configuration_map:
            return self.configuration_map[key]
        if key in self.test_case_map:
            return self.test_case_map[key]
        return str(item)

    def add_constraint_description(self, key, description: str) -> None:
        """Add description for KB constraint."""
        self.constraint_map[self._to_key(key)] = description

    def add_configuration_description(self, key, description: str) -> None:
        """Add description for configuration item."""
        self.configuration_map[self._to_key(key)] = description

    def add_test_case_description(self, key, description: str) -> None:
        """Add description for test case."""
        self.test_case_map[self._to_key(key)] = description

    def reset_constraint(self) -> None:
        """Reset constraint map."""
        self.constraint_map = {}

    def reset_configuration(self) -> None:
        """Reset configuration map."""
        self.configuration_map = {}


# === PREPARATION OUTPUT ===

@dataclass
class PreparationOutput:
    """Container for preparation result and description provider."""
    task: DiagnosisTask
    description_provider: DescriptionProvider


# === STRATEGY INTERFACES ===

class DiagnosisTaskPreparationStrategy(ABC):
    """Abstract strategy for preparing diagnosis tasks.

    Used for:
    - Configuration diagnosis
    - Feature model diagnosis
    - Configuration + feature model diagnosis
    - Error diagnosis with test case
    - Redundancy detection (with negated_constraint_map)
    """

    @abstractmethod
    def prepare(self, model: 'DiagnosisModel') -> PreparationOutput:
        """Prepare diagnosis task and return result with description provider.

        Args:
            model: DiagnosisModel containing variables, constraint_map, etc.

        Returns:
            PreparationOutput with DiagnosisTask and description provider
        """
        pass

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Return mode name for logging."""
        pass


class TestCaseTaskPreparationStrategy(ABC):
    """Abstract strategy for preparing tasks with test cases.

    Used for KBDiag algorithm with positive/negative test cases,
    and WipeOutR_T for test case redundancy detection.
    """

    @abstractmethod
    def prepare(self, model: 'DiagnosisModel') -> PreparationOutput:
        """Prepare test case task and return result with description provider.

        Args:
            model: DiagnosisModel containing variables, constraint_map, etc.

        Returns:
            PreparationOutput with TestCaseTask and description provider
        """
        pass

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Return mode name for logging."""
        pass


# === SHARED UTILITIES ===

class IncrementalKBPreparator:
    """Utility class for preparing knowledge base with assumptions.

    Shared between IncrementalDiagnosisTaskPreparation and IncrementalTestCaseTaskPreparation.
    """

    @staticmethod
    def prepare_kb(result: IncrementalTaskType,
                   provider: DescriptionProvider,
                   constraint_map: Dict[str, List[List]],
                   id_assumption: int,
                   negated_constraint_map: Optional[Dict[str, List[List]]]) -> int:
        """Prepare KB with assumptions and optionally negated forms.

        Args:
            result: Task to populate with KB data
            provider: Description provider for formatting
            constraint_map: Constraint name to clauses mapping
            id_assumption: Starting assumption ID
            negated_constraint_map: Optional negated constraints for redundancy detection

        Returns:
            Next available assumption ID
        """
        for key, clauses in constraint_map.items():
            # --- Original constraint with assumption ---
            original_id = id_assumption
            for clause in clauses:
                # assumption => clause
                # i.e., -assumption v clause
                # Copy clause to avoid modifying original constraint_map
                new_clause = clause.copy()
                new_clause.append(-original_id)
                result.set_kb.append(new_clause)

            result.assumptions.append(original_id)
            provider.add_constraint_description(original_id, key)
            id_assumption += 1

            # --- Negated constraint (if provided) ---
            if negated_constraint_map is not None:
                negated_key = f"NOT({key})"
                if negated_key in negated_constraint_map:
                    negated_id = id_assumption
                    for neg_clause in negated_constraint_map[negated_key]:
                        new_neg_clause = neg_clause.copy()
                        new_neg_clause.append(-negated_id)
                        result.set_kb.append(new_neg_clause)

                    result.assumptions.append(negated_id)
                    result.neg_c_map[original_id] = negated_id
                    provider.add_constraint_description(negated_id, negated_key)
                    id_assumption += 1
            # If negated_constraint_map is None, we skip adding negated forms

        return id_assumption

    @staticmethod
    def prepare_configuration(result: IncrementalDiagnosisTask,
                              provider: DescriptionProvider,
                              variables: Dict[str, int],
                              configuration: Configuration,
                              id_assumption: int) -> int:
        """Prepare configuration with assumptions.

        Args:
            result: Task to populate
            provider: Description provider
            variables: Variable name to ID mapping
            configuration: Configuration to prepare
            id_assumption: Starting assumption ID

        Returns:
            Next available assumption ID
        """
        configuration = convert_keys_to_features(configuration)
        for feat in configuration.elements:
            if feat.name not in variables:
                raise KeyError(f'Feature {feat.name} is not in the model.')

        for feat, value in configuration.elements.items():
            desc = f'{feat.name} = {"true" if value else "false"}'
            var = variables[feat.name] if value else -1 * variables[feat.name]
            clause = [var, -1 * id_assumption]

            result.assumptions.append(id_assumption)
            result.set_kb.append(clause)
            provider.add_configuration_description(id_assumption, desc)

            id_assumption += 1

        return id_assumption


# === INCREMENTAL DIAGNOSIS STRATEGY ===

class IncrementalDiagnosisTaskPreparation(DiagnosisTaskPreparationStrategy):
    """Incremental mode: uses assumptions for efficient repeated checks.

    Supported task types:
    1. Configuration diagnosis (is_CF_in_C = False):
        C = configuration, B = feature model (PySATModel) + root
    2. Configuration and feature model diagnosis (is_CF_in_C = True):
        C = configuration + feature model (PySATModel), B = root only
    3. Feature model diagnosis (test_case is None):
        C = FM constraints, B = root only
    4. Error diagnosis (debugging):
        C = FM constraints, B = root + test case
        where test_case is the following:
        + Dead feature: test_case = {fi = true}
        + False optional feature: test_case = {f_parent = true} & {f_child = false}
    5. Redundancy Detection Task (need negative constraints)
        C = CF (i.e., = PySATModel + {f0 = true})
        B = {}
    """

    @property
    def mode_name(self) -> str:
        return "incremental"

    def prepare(self, model: 'DiagnosisModel') -> PreparationOutput:
        result = IncrementalDiagnosisTask()
        provider = DescriptionProvider()

        task_input = model.task_input

        # Determine if negated forms should be used
        negated_constraint_map = model.negated_constraint_map if task_input.for_redundancy else None

        # Use next_tseitin_var to avoid conflicts with Tseitin variables
        id_assumption = model.next_tseitin_var

        # Prepare KB with assumptions and optionally negated forms
        id_assumption = IncrementalKBPreparator.prepare_kb(
            result, provider, model.constraint_map, id_assumption, negated_constraint_map)

        start_id_config = len(result.assumptions)
        if task_input.configuration is not None:
            id_assumption = IncrementalKBPreparator.prepare_configuration(
                result, provider, model.variables, task_input.configuration, id_assumption)

        start_id_test_case = len(result.assumptions)
        if task_input.test_case is not None:
            IncrementalKBPreparator.prepare_configuration(
                result, provider, model.variables, task_input.test_case, id_assumption)

        # Assign set_c and set_b
        has_negated_forms = negated_constraint_map is not None
        self._assign_sets(result, task_input, start_id_config, start_id_test_case, has_negated_forms)

        return PreparationOutput(result, provider)

    def _assign_sets(self, result: IncrementalDiagnosisTask, task_input: TaskInput,
                     start_id_config: int, start_id_test: int,
                     has_negated_forms: bool = True) -> None:
        """Assign set_c and set_b based on use case.

        Args:
            task_input: TaskInput containing configuration, test_case, with_cf_in_c
            has_negated_forms: If True, assumptions alternate between original and negated.
                              If False, assumptions are all original constraints.
        """
        # Determine step size for extracting original constraints
        # With negation: [root, neg_root, c1, neg_c1, ...] -> step=2
        # Without negation: [root, c1, c2, ...] -> step=1
        step = 2 if has_negated_forms else 1

        if task_input.configuration is not None:
            if not task_input.with_cf_in_c:
                # Diagnosis for configuration only
                # C = configuration, B = FM + root
                result.set_b = [result.assumptions[i] for i in range(0, start_id_config, step)]
                result.set_c = result.assumptions[start_id_config:]
            else:
                # Diagnosis for configuration + feature model
                # C = configuration + FM, B = root only
                result.set_b = [result.assumptions[0]]
                result.set_c = [result.assumptions[i] for i in range(step, start_id_config, step)] + \
                               result.assumptions[start_id_config:]
        else:
            if task_input.test_case is not None:
                # Error diagnosis with a test case
                # C = FM constraints, B = root + a test case
                result.set_b = [result.assumptions[0]] + result.assumptions[start_id_test:]
                result.set_c = [result.assumptions[i] for i in range(step, start_id_config, step)]
            else:
                # Feature model diagnosis
                # C = FM constraints, B = root only
                result.set_b = [result.assumptions[0]]
                result.set_c = [result.assumptions[i] for i in range(step, len(result.assumptions), step)]


# === NON-INCREMENTAL DIAGNOSIS STRATEGY ===

class NonIncrementalDiagnosisTaskPreparation(DiagnosisTaskPreparationStrategy):
    """Non-incremental mode: fresh solver for each check.

    Supported task types:
    1. Configuration diagnosis (is_CF_in_C = False):
        C = configuration, B = feature model (PySATModel) + root
    2. Configuration and feature model diagnosis (is_CF_in_C = True):
        C = configuration + feature model (PySATModel), B = root only
    3. Feature model diagnosis (test_case is None):
        C = FM constraints, B = root only
    4. Error diagnosis (debugging):
        C = FM constraints, B = root + test case
        where test_case is the following:
        + Dead feature: test_case = {fi = true}
        + False optional feature: test_case = {f_parent = true} & {f_child = false}
    5. Redundancy Detection Task (need negative constraints)
        C = CF (i.e., = PySATModel + {f0 = true})
        B = {}
    """

    @property
    def mode_name(self) -> str:
        return "non-incremental"

    def prepare(self, model: 'DiagnosisModel') -> PreparationOutput:
        result = NonIncrementalDiagnosisTask()
        provider = DescriptionProvider()

        task_input = model.task_input

        # Determine if negated forms should be used
        negated_constraint_map = model.negated_constraint_map if task_input.for_redundancy else None

        # Prepare KB from constraint_map (as clause lists) with optional negated forms
        for key, clauses in model.constraint_map.items():
            result.set_kb.append(clauses)
            provider.add_constraint_description(clauses, key)

            # Add negated constraint if provided
            if negated_constraint_map is not None:
                negated_key = f"NOT({key})"
                if negated_key in negated_constraint_map:
                    neg_clauses = negated_constraint_map[negated_key]
                    result.set_kb.append(neg_clauses)
                    result.neg_c_map[get_hashcode(clauses)] = neg_clauses
                    provider.add_constraint_description(neg_clauses, negated_key)

        start_id_config = len(result.set_kb)
        if task_input.configuration is not None:
            self._prepare_configuration(result, provider, model.variables, task_input.configuration)

        start_id_test_case = len(result.set_kb)
        if task_input.test_case is not None:
            self._prepare_configuration(result, provider, model.variables, task_input.test_case,
                                        add_to_map=False)

        # Assign set_c and set_b
        has_negated = negated_constraint_map is not None
        self._assign_sets(result, provider, model.constraint_map, task_input,
                          start_id_config, start_id_test_case, has_negated)

        return PreparationOutput(result, provider)

    def _prepare_configuration(self, result: NonIncrementalDiagnosisTask,
                               provider: DescriptionProvider,
                               variables: Dict[str, int],
                               configuration: Configuration,
                               add_to_map: bool = True) -> None:
        configuration = convert_keys_to_features(configuration)
        for feat in configuration.elements:
            if feat.name not in variables:
                raise KeyError(f'Feature {feat.name} is not in the model.')

        for feat, value in configuration.elements.items():
            desc = f'{feat.name} = {"true" if value else "false"}'
            var = variables[feat.name] if value else -1 * variables[feat.name]
            clause = [[var]]

            result.set_kb.append(clause)
            if add_to_map:
                provider.add_configuration_description(clause, desc)

    def _prepare_kb_map(self, provider: DescriptionProvider,
                        constraint_map: Dict[str, List[List]]) -> None:
        for key, clauses in constraint_map.items():
            provider.add_constraint_description(clauses, key)

    def _assign_sets(self, result: NonIncrementalDiagnosisTask,
                     provider: DescriptionProvider,
                     constraint_map: Dict[str, List[List]],
                     task_input: TaskInput,
                     start_id_config: int, start_id_test: int,
                     has_negated_forms: bool = False) -> None:
        """Assign set_c and set_b based on use case.

        Args:
            has_negated_forms: If True, set_kb alternates between original and negated.
                              If False, set_kb contains only original constraints.
        """
        # Determine step size for extracting original constraints
        # With negation: [root, neg_root, c1, neg_c1, ...] -> step=2
        # Without negation: [root, c1, c2, ...] -> step=1
        step = 2 if has_negated_forms else 1

        if task_input.configuration is not None:
            if not task_input.with_cf_in_c:
                result.set_b = [result.set_kb[i] for i in range(0, start_id_config, step)]
                result.set_c = result.set_kb[start_id_config:]
            else:
                self._prepare_kb_map(provider, constraint_map)
                result.set_b = [result.set_kb[0]]
                result.set_c = [result.set_kb[i] for i in range(step, start_id_config, step)] + \
                               result.set_kb[start_id_config:]
        else:
            self._prepare_kb_map(provider, constraint_map)
            if task_input.test_case is not None:
                result.set_b = [result.set_kb[0]] + result.set_kb[start_id_test:]
                result.set_c = [result.set_kb[i] for i in range(step, start_id_config, step)]
            else:
                result.set_b = [result.set_kb[0]]
                result.set_c = [result.set_kb[i] for i in range(step, len(result.set_kb), step)]


# === INCREMENTAL TEST CASE STRATEGY ===

class IncrementalTestCaseTaskPreparation(TestCaseTaskPreparationStrategy):
    """Strategy for test case task with test cases.

    Uses IncrementalKBPreparator for shared KB preparation logic.
    Prepares model for KBDiag algorithm with positive/negative test cases.
    Prepares model for WipeOutR_T for test case redundancy detection.

    Supported task types:
    1. Debugging task - Diagnosis with positive and negative
        C = FM constraints (excluding root)
        B = root constraint
        TC = positive test cases
        TV = negative test cases
    2. WipeOutR_T - Redundancy detection for test cases
        TC = positive test cases
    """

    @property
    def mode_name(self) -> str:
        return "incremental-testcase"

    def prepare(self, model: 'DiagnosisModel') -> PreparationOutput:
        """Prepare test case task with test cases.

        Args:
            model: DiagnosisModel containing variables, constraint_map, next_tseitin_var
            task_input: TaskInput containing positive_test_cases, negative_test_cases

        Returns:
            PreparationOutput with TestCaseTask and description provider
        """
        result = IncrementalTestCaseTask()
        provider = DescriptionProvider()
        task_input = model.task_input

        # Use start_var_id to avoid conflicts with Tseitin variables
        id_assumption = model.next_tseitin_var

        # Use shared KB preparation (no negated forms needed for TestCaseTask)
        id_assumption = IncrementalKBPreparator.prepare_kb(
            result, provider, model.constraint_map, id_assumption, negated_constraint_map=None)

        # Prepare positive test cases with negated forms
        start_id_tc = len(result.assumptions)
        id_assumption = self._prepare_testsuite_with_negation(
            result, provider, model.variables, task_input.positive_test_cases, id_assumption, is_negative=False)

        # Prepare negative test cases with negated forms if provided
        start_id_tv = len(result.assumptions)
        if task_input.negative_test_cases is not None:
            self._prepare_testsuite_with_negation(
                result, provider, model.variables, task_input.negative_test_cases, id_assumption, is_negative=True)

        # Assign sets: B = root, C = FM constraints, TC = positive, TV = negative
        self._assign_sets(result, start_id_tc, start_id_tv, task_input.negative_test_cases is not None)

        return PreparationOutput(result, provider)

    def _prepare_testsuite_with_negation(self, result: IncrementalTestCaseTask,
                                         provider: DescriptionProvider,
                                         variables: Dict[str, int],
                                         testsuite: TestSuite,
                                         id_assumption: int,
                                         is_negative: bool) -> int:
        """Prepare test cases with assumptions and their negated forms.

        Each test case gets two assumption IDs: original and negated.
        The negated form is a single clause with all literals negated.

        Args:
            result: DebuggingTask to populate
            provider: Description provider for formatting
            variables: Variable name to ID mapping
            testsuite: TestSuite containing test cases
            id_assumption: Starting assumption ID
            is_negative: Whether this is a negative test suite

        Returns:
            Next available assumption ID
        """
        for testcase in testsuite.testcases:
            # --- Original form ---
            original_id = id_assumption
            desc_parts = []
            literals = []

            for assignment in testcase.assignments:
                if assignment.feature not in variables:
                    raise KeyError(f'Feature {assignment.feature} is not in the model.')

                desc_parts.append(f'{assignment.feature}={"true" if assignment.value else "false"}')
                var = variables[assignment.feature] if assignment.value else -1 * variables[assignment.feature]
                literals.append(var)
                clause = [var, -original_id]
                result.set_kb.append(clause)

            result.assumptions.append(original_id)
            provider.add_test_case_description(original_id, ' & '.join(desc_parts))
            id_assumption += 1

            # --- Negated form ---
            negated_id = id_assumption
            # Negated clause: (¬l1 ∨ ¬l2 ∨ ... ∨ ¬ln)
            negated_clause = [-lit for lit in literals]
            negated_clause.append(-negated_id)
            result.set_kb.append(negated_clause)

            result.assumptions.append(negated_id)
            provider.add_test_case_description(negated_id, f"NOT({' & '.join(desc_parts)})")

            # Add to appropriate negated list
            if is_negative:
                result.set_neg_tv.append(negated_id)
            else:
                result.set_neg_tc.append(negated_id)

            # Map original to negated
            result.neg_tc_map[original_id] = negated_id

            id_assumption += 1

        return id_assumption

    def _assign_sets(self, result: IncrementalTestCaseTask,
                     start_id_tc: int, start_id_tv: int,
                     has_negative_test_cases: bool) -> None:
        """Assign sets from assumptions.

        Note: Each test case has two assumptions (original + negated),
        so we need to extract only the original assumptions for set_tc and set_tv.
        """
        result.set_b = [result.assumptions[0]]
        result.set_c = result.assumptions[1:start_id_tc]

        # Extract only original test case assumptions (every other one starting from start_id_tc)
        # Original assumptions are at even positions from start_id_tc
        tc_tv_assumptions = result.assumptions[start_id_tc:]
        original_tc_tv = [tc_tv_assumptions[i] for i in range(0, len(tc_tv_assumptions), 2)]

        # Calculate relative start of TV within original assumptions
        num_tc_original = (start_id_tv - start_id_tc) // 2
        result.set_tc = original_tc_tv[:num_tc_original]
        result.set_tv = original_tc_tv[num_tc_original:] if has_negative_test_cases else []


# === NON-INCREMENTAL TEST CASE STRATEGY ===

class NonIncrementalTestCaseTaskPreparation(TestCaseTaskPreparationStrategy):
    """Strategy for non-incremental test case task with test cases.

    Prepares model for KBDiag algorithm using clause-based consistency checking.
    Prepares model for WipeOutR_T for test case redundancy detection.
    No assumptions - each constraint/test case is represented as a list of clauses.

    Supported task types:
    1. Debugging task - Diagnosis with positive and negative
        C = FM constraints (excluding root)
        B = root constraint
        TC = positive test cases
        TV = negative test cases
    2. WipeOutR_T - Redundancy detection for test cases
        TC = positive test cases
    """

    @property
    def mode_name(self) -> str:
        return "non-incremental-testcase"

    def prepare(self, model: 'DiagnosisModel') -> PreparationOutput:
        """Prepare test case task with test cases.

        Args:
            model: DiagnosisModel containing variables, constraint_map
            task_input: TaskInput containing positive_test_cases, negative_test_cases

        Returns:
            PreparationOutput with NonIncrementalTestCaseTask and description provider
        """
        result = NonIncrementalTestCaseTask()
        provider = DescriptionProvider()
        task_input = model.task_input

        # Prepare KB from constraint_map (as clause lists)
        for key, clauses in model.constraint_map.items():
            result.set_kb.append(clauses)
            provider.add_constraint_description(clauses, key)

        start_id_tc = len(result.set_kb)

        # Prepare positive test cases with negated forms
        self._prepare_testsuite_with_negation(
            result, provider, model.variables, task_input.positive_test_cases, is_negative=False)

        start_id_tv = len(result.set_kb)

        # Prepare negative test cases if provided
        if task_input.negative_test_cases is not None:
            self._prepare_testsuite_with_negation(
                result, provider, model.variables, task_input.negative_test_cases, is_negative=True)

        # Assign sets
        self._assign_sets(result, start_id_tc, start_id_tv,
                          task_input.negative_test_cases is not None)

        return PreparationOutput(result, provider)

    def _prepare_testsuite_with_negation(self,
                                         result: NonIncrementalTestCaseTask,
                                         provider: DescriptionProvider,
                                         variables: Dict[str, int],
                                         testsuite: TestSuite,
                                         is_negative: bool) -> None:
        """Prepare test cases as clause lists with negated forms.

        Each test case produces two entries in set_kb:
        1. Original: [[var1], [var2], ...] (conjunction as unit clauses)
        2. Negated: [[-var1, -var2, ...]] (single disjunction clause)

        Args:
            result: NonIncrementalTestCaseTask to populate
            provider: Description provider for formatting
            variables: Variable name to ID mapping
            testsuite: TestSuite containing test cases
            is_negative: Whether this is a negative test suite
        """
        for testcase in testsuite.testcases:
            desc_parts = []
            literals = []

            for assignment in testcase.assignments:
                if assignment.feature not in variables:
                    raise KeyError(f'Feature {assignment.feature} is not in the model.')

                desc_parts.append(f'{assignment.feature}={"true" if assignment.value else "false"}')
                var = variables[assignment.feature] if assignment.value else -1 * variables[assignment.feature]
                literals.append(var)

            # Original form: conjunction as list of unit clauses
            original_clauses = [[lit] for lit in literals]
            result.set_kb.append(original_clauses)
            provider.add_test_case_description(original_clauses, ' & '.join(desc_parts))

            # Negated form: ¬(l1 ∧ l2 ∧ ... ∧ ln) = (¬l1 ∨ ¬l2 ∨ ... ∨ ¬ln)
            negated_clauses = [[-lit for lit in literals]]
            result.set_kb.append(negated_clauses)
            provider.add_test_case_description(negated_clauses, f"NOT({' & '.join(desc_parts)})")

            # Add negated to appropriate list
            if is_negative:
                result.set_neg_tv.append(negated_clauses)
            else:
                result.set_neg_tc.append(negated_clauses)

            # Map original to negated
            result.neg_tc_map[get_hashcode(original_clauses)] = negated_clauses

    def _assign_sets(self, result: NonIncrementalTestCaseTask,
                     start_id_tc: int, start_id_tv: int,
                     has_negative_test_cases: bool) -> None:
        """Assign sets from set_kb.

        Note: Each test case has two entries (original + negated),
        so we need to extract only the original clauses for set_tc and set_tv.
        """
        result.set_b = [result.set_kb[0]]
        result.set_c = result.set_kb[1:start_id_tc]

        # Extract original test cases (every other one starting from start_id_tc)
        tc_tv_clauses = result.set_kb[start_id_tc:]
        original_tc_tv = [tc_tv_clauses[i] for i in range(0, len(tc_tv_clauses), 2)]

        # Calculate relative start of TV within original clauses
        num_tc_original = (start_id_tv - start_id_tc) // 2
        result.set_tc = original_tc_tv[:num_tc_original]
        result.set_tv = original_tc_tv[num_tc_original:] if has_negative_test_cases else []


# === FORMATTER ===

class DiagnosisFormatter:
    """Formats diagnosis results for display."""

    @staticmethod
    def format(diagnoses: List[List], provider: DescriptionProvider) -> str:
        """Format diagnoses as human-readable string.

        Args:
            diagnoses: List of diagnoses to format
            provider: DescriptionProvider for looking up constraint descriptions
        """
        diagnoses_str = []
        for diag in diagnoses:
            diag_str = [provider.get_description(item) for item in diag]
            diagnoses_str.append(f"[{', '.join(diag_str)}]")
        return ','.join(diagnoses_str)


# === FACTORY ===

class TaskPreparationFactory:
    """Factory for creating task preparation strategies."""

    _incremental_diagnosis: DiagnosisTaskPreparationStrategy = None
    _non_incremental_diagnosis: DiagnosisTaskPreparationStrategy = None
    _incremental_testcase: TestCaseTaskPreparationStrategy = None
    _non_incremental_testcase: TestCaseTaskPreparationStrategy = None

    @classmethod
    def create_diagnosis(cls, is_incremental: bool) -> DiagnosisTaskPreparationStrategy:
        """Create diagnosis task preparation strategy.

        Args:
            is_incremental: Whether to use incremental mode

        Returns:
            DiagnosisTaskPreparationStrategy instance
        """
        if is_incremental:
            if cls._incremental_diagnosis is None:
                cls._incremental_diagnosis = IncrementalDiagnosisTaskPreparation()
            return cls._incremental_diagnosis
        else:
            if cls._non_incremental_diagnosis is None:
                cls._non_incremental_diagnosis = NonIncrementalDiagnosisTaskPreparation()
            return cls._non_incremental_diagnosis

    @classmethod
    def create_testcase(cls, is_incremental: bool = True) -> TestCaseTaskPreparationStrategy:
        """Create test case task preparation strategy.

        Args:
            is_incremental: Whether to use incremental mode (default: True)

        Returns:
            TestCaseTaskPreparationStrategy instance
        """
        if is_incremental:
            if cls._incremental_testcase is None:
                cls._incremental_testcase = IncrementalTestCaseTaskPreparation()
            return cls._incremental_testcase
        else:
            if cls._non_incremental_testcase is None:
                cls._non_incremental_testcase = NonIncrementalTestCaseTaskPreparation()
            return cls._non_incremental_testcase
