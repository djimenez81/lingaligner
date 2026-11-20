"""The facade: wiring, and the operations it exposes."""

from __future__ import annotations

import numpy as np
import pytest
from lingcore import FeatureMatrix, Segment

from lingaligner import (
    DistanceMatrix,
    FeatureCost,
    LinguisticAligner,
    MatrixCost,
    MissingDataError,
    ParallelCorpus,
    UnsupportedCorpusError,
)

SYMBOLS = ("a", "i", "u", "k", "t", "r")
FEATURES = ("CLOSED", "ROUNDED", "VOICE", "LABIAL")
ROWS = [
    [0.0, 0.0, 1.0, 0.0],
    [1.0, 0.0, 1.0, 0.0],
    [1.0, 1.0, 1.0, 0.0],
    [np.nan, np.nan, 0.0, 1.0],
    [np.nan, np.nan, 0.0, 0.0],
    [np.nan, np.nan, 1.0, 0.0],
]


class FakeInventory:
    """A stand-in for phonfeat's Inventory, with no features by default.

    The aligner only requires the four members of ``InventoryLike``,
    which is the point of the protocol: this object is enough to drive
    every operation.
    """

    def __init__(self, features=None, categories=None, unknown=()):
        self.segments = tuple(
            Segment(symbol=symbol, type="other") for symbol in SYMBOLS
        )
        self.categories = categories or {}
        self.features = features
        self.unknown = set(unknown)

    def tokenize(self, text):
        if any(character in self.unknown for character in text):
            raise ValueError("character outside the inventory")
        return tuple(
            Segment(symbol=character, type="other")
            for character in text
            if not character.isspace()
        )


def features():
    return FeatureMatrix(
        segment_ids=SYMBOLS,
        feature_names=FEATURES,
        data=np.array(ROWS),
    )


@pytest.fixture
def corpus():
    return ParallelCorpus(
        {
            "water": {"A": "kata", "B": "kata"},
            "sun": {"A": "ka", "B": "ta"},
        }
    )


@pytest.fixture
def aligner(corpus):
    return LinguisticAligner(
        corpus=corpus, inventory=FakeInventory(features())
    )


def test_tokenize_uses_the_inventory(aligner):
    segments = aligner.tokenize("kata")
    assert [segment.symbol for segment in segments] == ["k", "a", "t", "a"]


def test_align_returns_an_alignment(aligner):
    alignment = aligner.align("kata", "kata")
    assert not alignment.gapped
    assert len(alignment) == 4


def test_segment_distance(aligner):
    assert aligner.segment_distance("a", "i") == pytest.approx(0.25)


def test_alignment_distance_is_the_mean_column_penalty(aligner):
    """ka against ta: k-t costs 0.75, a-a costs 0."""
    assert aligner.alignment_distance("ka", "ta") == pytest.approx(0.375)


def test_language_distance_averages_over_shared_concepts(aligner):
    """water is identical, sun is 0.375 apart."""
    assert aligner.language_distance("A", "B") == pytest.approx(0.1875)


def test_language_matrix_is_symmetric_and_zero_diagonal(aligner):
    matrix = aligner.language_matrix()
    assert matrix.labels == ("A", "B")
    assert matrix.distance("A", "B") == pytest.approx(0.1875)
    assert matrix.distance("A", "A") == pytest.approx(0.0)


def test_gap_cost_reaches_the_alignment(aligner):
    strict = aligner.alignment_distance("ka", "kata")
    loose = LinguisticAligner(
        corpus=aligner.corpus,
        inventory=aligner.inventory,
        gap_cost=0.5,
    ).alignment_distance("ka", "kata")
    assert loose < strict


def test_the_distance_is_derived_from_the_inventory(aligner):
    assert isinstance(aligner.distance, FeatureCost)
    assert aligner.describe()["distance"]["kind"] == "features"


def test_a_supplied_distance_wins(corpus):
    labels = SYMBOLS
    values = np.zeros((len(labels), len(labels)))
    values[0, 1] = values[1, 0] = 0.5
    aligner = LinguisticAligner(
        corpus=corpus,
        inventory=FakeInventory(),
        distance=MatrixCost(DistanceMatrix(labels=labels, values=values)),
    )
    assert aligner.segment_distance("a", "i") == pytest.approx(0.5)


