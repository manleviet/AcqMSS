"""Tests for FMOracleModel."""

import pytest

from conacq.oracle.fm_oracle_model import FMOracleModel
from explanation.operations.algorithms.checker import CheckerFactory, CheckerModel


def _make_oracle_model(constraint_map, variables, next_available_id):
    """Test helper: create FMOracleModel from raw data and prepare."""
    model = FMOracleModel()
    model.constraint_map = constraint_map
    model.variables = variables
    model.next_available_id = next_available_id
    model.prepare()
    return model


class TestOracleModel:
    def test_from_fm_creates_valid_model(self):
        """FMOracleModel.from_fm produces valid set_kb and assumptions."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)

        assert len(model.get_assumptions()) == 5  # 1 FM constraint + 2 features * 2 (pos+neg)
        assert model._use_incremental is True
        # set_kb = 1 FM guarded clause + 4 feature assignment clauses
        assert len(model.get_kb()) == 1 + 4

    def test_satisfies_checker_model_protocol(self):
        """FMOracleModel satisfies CheckerModel Protocol."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, 2)
        assert isinstance(model, CheckerModel)

    def test_constraint_map_and_variables(self):
        """Verify constraint_map + variables stored correctly."""
        constraint_map = {"fm": [[1, 2], [-1, 3]]}
        variables = {"f1": 1, "f2": 2, "f3": 3}
        model = _make_oracle_model(constraint_map, variables, next_available_id=3)

        assert model.constraint_map == constraint_map
        assert model.variables == variables

    def test_config_to_active_assumptions(self):
        """Config dict correctly maps to assumption IDs."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)

        model.with_configuration({"f1": True, "f2": False})
        active = model.get_c()
        # set_c includes FM constraint assumptions + feature assignment assumptions
        assert model._pos_assignment_to_assumption["f1"] in active
        assert model._neg_assignment_to_assumption["f2"] in active

    def test_assumption_ids_start_after_tseitin(self):
        """Assumption IDs don't collide with FM variables."""
        model = _make_oracle_model({"fm": [[1, 2, 3]]}, {"f1": 1, "f2": 2, "f3": 3}, 3)
        # All assumption IDs should be >= next_available_id (3)
        for a in model.get_assumptions():
            assert a >= 3

    def test_checker_integration_sat(self):
        """CheckerFactory creates valid checker; SAT case."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)
        checker = CheckerFactory.create_from_model(model, 'glucose4')

        # f1=True, f2=True → SAT
        model.with_configuration({"f1": True, "f2": True})
        assert checker.is_consistent(model.get_c()) is True
        checker.cleanup()

    def test_checker_integration_unsat(self):
        """CheckerFactory creates valid checker; UNSAT case."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)
        checker = CheckerFactory.create_from_model(model, 'glucose4')

        # f1=False, f2=False → UNSAT (neither true violates f1 OR f2)
        model.with_configuration({"f1": False, "f2": False})
        assert checker.is_consistent(model.get_c()) is False
        checker.cleanup()


