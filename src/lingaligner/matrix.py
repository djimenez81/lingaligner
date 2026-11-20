"""Symmetric matrices of pairwise distances.

A distance matrix is the boundary of the package: everything upstream
turns forms into numbers, everything downstream (clustering,
ordination, a Newick file) can be somebody else's code. Keeping the
matrix a plain labelled array means the package does not have to own
phylogenetics to be useful to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .errors import DistanceMatrixError

__all__ = ["DistanceMatrix"]

_SYMMETRY_TOLERANCE = 1e-9


@dataclass(frozen=True, slots=True)
class DistanceMatrix:
    """A square, symmetric, zero-diagonal matrix with row labels.

    Parameters
    ----------
    labels : tuple of str
        One label per row, in row order.
    values : numpy.ndarray
        Square array of dissimilarities.

    Notes
    -----
    The diagonal is zero, because a language compared with itself has
    no distance. This is the opposite of the convention in the original
    study, which filled the diagonal with 1 as a sentinel so that a
    minimum search would never pick it; that sentinel is unnecessary
    once the diagonal means what it says, and it collides with any real
    distance of exactly 1.
    """

    labels: tuple[str, ...]
    values: np.ndarray = field(repr=False)

    def __post_init__(self) -> None:
        array = np.array(self.values, dtype=float, copy=True)
        if array.ndim != 2 or array.shape[0] != array.shape[1]:
            raise DistanceMatrixError(
                f"matrix must be square; got shape {array.shape}"
            )
        size = array.shape[0]
        if len(self.labels) != size:
            raise DistanceMatrixError(
                f"{len(self.labels)} labels for a {size}x{size} matrix"
            )
        if len(set(self.labels)) != len(self.labels):
            raise DistanceMatrixError("labels must be unique")
        if not np.all(np.isfinite(array)):
            raise DistanceMatrixError("matrix holds a non-finite value")
        symmetric = np.allclose(
            array, array.T, atol=_SYMMETRY_TOLERANCE, rtol=0
        )
        if not symmetric:
            raise DistanceMatrixError("matrix is not symmetric")
        flat = np.allclose(
            np.diag(array), 0.0, atol=_SYMMETRY_TOLERANCE, rtol=0
        )
        if not flat:
            raise DistanceMatrixError("diagonal must be zero")
        array.flags.writeable = False
        object.__setattr__(self, "values", array)
        object.__setattr__(self, "labels", tuple(self.labels))

    def __len__(self) -> int:
        return len(self.labels)

    def distance(self, language_a: str, language_b: str) -> float:
        """Return the distance between two labelled rows.

        Parameters
        ----------
        language_a, language_b : str
            Labels present in the matrix.

        Returns
        -------
        float
            The stored dissimilarity.

        Raises
        ------
        DistanceMatrixError
            If a label is not in the matrix.
        """
        index = {label: n for n, label in enumerate(self.labels)}
        try:
            return float(self.values[index[language_a], index[language_b]])
        except KeyError as exc:
            raise DistanceMatrixError(
                f"unknown label {exc.args[0]!r}"
            ) from None

    def to_records(self) -> list[dict[str, object]]:
        """Return the upper triangle as one record per pair.

        Returns
        -------
        list of dict
            Records with ``language_a``, ``language_b`` and
            ``distance`` keys, in row order.
        """
        records = []
        for i, language_a in enumerate(self.labels):
            for j in range(i + 1, len(self.labels)):
                records.append(
                    {
                        "language_a": language_a,
                        "language_b": self.labels[j],
                        "distance": float(self.values[i, j]),
                    }
                )
        return records
