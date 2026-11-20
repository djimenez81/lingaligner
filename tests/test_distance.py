"""Segment distances: features in both modes, and a supplied matrix."""

from __future__ import annotations

import numpy as np
import pytest
from lingcore import FeatureMatrix

from lingaligner import (
    DistanceMatrix,
    FeatureCost,
    MatrixCost,
    MissingSegmentError,
)

SYMBOLS = ("a", "i", "u", "k", "t", "r")
FEATURES = ("CLOSED", "ROUNDED", "VOICE", "LABIAL")


def matrix():
    """Vowels carry the first two features; consonants leave them out."""
    return FeatureMatrix(
        segment_ids=SYMBOLS,
        feature_names=FEATURES,
        data=np.array(
            [
                [0.0, 0.0, 1.0, 0.0],
                [1.0, 0.0, 1.0, 0.0],
                [1.0, 1.0, 1.0, 0.0],
                [np.nan, np.nan, 0.0, 1.0],
                [np.nan, np.nan, 0.0, 0.0],
                [np.nan, np.nan, 1.0, 0.0],
            ]
        ),
    )


@pytest.fixture
def cost():
    return FeatureCost(matrix())


def test_identical_symbols_cost_nothing(cost):
    assert cost.cost("k", "k") == pytest.approx(0.0)
    assert cost.cost("a", "a") == pytest.approx(0.0)


def test_a_difference_in_one_feature(cost):
    assert cost.cost("a", "i") == pytest.approx(0.25)
    assert cost.cost("i", "u") == pytest.approx(0.25)


def test_undefined_is_charged_as_a_difference(cost):
    """a and t differ in three of four features, one of them undefined."""
    assert cost.cost("t", "a") == pytest.approx(0.75)


def test_undefined_does_not_match_undefined(cost):
    """k and t agree on every defined cell and still cost three quarters.

    Both leave CLOSED and ROUNDED undefined, and an undefined cell
    disagrees with everything, including another undefined cell. The
    two segments are consequently not at distance 0 despite identical
    rows, which is the conservative reading: the feature system holds
    no evidence that they are the same.
    """
    assert cost.cost("k", "t") == pytest.approx(0.75)


def test_cost_is_symmetric(cost):
    assert cost.cost("t", "a") == pytest.approx(cost.cost("a", "t"))


def test_unknown_symbol_is_named(cost):
    with pytest.raises(MissingSegmentError, match="zz"):
        cost.cost("a", "zz")


def test_describe_reports_the_parameters(cost):
    described = cost.describe()
    assert described["kind"] == "features"
    assert described["features"] == 4
    assert described["undefined_cells"] == 6
    assert described["categories"] is None


def test_a_matrix_without_features_is_refused():
    empty = FeatureMatrix(
        segment_ids=("a",), feature_names=(), data=np.zeros((1, 0))
    )
    with pytest.raises(ValueError, match="no feature"):
        FeatureCost(empty)


class TestPartitioned:
    """The inventory declares categories, so classes are never compared."""

    CATEGORIES = {"C": ("k", "t", "r"), "V": ("a", "i", "u")}

    @pytest.fixture
    def cost(self):
        return FeatureCost(matrix(), categories=self.CATEGORIES)

    def test_within_a_class_the_rule_is_unchanged(self, cost):
        assert cost.cost("a", "i") == pytest.approx(0.25)

    def test_across_classes_costs_one_by_default(self, cost):
        assert cost.cost("t", "a") == pytest.approx(1.0)

    def test_the_cross_class_cost_can_be_lowered(self):
        cost = FeatureCost(
            matrix(), categories=self.CATEGORIES, cross_class_cost=0.4
        )
        assert cost.cost("t", "a") == pytest.approx(0.4)

    def test_describe_reports_the_partition(self, cost):
        described = cost.describe()
        assert described["categories"] == {"C": 3, "V": 3}
        assert described["cross_class_cost"] == 1.0

    def test_an_unclassified_symbol_is_refused(self):
        with pytest.raises(ValueError, match="not in any of them"):
            FeatureCost(matrix(), categories={"C": ("k", "t")})

    def test_a_symbol_in_two_classes_is_refused(self):
        with pytest.raises(ValueError, match="both"):
            FeatureCost(
                matrix(),
                categories={"C": ("k", "t", "r", "a"), "V": ("a", "i")},
            )

    def test_a_class_naming_an_unknown_symbol_is_refused(self):
        with pytest.raises(MissingSegmentError, match="zz"):
            FeatureCost(
                matrix(),
                categories={"C": ("k", "t", "r", "zz")},
            )


class TestMatrixCost:
    @pytest.fixture
    def cost(self):
        labels = ("k", "t", "a")
        values = np.array(
            [
                [0.0, 0.2, 0.8],
                [0.2, 0.0, 0.7],
                [0.8, 0.7, 0.0],
            ]
        )
        return MatrixCost(DistanceMatrix(labels=labels, values=values))

    def test_it_reads_the_stored_value(self, cost):
        assert cost.cost("k", "t") == pytest.approx(0.2)
        assert cost.cost("a", "k") == pytest.approx(0.8)

    def test_an_unknown_symbol_is_named(self, cost):
        with pytest.raises(MissingSegmentError, match="labels"):
            cost.cost("a", "zz")

    def test_describe_reports_the_size(self, cost):
        assert cost.describe() == {"kind": "matrix", "segments": 3}
