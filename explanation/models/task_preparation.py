"""Task preparation strategies and utilities for diagnosis.

This module provides strategy pattern implementations for preparing diagnosis tasks.

Strategy hierarchy:
- DiagnosisTaskPreparationStrategy: For diagnosis/conflict operations
  - IncrementalDiagnosisTaskPreparation
  - NonIncrementalDiagnosisTaskPreparation
- DebuggingTaskPreparationStrategy: For debugging operations with test cases
  - IncrementalDebuggingTaskPreparation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.fm_metamodel.models.feature_model import Feature

from explanation.models.testsuite import TestSuite
from explanation.operations.algorithms.utils import get_hashcode


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
class DebuggingTask(IncrementalDiagnosisTask):
    """Task data for debugging with test cases.

    Extends IncrementalDiagnosisTask to support KBDiag algorithm with positive/negative test cases.
    """
    # positive test cases (original form)
    set_tc: List = field(default_factory=list)
    # negative test cases (original form)
    set_tv: List = field(default_factory=list)
    # negated negative test cases (for KBDiag: B = B ∪ neg_Tν)
    set_neg_tv: List = field(default_factory=list)
    # negated positive test cases (for WipeOutR)
    set_neg_tc: List = field(default_factory=list)  # TODO: check usage
    # mapping: original assumption ID -> negated assumption ID
    # neg_map: Dict[int, int] = field(default_factory=dict)


# Backward compatibility alias
IncrementalDebuggingTask = DebuggingTask


# === DESCRIPTION PROVIDERS (For formatting only) ===

class DescriptionProvider(ABC):
    """Abstract provider for constraint descriptions.

    Used only for formatting diagnosis results, not for algorithm logic.
    """

    @abstractmethod
    def get_description(self, item) -> str:
        """Get human-readable description for a diagnosis."""
        pass

    @abstractmethod
    def add_description(self, key, description: str) -> None:
        """Add a description mapping."""
        pass


class IncrementalDescriptionProvider(DescriptionProvider):
    """Maps assumption IDs (int) to descriptions (str)."""

    def __init__(self):
        # map id of assumptions to relationships/constraint
        self.constraint_assumption_map: Dict[int, str] = {}

    def get_description(self, item: int) -> str:
        return self.constraint_assumption_map.get(item, str(item))

    def add_description(self, key: int, description: str) -> None:
        self.constraint_assumption_map[key] = description

    def reset(self) -> None:
        """Reset the map (used when is_CF_in_C)."""
        self.constraint_assumption_map = {}


class NonIncrementalDescriptionProvider(DescriptionProvider):
    """Maps clause hashcodes (str) to descriptions (str)."""

    def __init__(self):
        self.pretty_constraint_map: Dict[str, str] = {}

    def get_description(self, item) -> str:
        return self.pretty_constraint_map.get(get_hashcode(item), str(item))

    def add_description(self, key, description: str) -> None:
        """Add description. Key is a clause (will be hashed automatically)."""
        self.pretty_constraint_map[get_hashcode(key)] = description


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
    - Error diagnosis with test case
    """

    @abstractmethod
    def prepare(self,
                variables: Dict[str, int],
                constraint_map: Dict[str, List[List]],
                configuration: Optional[Configuration] = None,
                test_case: Optional[Configuration] = None,
                is_CF_in_C: bool = False) -> PreparationOutput:
        """Prepare diagnosis task and return result with description provider."""
        pass

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Return mode name for logging."""
        pass


class DebuggingTaskPreparationStrategy(ABC):
    """Abstract strategy for preparing debugging tasks with test cases.

    Used for KBDiag algorithm with positive/negative test cases.
    """

    @abstractmethod
    def prepare(self,
                variables: Dict[str, int],
                constraint_map: Dict[str, List[List]],
                positive_test_cases: TestSuite,
                negative_test_cases: Optional[TestSuite] = None) -> PreparationOutput:
        """Prepare debugging task and return result with description provider.

        Args:
            variables: Variable name to ID mapping
            constraint_map: Constraint name to clauses mapping
            positive_test_cases: TestSuite of positive test cases
            negative_test_cases: Optional TestSuite of negative test cases

        Returns:
            PreparationOutput with DebuggingTask and description provider
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

    Shared between IncrementalDiagnosisTaskPreparation and IncrementalDebuggingTaskPreparation.
    """

    @staticmethod
    def prepare_kb(result: IncrementalDiagnosisTask,
                   provider: IncrementalDescriptionProvider,
                   constraint_map: Dict[str, List[List]],
                   id_assumption: int) -> int:
        """Prepare KB with assumptions.

        Args:
            result: Task to populate with KB data
            provider: Description provider for formatting
            constraint_map: Constraint name to clauses mapping
            id_assumption: Starting assumption ID

        Returns:
            Next available assumption ID
        """
        for key, clauses in constraint_map.items():
            for clause in clauses:
                # assumption => clause
                # i.e., -assumption v clause
                clause.append(-1 * id_assumption)

            result.assumptions.append(id_assumption)
            result.set_kb.extend(clauses)
            provider.add_description(id_assumption, key)

            id_assumption += 1

        return id_assumption

    @staticmethod
    def prepare_configuration(result: IncrementalDiagnosisTask,
                              provider: IncrementalDescriptionProvider,
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
            provider.add_description(id_assumption, desc)

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
    2. Feature model diagnosis (test_case is None):
        C = FM constraints, B = root only
    3. Error diagnosis (debugging):
        C = FM constraints, B = root + test case
        where test_case is the following:
        + Dead feature: test_case = {fi = true}
        + False optional feature: test_case = {f_parent = true} & {f_child = false}
    """

    @property
    def mode_name(self) -> str:
        return "incremental"

    def prepare(self,
                variables: Dict[str, int],
                constraint_map: Dict[str, List[List]],
                configuration: Optional[Configuration] = None,
                test_case: Optional[Configuration] = None,
                is_CF_in_C: bool = False) -> PreparationOutput:

        result = IncrementalDiagnosisTask()
        provider = IncrementalDescriptionProvider()

        id_assumption = len(variables) + 1

        # Prepare KB with assumptions
        id_assumption = IncrementalKBPreparator.prepare_kb(
            result, provider, constraint_map, id_assumption)

        start_id_config = len(result.assumptions)
        if configuration is not None:
            if not is_CF_in_C:
                provider.reset()  # Reset provider, not result
            id_assumption = IncrementalKBPreparator.prepare_configuration(
                result, provider, variables, configuration, id_assumption)

        start_id_test_case = len(result.assumptions)
        if test_case is not None:
            IncrementalKBPreparator.prepare_configuration(
                result, provider, variables, test_case, id_assumption)

        # Assign set_c and set_b
        self._assign_sets(result, configuration, test_case,
                          start_id_config, start_id_test_case, is_CF_in_C)

        return PreparationOutput(result, provider)

    def _assign_sets(self, result: IncrementalDiagnosisTask,
                     configuration: Optional[Configuration],
                     test_case: Optional[Configuration],
                     start_id_config: int, start_id_test: int,
                     is_CF_in_C: bool) -> None:
        if configuration is not None:
            if not is_CF_in_C:
                result.set_b = result.assumptions[:start_id_config]
                result.set_c = result.assumptions[start_id_config:]
            else:
                result.set_b = [result.assumptions[0]]
                result.set_c = result.assumptions[1:]
        else:
            if test_case is not None:
                result.set_b = [result.assumptions[0]] + result.assumptions[start_id_test:]
                result.set_c = result.assumptions[1:start_id_test]
            else:
                result.set_b = [result.assumptions[0]]
                result.set_c = result.assumptions[1:]


