# Concepts

This document explains the mental model behind lingaligner's API.
Read it before the tutorial if you are new; read it after if you
prefer to learn by example.

## Items and sequences

The aligner works on **sequences of items**. An item is anything
hashable that a cost function can compare: a phone, a character, a
codon, a syllable. Nothing in the package inspects an item, so the
same code serves DNA and phonology.

An item becomes a phone only because a cost function says so, and that
function comes from outside.

## Costs

A **cost** is a function from two items to a number in `[0, 1]`,
where 0 means interchangeable and 1 means as different as two items
can be.

The range is not decoration. The aligner treats `1 - cost` as a
weight, so a cost above 1 would produce a negative weight and an
alignment that prefers dissimilarity. Costs outside the range are
rejected where they enter.

A cost is a plain callable, not a class. `exact_cost` — 0 for equal
items, 1 otherwise — is the simplest useful one, and the one that
makes the point that this is not a phonetic library.

## Two views of one number

The aligner **maximises** a score. A column holding two items is worth

```
1 - cost(a, b)
```

A column holding one item and a gap is worth `1 - gap_cost`, and
`gap_cost` defaults to 1, which makes it worth nothing.

The distance is the same number from the other side:

```
penalty = 1 - weight
```

so a gap column costs `gap_cost` when measuring. With the default, a
gap is free to place during alignment and exactly as expensive as
swapping two maximally different items when scoring — which is the
convention the original study used, and the reason a substitution is
preferred to an equally weighted gap.

Lowering `gap_cost` makes gaps cheaper than substitutions. One
substitution stands opposite *two* gap columns, because a diagonal
step consumes two items and a gap consumes one, so a substitution of
cost `c` wins only while `c < 2 * gap_cost - 1`. At `gap_cost = 0.5`
the two sides tie, and below that no substitution can ever win: every
alignment degenerates into gaps. `gap_cost = 0.9` reads as "gaps win
only once two items are more than 80% different".

## Alignments

An **`Alignment`** holds two sequences of the same length, with
`None` marking a gap:

```python
align(("k", "a", "t"), ("k", "a", "r", "t"), exact_cost)
# sequence_a  ('k', 'a', None, 't')
# sequence_b  ('k', 'a', 'r',  't')
# score       3.0
```

It knows its score, the `gap_cost` it was built with, how many
columns it has, how many columns are exact identities, and its
distance under a given cost.

## Ties

Several alignments can score the same and measure differently. The
distance is a mean, and the number of columns differs when the number
of matched pairs differs:

```
("a", "b") against ("a", "x")
  three optimal alignments, all scoring 1.0
  distances: 0.5, 0.667, 0.667
```

`align` returns one of them, deterministically: at equal score it
prefers the diagonal step, then the gap in the second sequence, then
the gap in the first. That preference is deliberate — a substitution
carries information a gap does not — but it is a choice.

`align_all` returns every optimal alignment instead, and refuses to
truncate silently if there are more than `limit`. Choosing between
them is then a visible modelling decision rather than an accident of
iteration order.

## Corpora

A **`ParallelCorpus`** is a table in which a concept is given a form
in each language:

```
"water": {"A": "kata", "B": "kja"}
"sun":   {"A": "to",   "B": "to"}
"moon":  {"A": "ni"}
```

It stores the forms **as written** and answers questions about them:
which languages there are, which concepts, which forms are missing,
how many concepts each language translates, and how many concepts
each *pair* of languages shares.

It does not tokenize, align or measure. Those are separate objects,
which is why the same corpus can be read with different tokenizers,
and why a corpus of a different shape does not have to reimplement
them.

The distinction between *coverage* (how much of the table a language
fills) and *overlap* (how much two languages share) matters, because
a language distance is a mean over the shared concepts only. Two well
covered languages can share few concepts, and their distance will then
rest on a small sample. `shared_counts()` exists so that this is
visible before the number is trusted.

## Segment distances

Two sources are implemented.

**`FeatureCost`** reads a `lingcore.FeatureMatrix`: rows are segments,
columns are features, cells are floats, and `NaN` means undefined. The
cost is the fraction of features on which two rows disagree.

Two rules are worth stating plainly:

- **An undefined cell disagrees with everything, including another
  undefined cell.** Absence of evidence must not become evidence of
  identity: if an undefined feature were dropped from the
  denominator, two different segments that differ only there could
  reach distance 0.
- **Identical segments always cost 0**, including segments whose
  whole row is undefined. Without the shortcut, the first rule would
  make a segment disagree with itself.

The consequence, on a table where vowel features are undefined for
consonants, is that every vowel-to-consonant comparison starts from a
floor rather than approaching zero.

**`MatrixCost`** reads a `DistanceMatrix` whose labels are segments.
It exists for distances computed elsewhere — a published table, a
fitted model, or a study that predates the inventory.

## Two modes, chosen by the inventory

An inventory may declare **categories**:

```python
{"vowel": ("a", "i", "u"), "consonant": ("k", "t", "p")}
```

- **Unified** (no categories declared): every feature applies to every
  segment, and undefined cells produce the graded floor described
  above.
- **Partitioned** (categories declared): segments in the same category
  are compared feature by feature; segments in different categories
  cost `cross_class_cost`, default 1.0, and are never compared
  feature by feature.

Within a category the ranking is the same in both modes. Only
cross-class distances differ, which is why the aligner reports which
mode is in force.

The mode follows the data rather than a flag, because an inventory
that declares categories is making a claim about which features apply
to which class, and an inventory that declares none is not.

## The aligner

**`LinguisticAligner`** holds a corpus, an inventory and a distance,
and exposes the operations that follow:

| Operation | Question it answers |
|---|---|
| `tokenize(text)` | what are the segments of this form? |
| `align(a, b)` | how do these two forms line up? |
| `segment_distance(a, b)` | how far apart are two phones? |
| `alignment_distance(a, b)` | how far apart are two forms? |
| `language_distance(a, b)` | how far apart are two languages? |
| `language_matrix()` | how far apart is every pair? |
| `describe()`, `render()` | what does this study consist of? |

It owns no data and no algorithm: the corpus holds the forms, the
inventory holds the notation and the features, the distance object
holds the arithmetic, `align` holds the alignment. Its job is wiring
and vocabulary.

When the inventory has no features and no distance was supplied, the
aligner still tokenizes and explores, and refuses to measure — with a
message saying why, rather than a number nobody can justify.

`language_distance` and `language_matrix` require a corpus indexed by
language. A cognate-set corpus has none, and asking it for a language
distance raises `UnsupportedCorpusError`: that is a category error, not
missing data.

## What a language distance is, and is not

A language distance is the mean, over the concepts two languages
share, of the mean column penalty of each pair's alignment. It is a
number in `[0, 1]` with no unit and no absolute meaning: it is only
comparable to other numbers produced by the same tokenizer, the same
inventory, the same distance rule and the same gap cost.

That is why every report echoes those parameters. A matrix printed
without them cannot be checked, and a claim built on it cannot be
reproduced.

## Where the packages meet

`lingaligner` does not import `phonfeat`. It consumes an
**`InventoryLike`**: four read-only members — `segments`, `categories`,
`features`, `tokenize`. `phonfeat.Inventory` satisfies it, and so does
a test double, which is what `tests/test_aligner.py` uses.

The dependency therefore reads

```
lingaligner  ->  (protocol)  <-  phonfeat
```

and a future inventory built from something else — a generator that
derives one from a corpus, say — needs no change here.
