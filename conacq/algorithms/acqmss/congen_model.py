"""
Model for ConGen algorithm.

Thin KB + codec container. Holds bias constraints; oracle injected at
prepare_task() time — model has no FM dependency.

prepare_task(task_input, oracle) -> ConGenTask with attached codec + describe.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from explanation.models.codec import VariableCodec
from explanation.models.task_preparation import TaskInput, DescriptionProvider, TestCaseTask
from explanation.models.testsuite import Assignment, TestCase, TestSuite
from .task_preparation import ConGenTask

if TYPE_CHECKING:
    from conacq.oracle import FeatureModelOracle
    from .congen import ConGenResult


class ConGenModel:
    """Thin KB container for ConGen algorithm.

    Holds bias constraints, variables, and negated_constraint_map (for
    redundancy detection).  Satisfies ModelProtocol.

    Call prepare_task(task_input, oracle) to get a fresh ConGenTask with
    attached VariableCodec (codec: just id_to_name — ConGen has no
    per-feature assignment assumptions).

    Each call to prepare_task returns an independent, fresh Task.
    Callers (runners, tests) must hold the returned task explicitly.
    """

    def __init__(self) -> None:
        # ModelProtocol fields
        self.constraint_map: Dict[str, List[List[int]]] = {}
        self.negated_constraint_map: Dict[str, List[List[int]]] = {}
        self.variables: Dict[str, int] = {}
        self.next_available_id: int = 1000

    # -------------------------------------------------------------------------
    # Sole public entry point: prepare_task
    # -------------------------------------------------------------------------

    def prepare_task(
            self,
            task_input: TaskInput,
            oracle: 'FeatureModelOracle',
    ) -> ConGenTask:
        """Prepare a fresh ConGenTask including GenerateNE.

        Oracle injected here — model stays FM-agnostic.
        Can be called multiple times (e.g., for CV folds); each call returns
        an independent, fresh Task.

        Attaches VariableCodec (id_to_name only — no per-feature assignment
        assumptions for ConGen) to the returned task.

        Args:
            task_input: TaskInput with positive/negative test cases + for_redundancy
            oracle: FeatureModelOracle for NE generation and FM metadata

        Returns:
            Fresh ConGenTask with task.codec and task.describe attached.
        """
        from .task_preparation import ConGenTaskPreparation

        preparation = ConGenTaskPreparation()
        output = preparation.prepare(self, task_input, oracle)

        assert isinstance(output.task, ConGenTask)
        task = output.task

        # Build codec: id_to_name only (ConGen has no assignment-assumption layer)
        codec = VariableCodec(
            id_to_name={vid: name for name, vid in self.variables.items()},
        )
        task.codec = codec
        task.describe = output.description_provider

        return task

    # -------------------------------------------------------------------------
    # Result resolution (used by ConGenRunner)
    # -------------------------------------------------------------------------

    def _resolve_ids(self, task: ConGenTask,
                     assumption_ids: List[int]) -> Tuple[List[List[int]], List[str]]:
        """Resolve assumption IDs to clauses and names via constraint_map."""
        provider = task.describe
        clauses: List[List[int]] = []
        names: List[str] = []
        for aid in assumption_ids:
            name = provider.get_description(aid)
            names.append(name)
            if name in self.constraint_map:
                clauses.extend(self.constraint_map[name])
        return clauses, names

    def resolve_result(self, task: ConGenTask, result: 'ConGenResult',
                       bg_clauses: Optional[List[List[int]]] = None,
                       ) -> Tuple[List[List[int]], List[List[int]], List[str], List[str]]:
        """Resolve a ConGenResult into clauses and names.

        Args:
            task: ConGenTask whose describe maps assumption IDs to names
            result: ConGenResult with assumption IDs.
            bg_clauses: Root/BG clauses (from oracle.get_root_clauses()); defaults to [].

        Returns:
            (bg_clauses, kb_clauses, kb_names, redundant_names)
        """
        bg = bg_clauses or []
        kb_clauses, kb_names = self._resolve_ids(task, result.kb_assumption_ids)
        _, redundant_names = self._resolve_ids(task, result.redundant_ids)
        return bg, kb_clauses, kb_names, redundant_names

    # -------------------------------------------------------------------------
    # Static helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _examples_to_testsuite(examples: List[Dict[str, bool]]) -> TestSuite:
        """Convert list of example dicts to TestSuite."""
        testcases = []
        for example in examples:
            assignments = [
                Assignment(feature=name, value=value)
                for name, value in example.items()
            ]
            testcases.append(TestCase(assignments=assignments))
        return TestSuite(testcases=testcases)
