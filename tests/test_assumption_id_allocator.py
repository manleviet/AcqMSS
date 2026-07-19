"""AssumptionIdAllocator hands out ids and emits (original, negated) pairs as a unit.

It carries only the running counter — no labels, no recorded originals. The
"originals are recorded at emission, not inferred by stride" proof lives on
``prepare_kb`` (the function that actually emits them), not here — see
``tests/test_assumption_slicer.py::test_prepare_kb_returns_originals_on_a_mixed_batch``.
"""
from explanation.models.assumption_id_allocator import AssumptionIdAllocator


def test_allocate_emits_single_contiguous_ids():
    a = AssumptionIdAllocator(start=100)
    assert a.allocate() == 100
    assert a.allocate() == 101
    assert a.next_id == 102


def test_allocate_pair_emits_two_contiguous_ids_original_then_negated():
    a = AssumptionIdAllocator(start=10)
    assert a.allocate_pair() == (10, 11)
    assert a.allocate_pair() == (12, 13)
    assert a.next_id == 14


def test_allocate_and_pair_interleave_contiguously():
    a = AssumptionIdAllocator(start=1)
    assert a.allocate_pair() == (1, 2)
    assert a.allocate() == 3
    assert a.allocate_pair() == (4, 5)
    assert a.next_id == 6


def test_default_start_is_one():
    a = AssumptionIdAllocator()
    assert a.allocate() == 1
    assert a.next_id == 2
