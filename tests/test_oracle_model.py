"""Tests for OracleModel and OneShotModel."""

import pytest

from acqmss.oracle.oracle_model import OracleModel, OneShotModel
from explanation.operations.algorithms.checker import CheckerFactory, CheckerModel


class TestOracleModel:
    def test_from_fm_creates_valid_model(self):
        """OracleModel.from_fm produces valid set_kb and assumptions."""
        constraint_map = {"fm": [[1, 2]]}
        variables = {"f1": 1, "f2": 2}
        model = OracleModel.from_fm(constraint_map, variables, next_tseitin_var=2)

        assert len(model.get_assumptions()) == 4  # 2 features * 2 (pos+neg)
        assert model.use_incremental is True
        # set_kb = 1 FM clause + 4 guarded clauses
        assert len(model.get_kb()) == 1 + 4

    def test_satisfies_checker_model_protocol(self):
        """OracleModel satisfies CheckerModel Protocol."""
        model = OracleModel.from_fm({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, 2)
        assert isinstance(model, CheckerModel)

    def test_constraint_map_and_variables(self):
        """Verify constraint_map + variables stored correctly."""
        constraint_map = {"fm": [[1, 2], [-1, 3]]}
        variables = {"f1": 1, "f2": 2, "f3": 3}
        model = OracleModel.from_fm(constraint_map, variables, next_tseitin_var=3)

        assert model.constraint_map == constraint_map
        assert model.variables == variables

    def test_config_to_active_assumptions(self):
        """Config dict correctly maps to assumption IDs."""
        constraint_map = {"fm": [[1, 2]]}
        variables = {"f1": 1, "f2": 2}
        model = OracleModel.from_fm(constraint_map, variables, next_tseitin_var=2)

        active = model.config_to_active_assumptions({"f1": True, "f2": False})
        assert len(active) == 2
        assert model._feature_to_pos_assumption["f1"] in active
        assert model._feature_to_neg_assumption["f2"] in active

    def test_assumption_ids_start_after_tseitin(self):
        """Assumption IDs don't collide with FM variables."""
        model = OracleModel.from_fm({"fm": [[1, 2, 3]]}, {"f1": 1, "f2": 2, "f3": 3}, 3)
        # All assumption IDs should be > next_tseitin_var (3)
        for a in model.get_assumptions():
            assert a > 3

    def test_checker_integration_sat(self):
        """CheckerFactory creates valid checker; SAT case."""
        constraint_map = {"fm": [[1, 2]]}  # f1 OR f2
        variables = {"f1": 1, "f2": 2}
        model = OracleModel.from_fm(constraint_map, variables, next_tseitin_var=2)
        checker = CheckerFactory.create_from_model(model, 'glucose4')

        # f1=True, f2=True → SAT
        active = model.config_to_active_assumptions({"f1": True, "f2": True})
        assert checker.is_consistent(active) is True
        checker.cleanup()

    def test_checker_integration_unsat(self):
        """CheckerFactory creates valid checker; UNSAT case."""
        constraint_map = {"fm": [[1, 2]]}  # f1 OR f2
        variables = {"f1": 1, "f2": 2}
        model = OracleModel.from_fm(constraint_map, variables, next_tseitin_var=2)
        checker = CheckerFactory.create_from_model(model, 'glucose4')

        # f1=False, f2=False → UNSAT (neither true violates f1 OR f2)
        active = model.config_to_active_assumptions({"f1": False, "f2": False})
        assert checker.is_consistent(active) is False
        checker.cleanup()


class TestOneShotModel:
    def test_bakes_unit_clauses(self):
        """OneShotModel bakes assumptions as unit clauses into set_kb."""
        clauses = [[1, 2], [-1, 3]]
        model = OneShotModel(clauses, [1, -2])

        kb = model.get_kb()
        assert [1] in kb
        assert [-2] in kb
        assert model.get_assumptions() == []
        assert model.use_incremental is False

    def test_satisfies_checker_model_protocol(self):
        """OneShotModel satisfies CheckerModel Protocol."""
        model = OneShotModel([[1, 2]])
        assert isinstance(model, CheckerModel)

    def test_no_assumptions_param(self):
        """OneShotModel works without unit_assumptions."""
        model = OneShotModel([[1, 2], [-1, 3]])
        assert model.get_kb() == [[1, 2], [-1, 3]]
        assert model.get_assumptions() == []

    def test_oneshot_checker_sat(self):
        """Factory creates NonIncremental checker; SAT case."""
        model = OneShotModel([[1, 2]], [1])
        checker = CheckerFactory.create_from_model(model, 'glucose4')
        assert checker.is_consistent([]) is True
        checker.cleanup()

    def test_oneshot_checker_unsat(self):
        """Factory creates NonIncremental checker; UNSAT case."""
        model = OneShotModel([[1], [-1]])
        checker = CheckerFactory.create_from_model(model, 'glucose4')
        assert checker.is_consistent([]) is False
        checker.cleanup()