# === NON-INCREMENTAL DIAGNOSIS STRATEGY ===

class NonIncrementalDiagnosisTaskPreparation(DiagnosisTaskPreparationStrategy):
    """Non-incremental mode: fresh solver for each check.

    Supported task types:
    1. Configuration diagnosis (is_CF_in_C = False):
        C = configuration, B = feature model (PySATModel) + root
    2. Configuration and feature model diagnosis (is_CF_in_C = True):
        C = configuration + feature model (PySATModel), B = root only
    2. Feature model diagnosis (test_case is None):
        C = FM constraints, B = root only
    3. Error diagnosis (debugging):
        C = FM constraints, B = root + test case
        where test_case is the following:
        + Dead feature: test_case = {fi = true}
        + False optional feature: test_case = {f_parent = true} & {f_child = false}
    """

    @property
    def mode_name(self) -> str:
        return "non-incremental"

    def prepare(self,
                variables: Dict[str, int],
                constraint_map: Dict[str, List[List]],
                configuration: Optional[Configuration] = None,
                test_case: Optional[Configuration] = None,
                is_CF_in_C: bool = False) -> PreparationOutput:

        result = NonIncrementalDiagnosisTask()
        provider = NonIncrementalDescriptionProvider()

        result.set_kb = [clauses for clauses in constraint_map.values()]

        start_id_config = len(result.set_kb)
        if configuration is not None:
            self._prepare_configuration(result, provider, variables, configuration)

        start_id_test_case = len(result.set_kb)
        if test_case is not None:
            self._prepare_configuration(result, provider, variables, test_case,
                                        add_to_map=False)

        # Assign set_c and set_b
        self._assign_sets(result, provider, constraint_map, configuration, test_case,
                          start_id_config, start_id_test_case, is_CF_in_C)

        return PreparationOutput(result, provider)

    def _prepare_configuration(self, result: NonIncrementalDiagnosisTask,
                               provider: NonIncrementalDescriptionProvider,
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
                provider.add_description(clause, desc)

    def _prepare_kb_map(self, provider: NonIncrementalDescriptionProvider,
                        constraint_map: Dict[str, List[List]]) -> None:
        for key, clauses in constraint_map.items():
            provider.add_description(clauses, key)

    def _assign_sets(self, result: NonIncrementalDiagnosisTask,
                     provider: NonIncrementalDescriptionProvider,
                     constraint_map: Dict[str, List[List]],
                     configuration: Optional[Configuration],
                     test_case: Optional[Configuration],
                     start_id_config: int, start_id_test: int,
                     is_CF_in_C: bool) -> None:
        if configuration is not None:
            if not is_CF_in_C:
                result.set_b = result.set_kb[:start_id_config]
                result.set_c = result.set_kb[start_id_config:]
            else:
                self._prepare_kb_map(provider, constraint_map)
                result.set_b = [result.set_kb[0]]
                result.set_c = result.set_kb[1:]
        else:
            self._prepare_kb_map(provider, constraint_map)
            if test_case is not None:
                result.set_b = [result.set_kb[0]] + result.set_kb[start_id_test:]
                result.set_c = result.set_kb[1:start_id_test]
            else:
                result.set_b = [result.set_kb[0]]
                result.set_c = result.set_kb[1:]


# === INCREMENTAL DEBUGGING STRATEGY ===

class IncrementalDebuggingTaskPreparation(DebuggingTaskPreparationStrategy):
    """Strategy for debugging task with test cases.

    Uses IncrementalKBPreparator for shared KB preparation logic.
    Prepares model for KBDiag algorithm with positive/negative test cases.

    Debugging task:
        C = FM constraints (excluding root)
        B = root constraint
        TC = positive test cases
        TV = negative test cases
    """

    @property
    def mode_name(self) -> str:
        return "incremental-debugging"

    def prepare(self,
                variables: Dict[str, int],
                constraint_map: Dict[str, List[List]],
                positive_test_cases: TestSuite,
                negative_test_cases: Optional[TestSuite] = None) -> PreparationOutput:
        """Prepare debugging task with test cases.

        Args:
            variables: Variable name to ID mapping
            constraint_map: Constraint name to clauses mapping
            positive_test_cases: TestSuite of positive test cases
            negative_test_cases: Optional TestSuite of negative test cases

        Returns:
            PreparationOutput with DebuggingTask and description provider
        """
        result = IncrementalDebuggingTask()
        provider = IncrementalDescriptionProvider()

        id_assumption = len(variables) + 1

        # Use shared KB preparation
        id_assumption = IncrementalKBPreparator.prepare_kb(
            result, provider, constraint_map, id_assumption)

        # Prepare positive test cases with negated forms
        start_id_tc = len(result.assumptions)
        id_assumption = self._prepare_testsuite_with_negation(
            result, provider, variables, positive_test_cases, id_assumption, is_negative=False)

        # Prepare negative test cases with negated forms if provided
        start_id_tv = len(result.assumptions)
        if negative_test_cases is not None:
            self._prepare_testsuite_with_negation(
                result, provider, variables, negative_test_cases, id_assumption, is_negative=True)

        # Assign sets: B = root, C = FM constraints, TC = positive, TV = negative
        self._assign_sets(result, start_id_tc, start_id_tv, negative_test_cases is not None)

        return PreparationOutput(result, provider)

    def _prepare_testsuite_with_negation(self, result: DebuggingTask,
                                         provider: IncrementalDescriptionProvider,
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
            provider.add_description(original_id, ' & '.join(desc_parts))
            id_assumption += 1

            # --- Negated form ---
            negated_id = id_assumption
            # Negated clause: (¬l1 ∨ ¬l2 ∨ ... ∨ ¬ln)
            negated_clause = [-lit for lit in literals]
            negated_clause.append(-negated_id)
            result.set_kb.append(negated_clause)

            result.assumptions.append(negated_id)
            provider.add_description(negated_id, f"NOT({' & '.join(desc_parts)})")

            # Store mapping
            # result.neg_map[original_id] = negated_id

            # Add to appropriate negated list
            if is_negative:
                result.set_neg_tv.append(negated_id)
            else:
                result.set_neg_tc.append(negated_id)

            id_assumption += 1

        return id_assumption

    def _assign_sets(self, result: DebuggingTask,
                     start_id_tc: int, start_id_tv: int,
                     has_negative_test_cases: bool) -> None:
        """Assign sets from assumptions.

        Note: Each test case has two assumptions (original + negated),
        so we need to extract only the original assumptions for set_tc and set_tv.
        """
        result.set_b = [result.assumptions[0]]
        result.set_c = result.assumptions[1:start_id_tc]
        result.set_tc = result.assumptions[start_id_tc:start_id_tv]
        result.set_tv = result.assumptions[start_id_tv:] if negative_test_cases else []

        # Extract only original test case assumptions (every other one starting from start_id_tc)
        # Original assumptions are at even positions from start_id_tc
        tc_tv_assumptions = result.assumptions[start_id_tc:]
        original_tc_tv = [tc_tv_assumptions[i] for i in range(0, len(tc_tv_assumptions), 2)]

        # Calculate relative start of TV within original assumptions
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
    _incremental_debugging: DebuggingTaskPreparationStrategy = None

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
    def create_debugging(cls, is_incremental: bool = True) -> DebuggingTaskPreparationStrategy:
        """Create debugging task preparation strategy.

        Args:
            is_incremental: Whether to use incremental mode (default: True)

        Returns:
            DebuggingTaskPreparationStrategy instance

        Raises:
            NotImplementedError: If non-incremental mode is requested
        """
        if is_incremental:
            if cls._incremental_debugging is None:
                cls._incremental_debugging = IncrementalDebuggingTaskPreparation()
            return cls._incremental_debugging
        else:
            raise NotImplementedError("Non-incremental debugging task preparation is not implemented.")