def test_categories_in_the_inventory_switch_the_mode(corpus):
    inventory = FakeInventory(
        features(), categories={"C": ("k", "t", "r"), "V": ("a", "i", "u")}
    )
    aligner = LinguisticAligner(corpus=corpus, inventory=inventory)
    assert aligner.describe()["distance"]["categories"] == {"C": 3, "V": 3}
    assert aligner.segment_distance("t", "a") == pytest.approx(1.0)


class TestWithoutAFeatureSystem:
    @pytest.fixture
    def aligner(self, corpus):
        return LinguisticAligner(corpus=corpus, inventory=FakeInventory())

    def test_the_distance_is_absent(self, aligner):
        assert aligner.distance is None
        assert aligner.describe()["distance"] is None

    def test_asking_for_a_distance_says_so(self, aligner):
        with pytest.raises(MissingDataError, match="no segment distance"):
            aligner.segment_distance("a", "i")
        with pytest.raises(MissingDataError, match="no segment distance"):
            aligner.alignment_distance("ka", "ta")

    def test_rendering_mentions_the_absence(self, aligner):
        assert "none (no features" in aligner.render()


class TestLanguageRequirements:
    def test_a_corpus_without_languages_is_refused(self):
        aligner = LinguisticAligner(
            corpus=ParallelCorpus({"water": {}, "sun": {}}),
            inventory=FakeInventory(features()),
        )
        with pytest.raises(UnsupportedCorpusError, match="no languages"):
            aligner.language_distance("A", "B")
        with pytest.raises(UnsupportedCorpusError, match="no languages"):
            aligner.language_matrix()

    def test_an_unknown_language_is_named(self, aligner):
        with pytest.raises(MissingDataError, match="unknown language"):
            aligner.language_distance("A", "Z")

    def test_min_shared_is_enforced(self, aligner):
        with pytest.raises(MissingDataError, match="min_shared is 3"):
            aligner.language_distance("A", "B", min_shared=3)

    def test_an_empty_form_is_refused(self):
        aligner = LinguisticAligner(
            corpus=ParallelCorpus({"sun": {"A": "", "B": "ka"}}),
            inventory=FakeInventory(features()),
        )
        with pytest.raises(MissingDataError, match="no segments"):
            aligner.language_distance("A", "B")


class TestExploration:
    def test_describe_counts_forms(self, aligner):
        described = aligner.describe()
        assert described["forms"] == 4
        assert described["tokenized"] == 4
        assert described["failed"] == 0
        assert described["concepts"] == 2
        assert described["languages"] == 2

    def test_describe_reports_coverage_and_overlap(self, aligner):
        described = aligner.describe()
        assert described["coverage"] == {"A": 1.0, "B": 1.0}
        assert described["shared_concepts"] == {"A | B": 2}

    def test_describe_reports_the_inventory(self, aligner):
        described = aligner.describe()
        assert described["inventory"]["segments"] == 6
        assert described["inventory"]["features"] == 4

    def test_an_untokenizable_form_is_reported_not_raised(self):
        aligner = LinguisticAligner(
            corpus=ParallelCorpus({"sun": {"A": "ka#", "B": "ka"}}),
            inventory=FakeInventory(features(), unknown={"#"}),
        )
        described = aligner.describe()
        assert described["failed"] == 1
        assert described["failures"][0]["language"] == "A"
        assert "ValueError" in described["failures"][0]["error"]

    def test_the_failure_list_is_capped(self):
        forms = {
            f"c{n}": {"A": "ka#", "B": "ka"} for n in range(15)
        }
        aligner = LinguisticAligner(
            corpus=ParallelCorpus(forms),
            inventory=FakeInventory(features(), unknown={"#"}),
        )
        described = aligner.describe()
        assert len(described["failures"]) == 10
        assert described["failures_truncated"] == 5

    def test_render_is_readable(self, aligner):
        text = aligner.render()
        assert "corpus" in text
        assert "features, unified" in text
        assert "gap cost    1.0" in text


def test_the_aligner_is_immutable(aligner):
    with pytest.raises(AttributeError):
        aligner.gap_cost = 0.5
