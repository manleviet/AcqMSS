"""Task preparation strategies and utilities for diagnosis.

This module provides strategy pattern implementations for preparing diagnosis tasks.

Strategy hierarchy:
- DiagnosisTaskPreparationStrategy: For diagnosis/conflict operations
  - DiagnosisTaskPreparation (single impl, mode via constructor)
- TestCaseTaskPreparationStrategy: For operations with test cases (KBDiag, WipeOutR_T)
  - TestCaseTaskPreparation (single impl, mode via constructor)

Task hierarchy (immutable, pure data — no methods/codec/describe):
- Task (ABC): intrinsic solve fields only
  - DiagnosisTask: marker (no extra fields)
  - TestCaseTask: adds test-case fields

Tasks are ``@dataclass(frozen=True)``: preparation builds every field into
local variables and constructs the frozen task once at the end (build-then-freeze).
Derived quantities live in free functions (e.g. ``cf(task)``), never on the task.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional, Tuple, TYPE_CHECKING

from flamapy.metamodels.configuration_metamodel.models import Configuration
from flamapy.metamodels.fm_metamodel.models.feature_model import Feature

from explanation.models.assignment_assumption_map import AssignmentAssumptionMap
from explanation.models.testsuite import TestSuite
from explanation.operations.algorithms.utils import get_hashcode

if TYPE_CHECKING:
    from .pysat_diagnosis_model import DiagnosisModel

# Each constraint produces a pair of assumptions (original + negated),
# so we stride by 2 to select only original assumptions.
_ASSUMPTION_PAIR_STRIDE = 2
_ASSUMPTION_SINGLE_STRIDE = 1


# === INPUT DATA CLASS ===

@dataclass(frozen=True)
class TaskInput:
    """Immutable input parameters for task preparation.

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

    Construct directly or via the use-case factory classmethods below.
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

    def __post_init__(self):
        # Diagnosis-config inputs and test-case inputs are mutually exclusive:
        # a task is either configuration/error diagnosis OR a test-case task.
        if self.positive_test_cases is not None and (
                self.configuration is not None or self.test_case is not None):
            raise ValueError(
                "TaskInput: configuration/test_case cannot be combined with "
                "positive_test_cases (diagnosis-config and test-case inputs are "
                "mutually exclusive).")

    def is_testcase_task(self) -> bool:
        """Check if this input is for a test case task."""
        return self.positive_test_cases is not None

    # --- Use-case factories (map 1:1 to the use cases above) ---

    @classmethod
    def fm_diagnosis(cls) -> 'TaskInput':
        """Use case 3: feature-model diagnosis (no inputs)."""
        return cls()

    @classmethod
    def config(cls, configuration: Configuration) -> 'TaskInput':
        """Use case 1: configuration diagnosis."""
        return cls(configuration=configuration)

    @classmethod
    def config_with_cf(cls, configuration: Configuration) -> 'TaskInput':
        """Use case 2: configuration + feature-model diagnosis."""
        return cls(configuration=configuration, with_cf_in_c=True)

    @classmethod
    def error(cls, test_case: Configuration) -> 'TaskInput':
        """Use case 4: error diagnosis (debugging)."""
        return cls(test_case=test_case)

    @classmethod
    def testcases(cls, positive: TestSuite,
                  negative: Optional[TestSuite] = None) -> 'TaskInput':
        """Use case 5: KBDiag with positive (+ optional negative) test cases."""
        return cls(positive_test_cases=positive, negative_test_cases=negative)

    @classmethod
    def redundancy_fm(cls) -> 'TaskInput':
        """Use case 7: WipeOutR_FM (FM-constraint redundancy)."""
        return cls(for_redundancy=True)

    @classmethod
    def redundancy_t(cls, positive: TestSuite) -> 'TaskInput':
        """Use case 6: WipeOutR_T (test-case redundancy)."""
        return cls(positive_test_cases=positive, for_redundancy=True)


# === UTILITIES ===

