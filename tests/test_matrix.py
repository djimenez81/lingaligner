"""Distance-matrix validation."""

from __future__ import annotations

import numpy as np
import pytest

from lingaligner import DistanceMatrix, DistanceMatrixError


def test_a_valid_matrix_round_trips():
    matrix = DistanceMatrix(
        labels=("A", "B"),
        values=np.array([[0.0, 0.25], [0.25, 0.0]]),
    )
    assert matrix.distance("A", "B") == pytest.approx(0.25)
    assert len(matrix) == 2


def test_records_carry_one_row_per_pair():
    matrix = DistanceMatrix(
        labels=("A", "B", "C"),
        values=np.array(
            [
                [0.0, 0.1, 0.2],
                [0.1, 0.0, 0.3],
                [0.2, 0.3, 0.0],
            ]
        ),
    )
    records = matrix.to_records()
    assert len(records) == 3
    assert records[0] == {
        "language_a": "A",
        "language_b": "B",
        "distance": pytest.approx(0.1),
    }


def test_values_are_read_only():
    matrix = DistanceMatrix(
        labels=("A", "B"),
        values=np.array([[0.0, 0.5], [0.5, 0.0]]),
    )
    with pytest.raises(ValueError):
        matrix.values[0, 1] = 0.9


def test_non_square_is_refused():
    with pytest.raises(DistanceMatrixError, match="square"):
        DistanceMatrix(labels=("A",), values=np.zeros((1, 2)))


def test_asymmetry_is_refused():
    with pytest.raises(DistanceMatrixError, match="symmetric"):
        DistanceMatrix(
            labels=("A", "B"),
            values=np.array([[0.0, 0.5], [0.4, 0.0]]),
        )


def test_a_non_zero_diagonal_is_refused():
    with pytest.raises(DistanceMatrixError, match="diagonal"):
        DistanceMatrix(
            labels=("A", "B"),
            values=np.array([[1.0, 0.5], [0.5, 1.0]]),
        )


def test_label_count_must_match_the_matrix():
    with pytest.raises(DistanceMatrixError, match="labels"):
        DistanceMatrix(labels=("A",), values=np.zeros((2, 2)))


def test_labels_must_be_unique():
    with pytest.raises(DistanceMatrixError, match="unique"):
        DistanceMatrix(
            labels=("A", "A"),
            values=np.array([[0.0, 0.2], [0.2, 0.0]]),
        )


def test_non_finite_values_are_refused():
    with pytest.raises(DistanceMatrixError, match="finite"):
        DistanceMatrix(
            labels=("A", "B"),
            values=np.array([[0.0, np.nan], [np.nan, 0.0]]),
        )


def test_unknown_label_is_named():
    matrix = DistanceMatrix(
        labels=("A", "B"),
        values=np.array([[0.0, 0.5], [0.5, 0.0]]),
    )
    with pytest.raises(DistanceMatrixError, match="C"):
        matrix.distance("A", "C")
