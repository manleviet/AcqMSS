"""Diagnosis model — an immutable knowledge base (KB).

A DiagnosisModel holds only KB data (constraint clauses, optional negated forms,
the feature→variable map, and the next free assumption ID). It carries no task
state: callers derive a fresh Task per invocation via ``prepare_task(task_input)``.
The same KB can produce any number of independent Tasks.
"""

from typing import Dict, List, Optional

from flamapy.metamodels.pysat_metamodel.models import PySATModel

from .codec import VariableCodec
from .task_preparation import (
    TaskPreparationFactory,
    TaskInput,
    Task,
)


class DiagnosisModel(PySATModel):
    """PySATModel extension representing an immutable diagnosis KB.

    Created via transformation (FmToDiagPysat or DimacsToDiagPysat), which
    populates ``constraint_map``, ``negated_constraint_map`` and
    ``next_available_id``. Per-task inputs (configuration, test cases,
    redundancy flag) are supplied to ``prepare_task`` as a TaskInput, never
    stored on the model.

    Satisfies ModelProtocol (constraint_map, negated_constraint_map, variables,
    next_available_id), which is the contract preparation strategies read.

    Supported task types (overview — see ``prepare_task`` for the full
    TaskInput → C/B/TC/TV mapping):
    1. Configuration diagnosis     — TaskInput(configuration=cfg)        → DiagnosisTask
    2. Config + FM diagnosis        — TaskInput(configuration=cfg, with_cf_in_c=True)  → DiagnosisTask
    3. FM diagnosis                 — TaskInput()                        → DiagnosisTask
    4. Error diagnosis              — TaskInput(test_case=tc)            → DiagnosisTask
    5. KBDiag debugging             — TaskInput(positive_test_cases=tc, negative_test_cases=tv) → TestCaseTask
    6. WipeOutR_T (TC redundancy)   — TaskInput(positive_test_cases=ts, for_redundancy=True)    → TestCaseTask
    7. WipeOutR_FM (FM redundancy)  — TaskInput(for_redundancy=True) + builder.with_negation()  → DiagnosisTask
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

        # Lazily-built codec (derived from variables); KB-level, shared by Tasks.
        self._codec: Optional[VariableCodec] = None

    def add_clause_to_map(self, description: str, clauses: List[List]) -> None:
        """Add clauses with description to constraint map."""
        self.constraint_map[description] = clauses

    def add_negated_clause_to_map(self, description: str, clauses: List[List]) -> None:
        """Add negated clauses with description to negated constraint map."""
        self.negated_constraint_map[description] = clauses

    @property
    def codec(self) -> VariableCodec:
        """Variable codec for this KB (id↔name).

        Built once from ``variables``. The assignment-assumption layer
        (pos/neg maps) is empty for DiagnosisModel: configuration assumptions
        are created per-task by the preparation strategy, not a stable KB layer.
        """
        if self._codec is None:
            self._codec = VariableCodec(
                id_to_name={vid: name for name, vid in self.variables.items()})
        return self._codec

    def prepare_task(self, task_input: Optional[TaskInput] = None) -> Task:
        """Derive a fresh Task from this KB for the given inputs (pure; no mutation).

        Each call builds a new Task; two calls yield independent Tasks. The
        returned Task carries its own formatter (``describe``) and the KB codec.

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

        Case 7 (WipeOutR_FM) consumes negated CONSTRAINT forms, so its KB must be
        built with ``DiagnosisModelBuilder.with_negation()`` (constraint negation
        is a KB property; ``for_redundancy`` is the per-task flag that consumes
        it). Case 6 (WipeOutR_T) needs no KB negation — the test-case strategy
        builds the test-case negations itself.

        Args:
            task_input: Per-task inputs (configuration, test cases, redundancy
                flag, ...). Defaults to an empty TaskInput (FM diagnosis, case 3).

        Returns:
            A DiagnosisTask (cases 1-4, 7) or TestCaseTask (cases 5-6) per the inputs.
        """
        task_input = task_input if task_input is not None else TaskInput()

        if task_input.is_testcase_task():
            strategy = TaskPreparationFactory.create_testcase()
        else:
            strategy = TaskPreparationFactory.create_diagnosis()

        output = strategy.prepare(self, task_input)
        task = output.task
        task.describe = output.description_provider
        task.codec = self.codec
        return task
