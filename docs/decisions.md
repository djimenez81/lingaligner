# Design decisions

Each entry records a choice, the reason, and what it costs. Entries are
not renumbered or deleted; a superseded decision is marked as such and
a new one explains the change.

## D1. The core is alphabet-agnostic

**Decision.** Alignment takes a sequence of items and a `Cost` callable.
It never imports `phonfeat` and never assumes an item is a segment.

**Why.** Alignment is a general algorithm over any alphabet; the
genetic analogy that motivated the original project is a feature, not
an embarrassment to hide. The phonological case becomes one client.
The proof is that DNA and syllables pass the same tests.

**Cost.** One extra indirection: callers must build the cost they want
instead of getting one for free.

## D2. A cost is a plain callable in `[0, 1]`

**Decision.** `Cost` is `Callable[[Item, Item], float]`, not a class
hierarchy. Values outside `[0, 1]` are rejected where they enter.

**Why.** The aligner's scoring and the distance view both rely on the
range: `weight = 1 - cost` is only a weight if `cost <= 1`. A class
hierarchy would restrict callers without buying anything the range
check does not already give.

## D3. Score is the sum of weights; `gap_cost` defaults to 1

**Decision.** A two-item column earns `1 - cost`; a one-item column
earns `1 - gap_cost`; the alignment maximises their sum. `gap_cost`
defaults to 1, so a gap earns nothing and costs exactly as much as a
maximal substitution in the distance view.

**Why.** This is the convention the Chibchan study used, generalised
from "1 for a match, 0 otherwise" to a graded match. It makes the gap
parameter explicit instead of implicit in an index.

**Cost.** Because one substitution stands opposite *two* gap columns, a
substitution of cost `c` wins only while `c < 2 * gap_cost - 1`. At
`gap_cost = 0.5` the sides tie; below that every alignment degenerates
into gaps. This is documented in `align.py` rather than blocked,
because a caller may have their own reason.

## D4. Ties break diagonal first

**Decision.** At equal score, prefer the substitution, then the gap in
the second sequence, then the gap in the first.

**Why.** The original code did this, and the intent is real: a
substitution carries information that a gap does not, so when the score
cannot distinguish them the substitution is the better reading.

**Cost.** `align` is deterministic but returns one of several optimal
alignments. `align_all` exists so a caller can choose on a second
criterion instead.

## D5. The distance is the dual of the score

**Decision.** `Alignment.distance(cost)` is the mean column penalty,
where a gap column is charged `gap_cost` -- exactly `1 - weight`.

**Why.** Two views of one number cannot drift. A gap that was free to
place during alignment is maximally expensive in the mean, because the
mean divides by the number of columns and a gap adds a column with no
match in it.

## D6. All optimal alignments can be enumerated

**Decision.** `align_all` returns every optimal alignment, refusing to
truncate silently if there are more than `limit`.

**Why.** Equal scores do not imply equal distances: the distance is a
mean and the number of columns differs when the number of matched pairs
differs. Two alignments of `("a", "b")` against `("a", "x")` both score
1.0 and measure 0.5 and 0.667. Choosing between them is a modelling
decision, so it should be visible.

## D7. A corpus is concepts by languages; the segmenter is injected

**Decision.** `ParallelCorpus` holds `{concept: {language: sequence}}`.
`from_strings` applies a caller-supplied segmenter. There is no file
reader, no spreadsheet adapter and no column convention.

**Why.** The files a study uses are examples of a class of file, not
the class itself. A package that knew about sheet names or column
positions would make one study's accidents into everyone's ontology.

**Cost.** Every caller writes ten lines of adapter code. That is the
price of not guessing.

## D8. Undefined feature values match nothing

**Decision.** A `NaN` cell disagrees with every value including another
`NaN`. Identical segments are special-cased to cost 0.

**Why.** Absence of evidence must not become evidence of identity: if
an undefined feature were dropped from the denominator, two different
segments that differ only there could reach distance 0. The identity
shortcut is required for consistency, since otherwise a segment with an
undefined cell would disagree with itself.

**Cost.** When a feature system has class-specific features, the
undefined cells give vowel-to-consonant comparisons a floor
(`5/16` in the Chibchan table) instead of letting them approach zero.
That floor replaces the original study's hard rule "different class
costs 1.0" with something graded, which changes cross-class distances
and therefore any tree built over a mixed inventory.

## D9. The diagonal of a distance matrix is zero

**Decision.** `DistanceMatrix` requires a zero diagonal, symmetry,
finite values and unique labels, and says so at construction.

**Why.** A language compared with itself has no distance. The original
study used 1 as a sentinel so that a minimum search would skip the
diagonal; that collides with any genuine distance of exactly 1.0 and is
unnecessary once the diagonal means what it says. Code that searches
for a minimum should mask the diagonal, not overload it.

## D10. Coverage travels with the distances

**Decision.** `ParallelCorpus.coverage()` reports the fraction of
concepts each language translates, `shared_counts()` reports how many
each pair shares, and `distance()` refuses a pair below `min_shared`.

