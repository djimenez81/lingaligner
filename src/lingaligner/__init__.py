"""Sequence alignment and distance matrices for comparative linguistics.

The package answers one question: given that two forms mean the same
thing, how different are they? It answers it in layers, and every layer
is usable on its own.

    align              sequences + a cost -> an Alignment
    Alignment          -> the mean column penalty (a term distance)
    ParallelCorpus     -> the forms, and questions about the forms
    distance           -> segment -> segment, from features or a matrix
    LinguisticAligner  -> corpus + inventory + distance, wired

Nothing in the bottom layer knows about phonology. An alignment needs a
sequence and a cost, so the same code aligns DNA, syllables or
orthographic tokens, and ``tests/test_generality.py`` does exactly
that. The phonological layer is assembled from a tokenizer and a
feature cost, both supplied by ``phonfeat`` through the
:class:`InventoryLike` protocol rather than imported from here.

Public API
----------
align, align_all, Alignment
    Global alignment over any sequence, all optimal alignments.
Cost, exact_cost, validate_cost
    The shape of a cost function, and the simplest one.
SegmentCost, FeatureCost, MatrixCost
    Distances between segments, with the parameters that produced them.
InventoryLike
    The four things the aligner needs from an inventory.
ParallelCorpus
    ``{concept: {language: form}}``, with coverage and shared counts.
LinguisticAligner
    The object a user holds: tokenize, align, segment distance, term
    distance, language distance, language matrix, describe.

Parameters that used to be constants
------------------------------------
Nothing here reads a file, knows a language name, or ships a corpus or
a feature table. The corpus, the inventory, the distance and the gap
cost all arrive as arguments, and ``LinguisticAligner.describe``
reports every one of them next to the numbers they produced.
"""

from __future__ import annotations

from .align import Alignment, align, align_all
from .aligner import LinguisticAligner
from .corpus import ParallelCorpus
from .cost import Cost, exact_cost, validate_cost
from .distance import FeatureCost, MatrixCost, SegmentCost
from .errors import (
    AlignmentLimitError,
    DistanceMatrixError,
    EmptyAlignmentError,
    LingalignerError,
    MissingDataError,
    MissingSegmentError,
    UnsupportedCorpusError,
)
from .inventory import InventoryLike
from .matrix import DistanceMatrix

__all__ = [
    "Alignment",
    "AlignmentLimitError",
    "Cost",
    "DistanceMatrix",
    "DistanceMatrixError",
    "EmptyAlignmentError",
    "FeatureCost",
    "InventoryLike",
    "LingalignerError",
    "LinguisticAligner",
    "MatrixCost",
    "MissingDataError",
    "MissingSegmentError",
    "ParallelCorpus",
    "SegmentCost",
    "UnsupportedCorpusError",
    "align",
    "align_all",
    "exact_cost",
    "validate_cost",
]
