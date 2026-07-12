"""Diagnosis model — an immutable knowledge base (KB).

A DiagnosisModel holds only KB data (constraint clauses, optional negated forms,
the feature↔variable catalog, and the next free assumption ID). It carries no
task state: callers derive a fresh PreparedTask per invocation via
``prepare_task(task_input)``. The same KB can produce any number of independent
tasks, and ``use_incremental`` is an operation/checker concern (not a model one).
"""

from typing import Dict, List, Mapping, Optional

from flamapy.metamodels.pysat_metamodel.models import PySATModel

from .task_preparation import (
    TaskPreparationFactory,
    TaskInput,
    PreparedTask,
)


class DiagnosisModel(PySATModel):
    """PySATModel extension representing an immutable diagnosis KB.

    Created via transformation (FmToDiagPysat or DimacsToDiagPysat), which
    populates ``constraint_map``, ``negated_constraint_map`` and
    ``next_available_id``. Per-task inputs (configuration, test cases, redundancy
    flag) are supplied to ``prepare_task`` as a TaskInput, never stored on the
    model.

    Supported task types (overview — see ``prepare_task`` for the full
    TaskInput → C/B/TC/TV mapping):
    1. Configuration diagnosis   — TaskInput(configuration=cfg)                          → DiagnosisTask
    2. Config + FM diagnosis      — TaskInput(configuration=cfg, with_cf_in_c=True)        → DiagnosisTask
    3. FM diagnosis               — TaskInput()                                            → DiagnosisTask
    4. Error diagnosis            — TaskInput(test_case=tc)                                → DiagnosisTask
    5. KBDiag debugging           — TaskInput(positive_test_cases=tc, negative_test_cases=tv) → TestCaseTask
    6. WipeOutR_T (TC redundancy) — TaskInput(positive_test_cases=ts, for_redundancy=True) → TestCaseTask
    7. WipeOutR_FM (FM redundancy)— TaskInput(for_redundancy=True) + builder.for_redundancy() → DiagnosisTask
    """

    @staticmethod
    def get_extension() -> str:
        return 'pysat_diagnosis'

    def __init__(self) -> None:
        super().__init__()
        # map clauses to relationships/constraint
        self.constraint_map: Dict[str, List[List]] = {}
        # map negated clauses to relationships/constraint (for WipeOutR_FM)
        self.negated_constraint_map: Dict[str, List[List]] = {}
        # Next available variable ID after Tseitin variables (set by transformation).
        # Used as starting ID for assumption literals to avoid conflicts.
        self.next_available_id: int = 1000

    # KB Protocol: name↔id catalog. flamapy's PySATModel owns the storage and
    # names it features/variables; these properties are the translation layer to
    # the KBProtocol names. They return the dicts directly — no runtime read-only
    # view (see ADR-0007); KBProtocol types them as Mapping, so read-only lives
    # at the type level for free.
    @property
    def id_to_name(self) -> Mapping[int, str]:
        """SAT variable id → feature name."""
        return self.features

    @property
    def name_to_id(self) -> Mapping[str, int]:
        """Feature name → SAT variable id."""
        return self.variables

    def add_clause_to_map(self, description: str, clauses: List[List]) -> None:
        """Add clauses with description to constraint map."""
        self.constraint_map[description] = clauses

    def add_negated_clause_to_map(self, description: str, clauses: List[List]) -> None:
        """Add negated clauses with description to negated constraint map."""
        self.negated_constraint_map[description] = clauses

    def prepare_task(self, task_input: Optional[TaskInput] = None) -> PreparedTask:
        """Derive a fresh PreparedTask from this KB for the given inputs (pure).

        The single entry point for preparation. Each call builds a new task; two
        calls yield independent tasks. Preparation does not mutate the model.

        Supported task types (selected by the TaskInput fields):
        1. Configuration diagnosis: TaskInput(configuration=cfg)
           C = configuration, B = FM + root  -> DiagnosisTask
        2. Config + FM diagnosis: TaskInput(configuration=cfg, with_cf_in_c=True)
           C = configuration + FM, B = root only  -> DiagnosisTask
        3. FM diagnosis: TaskInput()  (no inputs)
           C = FM constraints, B = root only  -> DiagnosisTask
        4. Error diagnosis: TaskInput(test_case=tc)
           C = FM constraints, B = root + test_case  -> DiagnosisTask
        5. KBDiag debugging: TaskInput(positive_test_cases=tc, negative_test_cases=tv)
           C = FM (excl. root), B = root, TC = positive, TV = negative  -> TestCaseTask
        6. WipeOutR_T (test case redundancy): TaskInput(positive_test_cases=ts, for_redundancy=True)
           -> TestCaseTask
        7. WipeOutR_FM (constraint redundancy): TaskInput(for_redundancy=True)
           C = CF (FM constraints, no root), B = {}  -> DiagnosisTask

        Args:
            task_input: Per-task inputs (configuration, test cases, redundancy
                flag, ...). Defaults to an empty TaskInput (FM diagnosis, case 3).

        Returns:
            PreparedTask bundling the task, its DescriptionProvider, and (empty)
            assignment map.
        """
        task_input = task_input if task_input is not None else TaskInput()

        if task_input.is_testcase_task():
            strategy = TaskPreparationFactory.create_testcase()
        else:
            strategy = TaskPreparationFactory.create_diagnosis()

        return strategy.prepare(self, task_input)
