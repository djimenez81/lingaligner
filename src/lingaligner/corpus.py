"""Parallel word lists: concepts by languages.

A Swadesh-style corpus is a table in which a concept is given a form in
each language, and real tables are incomplete. This class stores that
table and answers questions about it.

It stores **the forms as written**, not tokens. A corpus can therefore
be built before any inventory exists, and changing a tokenizer or an
orthographic profile does not require rebuilding it. Tokenizing is the
inventory's job and comparing is the aligner's; neither belongs here.

Nothing here reads a file. A spreadsheet or a JSON dump becomes a
corpus through whatever code the caller writes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

__all__ = ["ParallelCorpus"]


@dataclass(frozen=True, slots=True)
class ParallelCorpus:
    """Forms answering the same concepts in several languages.

    Parameters
    ----------
    forms : mapping
        ``{concept: {language: form}}``, with forms as written. A
        language missing for a concept is a missing form, not an
        error: real word lists are incomplete, and the gaps are part of
        what the corpus has to say.

    Notes
    -----
    Instances are immutable. The nested mappings are copied into
    read-only views at construction, so exploring the corpus cannot
    alter it.

    Concept order is the order given, and language order is the order
    in which languages first appear, so that output is reproducible.
    """

    forms: Mapping[str, Mapping[str, str]]

    def __post_init__(self) -> None:
        frozen = {}
        for concept, by_language in self.forms.items():
            values = {}
            for language, form in by_language.items():
                if not isinstance(form, str):
                    raise TypeError(
                        f"form for {concept!r}/{language!r} must be a "
                        f"string; got {type(form).__name__}"
                    )
                values[language] = form
            frozen[concept] = MappingProxyType(values)
        object.__setattr__(self, "forms", MappingProxyType(frozen))

    def __len__(self) -> int:
        return len(self.forms)

    @property
    def concepts(self) -> tuple[str, ...]:
        """The concepts, in the order given."""
        return tuple(self.forms)

    @property
    def languages(self) -> tuple[str, ...]:
        """The languages, in the order they first appear."""
        seen: dict[str, None] = {}
        for by_language in self.forms.values():
            for language in by_language:
                seen.setdefault(language, None)
        return tuple(seen)

    @property
    def has_languages(self) -> bool:
        """Whether this corpus is indexed by language.

        A language distance needs this. A corpus of cognate sets, or of
        a single word list, has no such index, and that is a property
        of the data rather than a missing feature.
        """
        return bool(self.languages)

    def form(self, concept: str, language: str) -> str | None:
        """Return one form as written, or ``None`` when it is missing."""
        return self.forms.get(concept, {}).get(language)

    def missing(self, language: str) -> tuple[str, ...]:
        """Return the concepts a language does not translate.

        Parameters
        ----------
        language : str
            A language label.

        Returns
        -------
        tuple of str
            Concepts with no form for that language, in corpus order.
        """
        return tuple(
            concept
            for concept, by_language in self.forms.items()
            if language not in by_language
        )

    def shared(self, language_a: str, language_b: str) -> tuple[str, ...]:
        """Return the concepts both languages translate.

        Parameters
        ----------
        language_a, language_b : str
            Two language labels.

        Returns
        -------
        tuple of str
            Concepts present for both, in corpus order.
        """
        return tuple(
            concept
            for concept, by_language in self.forms.items()
            if language_a in by_language and language_b in by_language
        )

    def counts(self) -> dict[str, int]:
        """Return how many concepts each language translates.

        Returns
        -------
        dict
            ``{language: number_of_forms}``.
        """
        counts = dict.fromkeys(self.languages, 0)
        for by_language in self.forms.values():
            for language in by_language:
                counts[language] += 1
        return counts

    def coverage(self) -> dict[str, float]:
        """Return the fraction of concepts each language translates.

        Returns
        -------
        dict
            ``{language: fraction}``, in ``[0, 1]``.
        """
        total = len(self.forms) or 1
        return {
            language: number / total
            for language, number in self.counts().items()
        }

    def shared_counts(self) -> dict[tuple[str, str], int]:
        """Return how many concepts each pair of languages shares.

        A language distance is a mean over shared concepts, so a pair
        sharing few concepts has a mean over a small sample. This table
        makes that visible before the distance is trusted.

        Returns
        -------
        dict
            ``{(language_a, language_b): shared_concepts}`` for every
            unordered pair, in corpus order.
        """
        languages = self.languages
        counts = {}
        for i, language_a in enumerate(languages):
            for language_b in languages[i + 1 :]:
                counts[(language_a, language_b)] = len(
                    self.shared(language_a, language_b)
                )
        return counts