def convert_keys_to_features(configuration: Configuration) -> Configuration:
    """Convert string keys to Feature objects."""
    new_elements = {Feature(key) if isinstance(key, str) else key: value
                    for key, value in configuration.elements.items()}
    return Configuration(new_elements)


def slice_assumptions(assumptions: List[int], start: int = 0,
                      stop: Optional[int] = None, stride: int = 1) -> List[int]:
    """Return ``assumptions[start:stop:stride]`` as a list.

    Single home for the offset+stride arithmetic that carves set_b/set_c/set_tc/
    set_tv out of the flat assumption list. Paired layouts (each constraint or
    test case stored as an original + negated form) pass
    ``stride=_ASSUMPTION_PAIR_STRIDE`` to pick only the originals; unpaired
    layouts use the default stride 1.
    """
    return list(assumptions[start:stop:stride])


# === RESULT DATA CLASSES (Core data only, immutable) ===

@dataclass(frozen=True)
class Task(ABC):
    """Immutable unit-of-work: intrinsic solve fields only.

    Pure data — no methods, no codec, no describe. Derived quantities are free
    functions (e.g. ``cf(task)``); formatting context lives outside the task.
    Frozen so a task built from one KB can be executed concurrently without
    aliasing hazards.
    """
    # set of constraints which could be faulty
    set_c: List[int] = field(default_factory=list)
    # background knowledge (i.e., the knowledge that is known to be true)
    set_b: List[int] = field(default_factory=list)
    # set of all CNF with added assumptions
    set_kb: List[List[int]] = field(default_factory=list)
    # mapping: original assumption ID -> negated assumption ID
    # Used by WipeOutR_FM (constraints) and WipeOutR_T (test cases)
    negation_map: Dict[int, int] = field(default_factory=dict)
    # list of assumptions for solver
    assumptions: List[int] = field(default_factory=list)


@dataclass(frozen=True)
class DiagnosisTask(Task):
    """Marker for diagnosis-shaped tasks (no test-case fields)."""
    pass


@dataclass(frozen=True)
class TestCaseTask(Task):
    """Task with test cases.

    Used by KBDiag algorithm with positive/negative test cases,
    WipeOutR_T for test case redundancy detection, and ConGen.
    """
    # positive test cases (original form)
    set_tc: List[int] = field(default_factory=list)
    # negative test cases (original form)
    set_tv: List[int] = field(default_factory=list)
    # negated negative test cases (for KBDiag: B = B ∪ neg_Tν)
    set_neg_tv: List[int] = field(default_factory=list)
    # negated positive test cases (for WipeOutR)
    set_neg_tc: List[int] = field(default_factory=list)


def cf(task: Task) -> List[int]:
    """All constraints (C ∪ B) for a task. Free function (was ``Task.get_cf``)."""
    return task.set_b + task.set_c


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

    def get_descriptions_for(self, ids: List[int]) -> Dict[int, str]:
        """Extract descriptions for given assumption IDs."""
        return {aid: self.get_description(aid) for aid in ids}

    def reset_constraint(self) -> None:
        """Reset constraint map."""
        self.constraint_map = {}

    def reset_configuration(self) -> None:
        """Reset configuration map."""
        self.configuration_map = {}


# === PREPARED TASK (preparation result container) ===

@dataclass
class PreparedTask:
    """Preparation result: the pure Task plus its formatting/assignment context.

    - ``task``: immutable, pure solve data (set_c/set_b/set_kb/assumptions/...).
    - ``describe``: DescriptionProvider used only to format results (never
      algorithm logic).
    - ``assignment_map``: feature-assignment → assumption-ID layer. Empty for
      plain diagnosis/test-case preparation (no assignment layer); populated by
      oracle-style preparation.

    Operations read ``prepared.task`` to solve and ``prepared.describe`` to
    format their results.
    """
    task: Task
    describe: DescriptionProvider
    assignment_map: AssignmentAssumptionMap = field(default_factory=AssignmentAssumptionMap)


# === STRATEGY INTERFACES ===

