"""The object a user holds: corpus, inventory and distance, wired.

A ``LinguisticAligner`` is a thin facade. It owns three decisions --
which corpus, which inventory, which segment distance -- and exposes
the operations that follow from them, from tokenizing one string to
computing a matrix of language distances.

It owns no data and no algorithm of its own: the corpus holds the
forms, the inventory holds the notation and the features, the distance
object holds the arithmetic, and ``align`` holds the alignment. Adding
a second kind of corpus or a second kind of distance means adding a
class, not editing this one.

Every number it produces is reproducible from the parameters reported
by :meth:`describe`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .align import Alignment
from .align import align as align_sequences
from .corpus import ParallelCorpus
from .cost import Cost, validate_cost
from .distance import FeatureCost, SegmentCost
from .errors import MissingDataError, UnsupportedCorpusError
from .inventory import InventoryLike
from .matrix import DistanceMatrix

__all__ = ["LinguisticAligner"]

_MAX_FAILURES = 10


@dataclass(frozen=True, slots=True)
class LinguisticAligner:
    """A corpus, an inventory and a distance, ready to be asked things.

    Parameters
    ----------
    corpus : ParallelCorpus
        The forms, as written.
    inventory : InventoryLike
        Segments, optional categories, optional features, and the
        tokenizer. ``phonfeat`` supplies this.
    distance : SegmentCost, optional
        How two segments are compared. When omitted, a
        :class:`FeatureCost` is built from the inventory's features --
        partitioned if the inventory declares categories, unified
        otherwise -- and stored in this same attribute. When the
        inventory has no features and no distance is given, the distance
        methods say so instead of guessing.
    gap_cost : float, optional
        Cost of a gap column, in ``[0, 1]``. Defaults to 1, the
        convention of the original study: a gap is free to place and as
        expensive as a maximal substitution.

    Notes
    -----
    Instances are immutable. Exploration reports; it never edits the
    corpus or the inventory.
    """

    corpus: ParallelCorpus
    inventory: InventoryLike
    distance: SegmentCost | None = None
    gap_cost: float = 1.0

    _segment_cost: Cost | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        validate_cost(self.gap_cost, name="gap_cost")
        if self.distance is None:
            features = self.inventory.features
            if features is not None:
                object.__setattr__(
                    self,
                    "distance",
                    FeatureCost(
                        matrix=features,
                        categories=self.inventory.categories or None,
                    ),
                )
        if self.distance is not None:
            cost = self.distance.cost

            def on_segments(segment_a, segment_b):
                return cost(segment_a.symbol, segment_b.symbol)

            object.__setattr__(self, "_segment_cost", on_segments)

    # -- notation ---------------------------------------------------

    def tokenize(self, text: str) -> tuple[Any, ...]:
        """Tokenize one written form with the inventory's tokenizer.

        Parameters
        ----------
        text : str
            A form as written.

        Returns
        -------
        tuple of lingcore.Segment
            The segments, in order.
        """
        return tuple(self.inventory.tokenize(text))

    # -- distances on segments and on terms -------------------------

    def segment_distance(self, symbol_a: str, symbol_b: str) -> float:
        """Return the distance between two segment symbols.

        Parameters
        ----------
        symbol_a, symbol_b : str
            Symbols as the inventory writes them.

        Returns
        -------
        float
            A dissimilarity in ``[0, 1]``.
        """
        return self._require_distance().cost(symbol_a, symbol_b)

    def align(self, form_a: str, form_b: str) -> Alignment:
        """Tokenize two forms and align them.

        Parameters
        ----------
        form_a, form_b : str
            Two forms as written.

        Returns
        -------
        Alignment
            Segments aligned column by column, gaps as ``None``.
        """
        return align_sequences(
            self.tokenize(form_a),
            self.tokenize(form_b),
            self._require_cost(),
            gap_cost=self.gap_cost,
        )

    def alignment_distance(self, form_a: str, form_b: str) -> float:
        """Return the mean column penalty of two forms' alignment."""
        return self.align(form_a, form_b).distance(self._require_cost())

    # -- distances between languages --------------------------------

    def language_distance(
        self,
        language_a: str,
        language_b: str,
        *,
        min_shared: int = 1,
    ) -> float:
        """Return the mean term distance between two languages.

        Parameters
        ----------
        language_a, language_b : str
            Language labels present in the corpus.
        min_shared : int, optional
            The smallest number of shared concepts to accept. Defaults
            to 1; raise it to refuse pairs whose mean would rest on too
            small a sample.

        Returns
        -------
        float
            The mean over shared concepts, in ``[0, 1]``.

        Raises
        ------
        UnsupportedCorpusError
            If the corpus is not indexed by language.
        MissingDataError
            If the pair shares fewer than ``min_shared`` concepts, if a
            language is unknown, or if a shared form tokenizes to no
            segments.
        """
        self._require_languages(language_a, language_b)
        shared = self.corpus.shared(language_a, language_b)
        if len(shared) < min_shared:
            raise MissingDataError(
                f"{language_a!r} and {language_b!r} share "
                f"{len(shared)} concept(s); min_shared is {min_shared}"
            )
        total = 0.0
        for concept in shared:
            total += self._concept_distance(concept, language_a, language_b)
        return total / len(shared)

    def language_matrix(self, *, min_shared: int = 1) -> DistanceMatrix:
        """Return the full matrix of language distances.

        Parameters
        ----------
        min_shared : int, optional
            The smallest number of shared concepts to accept.

        Returns
        -------
        DistanceMatrix
            Symmetric, zero-diagonal, labelled with the languages.

        Raises
        ------
        UnsupportedCorpusError
            If the corpus is not indexed by language.
        MissingDataError
            If any pair shares fewer than ``min_shared`` concepts.
        """
        languages = self.corpus.languages
        if not languages:
            raise UnsupportedCorpusError(
                "this corpus has no languages; a language distance "
                "needs a corpus indexed by language"
            )
        values = np.zeros((len(languages), len(languages)), dtype=float)
        for i, language_a in enumerate(languages):
            for j in range(i + 1, len(languages)):
                language_b = languages[j]
                distance = self.language_distance(
                    language_a, language_b, min_shared=min_shared
                )
                values[i, j] = distance
                values[j, i] = distance
        return DistanceMatrix(labels=languages, values=values)

    # -- exploration ------------------------------------------------

    def describe(self) -> dict[str, Any]:
        """Return what this aligner holds and what its numbers mean.

        Returns
        -------
        dict
            Corpus size and coverage, the tokenization result over
            every form, the inventory's shape, and the distance's
            parameters. Failures are listed with examples rather than
            raised, because exploring a corpus should not stop at the
            first bad cell.
        """
        concepts = self.corpus.concepts
        languages = self.corpus.languages
        failures: list[dict[str, str]] = []
        tokenized = 0
        total = 0
        for concept in concepts:
            for language in languages:
                form = self.corpus.form(concept, language)
                if form is None:
                    continue
                total += 1
                try:
                    if self.tokenize(form):
                        tokenized += 1
                    else:
                        raise ValueError("no segments")
                except Exception as error:  # diagnostic scan, not control
                    if len(failures) < _MAX_FAILURES:
                        failures.append(
                            {
                                "concept": concept,
                                "language": language,
                                "form": form,
                                "error": f"{type(error).__name__}: {error}",
                            }
                        )
        inventory: dict[str, Any] = {
            "segments": len(self.inventory.segments),
            "categories": {
                name: len(symbols)
                for name, symbols in self.inventory.categories.items()
            },
            "features": (
                len(self.inventory.features.feature_names)
                if self.inventory.features is not None
                else None
            ),
        }
        return {
            "concepts": len(concepts),
            "languages": len(languages),
            "coverage": self.corpus.coverage(),
            "shared_concepts": {
                f"{a} | {b}": count
                for (a, b), count in self.corpus.shared_counts().items()
            },
            "forms": total,
            "tokenized": tokenized,
            "failed": total - tokenized,
            "failures": failures,
            "failures_truncated": max(0, total - tokenized - len(failures)),
            "inventory": inventory,
            "distance": (
                self.distance.describe() if self.distance is not None else None
            ),
            "gap_cost": self.gap_cost,
        }

    def render(self) -> str:
        """Return :meth:`describe` as a short readable report."""
        report = self.describe()
        lines = [
            f"corpus      {report['concepts']} concepts, "
            f"{report['languages']} languages, {report['forms']} forms",
            f"tokenized   {report['tokenized']} of {report['forms']}"
            f" ({report['failed']} failed)",
        ]
        inventory = report["inventory"]
        categories = inventory["categories"]
        shape = f"{inventory['segments']} segments"
        if categories:
            shape += ", " + ", ".join(
                f"{name} {count}" for name, count in categories.items()
            )
        if inventory["features"] is not None:
            shape += f", {inventory['features']} features"
        lines.append(f"inventory   {shape}")
        distance = report["distance"]
        if distance is None:
            lines.append("distance    none (no features, none supplied)")
        elif distance["kind"] == "features":
            mode = "partitioned" if distance["categories"] else "unified"
            lines.append(
                f"distance    features, {mode}, "
                f"{distance['features']} columns, "
                f"{distance['undefined_cells']} undefined cells"
            )
        else:
            lines.append(
                f"distance    matrix, {distance['segments']} segments"
            )
        lines.append(f"gap cost    {report['gap_cost']}")
        for failure in report["failures"]:
            lines.append(
                f"  ! {failure['concept']}/{failure['language']} "
                f"{failure['form']!r}: {failure['error']}"
            )
        truncated = report["failures_truncated"]
        if truncated:
            lines.append(f"  ! ... {truncated} more failures")
        return "\n".join(lines)

    # -- internals --------------------------------------------------

    def _concept_distance(
        self,
        concept: str,
        language_a: str,
        language_b: str,
    ) -> float:
        form_a = self.corpus.form(concept, language_a)
        form_b = self.corpus.form(concept, language_b)
        if form_a is None or form_b is None:  # pragma: no cover
            raise MissingDataError(
                f"{concept!r} is not present in both languages"
            )
        if not self.tokenize(form_a) or not self.tokenize(form_b):
            raise MissingDataError(
                f"{concept!r}: a form tokenizes to no segments "
                f"({language_a}={form_a!r}, {language_b}={form_b!r})"
            )
        return self.alignment_distance(form_a, form_b)

    def _require_languages(self, language_a: str, language_b: str) -> None:
        if not self.corpus.has_languages:
            raise UnsupportedCorpusError(
                "this corpus has no languages; a language distance "
                "needs a corpus indexed by language"
            )
        known = self.corpus.languages
        for language in (language_a, language_b):
            if language not in known:
                raise MissingDataError(
                    f"unknown language {language!r}; this corpus has "
                    f"{list(known)}"
                )

    def _require_distance(self) -> SegmentCost:
        if self.distance is None:
            raise MissingDataError(
                "no segment distance: the inventory has no features and "
                "none was supplied"
            )
        return self.distance

    def _require_cost(self) -> Cost:
        cost = self._segment_cost
        if cost is None:
            raise MissingDataError(
                "no segment distance: the inventory has no features and "
                "none was supplied"
            )
        return cost