**Why.** A language distance is a mean over shared concepts, so a pair
sharing few concepts has a mean over a small sample. Ranking those
against well-covered pairs is not wrong arithmetic, but it is
unreadable without the sample size.

## D11. Local alignment is deferred

**Decision.** Only global alignment is implemented.

**Why.** Local alignment needs a contract this package has not decided:
whether the result reports the aligned substrings, the offsets in each
original sequence, or both. Real morphology (`man-abala`) will want it;
guessing the contract now would be worse than adding it deliberately.

## D12. Clustering and trees are not in this package yet

**Decision.** The package stops at `DistanceMatrix`.

**Why.** A matrix is a boundary: clustering can be `scipy`, or
`Bio.Phylo`, or code written here later. Defining the boundary first
keeps the option open. When clustering arrives it must mask the
diagonal rather than assume a sentinel, and it must expose its linkage
method, since single linkage is what the original study used and
average linkage is what most phylogenetic work assumes.


## D13. The corpus holds forms, not tokens

**Decision.** `ParallelCorpus` stores ``{concept: {language: form}}``
with the forms as written, and answers questions about them. It has no
tokenizer, no alignment and no distance.

**Why.** Tokenizing is the inventory's job and comparing is the
aligner's. While the corpus owned a segmenter, changing a tokenizer or
an orthographic profile meant rebuilding the data, and the corpus could
not exist before an inventory did. It also gave the class three methods
whose vocabulary assumed a Swadesh table -- `aligned`, `distance`,
`matrix` -- none of which means anything for a corpus of cognate sets.

**Cost.** Comparing forms now needs both objects. That is the point:
the aligner is what holds them together.

## D14. The inventory belongs to phonfeat, reached through a protocol

**Decision.** `lingaligner` consumes an `InventoryLike`: segments,
categories, an optional `FeatureMatrix`, and `tokenize`. `phonfeat`
owns the implementation. Nothing about notation, symbol tables or
feature systems is duplicated here.

**Why.** The data is `phonfeat`'s business; only the arithmetic is new.
A protocol rather than an import keeps the dependency reading
`lingaligner -> (protocol) <- phonfeat`, so an inventory built
somewhere else -- a test double, or a future generator that derives one
from a corpus -- works without touching this package.

**Cost.** Two contracts to keep in step instead of one class. The
protocol is four members and lives in `inventory.py`.

## D15. Segment distances are lingaligner's, and they explain themselves

**Decision.** `FeatureCost` and `MatrixCost` implement `SegmentCost`:
a `cost` in ``[0, 1]`` and a `describe` that returns the parameters
that produced it.

**Why.** `phonfeat` exposes features and categories; how far apart two
segments are is a modelling decision, not a fact about the notation. A
number separated from its parameters cannot be checked later, so the
two travel together, and `LinguisticAligner.describe` prints them next
to the distances.

**Cost.** A user who wants a third kind of distance writes a class
instead of passing a lambda. That is deliberate: a lambda cannot
describe itself.

## D16. Categories select the mode; the inventory decides

**Decision.** An inventory with no categories gives the unified mode:
every feature is compared, and an undefined cell disagrees with
everything. An inventory that declares categories gives the partitioned
mode: segments in different categories cost `cross_class_cost`
(default 1.0) and are never compared feature by feature.

**Why.** An inventory that is split into classes is making a claim
about which features apply to which segments, and the distance should
respect the claim. An inventory that is not split is making no such
claim, and the undefined cells already produce the graded floor.

**Cost.** The two modes give different cross-class numbers on the same
table: on the Chibchan inventory, a vowel-to-consonant pair costs
0.438-0.812 unified against a flat 1.0 partitioned. Within a class the
ranking is identical in both, so a tree over one class cannot tell the
modes apart -- which is why the mode belongs in `describe`.

## D17. Language operations require a corpus with languages

**Decision.** `language_distance` and `language_matrix` raise
`UnsupportedCorpusError` when the corpus has no languages. There is no
`unit` abstraction standing in for "language".

**Why.** A cognate-set corpus has no languages, and a language distance
over it is a category error rather than missing data; saying so plainly
is better than a generic verb that would then need a generic noun. The
Austronesian case will want its own operations -- a BLOSUM-style
segment matrix is the stated goal -- and those are new methods, not a
reinterpretation of these.

**Cost.** Two operations that only one corpus shape can answer. If a
third shape appears that also has languages, this is the seam to
revisit.

## D18. One facade, and every capability stays reachable

**Decision.** `LinguisticAligner` is the documented entry point, and
every method it offers corresponds to something callable directly --
`align`, `FeatureCost`, `ParallelCorpus.shared`, and so on.

**Why.** A single object is easier to hold and to configure from a
future settings file, but a facade that becomes the only path turns
into the next hardcoded thing: every new corpus type would edit it
rather than extend it. The rule that keeps it honest is that the facade
wires and names; it does not implement.

**Cost.** Two ways to do everything, and the documentation has to say
which one to start with.

