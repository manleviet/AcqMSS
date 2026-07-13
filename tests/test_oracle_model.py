"""Tests for FMOracleModel."""

import pytest

from conacq.oracle.fm_oracle_model import FMOracleModel
from explanation.api import config_to_assignment_assumptions
from explanation.checker.backend import build_checker, SolverBackend


def _make_oracle_model(constraint_map, variables, next_available_id):
    """Test helper: create FMOracleModel from raw data and prepare."""
    model = FMOracleModel()
    model.constraint_map = constraint_map
    model.name_to_id = variables
    model.next_available_id = next_available_id
    model.prepare()
    return model


def _query_set_c(model, config):
    """The set_c a membership query builds (mirrors FMOracle.is_valid): the task's
    FM constraints plus this query's assignment assumptions, via the model's
    one-off assignment_map. Pure — never touches the model."""
    return model.get_c() + config_to_assignment_assumptions(config, model.assignment_map)


class TestOracleModel:
    def test_from_fm_creates_valid_model(self):
        """FMOracleModel.from_fm produces valid set_kb and assumptions."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)

        assert len(model.get_assumptions()) == 5  # 1 FM constraint + 2 features * 2 (pos+neg)
        assert model._use_incremental is True
        # set_kb = 1 FM guarded clause + 4 feature assignment clauses
        assert len(model.get_kb()) == 1 + 4

    def test_satisfies_checker_model_protocol(self):
        """FMOracleModel exposes the task + use_incremental used by create_from_task."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, 2)
        assert isinstance(model.use_incremental, bool)
        assert model.task.set_kb is not None
        assert model.task.assumptions is not None

    def test_constraint_map_and_variables(self):
        """Verify constraint_map + variables stored correctly."""
        constraint_map = {"fm": [[1, 2], [-1, 3]]}
        variables = {"f1": 1, "f2": 2, "f3": 3}
        model = _make_oracle_model(constraint_map, variables, next_available_id=3)

        assert model.constraint_map == constraint_map
        assert model.name_to_id == variables

    def test_query_set_c_maps_query_without_mutating(self):
        """A membership query's set_c contains that query's assignment assumptions
        (mapped via the model's one-off assignment_map) and leaves the model
        untouched — no query leaks into get_c()."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)

        before = model.get_c()
        active = _query_set_c(model, {"f1": True, "f2": False})

        # The query's assignment assumptions are present in the returned set_c...
        assert model.assignment_map.pos_assignment_to_assumption["f1"] in active
        assert model.assignment_map.neg_assignment_to_assumption["f2"] in active
        # ...but the model's own state (get_c) is unchanged — no query leaks in.
        assert model.get_c() == before
        assert active != before

    def test_assumption_ids_start_after_tseitin(self):
        """Assumption IDs don't collide with FM variables."""
        model = _make_oracle_model({"fm": [[1, 2, 3]]}, {"f1": 1, "f2": 2, "f3": 3}, 3)
        # All assumption IDs should be >= next_available_id (3)
        for a in model.get_assumptions():
            assert a >= 3

    def test_checker_integration_sat(self):
        """build_checker creates valid checker; SAT case."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)
        checker = build_checker(model.task, SolverBackend.from_flags(use_incremental=model.use_incremental), 'glucose4')

        # f1=True, f2=True → SAT
        assert checker.is_consistent(_query_set_c(model, {"f1": True, "f2": True})) is True
        checker.cleanup()

    def test_checker_integration_unsat(self):
        """build_checker creates valid checker; UNSAT case."""
        model = _make_oracle_model({"fm": [[1, 2]]}, {"f1": 1, "f2": 2}, next_available_id=2)
        checker = build_checker(model.task, SolverBackend.from_flags(use_incremental=model.use_incremental), 'glucose4')

        # f1=False, f2=False → UNSAT (neither true violates f1 OR f2)
        assert checker.is_consistent(_query_set_c(model, {"f1": False, "f2": False})) is False
        checker.cleanup()