class DiagnosisTaskPreparationStrategy(ABC):
    """Abstract strategy for preparing diagnosis tasks.

    Used for:
    - Configuration diagnosis
    - Feature model diagnosis
    - Configuration + feature model diagnosis
    - Error diagnosis with test case
    - Redundancy detection (with negated_constraint_map)

    The model parameter accepts any object with: constraint_map, negated_constraint_map,
    variables, next_available_id, background_knowledge (duck-typed).
    """

    @abstractmethod
    def prepare(self, model: Any, task_input: TaskInput) -> PreparedTask:
        """Prepare diagnosis task and return result with description provider."""
        pass

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Return mode name for logging."""
        pass


class TestCaseTaskPreparationStrategy(ABC):
    """Abstract strategy for preparing tasks with test cases.

    Used for KBDiag algorithm with positive/negative test cases,
    WipeOutR_T for test case redundancy detection, and ConGen.

    The model parameter accepts any object with: constraint_map, negated_constraint_map,
    variables, next_available_id, background_knowledge (duck-typed).
    """

    @abstractmethod
    def prepare(self, model: Any, task_input: TaskInput) -> PreparedTask:
        """Prepare test case task and return result with description provider."""
        pass

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Return mode name for logging."""
        pass


# === SHARED KB PREPARATION FUNCTIONS ===
# These mutate the caller's local accumulation lists (build-then-freeze); the
# frozen task is constructed once, at the end of each strategy's prepare().

def prepare_kb(set_kb: List[List[int]],
               assumptions: List[int],
               negation_map: Dict[int, int],
               provider: DescriptionProvider,
               constraint_map: Dict[str, List[List]],
               id_assumption: int,
               negated_constraint_map: Optional[Dict[str, List[List]]]) -> int:
    """Populate KB with assumptions and optionally negated forms.

    Appends guarded clauses to ``set_kb``, assumption IDs to ``assumptions`` and
    original→negated pairs to ``negation_map``.

    Returns:
        Next available assumption ID
    """
    for key, clauses in constraint_map.items():
        # --- Original constraint with assumption ---
        original_id = id_assumption
        for clause in clauses:
            # assumption => clause (i.e., -assumption v clause)
            new_clause = clause.copy()
            new_clause.append(-original_id)
            set_kb.append(new_clause)

        assumptions.append(original_id)
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
                    set_kb.append(new_neg_clause)

                assumptions.append(negated_id)
                negation_map[original_id] = negated_id
                provider.add_constraint_description(negated_id, negated_key)
                id_assumption += 1

    return id_assumption


