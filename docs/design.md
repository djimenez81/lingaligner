# Design notes

Why `lingaligner` is shaped the way it is. The decisions themselves,
with their costs, are in [decisions.md](decisions.md); this document
is the shape they add up to.

## Three layers, one direction

```
align + cost        generic: any sequence, any cost
      |
distance            segment -> segment, from features or a matrix
      |
corpus              the forms, and questions about the forms
      |
LinguisticAligner   the three wired together
```

The bottom layer knows nothing about linguistics: an alignment needs a
sequence and a cost, and `tests/test_generality.py` aligns DNA and
syllables to keep it honest. The upper layers know a great deal about
linguistics and nothing about the algorithm.

The dependency direction is one-way, and the package does not import
`phonfeat` at all. Inventory data arrives through the `InventoryLike`
protocol (D14), so the two packages meet at a contract rather than at
a class.

## Why the corpus stores strings, not tokens

The first version of this package stored segmented forms, which forced
a tokenizer into the corpus constructor. That had three costs, all of
them avoidable (D13):

- the corpus could not exist before an inventory did;
- changing a tokenizer or an orthographic profile meant rebuilding the
  data;
- the corpus grew three methods whose vocabulary assumed a Swadesh
  table — `aligned(concept, a, b)`, `distance(language_a, ...)`,
  `matrix()` — none of which means anything for a corpus of cognate
  sets.

Storing the forms as written fixes all three. Tokenizing is the
inventory's job, comparing is the aligner's, and the corpus is left
with the questions that are really about the data: what is here, what
is missing, what is shared.

## Why the inventory is a protocol and not a class

The aligner needs four things from an inventory: segments, categories,
features and a tokenizer. It does not need to know how they were
produced.

A class in this package would have forced `phonfeat` to inherit from
it, or forced a copy of its code. A protocol leaves the dependency
reading

```
lingaligner -> (protocol) <- phonfeat
```

and lets a test double, a hand-written object, or a future generator
satisfy it with no change here. `tests/test_aligner.py` drives every
operation through a four-member stand-in, which is the proof.

## Why costs are objects and not lambdas

`align` takes a plain callable, and that is deliberate: the alignment
layer should accept anything that can produce a number.

Distances are objects, though, for one reason: a number separated from
its parameters cannot be checked later. `FeatureCost` knows which
matrix it read and how it treats undefined cells; `MatrixCost` knows
which table it came from; both can `describe()` themselves, and
`LinguisticAligner.describe()` prints that next to the numbers it
produced (D15).

The gap cost is stored on the `Alignment` for the same reason.

## Why the matrix is the boundary

The package stops at `DistanceMatrix`. Everything upstream turns forms
into numbers; everything downstream — clustering, ordination, a Newick
file — can be somebody else's code.

That boundary is what keeps a phylogenetics toolkit out of the
package. When clustering does arrive it will have two obligations
recorded in advance: mask the diagonal rather than assume a sentinel,
and expose its linkage method, because single linkage is what the
original study used and average linkage is what most phylogenetic work
assumes (D12).

## Two modes, and why the inventory decides

An inventory that declares categories is claiming that vowel features
do not apply to consonants. An inventory that declares none is making
no such claim. The distance respects whichever claim was made (D16):

- **unified** — every feature applies to every segment; an undefined
  cell disagrees with everything, which gives cross-class comparisons
  a floor;
- **partitioned** — different categories cost `cross_class_cost`,
  default 1.0, and are never compared feature by feature.

Within a class the ranking is identical in both, so a tree over a
single class cannot tell the modes apart. Cross-class numbers differ
substantially: on the Chibchan inventory, a vowel-to-consonant pair
costs between 0.44 and 0.81 unified against a flat 1.0 partitioned.

## Reproducing the original study

The package is meant to make the published analysis reproducible, and
it does not reproduce it silently. Four differences, all deliberate:

| Original | Here | Why |
|---|---|---|
| distance-matrix diagonal of 1 | 0 | A language compared with itself has no distance. The 1 was a sentinel so a minimum search would skip the diagonal; it collides with any real distance of exactly 1. Code that searches for a minimum should mask the diagonal instead (D9). |
| free gaps to place, charged 1.0 to measure | one `gap_cost`, read from both sides | The two conventions were duals of the same number, which is only true while the gap cost is the maximum. Expressing it once makes the duality checkable (D3, D5). |
| cross-class cost hard-coded to 1.0 | derived from undefined feature values, or declared as categories | The hard-coded rule is one of the two modes now, not the only behaviour (D8, D16). |
| languages dropped by hand for thin data | `min_shared` | A mean over four concepts and a mean over eighty are not the same claim, and the threshold makes the difference explicit (D10). |

Anyone re-running the published analysis should expect the same
rankings within a class, a different absolute scale, and possibly a
different tree where cross-class comparisons change the ordering.

## What is deliberately absent

**Local alignment.** Affixed forms (`man-abala`) want it. It needs a
contract this package has not decided: whether the result reports the
aligned substrings, the offsets in each original sequence, or both
(D11). Guessing now would be worse than adding it deliberately.

**Clustering.** The matrix is the boundary, and the linkage method is
a scientific choice that should be exposed rather than assumed.

**A corpus shape for every study.** One shape is implemented. A
cognate-set corpus will be a second class, with its own operations,
when it is needed — not a general abstraction invented in advance
(D17, D18).

## The guiding principle

A distance is a claim, and a claim needs its terms. Everything in this
package that looks like ceremony — the frozen dataclasses, the
validated matrices, the distances that describe themselves, the
aligner that reports its own configuration — exists so that a number
can be traced back to the decisions that produced it.
