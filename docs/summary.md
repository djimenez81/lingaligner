# Project summary

## What lingaligner is

`lingaligner` compares linguistic forms. Given two words that mean the
same thing in two languages, it aligns them phone by phone and turns
the alignment into a number; given a word list, it turns those numbers
into a matrix.

It is the comparison layer of a family of three packages:

```
lingcore      abstract structures: segments, features, matrices
   |
phonfeat      notation, tokenization, feature data, inventories
   |
lingaligner   alignment, distances, comparison
```

The package grew out of a study of the Chibchan family, in which the
phylogenetic history of a group of languages was estimated from
Swadesh-list data using alignment methods borrowed from genetics. The
original code was written for that one file and that one feature
table. This package is the same method with the study's particulars
removed: the corpus, the inventory, the distance and the gap cost all
arrive as arguments.

## What lingaligner is not

- **Not a phonetic library.** It knows nothing about IPA, X-SAMPA or
  feature systems. It needs a sequence of items and a cost on pairs of
  items, and it does not ask where either came from.
- **Not a file reader.** A corpus is a mapping the caller builds.
- **Not a theory of relatedness.** It computes distances between forms
  and aggregates them. Whether a number means "cognate" is a
  linguistic judgement the package does not make.
- **Not a phylogenetics toolkit.** It produces a distance matrix and
  stops. Clustering and trees are not implemented yet.

## Design principles

1. **The algorithm is generic, the application is not.** Alignment is
   a general method over any alphabet; the phonological case is one
   client. `tests/test_generality.py` aligns DNA and syllables with the
   same code as phones, which is the cheapest available proof.
2. **Costs are plain callables.** No class hierarchy, no registry: a
   function from two items to a number in `[0, 1]`. Anything that can
   produce that number can drive the aligner.
3. **The distance is the dual of the score.** A column is worth
   `1 - cost` while aligning and costs `cost` when measuring. One
   number, read from two sides, so the two cannot drift apart.
4. **Parameters travel with results.** An `Alignment` keeps the
   `gap_cost` it was built with; a distance object describes itself;
   the aligner reports the whole configuration next to the numbers.
5. **Data, policy and computation are separate objects.** The corpus
   stores forms, the inventory stores what a study considers a sound,
   the distance object holds the arithmetic, and the aligner wires
   them. Adding a corpus shape or a distance type means adding a class.

## Status

### Implemented in v0.1

- `align`, `align_all`, `Alignment` — global alignment with a graded
  match score, and enumeration of every optimal alignment.
- `Cost`, `exact_cost`, `validate_cost` — the cost protocol and the
  simplest instance.
- `SegmentCost`, `FeatureCost`, `MatrixCost` — segment distances from a
  feature matrix or from a table computed elsewhere.
- `InventoryLike` — the four things the aligner needs from an
  inventory, satisfied by `phonfeat.Inventory`.
- `ParallelCorpus` — concepts by languages, with coverage and overlap.
- `DistanceMatrix` — a labelled, symmetric, zero-diagonal matrix.
- `LinguisticAligner` — the object a user holds.

### Planned

- **Clustering and trees.** Single, complete, average and WPGMA
  linkage over a `DistanceMatrix`, with branch lengths and Newick
  output. The matrix is deliberately the boundary; everything
  downstream can stay somebody else's code.
- **Local alignment.** For affixed and partially matching forms, which
  global alignment handles badly. It needs a contract for reporting
  the aligned substrings and their offsets, which is why it is not
  here yet.
- **A BLOSUM-style segment matrix.** Building a substitution matrix
  from a collection of cognate sets, which is the reason the
  Austronesian cognate corpus matters to this package.
- **A settings file.** Loading a whole study — corpus, inventory,
  distance, gap cost — from a small YAML document.

### Not planned

- **Notation and feature data.** That is `phonfeat`'s work, reached
  through the `InventoryLike` protocol.
- **File readers.** The caller builds the corpus from whatever they
  have.
- **A corpus shape for every study.** One shape is implemented; a
  cognate-set corpus will be a second class when it is needed, not a
  general abstraction invented in advance.

## Provenance and reproduction

The package is intended to make the original study reproducible, and
it does not reproduce it silently. Four things differ, each recorded
in `docs/decisions.md`:

- the diagonal of a distance matrix is 0, not 1;
- gaps are free to place and maximally expensive to score, which is
  the dual of one number rather than two independent conventions;
- cross-class segment costs come from undefined feature values rather
  than a hard-coded 1.0, unless the inventory declares categories;
- the languages compared are dropped by `min_shared` rather than by
  hand.

Anyone re-running the published analysis should read `design.md`
before comparing numbers.

## Versioning

`lingaligner` follows [semantic versioning](https://semver.org/) from
`0.1.0`. While the major version is `0`, breaking changes may occur
between minor versions and are recorded in `docs/decisions.md`.

## License

GPL-3.0-or-later. See `LICENSE`.
