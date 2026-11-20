"""Substitution costs.

A cost is an ordinary callable, not a class. That is the whole point:
the aligner never asks where the number came from, so the same code
serves a hand-written feature system, one computed from an inventory,
an identity test on DNA, or anything else a caller invents.

A cost takes two items and returns a number in ``[0, 1]``, where 0
means the items are interchangeable and 1 means they are as different
as two items can be. Anything outside that range is a bug in the cost,
not a stylistic choice: the aligner's scoring and the distance view
both assume the range, and ``1 - cost`` is used as a weight.
"""

from __future__ import annotations

import math
from collections.abc import Callable

__all__ = ["Cost", "exact_cost", "validate_cost"]

# A symmetric function from two items to a dissimilarity in [0, 1].
type Cost[Item] = Callable[[Item, Item], float]


def exact_cost[Item](item_a: Item, item_b: Item) -> float:
    """Return 0.0 for equal items and 1.0 otherwise.

    The simplest useful cost, and the one that shows the aligner is not
    a phonetic tool: pass letters, codons or syllables and it behaves
    identically.
    """
    return 0.0 if item_a == item_b else 1.0


def validate_cost(value: float, *, name: str = "cost") -> float:
    """Return ``value`` as a float, raising if it is not a valid cost.

    Parameters
    ----------
    value : float
        The candidate cost.
    name : str, optional
        The parameter name, used in the error message.

    Returns
    -------
    float
        The same value, converted to ``float``.

    Raises
    ------
    ValueError
        If ``value`` is not a finite number in ``[0, 1]``.
    """
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(
            f"{name} must be a finite number in [0, 1]; got {value!r}"
        )
    return number
