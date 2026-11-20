"""Alignment behaviour, pinned to hand-computed alignments."""

from __future__ import annotations

import pytest

from lingaligner import (
    Alignment,
    AlignmentLimitError,
    EmptyAlignmentError,
    align,
    align_all,
    exact_cost,
)


def test_identical_sequences_align_without_gaps():
    alignment = align(("a", "b", "c"), ("a", "b", "c"), exact_cost)
    assert alignment.score == pytest.approx(3.0)
    assert not alignment.gapped
    assert alignment.distance(exact_cost) == pytest.approx(0.0)
    assert alignment.identities == 3


def test_deletion_becomes_one_gap_column():
    alignment = align(("a", "b", "c"), ("a", "c"), exact_cost)
    assert alignment.score == pytest.approx(2.0)
    assert len(alignment) == 3
    assert alignment.sequence_a == ("a", "b", "c")
    assert alignment.sequence_b == ("a", None, "c")
    # the gap column is charged the full gap cost, so the mean is 1/3
    assert alignment.distance(exact_cost) == pytest.approx(1 / 3)


def test_insertion_mirrors_deletion():
    alignment = align(("a", "c"), ("a", "b", "c"), exact_cost)
    assert alignment.sequence_a == ("a", None, "c")
    assert alignment.sequence_b == ("a", "b", "c")
    assert alignment.distance(exact_cost) == pytest.approx(1 / 3)


def test_tie_prefers_a_substitution_over_a_gap():
    """Two maximally different items tie with a gap pair; the swap wins."""
    alignment = align(("a",), ("b",), exact_cost)
    assert alignment.score == pytest.approx(0.0)
    assert not alignment.gapped
    assert alignment.distance(exact_cost) == pytest.approx(1.0)


def test_cheaper_gaps_are_taken():
    """At gap_cost 0.6 a gap pair outscores a maximal substitution."""
    alignment = align(("a",), ("b",), exact_cost, gap_cost=0.6)
    assert len(alignment) == 2
    assert alignment.gapped
    assert alignment.score == pytest.approx(0.8)
    assert alignment.distance(exact_cost) == pytest.approx(0.6)


def test_gap_cost_does_not_disturb_a_perfect_alignment():
    alignment = align(("a", "b"), ("a", "b"), exact_cost, gap_cost=0.6)
    assert not alignment.gapped
    assert alignment.score == pytest.approx(2.0)


def test_score_is_the_dual_of_the_distance():
    """score = sum(1 - penalty) over columns, by construction."""
    cost = exact_cost
    alignment = align(("a", "b", "c"), ("a", "c"), cost)
    penalties = []
    for item_a, item_b in alignment.columns():
        if item_a is None or item_b is None:
            penalties.append(alignment.gap_cost)
        else:
            penalties.append(cost(item_a, item_b))
    assert sum(1.0 - penalty for penalty in penalties) == pytest.approx(
        alignment.score
    )


def test_empty_sequences_have_no_columns():
    alignment = align((), (), exact_cost)
    assert len(alignment) == 0
    assert alignment.score == pytest.approx(0.0)
    with pytest.raises(EmptyAlignmentError):
        alignment.distance(exact_cost)


def test_empty_against_nonempty_is_all_gaps():
    alignment = align((), ("a",), exact_cost)
    assert alignment.sequence_a == (None,)
    assert alignment.sequence_b == ("a",)
    assert alignment.distance(exact_cost) == pytest.approx(1.0)


def test_align_all_returns_every_tie():
    """Three alignments score 1.0 and measure two different distances.

    Aligning ``("a", "b")`` with ``("a", "x")`` leaves one good column
    and one bad one. The bad pair can be a substitution or a gap in
    either sequence, and the three readings score the same while the
    mean penalty differs: 0.5 for two columns against 2/3 for three,
    because each gap adds a column that holds no match.
    """
    cost = exact_cost
    alignments = align_all(("a", "b"), ("a", "x"), cost)
    assert len(alignments) == 3
    assert {round(item.score, 12) for item in alignments} == {1.0}
    distances = sorted(item.distance(cost) for item in alignments)
    assert distances[0] == pytest.approx(0.5)
    assert distances[1:] == [pytest.approx(2 / 3)] * 2


def test_align_returns_the_first_optimal_alignment():
    alignment = align(("a", "b"), ("a", "x"), exact_cost)
    assert not alignment.gapped
    assert alignment.distance(exact_cost) == pytest.approx(0.5)


def test_align_all_refuses_to_truncate():
    with pytest.raises(AlignmentLimitError):
        align_all(("a", "b"), ("a", "x"), exact_cost, limit=1)


def test_align_all_on_an_unambiguous_pair_returns_one():
    alignments = align_all(("a", "b"), ("a", "b"), exact_cost)
    assert len(alignments) == 1
    assert alignments[0].distance(exact_cost) == pytest.approx(0.0)


def test_cost_is_evaluated_once_per_pair():
    calls = []

    def cost(item_a, item_b):
        calls.append((item_a, item_b))
        return exact_cost(item_a, item_b)

    align(("a", "b", "c"), ("x", "y"), cost)
    assert len(calls) == 6


@pytest.mark.parametrize("gap_cost", [-0.1, 1.5, float("nan"), float("inf")])
def test_invalid_gap_cost_is_rejected(gap_cost):
    with pytest.raises(ValueError):
        align(("a",), ("a",), exact_cost, gap_cost=gap_cost)


def test_alignment_rejects_sequences_of_different_length():
    with pytest.raises(ValueError):
        Alignment(("a",), (None, None), 0.0)


def test_identities_counts_only_exact_matches():
    alignment = align(("a", "b"), ("a", "c"), exact_cost)
    assert alignment.identities == 1
