"""Pairwise alignment over any alphabet.

Alignment needs a sequence of items and a cost on pairs of items. It
knows nothing about phonology: DNA, syllables and orthographic tokens
use the same code, and the phonological case is one client among many.

The score follows the convention the Chibchan study used, generalised.
A column with two items earns ``1 - cost``; a column with one item and
a gap earns ``1 - gap_cost``. Costs live in ``[0, 1]``, so the default
``gap_cost=1`` makes a gap free to place and exactly as expensive as
swapping two maximally different items. The distance view is the same
number from the other side: ``penalty = 1 - weight``.

Lowering ``gap_cost`` makes gaps cheaper than substitutions. One
substitution stands opposite *two* gap columns, because a diagonal step
consumes two items and a gap consumes one, so a substitution of cost
``c`` is preferred only while ``c < 2 * gap_cost - 1``. At
``gap_cost=0.5`` the two sides tie, and below that no substitution can
ever win: every alignment degenerates into gaps. ``gap_cost=0.9`` means
gaps win only once two items are more than 80% different.

Ties are broken in the order diagonal, then left, then up, which is the
order the original study used: a substitution is preferred to an
equally weighted gap.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import numpy as np

from .cost import Cost, validate_cost
from .errors import AlignmentLimitError, EmptyAlignmentError

__all__ = ["Alignment", "align", "align_all"]

_TOLERANCE = 1e-12


@dataclass(frozen=True, slots=True)
class Alignment[Item]:
    """Two sequences aligned column by column.

    Attributes
    ----------
    sequence_a, sequence_b : tuple
        The aligned sequences. ``None`` marks a gap, so both have the
        same length by construction.
    score : float
        The alignment score: the sum of the weights of every column.
    gap_cost : float
        The cost a gap was charged, kept so that :meth:`distance` does
        not need it passed again.

    Notes
    -----
    Instances are immutable and compare by value.
    """

    sequence_a: tuple[Item | None, ...]
    sequence_b: tuple[Item | None, ...]
    score: float
    gap_cost: float = 1.0

    def __post_init__(self) -> None:
        if len(self.sequence_a) != len(self.sequence_b):
            raise ValueError(
                "aligned sequences must have the same length; got "
                f"{len(self.sequence_a)} and {len(self.sequence_b)}"
            )

    def __len__(self) -> int:
        return len(self.sequence_a)

    def columns(self) -> Iterator[tuple[Item | None, Item | None]]:
        """Yield the columns as ``(item_a, item_b)`` pairs."""
        yield from zip(self.sequence_a, self.sequence_b, strict=True)

    @property
    def gapped(self) -> bool:
        """Whether any column holds a gap."""
        return any(
            item_a is None or item_b is None
            for item_a, item_b in self.columns()
        )

    @property
    def identities(self) -> int:
        """The number of columns where both items are present and equal."""
        return sum(
            1
            for item_a, item_b in self.columns()
            if item_a is not None and item_a == item_b
        )

    def distance(self, cost: Cost[Item]) -> float:
        """Return the mean column penalty of this alignment.

        A gap column is charged ``gap_cost``, which is the dual of the
        weight it earned: ``penalty = 1 - weight``.

        Parameters
        ----------
        cost : callable
            The substitution cost used for columns holding two items.

        Returns
        -------
        float
            The mean penalty over all columns, in ``[0, 1]``.

        Raises
        ------
        EmptyAlignmentError
            If the alignment has no columns.
        """
        if not len(self):
            raise EmptyAlignmentError(
                "cannot take the distance of an alignment with no columns"
            )
        total = 0.0
        for item_a, item_b in self.columns():
            if item_a is None or item_b is None:
                total += self.gap_cost
            else:
                total += cost(item_a, item_b)
        return total / len(self)


def align[Item](
    sequence_a: Sequence[Item],
    sequence_b: Sequence[Item],
    cost: Cost[Item],
    *,
    gap_cost: float = 1.0,
) -> Alignment[Item]:
    """Align two sequences end to end, maximising the score.

    This is the Needleman-Wunsch recurrence with a graded substitution
    score: a match earns ``1 - cost`` rather than a flat 1, so two
    similar items are worth more than two different ones.

    Parameters
    ----------
    sequence_a, sequence_b : sequence
        The items to align, in order.
    cost : callable
        Dissimilarity of two items, in ``[0, 1]``.
    gap_cost : float, optional
        Cost of a gap column, in ``[0, 1]``. Defaults to 1, which makes
        a gap free to place and as expensive as a maximal substitution.

    Returns
    -------
    Alignment
        The highest-scoring alignment. When several score equally, the
        one reached by preferring diagonal steps is returned.
    """
    gap_cost = validate_cost(gap_cost, name="gap_cost")
    weights = _match_weights(sequence_a, sequence_b, cost)
    scores = _score_table(weights, gap_cost)
    steps = _trace(scores, weights, 1.0 - gap_cost)
    return _build(sequence_a, sequence_b, steps, scores[-1, -1], gap_cost)


def align_all[Item](
    sequence_a: Sequence[Item],
    sequence_b: Sequence[Item],
    cost: Cost[Item],
    *,
    gap_cost: float = 1.0,
    limit: int = 256,
) -> tuple[Alignment[Item], ...]:
    """Return every optimal alignment, up to ``limit``.

    Two alignments with the same score can still have different
    distances, because the distance is a mean and the number of columns
    differs when the number of matched pairs differs. Enumerating the
    ties is what makes the choice explicit instead of accidental.

    Parameters
    ----------
    sequence_a, sequence_b : sequence
        The items to align, in order.
    cost : callable
        Dissimilarity of two items, in ``[0, 1]``.
    gap_cost : float, optional
        Cost of a gap column. Defaults to 1.
    limit : int, optional
        The largest number of alignments to return. Defaults to 256.

    Returns
    -------
    tuple of Alignment
        Every optimal alignment, in a deterministic order: at each
        backtracking step the diagonal successor is explored first.

    Raises
    ------
    AlignmentLimitError
        If more than ``limit`` optimal alignments exist. Raise the
        limit rather than accept a truncated answer.
    """
    gap_cost = validate_cost(gap_cost, name="gap_cost")
    weights = _match_weights(sequence_a, sequence_b, cost)
    scores = _score_table(weights, gap_cost)
    gap_weight = 1.0 - gap_cost
    found: list[tuple[tuple[int, int, int, int], ...]] = []
    _walk(
        scores,
        weights,
        gap_weight,
        len(sequence_a),
        len(sequence_b),
        [],
        found,
        limit,
    )
    return tuple(
        _build(sequence_a, sequence_b, steps, scores[-1, -1], gap_cost)
        for steps in found
    )


def _match_weights[Item](
    sequence_a: Sequence[Item],
    sequence_b: Sequence[Item],
    cost: Cost[Item],
) -> np.ndarray:
    """Return the weight of matching each pair of items."""
    weights = np.empty((len(sequence_a), len(sequence_b)), dtype=float)
    for i, item_a in enumerate(sequence_a):
        for j, item_b in enumerate(sequence_b):
            weights[i, j] = 1.0 - cost(item_a, item_b)
    return weights


def _score_table(weights: np.ndarray, gap_cost: float) -> np.ndarray:
    """Return the score of the best alignment of every prefix pair."""
    rows, columns = weights.shape
    scores = np.zeros((rows + 1, columns + 1), dtype=float)
    gap_weight = 1.0 - gap_cost
    for i in range(1, rows + 1):
        scores[i, 0] = scores[i - 1, 0] + gap_weight
    for j in range(1, columns + 1):
        scores[0, j] = scores[0, j - 1] + gap_weight
    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            scores[i, j] = max(
                scores[i - 1, j - 1] + weights[i - 1, j - 1],
                scores[i - 1, j] + gap_weight,
                scores[i, j - 1] + gap_weight,
            )
    return scores


def _same(value: float, other: float) -> bool:
    return abs(value - other) <= _TOLERANCE


def _predecessors(
    scores: np.ndarray,
    weights: np.ndarray,
    gap_weight: float,
    i: int,
    j: int,
) -> list[tuple[int, int]]:
    """Return the optimal predecessors of cell ``(i, j)``, best first."""
    here = scores[i, j]
    found: list[tuple[int, int]] = []
    if i and j and _same(scores[i - 1, j - 1] + weights[i - 1, j - 1], here):
        found.append((i - 1, j - 1))
    if j and _same(scores[i, j - 1] + gap_weight, here):
        found.append((i, j - 1))
    if i and _same(scores[i - 1, j] + gap_weight, here):
        found.append((i - 1, j))
    return found


def _trace(
    scores: np.ndarray,
    weights: np.ndarray,
    gap_weight: float,
) -> list[tuple[int, int, int, int]]:
    """Walk back from the last cell, taking the first optimal step."""
    i, j = scores.shape[0] - 1, scores.shape[1] - 1
    steps: list[tuple[int, int, int, int]] = []
    while i or j:
        predecessors = _predecessors(scores, weights, gap_weight, i, j)
        if not predecessors:
            raise RuntimeError(
                f"no optimal predecessor at ({i}, {j}); the score table "
                "and the weights disagree"
            )
        previous_i, previous_j = predecessors[0]
        steps.append((previous_i, previous_j, i, j))
        i, j = previous_i, previous_j
    steps.reverse()
    return steps


def _walk(
    scores: np.ndarray,
    weights: np.ndarray,
    gap_weight: float,
    i: int,
    j: int,
    path: list[tuple[int, int, int, int]],
    found: list[tuple[tuple[int, int, int, int], ...]],
    limit: int,
) -> None:
    """Collect every optimal path ending at cell ``(i, j)``."""
    if len(found) >= limit:
        raise AlignmentLimitError(
            f"more than {limit} optimal alignments; raise the limit to "
            "enumerate them all"
        )
    if not i and not j:
        found.append(tuple(reversed(path)))
        return
    for previous_i, previous_j in _predecessors(
        scores, weights, gap_weight, i, j
    ):
        path.append((previous_i, previous_j, i, j))
        _walk(
            scores,
            weights,
            gap_weight,
            previous_i,
            previous_j,
            path,
            found,
            limit,
        )
        path.pop()


def _build[Item](
    sequence_a: Sequence[Item],
    sequence_b: Sequence[Item],
    steps: Sequence[tuple[int, int, int, int]],
    score: float,
    gap_cost: float,
) -> Alignment[Item]:
    """Turn a path through the score table into an alignment."""
    items_a: list[Item | None] = []
    items_b: list[Item | None] = []
    for previous_i, previous_j, i, j in steps:
        items_a.append(sequence_a[previous_i] if i > previous_i else None)
        items_b.append(sequence_b[previous_j] if j > previous_j else None)
    return Alignment(tuple(items_a), tuple(items_b), float(score), gap_cost)
