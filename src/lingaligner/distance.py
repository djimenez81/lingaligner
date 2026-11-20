"""Segment distances: what it costs to read one segment as another.

``phonfeat`` supplies inventory data; the arithmetic lives here. Two
sources are supported: a feature matrix, and a matrix of distances that
was computed elsewhere.

A distance object is a pair of things the aligner needs together: a
``cost`` in ``[0, 1]``, and a ``describe`` that reports the parameters
that produced it. A number without its parameters cannot be checked
later, so the two travel in the same object.

Two feature modes, decided by the inventory rather than by a flag:

- **Unified** (``categories`` empty): every feature applies to every
  segment. An undefined cell is a disagreement with everything,
  including another undefined cell, and the denominator is the number
  of features. A feature that does not apply to a class therefore
  charges a constant floor to comparisons across classes.
- **Partitioned** (``categories`` given): segments in different
  categories cost ``cross_class_cost``, default 1.0, and are never
  compared feature by feature. Segments in the same category are
  compared exactly as in the unified mode.

The difference is visible and measurable: on a table with five
vowel-only features, the unified mode gives a vowel-to-consonant pair a
floor of 5/16 rather than the flat 1.0 of the partitioned mode.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

import numpy as np
from lingcore import FeatureMatrix

from .cost import validate_cost
from .errors import MissingSegmentError
from .matrix import DistanceMatrix

__all__ = ["FeatureCost", "MatrixCost", "SegmentCost"]


class SegmentCost(Protocol):
    """A segment distance that can explain itself."""

    def cost(self, symbol_a: str, symbol_b: str) -> float:
        """Return the dissimilarity of two segment symbols, in [0, 1]."""
        ...

    def describe(self) -> dict[str, object]:
        """Return the parameters that produced the cost."""
        ...


@dataclass(frozen=True, slots=True)
class FeatureCost:
    """Distance from a feature matrix: the fraction of differing rows.

    Parameters
    ----------
    matrix : lingcore.FeatureMatrix
        Rows are segment symbols, columns are features, cells are
        floats, and ``NaN`` marks an undefined value.
    categories : mapping, optional
        ``{category_name: symbols}``. Empty or ``None`` means a single
        undivided inventory. When given, every symbol in the matrix
        must belong to exactly one category; an unclassified symbol is
        refused at construction, because a distance that quietly
        guessed the class would be unfalsifiable.
    cross_class_cost : float, optional
        Cost of comparing two segments from different categories.
        Defaults to 1.0.

    Notes
    -----
    Two identical symbols always cost 0, whatever their row holds. The
    shortcut is required: since an undefined cell disagrees with
    everything, a segment with an undefined cell would otherwise
    disagree with itself.
    """

    matrix: FeatureMatrix
    categories: Mapping[str, tuple[str, ...]] | None = None
    cross_class_cost: float = 1.0

    _index: dict[str, int] = field(
        init=False, repr=False, default_factory=dict
    )
    _category_of: dict[str, str] = field(
        init=False, repr=False, default_factory=dict
    )
    _width: int = field(init=False, repr=False, default=0)

    def __post_init__(self) -> None:
        if not self.matrix.feature_names:
            raise ValueError("the feature matrix has no feature columns")
        width = self.matrix.data.shape[1]
        index = {
            symbol: row
            for row, symbol in enumerate(self.matrix.segment_ids)
        }
        category_of: dict[str, str] = {}
        categories: Mapping[str, tuple[str, ...]] | None = self.categories
        if categories:
            frozen = {}
            for name, symbols in categories.items():
                frozen[name] = tuple(symbols)
                for symbol in symbols:
                    if symbol not in index:
                        raise MissingSegmentError(
                            f"category {name!r} lists {symbol!r}, which "
                            "is not a row of the feature matrix"
                        )
                    if symbol in category_of:
                        raise ValueError(
                            f"{symbol!r} is listed in both "
                            f"{category_of[symbol]!r} and {name!r}"
                        )
                    category_of[symbol] = name
            unclassified = sorted(set(index) - set(category_of))
            if unclassified:
                raise ValueError(
                    "categories are given but these symbols are not in "
                    f"any of them: {unclassified}"
                )
            categories = MappingProxyType(frozen)
        else:
            categories = None
        object.__setattr__(self, "categories", categories)
        object.__setattr__(self, "_index", index)
        object.__setattr__(self, "_category_of", category_of)
        object.__setattr__(self, "_width", width)
        validate_cost(self.cross_class_cost, name="cross_class_cost")

    def cost(self, symbol_a: str, symbol_b: str) -> float:
        """Return the fraction of features on which two rows disagree.

        Parameters
        ----------
        symbol_a, symbol_b : str
            Segment symbols present in the matrix.

        Returns
        -------
        float
            A dissimilarity in ``[0, 1]``.

        Raises
        ------
        MissingSegmentError
            If a symbol is not a row of the matrix.
        """
        if symbol_a == symbol_b:
            return 0.0
        if self.categories:
            if self._category_of[symbol_a] != self._category_of[symbol_b]:
                return self.cross_class_cost
        row_a = self._row(symbol_a)
        row_b = self._row(symbol_b)
        return int(np.count_nonzero(~(row_a == row_b))) / self._width

    def describe(self) -> dict[str, object]:
        """Return the parameters of this distance."""
        return {
            "kind": "features",
            "features": len(self.matrix.feature_names),
            "segments": len(self.matrix.segment_ids),
            "undefined_cells": int(np.isnan(self.matrix.data).sum()),
            "categories": (
                {
                    name: len(symbols)
                    for name, symbols in self.categories.items()
                }
                if self.categories
                else None
            ),
            "cross_class_cost": self.cross_class_cost,
        }

    def _row(self, symbol: str) -> np.ndarray:
        try:
            return self.matrix.data[self._index[symbol]]
        except KeyError:
            raise MissingSegmentError(
                f"segment {symbol!r} is not in the feature matrix"
            ) from None


@dataclass(frozen=True, slots=True)
class MatrixCost:
    """Distance read from a matrix computed elsewhere.

    Parameters
    ----------
    matrix : DistanceMatrix
        A labelled, symmetric, zero-diagonal matrix whose labels are
        segment symbols. Useful when the segment distances come from a
        source this package does not model -- a published table, a
        fitted model, or a study that predates the inventory.
    """

    matrix: DistanceMatrix

    def cost(self, symbol_a: str, symbol_b: str) -> float:
        """Return the stored distance between two symbols.

        Raises
        ------
        MissingSegmentError
            If a symbol is not a label of the matrix.
        """
        try:
            return self.matrix.distance(symbol_a, symbol_b)
        except Exception as error:
            raise MissingSegmentError(
                f"{error}; the matrix labels are {self.matrix.labels}"
            ) from None

    def describe(self) -> dict[str, object]:
        """Return the parameters of this distance."""
        return {"kind": "matrix", "segments": len(self.matrix)}
