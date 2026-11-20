# API reference

Every public class and function exported by lingaligner.

All exceptions derive from `LingalignerError`, so one `except` clause
catches the family.

## `align(sequence_a, sequence_b, cost, *, gap_cost=1.0)`

**Purpose.** Align two sequences end to end, maximising the score.

**Signature.**

```python
align(
    sequence_a: Sequence[Item],
    sequence_b: Sequence[Item],
    cost: Cost[Item],
    *,
    gap_cost: float = 1.0,
) -> Alignment[Item]
```

**Parameters.**

| Name | Type | Description |
|---|---|---|
| `sequence_a`, `sequence_b` | sequence | The items to align, in order. |
| `cost` | callable | Dissimilarity of two items, in `[0, 1]`. |
| `gap_cost` | `float` | Cost of a gap column, in `[0, 1]`. Defaults to 1. |

**Returns.** The highest-scoring alignment. When several score
equally, the one reached by preferring diagonal steps.

**Raises.** `ValueError` if `gap_cost` is outside `[0, 1]`.

**Notes.** Needleman-Wunsch with a graded substitution score: a
column of two items earns `1 - cost`, a column of one item and a gap
earns `1 - gap_cost`. Ties break diagonal, then gap in the second
sequence, then gap in the first.

---

## `align_all(sequence_a, sequence_b, cost, *, gap_cost=1.0, limit=256)`

**Purpose.** Return every optimal alignment.

**Signature.**

```python
align_all(
    sequence_a: Sequence[Item],
    sequence_b: Sequence[Item],
    cost: Cost[Item],
    *,
    gap_cost: float = 1.0,
    limit: int = 256,
) -> tuple[Alignment[Item], ...]
```

**Returns.** Every optimal alignment, in a deterministic order: at
each backtracking step the diagonal successor is explored first.

**Raises.** `AlignmentLimitError` if more than `limit` optimal
alignments exist. It refuses to truncate, because a partial answer
would look complete.

**Notes.** Equal scores do not imply equal distances, so ties are a
modelling decision rather than a detail. See `Concepts`.

---

## `Alignment`

**Purpose.** Two sequences aligned column by column.

**Signature.**

```python
Alignment(
    sequence_a: tuple[Item | None, ...],
    sequence_b: tuple[Item | None, ...],
    score: float,
    gap_cost: float = 1.0,
)
```

**Fields.**

| Field | Type | Description |
|---|---|---|
| `sequence_a`, `sequence_b` | `tuple` | The aligned sequences; `None` marks a gap. Equal length by construction. |
| `score` | `float` | Sum of the weights of every column. |
| `gap_cost` | `float` | The cost gaps were charged, kept so `distance` need not be told again. |

**Methods and properties.**

- `columns()` — yields `(item_a, item_b)` pairs.
- `distance(cost)` — mean column penalty, gaps charged `gap_cost`.
- `gapped` — whether any column holds a gap.
- `identities` — number of columns where both items are present and
  equal.
- `len(alignment)` — number of columns.

**Raises.** `ValueError` if the two sequences differ in length;
`EmptyAlignmentError` from `distance` if there are no columns.

---

## `Cost`

**Purpose.** The type of a cost function.

```python
type Cost[Item] = Callable[[Item, Item], float]
```

**Notes.** A plain callable, not a class: anything that maps two items
to a number in `[0, 1]` can drive the aligner. Not enforced at the
type level — `validate_cost` checks the range where a number enters.

---

## `exact_cost(item_a, item_b)`

**Purpose.** 0 for equal items, 1 otherwise.

**Signature.**

```python
exact_cost[Item](item_a: Item, item_b: Item) -> float
```

**Notes.** The simplest useful cost, and the one that demonstrates
the aligner is alphabet-agnostic.

---

## `validate_cost(value, *, name="cost")`

**Purpose.** Reject a cost outside `[0, 1]` where it enters.

**Signature.**

```python
validate_cost(value: float, *, name: str = "cost") -> float
```

**Raises.** `ValueError` for a non-finite value or one outside the
range.

---

## `SegmentCost`

**Purpose.** A segment distance that can explain itself.

**Members.**

- `cost(symbol_a, symbol_b) -> float` — dissimilarity in `[0, 1]`.
- `describe() -> dict` — the parameters that produced it.

**Notes.** A protocol. `FeatureCost` and `MatrixCost` implement it; so
can anything else.

---

## `FeatureCost`

**Purpose.** Distance from a feature matrix: the fraction of features
on which two rows disagree.

**Signature.**

```python
FeatureCost(
    matrix: lingcore.FeatureMatrix,
    categories: Mapping[str, tuple[str, ...]] | None = None,
    cross_class_cost: float = 1.0,
)
```

**Parameters.**

| Name | Type | Description |
|---|---|---|
| `matrix` | `FeatureMatrix` | Rows are segment symbols, columns are features, `NaN` is undefined. |
| `categories` | mapping or `None` | `{category: symbols}`. Empty or `None` means a single undivided inventory. |
| `cross_class_cost` | `float` | Cost of comparing across categories. Defaults to 1.0. |

**Methods.** `cost(symbol_a, symbol_b)` and `describe()`.

**Raises.** `ValueError` if the matrix has no features, if a symbol
appears in two categories, if the categories leave a symbol
unclassified, or if `cross_class_cost` is outside `[0, 1]`.
`MissingSegmentError` for a symbol with no row, and for a category
naming a symbol the matrix lacks.

