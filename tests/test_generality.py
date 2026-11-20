"""The aligner is not a phonetic tool; these are the non-phonetic cases."""

from __future__ import annotations

import pytest

from lingaligner import align, exact_cost


def test_dna_aligns_like_anything_else():
    strand = ("G", "A", "T", "T", "A", "C", "A")
    alignment = align(strand, strand, exact_cost)
    assert alignment.score == pytest.approx(7.0)
    assert alignment.distance(exact_cost) == pytest.approx(0.0)


def test_a_substitution_in_dna_costs_one_column():
    alignment = align(("G", "A", "T"), ("G", "C", "T"), exact_cost)
    assert not alignment.gapped
    assert alignment.distance(exact_cost) == pytest.approx(1 / 3)


def test_nucleotides_with_equal_lengths_and_no_gaps_available():
    """A mismatch is preferred to a gap unless gaps are made cheaper."""
    strict = align(("A",), ("C",), exact_cost)
    loose = align(("A",), ("C",), exact_cost, gap_cost=0.4)
    assert not strict.gapped
    assert loose.gapped


def test_a_custom_cost_changes_the_score():
    """Transitions cheaper than transversions, as in real sequence work."""
    transition = {("A", "G"), ("G", "A"), ("C", "T"), ("T", "C")}

    def cost(item_a, item_b):
        if item_a == item_b:
            return 0.0
        return 0.3 if (item_a, item_b) in transition else 0.9

    alignment = align(("A",), ("G",), cost)
    assert alignment.score == pytest.approx(0.7)
    assert alignment.distance(cost) == pytest.approx(0.3)


def test_syllables_are_items_too():
    def cost(item_a, item_b):
        return 0.0 if item_a == item_b else 1.0

    alignment = align(("ka", "ra", "po"), ("ka", "ri", "po"), cost)
    assert alignment.distance(cost) == pytest.approx(1 / 3)
