"""What the aligner needs to know about an inventory.

The aligner does not own inventory data and does not load it. It needs
four things from whatever object represents an inventory, and those
four are declared here as a protocol so that ``phonfeat`` can supply
the real implementation without this package importing it.

``phonfeat`` owns notation, tokenization and feature systems. Its
``Inventory`` is expected to satisfy this protocol; nothing in
lingaligner duplicates it.

Why a protocol rather than a base class: the dependency stays
``lingaligner -> (protocol) <- phonfeat``, so lingaligner keeps working
with an inventory built elsewhere -- a test double, a hand-written
object, or a future generator that derives the inventory from a corpus.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from lingcore import FeatureMatrix, Segment

__all__ = ["InventoryLike"]


class InventoryLike(Protocol):
    """The inventory surface the aligner depends on.

    The members are read-only, so a plain attribute satisfies them. No
    inheritance is required or expected.
    """

    @property
    def segments(self) -> Sequence[Segment]:
        """The segments the inventory holds.

        Used for size and reporting; the distance works from
        ``features``.
        """
        ...

    @property
    def categories(self) -> Mapping[str, tuple[str, ...]]:
        """``{category_name: symbols}``, or empty for a single inventory.

        A corpus keyed by category lets the distance apply a
        cross-category cost instead of comparing feature by feature.
        """
        ...

    @property
    def features(self) -> FeatureMatrix | None:
        """Segments by features, or ``None`` when there are no features.

        Without features the aligner cannot build a distance of its
        own, and the caller must supply one.
        """
        ...

    def tokenize(self, text: str) -> Sequence[Segment]:
        """Split one written form into segments."""
        ...
