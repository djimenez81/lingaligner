# lingaligner

Sequence alignment and distance matrices for comparative linguistics.

Given two forms that answer the same concept, how different are they?
The package answers that in layers, and each layer is usable on its own:

```
align              sequences + a cost -> an Alignment
Alignment          -> the mean column penalty (a term distance)
ParallelCorpus     -> the forms, and questions about the forms
distance           -> segment -> segment, from features or a matrix
LinguisticAligner  -> corpus + inventory + distance, wired together
```

Nothing in the bottom layer knows about phonology. An alignment needs a
sequence and a cost, so the same code aligns DNA, syllables or
orthographic tokens; `tests/test_generality.py` does exactly that. The
phonological layer is assembled from a tokenizer and a feature cost,
supplied by `phonfeat` through the `InventoryLike` protocol rather than
imported from here.

## Status

0.1.0, alpha, unpublished. Alignment, corpus, distances and the
facade are implemented and tested. Clustering, trees, and any file or
settings reader are not here yet.

## Install

```sh
pip install -e ../lingcore
pip install -e ".[dev]"
pytest
```

## Use

```python
from lingaligner import LinguisticAligner, ParallelCorpus

corpus = ParallelCorpus({
    "water": {"A": "kata", "B": "kata"},
    "sun":   {"A": "ka",   "B": "ta"},
})

aligner = LinguisticAligner(corpus=corpus, inventory=inventory)

aligner.render()                     # what it holds, and what it can measure
aligner.tokenize("kata")             # one string -> segments
aligner.align("ka", "ta")            # an Alignment, gaps as None
aligner.segment_distance("a", "i")   # segment -> segment
aligner.alignment_distance("ka", "ta")   # term -> term
aligner.language_distance("A", "B")      # language -> language
aligner.language_matrix()                # DistanceMatrix
```

`inventory` is anything satisfying `InventoryLike`: `segments`,
`categories`, `features` (a `lingcore.FeatureMatrix` or `None`) and
`tokenize`. `phonfeat` supplies the real one.

Without features the aligner still tokenizes and explores; it refuses
to measure, and says why:

```python
LinguisticAligner(corpus=corpus, inventory=no_features).segment_distance("a", "i")
# MissingDataError: no segment distance: the inventory has no features ...
```

A distance can be supplied instead of derived, either from a feature
matrix computed elsewhere or from a precomputed table:

```python
from lingaligner import DistanceMatrix, MatrixCost

table = MatrixCost(DistanceMatrix(labels=..., values=...))
aligner = LinguisticAligner(corpus=corpus, inventory=inventory, distance=table)
```

## The two numbers

Costs live in `[0, 1]`. A column with two items earns `1 - cost`; a
column with one item and a gap earns `1 - gap_cost`, and `gap_cost`
defaults to 1. So with the default, a gap is free to place and exactly
as expensive as swapping two maximally different items -- the
convention the original study used. The distance is the same number
from the other side: `penalty = 1 - weight`.

`gap_cost` below 1 makes gaps cheaper than substitutions. One
substitution stands opposite two gap columns, so a substitution of cost
`c` wins only while `c < 2 * gap_cost - 1`. At `gap_cost = 0.5` the
sides tie and below that every alignment degenerates into gaps.

`Alignment` keeps the `gap_cost` it was built with, `SegmentCost`
objects describe themselves, and `LinguisticAligner.describe()` reports
the whole configuration next to the corpus statistics, so a matrix is
never separated from the parameters that produced it.

## Two distance modes

The inventory decides, not a flag:

- **Unified** (no categories): every feature is compared. An undefined
  cell disagrees with everything, including another undefined cell, so
  two different segments can never reach distance 0 through absence of
  evidence.
- **Partitioned** (`categories` given): segments in the same category
  are compared feature by feature; segments in different categories
  cost `cross_class_cost`, default 1.0.

Within a class the ranking is the same in both modes; only cross-class
distances differ, and `describe()` reports which mode is in force.

## What is not in the package

No file readers. A corpus is a mapping the caller builds; an inventory
is `phonfeat`'s. No inventory, no feature table, no language names and
no notation live here: they are arguments, never constants.

`language_distance` and `language_matrix` require a corpus indexed by
language and say so when there is none. A corpus of cognate sets is a
different shape and will get its own operations.

## Layout

```
src/lingaligner/
  cost.py       the Cost type, exact_cost, validation
  align.py      Needleman-Wunsch with graded match scores, all ties
  corpus.py     ParallelCorpus: forms as written, coverage, overlap
  matrix.py     DistanceMatrix: symmetric, zero diagonal, validated
  inventory.py  InventoryLike: what the aligner needs from phonfeat
  distance.py   FeatureCost, MatrixCost
  aligner.py    LinguisticAligner: the facade
  errors.py     one exception family
```

## Documentation

- [`docs/index.md`](docs/index.md) — entry point.
- [`docs/summary.md`](docs/summary.md) — what the package is, its
  status, and how it relates to the published study.
- [`docs/concepts.md`](docs/concepts.md) — the mental model.
- [`docs/tutorial.md`](docs/tutorial.md) — a worked example.
- [`docs/api.md`](docs/api.md) — the public surface.
- [`docs/design.md`](docs/design.md) — why the layers are where they
  are, including the four ways this differs from the original study.
- [`docs/decisions.md`](docs/decisions.md) — the decision log.

## Testing

```sh
pytest                 # 88 tests
```

`tests/test_aligner.py` drives every operation through a test double
that implements `InventoryLike` and nothing else, which is the proof
that the facade depends on the contract rather than on `phonfeat`.