def prepare_configuration(set_kb: List[List[int]],
                          assumptions: List[int],
                          provider: DescriptionProvider,
                          variables: Dict[str, int],
                          configuration: Configuration,
                          id_assumption: int) -> int:
    """Populate configuration assumptions.

    Appends guarded unit clauses to ``set_kb`` and assumption IDs to ``assumptions``.

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

        assumptions.append(id_assumption)
        set_kb.append(clause)
        provider.add_configuration_description(id_assumption, desc)

        id_assumption += 1

    return id_assumption


def _add_assignment_assumption(set_kb: List[List[int]], assumptions: List[int],
                               provider: DescriptionProvider, assumption_id: int,
                               feature_id: int, description: str, *, value: bool) -> int:
    """Add one assumption-guarded feature-assignment clause; return the next id.

    ``value=True``  → clause ``[-a, feature_id]``  (assumption active ⇒ feature true)
    ``value=False`` → clause ``[-a, -feature_id]`` (assumption active ⇒ feature false)
    """
    literal = feature_id if value else -feature_id
    set_kb.append([-assumption_id, literal])
    assumptions.append(assumption_id)
    provider.add_configuration_description(assumption_id, description)
    return assumption_id + 1


def prepare_variable_assignments(set_kb: List[List[int]], assumptions: List[int],
                                 provider: DescriptionProvider,
                                 name_to_id: Dict[str, int],
                                 id_assumption: int):
    """Append paired (feature=true, feature=false) assignment assumptions.

    Builds the variable-assignment block of the oracle assumption layout: for
    each feature, two assumption-guarded clauses forcing it true / false when
    the corresponding assumption is active. Mutates ``set_kb`` / ``assumptions``
    (build-then-freeze).

    Returns:
        (next_id, pos_map, neg_map) where the maps are feature name → assumption id.
    """
    pos_assignment_to_assumption: Dict[str, int] = {}
    neg_assignment_to_assumption: Dict[str, int] = {}
    for name, fid in name_to_id.items():
        pos_assignment_to_assumption[name] = id_assumption
        id_assumption = _add_assignment_assumption(
            set_kb, assumptions, provider, id_assumption, fid, f'{name}=true', value=True)
        neg_assignment_to_assumption[name] = id_assumption
        id_assumption = _add_assignment_assumption(
            set_kb, assumptions, provider, id_assumption, fid, f'{name}=false', value=False)
    return id_assumption, pos_assignment_to_assumption, neg_assignment_to_assumption


# === DIAGNOSIS STRATEGY ===

class DiagnosisTaskPreparation(DiagnosisTaskPreparationStrategy):
    """Prepare diagnosis task using assumptions.

    Supported task types:
    1. Configuration diagnosis (is_CF_in_C = False):
        C = configuration, B = feature model (PySATModel) + root
    2. Configuration and feature model diagnosis (is_CF_in_C = True):
        C = configuration + feature model (PySATModel), B = root only
    3. Feature model diagnosis (test_case is None):
        C = FM constraints, B = root only
    4. Error diagnosis (debugging):
        C = FM constraints, B = root + test case
    5. Redundancy Detection Task (need negative constraints)
        C = CF (i.e., = PySATModel + {f0 = true}), B = {}
    """

    def __init__(self, mode_name: str = "diagnosis"):
        self._mode_name = mode_name

    @property
    def mode_name(self) -> str:
        return self._mode_name

    def prepare(self, model: 'DiagnosisModel', task_input: TaskInput) -> PreparedTask:
        provider = DescriptionProvider()

        # Determine if negated forms should be used
        negated_constraint_map = model.negated_constraint_map if task_input.for_redundancy else None

        # Use next_available_id to avoid conflicts with Tseitin variables
        id_assumption = model.next_available_id

        # Local accumulation (build-then-freeze)
        set_kb: List[List[int]] = []
        assumptions: List[int] = []
        negation_map: Dict[int, int] = {}

        # Prepare KB with assumptions and optionally negated forms
        id_assumption = prepare_kb(
            set_kb, assumptions, negation_map, provider,
            model.constraint_map, id_assumption, negated_constraint_map)

        start_id_config = len(assumptions)
        if task_input.configuration is not None:
            id_assumption = prepare_configuration(
                set_kb, assumptions, provider, model.variables,
                task_input.configuration, id_assumption)

        start_id_test_case = len(assumptions)
        if task_input.test_case is not None:
            prepare_configuration(
                set_kb, assumptions, provider, model.variables,
                task_input.test_case, id_assumption)

        # Assign set_c and set_b
        has_negated_forms = negated_constraint_map is not None
        set_b, set_c = self._assign_sets(
            assumptions, task_input, start_id_config, start_id_test_case, has_negated_forms)

        task = DiagnosisTask(
            set_c=set_c, set_b=set_b, set_kb=set_kb,
            negation_map=negation_map, assumptions=assumptions)
        return PreparedTask(task, provider)

    def _assign_sets(self, assumptions: List[int], task_input: TaskInput,
                     start_id_config: int, start_id_test: int,
                     has_negated_forms: bool = True) -> Tuple[List[int], List[int]]:
        """Compute (set_b, set_c) from assumptions based on use case."""
        # With negation: [root, neg_root, c1, neg_c1, ...] -> step=2
        # Without negation: [root, c1, c2, ...] -> step=1
        step = _ASSUMPTION_PAIR_STRIDE if has_negated_forms else _ASSUMPTION_SINGLE_STRIDE

        set_b: List[int] = []
        set_c: List[int] = []

        if task_input.configuration is not None:
            if not task_input.with_cf_in_c:
                # C = configuration, B = FM + root
                set_b = slice_assumptions(assumptions, 0, start_id_config, step)
                set_c = slice_assumptions(assumptions, start_id_config)
            else:
                # C = configuration + FM, B = root only
                set_b = [assumptions[0]]
                set_c = slice_assumptions(assumptions, step, start_id_config, step) + \
                    slice_assumptions(assumptions, start_id_config)
        else:
            if task_input.test_case is not None:
                # C = FM constraints, B = root + test case
                set_b = [assumptions[0]] + slice_assumptions(assumptions, start_id_test)
                set_c = slice_assumptions(assumptions, step, start_id_config, step)
            else:
                if has_negated_forms:
                    # Redundancy detection: C = CF (PySATModel, no root), B = {}
                    set_c = slice_assumptions(assumptions, step, None, step)
                else:
                    # C = FM constraints, B = root only
                    set_b = [assumptions[0]]
                    set_c = slice_assumptions(assumptions, step, None, step)

        return set_b, set_c


# === TEST CASE STRATEGY ===

def prepare_testsuite_with_negation(set_kb: List[List[int]],
                                    assumptions: List[int],
                                    negation_map: Dict[int, int],
                                    provider: DescriptionProvider,
                                    variables: Dict[str, int],
                                    testsuite: TestSuite,
                                    id_assumption: int) -> Tuple[int, List[int]]:
    """Populate test cases with assumptions and their negated forms.

    Each test case gets two assumption IDs: original and negated. The negated
    form is a single clause with all literals negated. Appends to ``set_kb``,
    ``assumptions`` and ``negation_map``; returns the negated assumption IDs
    (in test-case order) so the caller can route them to set_neg_tv/set_neg_tc.

    Returns:
        (next available assumption ID, negated assumption IDs)
    """
    negated_ids: List[int] = []
    for testcase in testsuite.testcases:
        # --- Original form ---
        original_id = id_assumption
        desc_parts = []
        literals = []

        for assignment in testcase.assignments:
            if assignment.feature not in variables:
                raise KeyError(f'Feature {assignment.feature} is not in the model.')

            desc_parts.append(f'{assignment.feature}={"true" if assignment.value else "false"}')
            var = variables[assignment.feature] if assignment.value else -variables[assignment.feature]
            literals.append(var)
            set_kb.append([var, -original_id])

        assumptions.append(original_id)
        desc = ' & '.join(desc_parts)
        provider.add_test_case_description(original_id, desc)
        id_assumption += 1

        # --- Negated form ---
        negated_id = id_assumption
        negated_clause = [-lit for lit in literals]
        negated_clause.append(-negated_id)
        set_kb.append(negated_clause)

        assumptions.append(negated_id)
        provider.add_test_case_description(negated_id, f"NOT({' & '.join(desc_parts)})")
        negated_ids.append(negated_id)

        negation_map[original_id] = negated_id
        id_assumption += 1

    return id_assumption, negated_ids


class TestCaseTaskPreparation(TestCaseTaskPreparationStrategy):
    """Prepare test case task using assumptions.

    Prepares model for KBDiag algorithm with positive/negative test cases.
    Prepares model for WipeOutR_T for test case redundancy detection.

    Supported task types:
    1. Debugging task - Diagnosis with positive and negative
        C = FM constraints (excluding root), B = root constraint
        TC = positive test cases, TV = negative test cases
    2. WipeOutR_T - Redundancy detection for test cases
        TC = positive test cases
    """

    def __init__(self, mode_name: str = "testcase"):
        self._mode_name = mode_name

    @property
    def mode_name(self) -> str:
        return self._mode_name

    def prepare(self, model: 'DiagnosisModel', task_input: TaskInput) -> PreparedTask:
        provider = DescriptionProvider()

        # Start assumption IDs after Tseitin variables
        id_assumption = model.next_available_id

        # Local accumulation (build-then-freeze)
        set_kb: List[List[int]] = []
        assumptions: List[int] = []
        negation_map: Dict[int, int] = {}
        set_neg_tv: List[int] = []
        set_neg_tc: List[int] = []

        # Prepare KB (no negated forms needed for TestCaseTask)
        id_assumption = prepare_kb(
            set_kb, assumptions, negation_map, provider,
            model.constraint_map, id_assumption, negated_constraint_map=None)

        # Prepare positive test cases with negated forms
        start_id_tc = len(assumptions)
        id_assumption, pos_negated_ids = prepare_testsuite_with_negation(
            set_kb, assumptions, negation_map, provider, model.variables,
            task_input.positive_test_cases, id_assumption)
        set_neg_tc.extend(pos_negated_ids)

        # Prepare negative test cases with negated forms if provided
        start_id_tv = len(assumptions)
        if task_input.negative_test_cases is not None:
            id_assumption, neg_negated_ids = prepare_testsuite_with_negation(
                set_kb, assumptions, negation_map, provider, model.variables,
                task_input.negative_test_cases, id_assumption)
            set_neg_tv.extend(neg_negated_ids)

        set_b, set_c, set_tc, set_tv = self._assign_sets(
            assumptions, start_id_tc, start_id_tv, task_input.negative_test_cases is not None)

        task = TestCaseTask(
            set_c=set_c, set_b=set_b, set_kb=set_kb,
            negation_map=negation_map, assumptions=assumptions,
            set_tc=set_tc, set_tv=set_tv,
            set_neg_tv=set_neg_tv, set_neg_tc=set_neg_tc)
        return PreparedTask(task, provider)

    def _assign_sets(self, assumptions: List[int],
                     start_id_tc: int, start_id_tv: int,
                     has_negative_test_cases: bool
                     ) -> Tuple[List[int], List[int], List[int], List[int]]:
        """Compute (set_b, set_c, set_tc, set_tv) from assumptions.

        Each test case has two assumptions (original + negated),
        so extract only the original assumptions for set_tc and set_tv.
        Invariant: (start_id_tv - start_id_tc) is even (whole original+negated
        pairs), so slicing originals directly from each sub-region is exact.
        """
        set_b = [assumptions[0]]
        set_c = slice_assumptions(assumptions, 1, start_id_tc)

        # Each test case is stored as an (original, negated) pair; stride by 2 to
        # keep only the originals, sliced directly from each sub-region.
        set_tc = slice_assumptions(assumptions, start_id_tc, start_id_tv, _ASSUMPTION_PAIR_STRIDE)
        set_tv = (slice_assumptions(assumptions, start_id_tv, None, _ASSUMPTION_PAIR_STRIDE)
                  if has_negative_test_cases else [])
        return set_b, set_c, set_tc, set_tv


# === FORMATTER ===

class DiagnosisFormatter:
    """Formats diagnosis results for display."""

    @staticmethod
    def format(diagnoses: List[List], provider: DescriptionProvider) -> str:
        """Format diagnoses as human-readable string."""
        diagnoses_str = []
        for diag in diagnoses:
            diag_str = [provider.get_description(item) for item in diag]
            diagnoses_str.append(f"[{', '.join(diag_str)}]")
        return ','.join(diagnoses_str)


# === FACTORY ===

class TaskPreparationFactory:
    """Factory for creating task preparation strategies.

    Uses single cached instances since incremental/non-incremental
    distinction only affects the checker, not preparation.
    """

    _diagnosis: DiagnosisTaskPreparation = None
    _testcase: TestCaseTaskPreparation = None

    @classmethod
    def create_diagnosis(cls) -> DiagnosisTaskPreparationStrategy:
        """Create diagnosis task preparation strategy (incremental-agnostic)."""
        if cls._diagnosis is None:
            cls._diagnosis = DiagnosisTaskPreparation()
        return cls._diagnosis

    @classmethod
    def create_testcase(cls) -> TestCaseTaskPreparationStrategy:
        """Create test case task preparation strategy (incremental-agnostic)."""
        if cls._testcase is None:
            cls._testcase = TestCaseTaskPreparation()
        return cls._testcase
