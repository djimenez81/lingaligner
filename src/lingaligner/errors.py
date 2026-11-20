"""Exceptions raised by lingaligner.

All lingaligner exceptions inherit from :class:`LingalignerError`, so
callers can catch the whole family with one except clause.
"""

from __future__ import annotations

__all__ = [
    "AlignmentLimitError",
    "DistanceMatrixError",
    "EmptyAlignmentError",
    "LingalignerError",
    "MissingDataError",
    "MissingSegmentError",
    "UnsupportedCorpusError",
]


class LingalignerError(Exception):
    """Base class for all lingaligner exceptions."""


class EmptyAlignmentError(LingalignerError):
    """Raised when a distance is asked of an alignment with no columns."""


class AlignmentLimitError(LingalignerError):
    """Raised when more optimal alignments exist than were asked for."""


class MissingSegmentError(LingalignerError):
    """Raised when a symbol has no entry in the inventory or matrix."""


class MissingDataError(LingalignerError):
    """Raised when there is too little data to answer a question."""


class UnsupportedCorpusError(LingalignerError):
    """Raised when an operation needs something the corpus does not have.

    A language distance needs a corpus indexed by language. A corpus of
    cognate sets has no languages, and asking it for a language
    distance is a category error rather than missing data.
    """


class DistanceMatrixError(LingalignerError):
    """Raised when a matrix is not square, symmetric or zero-diagonal."""
