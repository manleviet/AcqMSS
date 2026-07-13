"""The narrow oracle protocols are real contracts, and they distinguish.

FMOracle must satisfy every role protocol (it is the full oracle), and
FMOracleModel must satisfy CatalogProvider (it owns the catalog now). Crucially,
the protocols must DISCRIMINATE: an object with only is_valid is a MembershipOracle
but not a KBProvider, and vice versa. A protocol that everything satisfies is a
decorative protocol — this test is what keeps these honest.
"""
import pytest

from conacq.oracle import (
    FMOracle,
    MembershipOracle,
    CompletableOracle,
    CatalogProvider,
    BGProvider,
    KBProvider,
    GeneratorOracle,
    PreparationOracle,
)
from tests.resource_paths import FM_PATH

_ALL_PROTOCOLS = [
    MembershipOracle, CompletableOracle, CatalogProvider,
    BGProvider, KBProvider, GeneratorOracle, PreparationOracle,
]


@pytest.fixture(scope="module")
def fm_oracle():
    if not FM_PATH.exists():
        pytest.skip(f"feature model not found: {FM_PATH}")
    return FMOracle(str(FM_PATH))


@pytest.mark.parametrize("protocol", _ALL_PROTOCOLS, ids=lambda p: p.__name__)
def test_feature_model_oracle_satisfies_every_protocol(fm_oracle, protocol):
    assert isinstance(fm_oracle, protocol)


def test_fm_oracle_model_owns_the_catalog(fm_oracle):
    """The catalog lives on FMOracleModel; the oracle only delegates."""
    model = fm_oracle._oracle_model
    assert isinstance(model, CatalogProvider)
    # Delegation is byte-identical.
    assert fm_oracle.get_variables() == model.get_variables()
    assert fm_oracle.get_variable_ids() == model.get_variable_ids()


# --- discrimination: the roles must be distinguishable, not decorative ---
class _OnlyMembership:
    def is_valid(self, assignments):
        return True


class _OnlyKB:
    def get_kb(self):
        return []

    def get_assumptions(self):
        return []

    def get_c(self):
        return []


def test_membership_only_object_is_not_a_kb_provider():
    obj = _OnlyMembership()
    assert isinstance(obj, MembershipOracle)
    assert not isinstance(obj, KBProvider)
    # ...and it is not a composite that demands more than membership.
    assert not isinstance(obj, GeneratorOracle)


def test_kb_only_object_is_not_a_membership_oracle():
    obj = _OnlyKB()
    assert isinstance(obj, KBProvider)
    assert not isinstance(obj, MembershipOracle)


def test_kb_provider_and_bg_provider_are_distinct_roles():
    """The A6-affected KB surface is its own role, not merged into BGProvider."""
    # An object with only BG methods is not a KBProvider (and vice versa).
    class _OnlyBG:
        def get_bg_data(self):
            return None

        def get_root_clauses(self):
            return []

    assert isinstance(_OnlyBG(), BGProvider)
    assert not isinstance(_OnlyBG(), KBProvider)
    assert not isinstance(_OnlyKB(), BGProvider)
