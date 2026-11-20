"""The corpus stores forms and nothing else."""

from __future__ import annotations

import pytest

from lingaligner import ParallelCorpus

FORMS = {
    "water": {"A": "kata", "B": "kja"},
    "sun": {"A": "to", "B": "to"},
    "moon": {"A": "ni"},
}


@pytest.fixture
def corpus():
    return ParallelCorpus(FORMS)


def test_languages_follow_first_appearance(corpus):
    assert corpus.languages == ("A", "B")
    assert corpus.concepts == ("water", "sun", "moon")


def test_has_languages(corpus):
    assert corpus.has_languages
    assert not ParallelCorpus({"water": {}}).has_languages


def test_forms_are_returned_as_written(corpus):
    assert corpus.form("water", "A") == "kata"
    assert corpus.form("moon", "B") is None
    assert corpus.form("nothing", "A") is None


def test_shared_concepts(corpus):
    assert corpus.shared("A", "B") == ("water", "sun")


def test_missing_concepts(corpus):
    assert corpus.missing("A") == ()
    assert corpus.missing("B") == ("moon",)


def test_counts_and_coverage(corpus):
    assert corpus.counts() == {"A": 3, "B": 2}
    assert corpus.coverage()["A"] == pytest.approx(1.0)
    assert corpus.coverage()["B"] == pytest.approx(2 / 3)


def test_shared_counts_make_thin_samples_visible(corpus):
    assert corpus.shared_counts() == {("A", "B"): 2}


def test_the_corpus_is_immutable(corpus):
    with pytest.raises(TypeError):
        corpus.forms["water"]["A"] = "kat"
    with pytest.raises(TypeError):
        corpus.forms["new"] = {}
    with pytest.raises(AttributeError):
        corpus.forms = {}


def test_a_form_must_be_a_string():
    with pytest.raises(TypeError, match="must be a string"):
        ParallelCorpus({"water": {"A": ["k", "a"]}})


def test_an_empty_corpus_is_allowed():
    corpus = ParallelCorpus({})
    assert len(corpus) == 0
    assert corpus.languages == ()
    assert corpus.coverage() == {}


def test_an_unknown_language_translates_nothing(corpus):
    assert corpus.missing("Z") == corpus.concepts
