"""Tests for FMOracleModel and the new prepare_task contract."""

import pytest

from conacq.oracle.fm_oracle_model import FMOracleModel
from explanation.models.task_preparation import DiagnosisTask
from explanation.models.codec import VariableCodec
from explanation.operations.algorithms.checker import CheckerFactory


def _make_oracle_model(constraint_map, variables, next_available_id):
    """Test helper: create FMOracleModel from raw data and call prepare_task."""
    model = FMOracleModel()
    model.constraint_map = constraint_map
    model.variables = variables
    model.next_available_id = next_available_id
    model.prepare_task()
    return model


class TestOracleModel:
    def test_from_fm_creates_valid_model(self):
        """FMOracleModel.prepare_task() produces valid set_kb and assumptions."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)
        task = model.prepare_task()

        assert len(task.assumptions) == 5  # 1 FM constraint + 2 features * 2 (pos+neg)
        # set_kb = 1 FM guarded clause + 4 feature assignment clauses
        assert len(task.set_kb) == 1 + 4

    def test_prepare_task_returns_task_with_codec(self):
        """prepare_task() returns DiagnosisTask with codec + describe attached.

        Replaces the old isinstance(model, CheckerModel) test with a meaningful
        assertion on the new contract: the returned Task has a working
        VariableCodec and the codec round-trips feature assignments.
        """
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, 2)
        task = model.prepare_task()

        # Task is a DiagnosisTask
        assert isinstance(task, DiagnosisTask)

        # Codec is attached and has correct id_to_name
        assert task.codec is not None
        assert isinstance(task.codec, VariableCodec)
        assert task.codec.id_to_name == {1: "f1", 2: "f2"}

        # Codec pos/neg maps are populated (Part 4 assumption layer)
        assert "f1" in task.codec.pos_assignment_to_assumption
        assert "f2" in task.codec.neg_assignment_to_assumption

        # Round-trip: config_to_assumptions produces valid assumption IDs
        config = {"f1": True, "f2": False}
        asm = task.codec.config_to_assumptions(config)
        assert len(asm) == 2
        assert task.codec.pos_assignment_to_assumption["f1"] in asm
        assert task.codec.neg_assignment_to_assumption["f2"] in asm

        # describe is attached (DescriptionProvider)
        assert task.describe is not None

        # A checker built from this task works correctly
        checker = CheckerFactory.create_from_task(task, solver_name='glucose4')
        try:
            # f1=True, f2=True => SAT (clause [1,2] satisfied)
            set_c = (list(model._base_set_c) +
                     task.codec.config_to_assumptions({"f1": True, "f2": True}))
            assert checker.is_consistent(set_c) is True
        finally:
            checker.cleanup()

    def test_constraint_map_and_variables(self):
        """Verify constraint_map + variables stored correctly."""
        constraint_map = {"fm": [[1, 2], [-1, 3]]}
        variables = {"f1": 1, "f2": 2, "f3": 3}
        model = _make_oracle_model(constraint_map, variables, next_available_id=3)

        assert model.constraint_map == constraint_map
        assert model.variables == variables

    def test_config_to_active_assumptions(self):
        """Config dict correctly maps to assumption IDs via codec."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)
        task = model.prepare_task()

        # Apply config via codec + base_set_c (replicating old with_configuration logic)
        config = {"f1": True, "f2": False}
        config_assumptions = task.codec.config_to_assumptions(config)
        active = list(model._base_set_c) + config_assumptions

        assert task.codec.pos_assignment_to_assumption["f1"] in active
        assert task.codec.neg_assignment_to_assumption["f2"] in active

    def test_assumption_ids_start_after_tseitin(self):
        """Assumption IDs don't collide with FM variables."""
        model = _make_oracle_model({"fm": [[1, 2, 3]]}, {"f1": 1, "f2": 2, "f3": 3}, 3)
        task = model.prepare_task()
        # All assumption IDs should be >= next_available_id (3)
        for a in task.assumptions:
            assert a >= 3

    def test_checker_integration_sat(self):
        """CheckerFactory.create_from_task creates valid checker; SAT case."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)
        task = model.prepare_task()
        checker = CheckerFactory.create_from_task(task, solver_name='glucose4')

        # f1=True, f2=True → SAT
        set_c = (list(model._base_set_c) +
                 task.codec.config_to_assumptions({"f1": True, "f2": True}))
        assert checker.is_consistent(set_c) is True
        checker.cleanup()

    def test_checker_integration_unsat(self):
        """CheckerFactory.create_from_task creates valid checker; UNSAT case."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)
        task = model.prepare_task()
        checker = CheckerFactory.create_from_task(task, solver_name='glucose4')

        # f1=False, f2=False → UNSAT (neither true violates f1 OR f2)
        set_c = (list(model._base_set_c) +
                 task.codec.config_to_assumptions({"f1": False, "f2": False}))
        assert checker.is_consistent(set_c) is False
        checker.cleanup()
