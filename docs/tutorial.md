# Tutorial

A worked example. By the end you will have aligned two forms, measured
their distance, and computed a matrix over a small word list.

## 1. Install

```
pip install lingaligner
```

`lingcore` is installed with it. `phonfeat` is not required: nothing
in this package imports it.

## 2. Align two sequences

```python
from lingaligner import align, exact_cost

alignment = align(("k", "a", "t"), ("k", "a", "r", "t"), exact_cost)
print(alignment.sequence_a)
print(alignment.sequence_b)
print(alignment.score, alignment.distance(exact_cost))
```

```
('k', 'a', None, 't')
('k', 'a', 'r', 't')
3.0 0.25
```

Four columns, one of them a gap. `exact_cost` gives 1 for any two
different items, so the three matched columns score 1 each and the gap
scores 0 — hence 3.0.

The distance is the same number from the other side: three columns
cost 0 and the gap column costs 1, so the mean is 0.25.

## 3. Watch the ties

```python
from lingaligner import align_all

for alignment in align_all(("a", "b"), ("a", "x"), exact_cost):
    print(alignment.sequence_a, alignment.sequence_b,
          alignment.score, round(alignment.distance(exact_cost), 4))
```

```
('a', 'b') ('a', 'x') 1.0 0.5
('a', 'b', None) ('a', None, 'x') 1.0 0.6667
('a', None, 'b') ('a', 'x', None) 1.0 0.6667
```

Three alignments, all scoring 1.0, and two different distances. The
bad pair can be a substitution or a gap in either sequence; each gap
adds a column that holds no match, which raises the mean.

`align` returns the first of these, deterministically. `align_all`
lets you choose on a second criterion — the smallest distance, say —
instead of inheriting the tie-break.

## 4. Use a table instead of a rule

A real study does not treat every pair as equally different. Segment
distances can come from anywhere; here they come from a small table:

```python
import numpy as np
from lingaligner import DistanceMatrix, MatrixCost

labels = ("a", "k", "t", "ɡ")
values = np.zeros((4, 4))
for i, j, distance in [
    (0, 1, 0.5), (0, 2, 0.5), (0, 3, 0.5),
    (1, 2, 0.25), (1, 3, 0.75), (2, 3, 0.75),
]:
    values[i, j] = values[j, i] = distance
cost = MatrixCost(DistanceMatrix(labels=labels, values=values))

print(cost.cost("k", "t"), cost.cost("k", "ɡ"))
print(cost.describe())
```

```
0.25 0.75
{'kind': 'matrix', 'segments': 4}
```

`k` and `t` are 0.25 apart; `k` and `ɡ` are 0.75 apart. The matrix
validates itself on construction: square, symmetric, zero diagonal,
finite, unique labels.

## 5. Wrap it in a study

A `LinguisticAligner` needs three things: the corpus, an inventory
and a distance. The inventory is anything with four read-only
members — for a quick look, ten lines will do:

```python
from lingcore import Segment
from lingaligner import LinguisticAligner, ParallelCorpus

class Inventory:
    segments = tuple(Segment(symbol=s, type="other") for s in labels)
    categories = {}
    features = None
    def tokenize(self, text):
        return tuple(Segment(symbol=c, type="other") for c in text)

corpus = ParallelCorpus({
    "water": {"A": "kata", "B": "ɡata"},
    "sun":   {"A": "ta",   "B": "ta"},
    "moon":  {"A": "ka"},
})
aligner = LinguisticAligner(corpus=corpus, inventory=Inventory(),
                            distance=cost)
```

In practice the inventory comes from
[`phonfeat`](https://github.com/<your-user>/phonfeat), which does the
same job for real notations:

```python
from phonfeat import Inventory, load_feature_model

inventory = Inventory.from_feature_model(load_feature_model("hayes"))
aligner = LinguisticAligner(corpus=corpus, inventory=inventory)
```

With features available, the distance is built automatically: a
`FeatureCost` over the inventory's matrix, partitioned if the
inventory declares categories and unified otherwise.

## 6. Ask it questions

```python
print([s.symbol for s in aligner.tokenize("kata")])
print(aligner.segment_distance("k", "t"))
print(aligner.alignment_distance("kata", "ɡata"))
```

```
['k', 'a', 't', 'a']
0.25
0.1875
```

`kata` against `ɡata` is one substitution at 0.75 and three exact
matches at 0, so the mean column penalty is 0.1875.

## 7. Compare languages

```python
print(aligner.language_distance("A", "B"))
```

```
0.09375
```

The two languages share two concepts. `water` costs 0.1875; `sun` is
identical and costs 0. The mean is 0.09375. `moon` is missing from
`B`, so it takes no part — and that is worth knowing rather than
assuming, which is what `min_shared` is for:

```python
aligner.language_distance("A", "B", min_shared=3)
# MissingDataError: 'A' and 'B' share 2 concept(s); min_shared is 3
```

The full matrix:

```python
matrix = aligner.language_matrix()
print(matrix.labels, matrix.values.tolist())
```

```
('A', 'B') [[0.0, 0.09375], [0.09375, 0.0]]
```

Symmetric, zero diagonal, labelled.

## 8. Look before you compute

```python
print(aligner.render())
```

```
corpus      3 concepts, 2 languages, 5 forms
tokenized   5 of 5 (0 failed)
inventory   4 segments
distance    matrix, 4 segments
gap cost    1.0
```

`describe()` returns the same as a dict, with coverage per language,
the shared-concept count per pair, and any form that failed to
tokenize — listed with its concept, language and error, rather than
raised. Exploration should not stop at the first bad cell; measuring
should, and does.

## 9. What next

- **Clustering.** The matrix is where this package stops. Feed it to
  whatever builds trees; when clustering arrives here it will expose
  its linkage method rather than assume one.
- **Your own corpus shape.** `ParallelCorpus` is concepts by
  languages. A different shape — cognate sets, say — is a second
  class with its own operations, not a configuration of this one.
- **Reproducing a published study?** Read "Reproducing the original
  study" in [Design notes](design.md) before comparing numbers.