**Notes.** An undefined cell disagrees with everything, including
another undefined cell; identical symbols always cost 0. In
partitioned mode, segments in different categories cost
`cross_class_cost` and are never compared feature by feature.

---

## `MatrixCost`

**Purpose.** Distance read from a matrix computed elsewhere.

**Signature.**

```python
MatrixCost(matrix: DistanceMatrix)
```

**Methods.** `cost(symbol_a, symbol_b)` and `describe()`.

**Raises.** `MissingSegmentError` for a symbol that is not one of the
matrix's labels.

---

## `InventoryLike`

**Purpose.** The four things the aligner needs from an inventory. A
protocol; `phonfeat.Inventory` satisfies it.

**Members (all read-only).**

| Member | Type | Description |
|---|---|---|
| `segments` | sequence of `lingcore.Segment` | The phones the inventory holds. |
| `categories` | mapping | `{category: symbols}`, empty for an undivided inventory. |
| `features` | `FeatureMatrix` or `None` | Segments by features. |
| `tokenize(text)` | method | Splits one written form into segments. |

---

## `ParallelCorpus`

**Purpose.** Forms answering the same concepts in several languages.

**Signature.**

```python
ParallelCorpus(forms: Mapping[str, Mapping[str, str]])
```

**Parameters.** `forms` — `{concept: {language: form}}`, with forms as
written, not tokenized.

**Properties.** `concepts`, `languages` (in first-appearance order),
`has_languages`.

**Methods.**

| Method | Returns |
|---|---|
| `form(concept, language)` | the form, or `None` when missing |
| `missing(language)` | concepts that language does not translate |
| `shared(language_a, language_b)` | concepts both translate |
| `counts()` | `{language: forms}` |
| `coverage()` | `{language: fraction}` |
| `shared_counts()` | `{(a, b): shared_concepts}` |

**Raises.** `TypeError` if a form is not a string.

**Notes.** Immutable; nested mappings are read-only views. It stores
forms, not tokens, and computes no distances.

---

## `DistanceMatrix`

**Purpose.** A labelled, symmetric, zero-diagonal matrix of
dissimilarities.

**Signature.**

```python
DistanceMatrix(labels: tuple[str, ...], values: numpy.ndarray)
```

**Methods.**

- `distance(language_a, language_b) -> float` — the stored value.
- `to_records() -> list[dict]` — the upper triangle as
  `{"language_a", "language_b", "distance"}`, in row order.
- `len(matrix)` — number of labels.

**Raises.** `DistanceMatrixError` if the array is not square, if the
label count does not match, if labels repeat, if a value is not
finite, if the matrix is not symmetric, or if the diagonal is not
zero. `distance` raises it for an unknown label.

**Notes.** Values are copied and made read-only. The zero diagonal is
deliberate: a language compared with itself has no distance, and any
code searching for a minimum must mask the diagonal rather than rely
on a sentinel.

---

## `LinguisticAligner`

**Purpose.** The object a user holds: corpus, inventory and distance,
wired together.

**Signature.**

```python
LinguisticAligner(
    corpus: ParallelCorpus,
    inventory: InventoryLike,
    distance: SegmentCost | None = None,
    gap_cost: float = 1.0,
)
```

**Parameters.**

| Name | Type | Description |
|---|---|---|
| `corpus` | `ParallelCorpus` | The forms. |
| `inventory` | `InventoryLike` | Segments, categories, features, tokenizer. |
| `distance` | `SegmentCost` or `None` | When omitted, a `FeatureCost` is built from the inventory's features — partitioned if it declares categories, unified otherwise — and stored in this attribute. |
| `gap_cost` | `float` | Gap cost, in `[0, 1]`. Defaults to 1. |

**Methods.**

| Method | Returns |
|---|---|
| `tokenize(text)` | `tuple[lingcore.Segment, ...]` |
| `align(form_a, form_b)` | `Alignment` |
| `segment_distance(symbol_a, symbol_b)` | `float` |
| `alignment_distance(form_a, form_b)` | `float` |
| `language_distance(a, b, *, min_shared=1)` | `float` |
| `language_matrix(*, min_shared=1)` | `DistanceMatrix` |
| `describe()` | `dict` |
| `render()` | `str` |

**Raises.** `MissingDataError` when there is no distance to use, when
the inventory has no features and none was supplied, when a pair
shares fewer than `min_shared` concepts, when a language is unknown,
or when a shared form tokenizes to no segments.
`UnsupportedCorpusError` from the language operations when the corpus
is not indexed by language.

**Notes.** Immutable. `describe()` tokenizes every form and lists
failures with examples rather than raising, so exploration survives a
bad cell; the distance methods stay strict. `render()` is the same
information as text, including the distance's own parameters and the
gap cost.

---

## Exceptions

| Exception | Raised when |
|---|---|
| `LingalignerError` | Base class. |
| `EmptyAlignmentError` | A distance is asked of an alignment with no columns. |
| `AlignmentLimitError` | More optimal alignments exist than were asked for. |
| `MissingSegmentError` | A symbol has no entry in the inventory or matrix. |
| `MissingDataError` | Too little data to answer: no distance, too few shared concepts, an unknown language. |
| `UnsupportedCorpusError` | The operation needs something the corpus does not have, e.g. a language distance over a corpus with no languages. |
| `DistanceMatrixError` | A matrix is not square, symmetric, zero-diagonal, finite, or uniquely labelled. |
