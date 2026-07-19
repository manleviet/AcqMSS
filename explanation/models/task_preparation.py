"""Task preparation strategies and utilities for diagnosis.

This module provides strategy pattern implementations for preparing diagnosis tasks.

Strategy hierarchy — one ABC, ``TaskPreparationStrategy``, with concrete impls:
- DiagnosisTaskPreparation: diagnosis / conflict operations
- TestCaseTaskPreparation: operations with test cases (KBDiag, WipeOutR_T)
- ConGenTaskPreparation (in conacq): ConGen acquisition

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
from explanation.models.assumption_id_allocator import AssumptionIdAllocator
from explanation.models.testsuite import TestSuite
from explanation.operations.algorithms.utils import get_hashcode
from explanation.models.frozen_dict import FrozenDict

if TYPE_CHECKING:
    from .pysat_diagnosis_model import DiagnosisModel


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


# === RESULT DATA CLASSES (Core data only, immutable) ===

@dataclass(frozen=True)
class Task(ABC):
    """Unit-of-work: intrinsic solve fields only.

    Pure data — no methods, no codec, no describe. Derived quantities are free
    functions (e.g. ``cf(task)``); formatting context lives outside the task.

    **Deeply frozen.** ``@dataclass(frozen=True)`` blocks *rebinding* a field
    (``task.set_c = ...`` raises ``FrozenInstanceError``); ``__post_init__``
    additionally coerces the list-valued solve fields to tuples, so their contents
    cannot be mutated in place either (``task.set_c.append(...)`` raises
    ``AttributeError`` — a loud failure at the call, not silent drift). Constructors
    still accept lists; the coercion is transparent. ``negation_map`` is coerced to a
    ``FrozenDict`` — a read-only ``dict`` that still *pickles* (FastDiagP ships the
    task to workers), unlike the abandoned ``MappingProxyType`` (ADR-0007) which does
    not.
    """
    # set of constraints which could be faulty
    set_c: Tuple[int, ...] = field(default_factory=tuple)
    # background knowledge (i.e., the knowledge that is known to be true)
    set_b: Tuple[int, ...] = field(default_factory=tuple)
    # set of all CNF with added assumptions
    set_kb: Tuple[Tuple[int, ...], ...] = field(default_factory=tuple)
    # mapping: original assumption ID -> negated assumption ID. Frozen (read-only).
    # Annotated as its stored type (like the Tuple fields); constructors pass a plain
    # dict and __post_init__ coerces. Used by WipeOutR_FM/WipeOutR_T.
    # Task is intentionally NOT hashable: negation_map is a FrozenDict (a dict
    # subclass, hence unhashable), so hash(task) raises TypeError. No caller hashes a
    # task or uses one as a dict key / set member (verified by grep); revisit before
    # adding one.
    negation_map: "FrozenDict[int, int]" = field(default_factory=dict)
    # list of assumptions for solver
    assumptions: Tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # Deep-freeze every field (frozen=True only blocks rebinding).
        # Constructors pass lists/dicts for convenience; storing tuples/FrozenDict
        # makes in-place mutation raise. FrozenDict pickles (FastDiagP ships tasks).
        object.__setattr__(self, 'set_c', tuple(self.set_c))
        object.__setattr__(self, 'set_b', tuple(self.set_b))
        object.__setattr__(self, 'assumptions', tuple(self.assumptions))
        object.__setattr__(self, 'set_kb', tuple(tuple(clause) for clause in self.set_kb))
        object.__setattr__(self, 'negation_map', FrozenDict(self.negation_map))


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
    set_tc: Tuple[int, ...] = field(default_factory=tuple)
    # negative test cases (original form)
    set_tv: Tuple[int, ...] = field(default_factory=tuple)
    # negated negative test cases (for KBDiag: B = B ∪ neg_Tν)
    set_neg_tv: Tuple[int, ...] = field(default_factory=tuple)
    # negated positive test cases (for WipeOutR)
    set_neg_tc: Tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, 'set_tc', tuple(self.set_tc))
        object.__setattr__(self, 'set_tv', tuple(self.set_tv))
        object.__setattr__(self, 'set_neg_tv', tuple(self.set_neg_tv))
        object.__setattr__(self, 'set_neg_tc', tuple(self.set_neg_tc))


def cf(task: Task) -> Tuple[int, ...]:
    """All constraints (C ∪ B) for a task. Free function (was ``Task.get_cf``).
    Both fields are frozen tuples, so this is one tuple concat — no production
    caller exists (only tests), and none mutates the result."""
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

@dataclass(frozen=True)
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

class TaskPreparationStrategy(ABC):
    """Abstract strategy for preparing a task from a model + task input.

    One strategy per task shape — diagnosis, test-case (KBDiag / WipeOutR_T), ConGen.
    The model is duck-typed: any object with constraint_map / negated_constraint_map /
    variables / next_available_id.

    Was two structurally-identical strategy ABCs (one for diagnosis, one for
    test-case tasks), each also declaring a logging-mode accessor that had zero call
    sites — collapsed to one, and that dead accessor removed.
    """

    @abstractmethod
    def prepare(self, model: Any, task_input: TaskInput) -> PreparedTask:
        """Prepare the task and return it with its description provider."""
        ...


# === SHARED KB PREPARATION FUNCTIONS ===
# These mutate the caller's local accumulation lists (build-then-freeze); the
# frozen task is constructed once, at the end of each strategy's prepare().

def prepare_kb(set_kb: List[List[int]],
               assumptions: List[int],
               negation_map: Dict[int, int],
               provider: DescriptionProvider,
               constraint_map: Dict[str, List[List]],
               alloc: 'AssumptionIdAllocator',
               negated_constraint_map: Optional[Dict[str, List[List]]]) -> List[int]:
    """Populate KB with assumptions and optionally negated forms.

    Appends guarded clauses to ``set_kb``, assumption IDs to ``assumptions`` and
    original→negated pairs to ``negation_map``. Ids come from ``alloc``.

    Pairing is decided per key: ``allocate_pair`` when this constraint has a negated
    form, ``allocate`` when it does not — so the returned originals are exactly the
    ids emitted as originals, not a stride over the flat list. A constraint_map that
    mixes negated and non-negated keys would break ``assumptions[start::2]`` but not
    this.

    Returns:
        The original (un-negated) assumption ids, in constraint_map order — the
        caller's ``set_c`` for a bias/FM constraint block.
    """
    originals: List[int] = []
    for key, clauses in constraint_map.items():
        has_negated = (negated_constraint_map is not None
                       and f"NOT({key})" in negated_constraint_map)

        if has_negated:
            original_id, negated_id = alloc.allocate_pair()
        else:
            original_id = alloc.allocate()
        originals.append(original_id)

        # --- Original constraint with assumption ---
        for clause in clauses:
            # assumption => clause (i.e., -assumption v clause)
            new_clause = clause.copy()
            new_clause.append(-original_id)
            set_kb.append(new_clause)

        assumptions.append(original_id)
        provider.add_constraint_description(original_id, key)

        # --- Negated constraint (if provided) ---
        if has_negated:
            negated_key = f"NOT({key})"
            for neg_clause in negated_constraint_map[negated_key]:
                new_neg_clause = neg_clause.copy()
                new_neg_clause.append(-negated_id)
                set_kb.append(new_neg_clause)

            assumptions.append(negated_id)
            negation_map[original_id] = negated_id
            provider.add_constraint_description(negated_id, negated_key)

    return originals


def prepare_configuration(set_kb: List[List[int]],
                          assumptions: List[int],
                          provider: DescriptionProvider,
                          variables: Dict[str, int],
                          configuration: Configuration,
                          alloc: 'AssumptionIdAllocator') -> List[int]:
    """Populate configuration assumptions.

    Appends guarded unit clauses to ``set_kb`` and assumption IDs to ``assumptions``.

    Returns:
        The configuration assumption ids, in configuration order.
    """
    configuration = convert_keys_to_features(configuration)
    for feat in configuration.elements:
        if feat.name not in variables:
            raise KeyError(f'Feature {feat.name} is not in the model.')

    config_ids: List[int] = []
    for feat, value in configuration.elements.items():
        aid = alloc.allocate()
        config_ids.append(aid)
        desc = f'{feat.name} = {"true" if value else "false"}'
        var = variables[feat.name] if value else -1 * variables[feat.name]
        clause = [var, -1 * aid]

        assumptions.append(aid)
        set_kb.append(clause)
        provider.add_configuration_description(aid, desc)

    return config_ids


def _add_assignment_assumption(set_kb: List[List[int]], assumptions: List[int],
                               provider: DescriptionProvider, assumption_id: int,
                               feature_id: int, description: str, *, value: bool) -> None:
    """Add one assumption-guarded feature-assignment clause.

    ``value=True``  → clause ``[-a, feature_id]``  (assumption active ⇒ feature true)
    ``value=False`` → clause ``[-a, -feature_id]`` (assumption active ⇒ feature false)
    """
    literal = feature_id if value else -feature_id
    set_kb.append([-assumption_id, literal])
    assumptions.append(assumption_id)
    provider.add_configuration_description(assumption_id, description)


def prepare_variable_assignments(set_kb: List[List[int]], assumptions: List[int],
                                 provider: DescriptionProvider,
                                 name_to_id: Dict[str, int],
                                 alloc: 'AssumptionIdAllocator'):
    """Append paired (feature=true, feature=false) assignment assumptions.

    Builds the variable-assignment block of the oracle assumption layout: for
    each feature, two assumption-guarded clauses forcing it true / false when
    the corresponding assumption is active. Mutates ``set_kb`` / ``assumptions``
    (build-then-freeze). The pos/neg ids are one ``allocate_pair`` per feature.

    Returns:
        (pos_map, neg_map) where the maps are feature name → assumption id.
    """
    pos_assignment_to_assumption: Dict[str, int] = {}
    neg_assignment_to_assumption: Dict[str, int] = {}
    for name, fid in name_to_id.items():
        pos_id, neg_id = alloc.allocate_pair()
        pos_assignment_to_assumption[name] = pos_id
        _add_assignment_assumption(
            set_kb, assumptions, provider, pos_id, fid, f'{name}=true', value=True)
        neg_assignment_to_assumption[name] = neg_id
        _add_assignment_assumption(
            set_kb, assumptions, provider, neg_id, fid, f'{name}=false', value=False)
    return pos_assignment_to_assumption, neg_assignment_to_assumption


# === DIAGNOSIS STRATEGY ===

class DiagnosisTaskPreparation(TaskPreparationStrategy):
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

    def prepare(self, model: 'DiagnosisModel', task_input: TaskInput) -> PreparedTask:
        provider = DescriptionProvider()

        # Determine if negated forms should be used
        negated_constraint_map = model.negated_constraint_map if task_input.for_redundancy else None

        # Seed the allocator after the Tseitin variables (avoid id conflicts).
        alloc = AssumptionIdAllocator(model.next_available_id)

        # Local accumulation (build-then-freeze)
        set_kb: List[List[int]] = []
        assumptions: List[int] = []
        negation_map: Dict[int, int] = {}

        # Prepare KB. Each primitive RETURNS its originals (the ids it emitted as
        # originals, de-paired), so the sets are assigned by role below — no offset+
        # stride re-derivation of what the primitives already know.
        fm_originals = prepare_kb(set_kb, assumptions, negation_map, provider,
                                  model.constraint_map, alloc, negated_constraint_map)

        config_originals: List[int] = []
        if task_input.configuration is not None:
            config_originals = prepare_configuration(
                set_kb, assumptions, provider, model.variables,
                task_input.configuration, alloc)

        tc_originals: List[int] = []
        if task_input.test_case is not None:
            tc_originals = prepare_configuration(
                set_kb, assumptions, provider, model.variables,
                task_input.test_case, alloc)

        set_b, set_c = self._assign_sets(
            task_input, fm_originals, config_originals, tc_originals)

        task = DiagnosisTask(
            set_c=set_c, set_b=set_b, set_kb=set_kb,
            negation_map=negation_map, assumptions=assumptions)
        return PreparedTask(task, provider)

    def _assign_sets(self, task_input: TaskInput, fm_originals: List[int],
                     config_originals: List[int], tc_originals: List[int]
                     ) -> Tuple[List[int], List[int]]:
        """Assign (set_b, set_c) roles per use case from the returned originals.

        ``fm_originals[0]`` is the root constraint; ``fm_originals[1:]`` the rest.
        Config/test-case originals come straight off ``prepare_configuration``. No
        positional slicing — the scenario decides which originals play which role.
        """
        set_b: List[int] = []
        set_c: List[int] = []

        if task_input.configuration is not None:
            if not task_input.with_cf_in_c:
                # C = configuration, B = FM + root
                set_b = list(fm_originals)
                set_c = list(config_originals)
            else:
                # C = configuration + FM, B = root only
                set_b = [fm_originals[0]]
                set_c = fm_originals[1:] + config_originals
        elif task_input.test_case is not None:
            # C = FM constraints (no root), B = root + test case
            set_b = [fm_originals[0]] + tc_originals
            set_c = fm_originals[1:]
        elif task_input.for_redundancy:
            # WipeOutR_FM: C = FM constraint originals (no root), B = {}
            set_c = fm_originals[1:]
        else:
            # FM diagnosis: C = FM constraints (no root), B = root only
            set_b = [fm_originals[0]]
            set_c = fm_originals[1:]

        return set_b, set_c


# === TEST CASE STRATEGY ===

def prepare_testsuite_with_negation(set_kb: List[List[int]],
                                    assumptions: List[int],
                                    negation_map: Dict[int, int],
                                    provider: DescriptionProvider,
                                    variables: Dict[str, int],
                                    testsuite: TestSuite,
                                    alloc: 'AssumptionIdAllocator') -> Tuple[List[int], List[int]]:
    """Populate test cases with assumptions and their negated forms.

    Each test case gets one ``allocate_pair`` — (original, negated). The negated
    form is a single clause with all literals negated. Appends to ``set_kb``,
    ``assumptions`` and ``negation_map``.

    Returns:
        (original ids, negated ids) — both in test-case order. The originals are the
        caller's set_tc/set_tv; the negated ids route to set_neg_tv/set_neg_tc.
    """
    original_ids: List[int] = []
    negated_ids: List[int] = []
    for testcase in testsuite.testcases:
        original_id, negated_id = alloc.allocate_pair()

        # --- Original form ---
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
        original_ids.append(original_id)

        # --- Negated form ---
        negated_clause = [-lit for lit in literals]
        negated_clause.append(-negated_id)
        set_kb.append(negated_clause)

        assumptions.append(negated_id)
        provider.add_test_case_description(negated_id, f"NOT({' & '.join(desc_parts)})")
        negated_ids.append(negated_id)

        negation_map[original_id] = negated_id

    return original_ids, negated_ids


class TestCaseTaskPreparation(TaskPreparationStrategy):
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

    def prepare(self, model: 'DiagnosisModel', task_input: TaskInput) -> PreparedTask:
        provider = DescriptionProvider()

        # Seed the allocator after the Tseitin variables.
        alloc = AssumptionIdAllocator(model.next_available_id)

        # Local accumulation (build-then-freeze)
        set_kb: List[List[int]] = []
        assumptions: List[int] = []
        negation_map: Dict[int, int] = {}
        set_neg_tv: List[int] = []
        set_neg_tc: List[int] = []

        # Prepare KB (no negated forms needed for TestCaseTask). Each primitive
        # RETURNS its originals, so the sets are assigned by role below.
        fm_originals = prepare_kb(set_kb, assumptions, negation_map, provider,
                                  model.constraint_map, alloc, negated_constraint_map=None)

        # Prepare positive test cases with negated forms
        pos_original_ids, pos_negated_ids = prepare_testsuite_with_negation(
            set_kb, assumptions, negation_map, provider, model.variables,
            task_input.positive_test_cases, alloc)
        set_neg_tc.extend(pos_negated_ids)

        # Prepare negative test cases with negated forms if provided
        neg_original_ids: List[int] = []
        if task_input.negative_test_cases is not None:
            neg_original_ids, neg_negated_ids = prepare_testsuite_with_negation(
                set_kb, assumptions, negation_map, provider, model.variables,
                task_input.negative_test_cases, alloc)
            set_neg_tv.extend(neg_negated_ids)

        set_b, set_c, set_tc, set_tv = self._assign_sets(
            fm_originals, pos_original_ids, neg_original_ids)

        task = TestCaseTask(
            set_c=set_c, set_b=set_b, set_kb=set_kb,
            negation_map=negation_map, assumptions=assumptions,
            set_tc=set_tc, set_tv=set_tv,
            set_neg_tv=set_neg_tv, set_neg_tc=set_neg_tc)
        return PreparedTask(task, provider)

    def _assign_sets(self, fm_originals: List[int], pos_original_ids: List[int],
                     neg_original_ids: List[int]
                     ) -> Tuple[List[int], List[int], List[int], List[int]]:
        """Assign the KBDiag roles from the returned originals — no positional slicing.

        B = root, C = FM constraints minus root, TC = positive test-case originals,
        TV = negative test-case originals (empty when there are no negatives). The
        originals come straight off ``prepare_testsuite_with_negation``; the negated
        twins already routed to set_neg_tc / set_neg_tv in ``prepare``.
        """
        set_b = [fm_originals[0]]
        set_c = fm_originals[1:]
        set_tc = list(pos_original_ids)
        set_tv = list(neg_original_ids)
        return set_b, set_c, set_tc, set_tv


# === FORMATTER ===

def format_diagnoses(diagnoses: List[List], provider: DescriptionProvider) -> str:
    """Format diagnoses as a human-readable string."""
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
    def create_diagnosis(cls) -> TaskPreparationStrategy:
        """Create diagnosis task preparation strategy (incremental-agnostic)."""
        if cls._diagnosis is None:
            cls._diagnosis = DiagnosisTaskPreparation()
        return cls._diagnosis

    @classmethod
    def create_testcase(cls) -> TaskPreparationStrategy:
        """Create test case task preparation strategy (incremental-agnostic)."""
        if cls._testcase is None:
            cls._testcase = TestCaseTaskPreparation()
        return cls._testcase
