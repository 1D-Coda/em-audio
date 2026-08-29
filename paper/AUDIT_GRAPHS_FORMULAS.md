# Audit: graphs and formulas

Two passes. Formulas were checked by exhaustive computation over the claim
domain, not by reading. Figures were checked against the data they encode, not
against their captions.

## Part 1: formulas

### Verified by exhaustive computation

The claim domain is $\{\bot\} \cup (2^{\{C,G\}} \setminus \emptyset)$, four
elements, so every algebraic property can be checked on all cases rather than
argued.

| Property | Cases checked | Result |
|---|---|---|
| Eq. 2 is reflexive | 4 | holds |
| Eq. 2 is antisymmetric | 16 | holds |
| Eq. 2 is transitive | 64 | holds |
| Eq. 3 is a lower bound of its arguments | 16 | holds |
| Eq. 3 is the *greatest* lower bound | 16 | holds |
| Meet is commutative, associative, idempotent | 16 / 64 / 4 | all hold |
| $\bot$ is absorbing and is the bottom element | 4 / 4 | holds |
| No greatest element exists | 4 | confirmed, so "meet-semilattice" is the correct term and "lattice" would be wrong |
| Prop. 4: enlarging $D_y$ never strengthens the claim | 340 source multisets | 0 violations |

Eq. 2 is therefore a genuine partial order and Eq. 3 is genuinely its meet.
Both were stated correctly.

### Defects found and fixed

1. **Proposition 1's statement was false in one case.** It asserted
   unconditionally that "$P_y$ contains every atom present on a required source
   and no other". When any required source is $\bot$, the meet gives
   $P_y = \bot$, which contains no atoms at all, so the clause fails whenever a
   source is unverified. The *proof* handled the case; the *statement* did not
   condition on it. The conclusion was never unsafe (the output is weaker, never
   stronger), but a formal-methods reviewer would have caught the imprecision.
   The statement now separates the ordering clause, which holds always, from the
   exact-union clause, which holds when no source is $\bot$.

2. **Theorem 1 did not name requirement (iv$'$).** It said "each satisfying
   (i)--(v)", and (iv$'$) is the one requirement this work adds over its
   predecessor. It is now named explicitly in the theorem statement.

3. **The semilattice claim was asserted, not justified.** The text called
   $\widehat{\mathcal{C}}$ a meet-semilattice without saying why it is not a
   lattice. It now states that $\{C\}$ and $\{G\}$ have no upper bound, because
   an upper bound would have to be a non-empty subset of both, which is why the
   weaker term is the right one.

## Part 2: figures

### Defects found and fixed

1. **Figure 5 argued against its own caption.** The panel titles claim cost
   grows *linearly* in the number of evidence intervals, but the x-axis was
   $\log_2$ and the y-axis linear, so a linear relation rendered as an
   exponential-looking curve. A reader glancing at the figure saw explosive
   growth, the opposite of the finding. Both axes are now linear, the measured
   points now fall on a visible straight line, and a linear fit is drawn behind
   them so the claim can be checked by eye.

2. **Figure 5 contained a rendering artifact.** The right-hand title printed
   `0.16\% of FFmpeg time`, with a literal backslash, because a LaTeX escape was
   passed to matplotlib text. Fixed.

3. **Figure 4's right panel encoded almost nothing.** Its four bars were
   600, 600, 0 and 0: two at the maximum and two at zero, duplicating a row of
   the main results table. It has been removed and the figure is now a single
   informative panel. The counts remain in the text and the table.

4. **Figure 4's legend pointed at nothing.** Complete-source promotion is zero
   for every transformation, so its bars had no extent while a green legend
   swatch implied a visible series. The series is now drawn as explicit markers
   at the origin, and the legend label says "0 for every transformation".

5. **Figure 3's middle panel had a legend sitting on top of data.** Every bar
   in that panel reaches past 90%, so an in-axes legend at lower right covered
   the silence-removal bar. It also duplicated the key already given in the left
   panel. Removed.

6. **Zero-valued series were invisible in two panels.** Complete-source
   promotion is zero everywhere, so its bars had no extent while the legend
   implied a drawn series. Both the single-operator panel and the corpus figure
   now show it as a marker at the origin, and the captions say so.

7. **Figure 3's truncated axis was undisclosed.** The control panel runs
   80--100%. The truncation is defensible, since it makes any divergence between
   measurement and closed form more visible rather than less, but it was not
   stated. The caption now states it.

### Checked and left alone

- All bar charts start at zero.
- Figure 3's left panel plots two flat lines. Flatness is the finding, not an
  absence of one, and the caption says so, so a line encoding is appropriate.
- Figure 1 uses no quantitative axis and makes a qualitative point; no scale
  can mislead.
- Colour choices are distinguishable in greyscale and the red/green pair is
  reinforced by position and by text labels, so the figures do not rely on hue
  alone.

## Part 3: claims

Every use of "proves", "guarantees" or "ensures" was extracted and checked. All
nine are either properly hedged, attributed to the cited work rather than to
this one, or refer to a proposition proved in the paper.

One unverified mechanistic claim was found and corrected. The text asserted that
a rate change "scales the bands inherited from upstream". That follows from the
interval model, but the composition experiment cannot isolate it, because the
chain's only rate change happens at depth 2 when no upstream bands exist yet.
The text now reports what the data does isolate, that depth 4 equals depth 3 to
the last digit because the operator added there declares a zero footprint, and
labels the rate-scaling as a property of the model rather than a measurement.


---

# Round 4: support containment, terminology and table semantics

A fourth review round raised eight points. All eight were verified against the
source and the specification text, and all eight were correct.

## The substantive one

**Output-length agreement was being treated as evidence of support
containment.** The text said the guard bands covering the observed
predicted-versus-actual deviation "is the condition Proposition 4 requires". It
is not. Proposition 4 requires the declared required-source set to *contain* the
actual dependency set, and an operator can emit exactly the predicted number of
samples while depending on source samples outside the declared footprint. The
transformation matrix bounds mapping and alignment; it says nothing about local
dependency.

Rather than only weakening the prose, the containment condition is now tested
directly. **Experiment K** builds two sources identical except at one sample,
where one carries an added impulse, pushes both through the same stock ffmpeg
command, decodes both and subtracts. Every output sample whose decoded value
differs was influenced by that one source sample and by nothing else, because
the inputs differ nowhere else. Containment holds when the probe position lies
inside the declared required-source range of every output sample it influenced.
The threshold is one 16-bit LSB, so an influence far below audibility still
counts. Across 70 probes over 7 operator configurations, 19,582 output samples
were influenced and 0 fell outside the declared support.

Two things emerged while building it, both reported in the paper:

- **A harness bug that produced 695 false violations.** The first version
  decoded every output at the source rate, which resampled the output of a
  rate-changing operator back up, so output indices no longer matched the
  model's coordinates. Fixed by decoding at each file's own rate.
- **Probing against silence badly under-tests signal-dependent operators.** An
  impulse in an empty buffer is copied through, so every operator looks like a
  one-to-one map. The probe now carries a deterministic non-silent tone. Time
  stretching went from an apparent 1-sample dependency to 2,021 samples at the
  probe positions that land inside an overlap region.
- **The spread statistic was both wrongly computed and the wrong statistic.**
  The median took the upper-middle element rather than the true median, and for
  overlap-add time stretching the median is 1 while the maximum is 2,021,
  because only 3 of 10 probe positions land in an overlap. Containment is a
  worst-case property, so the maximum is now reported and the position
  dependence is stated.

The margins also justify the particular bands rather than merely permitting
them: the closest any measured influence came to the edge of its declared range
was 65 samples against a declared 97 for resampling, 898 against 2,304 for MP3,
and 688 against 2,577 for time stretching.

## The other seven

1. **"Lattice" where the paper proves "meet-semilattice".** Section 4.2 proves
   the structure has no joins, yet three other places said lattice. Corrected
   throughout; zero occurrences remain.
2. **The provenance-semiring characterisation was inaccurate.** The text
   described the framework as combining annotations "associatively and
   idempotently" and referred to "absorptive semirings". Idempotence is not part
   of the general framework and is incompatible with several of its standard
   instances. Rewritten to describe combination as associative and distributing
   over alternative derivations, with idempotence attributed to this particular
   structure.
3. **The main results table was semantically misleading.** Section A's "0
   failed" sat under the *Boundary-only* column, where it means nothing, and the
   regression-test row the text cited did not exist. Section A outcomes now span
   both comparison columns, and a named-regression-test row was added.
4. **The machine was said to be declared but never was.** Methods claimed
   timings were reported "with the machine declared" while no CPU, OS or runtime
   appeared anywhere. Now stated, and generated from the environment rather than
   typed so the number checker stays strict.
5. **The robustness arm was missing from Data Availability.** It named only
   LibriSpeech and eSpeak NG. It now names the Piper voice, its LJSpeech
   provenance, the checksum-verified fetch and the seeded noise generation.
6. **The duration result was over-generalised.** "Falls in inverse proportion to
   asset length" is conditional on a fixed chain and a fixed boundary count,
   since more boundaries would place more bands. Now stated conditionally.
7. **The `c2pa.placed` reading was too categorical.** The specification does not
   state that concatenation is not mixing, and `c2pa.remixed` explicitly covers
   re-arranging. The text now says we *interpret* sequential concatenation as
   placement, notes `c2pa.remixed`, and separates the one part that is not
   interpretive: `c2pa.mixed` presupposes `c2pa.placed`.
8. **A preprint was called a "published analysis".** Now "a publicly available
   security analysis, a preprint at the time of writing", matching the
   bibliography's own label.


---

# Round 5: eleven corrections, two of them worse than reported

All eleven points were verified against the source, the rendered PDF and the
C2PA site, and all eleven were correct. Two had a cause the review had not seen.

## The two that were worse than described

**The 33-versus-97 footprint inconsistency had a structural cause.** Table 3's
33 was the bare kernel radius for the 16 to 8 kHz configuration; the containment
experiment's 97 was that same radius plus the 64-sample guard band. Two
different quantities were both being labelled "declared footprint", which is
precisely the distinction the paper had just spent a section establishing. The
fix is therefore not a footnote but a restructured table: Table 3 now carries
**Kernel**, **Guard** and **Declared** as separate columns computed from the
implementation constants, so resampling reads 33 + 64 = 97 and reconciles with
the containment table by construction.

**The results-table defect was genuinely not fixed the first time.** The
previous round replaced the misplaced value with `\multicolumn{2}{c}`, which
centres across the two comparison columns. Because column 3 holds narrow
right-aligned numbers, the centred text still landed under *Boundary-only* in the
rendering. The error was in the checking, not only in the fix: the `.tex` source
was inspected instead of the rendered page. Extracting the PDF layout confirmed
"0 failed" sat at the same horizontal position as "9,455 (94.5\%)". Section A
rows now span columns 2 to 4, left aligned, so no value sits under either
comparison header. Verified by re-extracting the rendered layout rather than by
reading the source.

## The other nine

1. **Section 5.2 still asserted that the transformation matrix tests whether the
   footprint bound holds.** It now states that Section 7.4 validates mapping and
   alignment, Section 7.6 probes support containment, and neither substitutes
   for the other.
2. **The Limitations calibration proposal repeated the same conflation.** It is
   now split into a mapping-guard calibration, driven by output-length
   deviation, and a support-footprint calibration, driven by an impulse sweep,
   with an explicit note that substituting the first for the second is the error
   this paper had to correct in its own draft.
3. **The normalisation row in the containment table implied a measured
   computational support of zero.** It now carries a dagger: the zero is a
   representational footprint, the gain depends computationally on the whole
   signal, and the probe confirms the representational reading only.
4. **The claim--evidence boundary had no row for the containment experiment.**
   Added, with what it does not establish stated: containment for probe
   positions, signals, codecs or configurations not tested.
5. **"Influenced by that one source sample and by nothing else" was
   attackable.** Every other source sample does contribute to every output
   sample. The claim is now that the paired *difference* is attributable to the
   perturbed sample, because the other contributions are identical in both runs.
6. **The seven-versus-eight configuration count was unexplained.** Overlay is
   excluded because its required-source set is by construction every covering
   source and the sample-wise sum has no temporal kernel, so there is no
   footprint to under-declare.
7. **Table 1 still said "independent oracle"** while the paper elsewhere denies
   author independence. Now "separately implemented oracle".
8. **The July 2026 C2PA implementation guidance was missing.** Checking it
   helped rather than hurt: it develops the vocabulary for representing AI
   involvement, including `digitalSourceType`, an AI-disclosure assertion and
   regions of interest localising affected audio segments, and defines no
   aggregation rule. It is cited as sharpening the same boundary from the other
   side.
9. **The clean-clone description overstated slightly.** "Self-contained" is now
   "self-contained conditional on the two checksum-pinned external artefacts",
   in both the manuscript and the reproduction record.


---

# Round 6: six corrections, and an "optional" item that found a real defect

All six points verified and applied. Two produced findings larger than the point
that prompted them.

## The MP3 arithmetic, and what it was hiding

The conjecture in the review was exactly right: 1728 + 576 = 2304. The
implementation used `max(kernel, guard)` with the guard set to 2304, which
produced the correct declared value by coincidence while breaking the additive
relationship every other row obeyed. The guard is now 576, one MPEG-1 Layer III
granule, which is a principled frame-alignment quantity, and the operator uses
kernel + guard like everything else. The declared value is unchanged, so no
result moved, and all nine rows are additive.

The bit-reservoir observation was also correct. `libmp3lame` defaults to
`reservoir=1`, confirmed by encoding with and without: the default is
byte-identical to `-reservoir 1` and differs from `-reservoir 0`. The reservoir
is left enabled, since a stateful encoder is the harder test, but it is now
pinned explicitly rather than inherited, and the declared footprint is described
as an empirically validated bound for that frozen configuration rather than a
consequence of the MDCT window alone.

## The optional item was not optional

Adding three further signal contexts to the containment probe was offered as an
optional hardening. It broke containment, and the diagnosis produced two
findings.

**The probe design was wrong.** A fixed impulse amplitude was roughly two
hundred times the carrier in the low-level context. That does not perturb an
adaptive operator's input so much as replace it: the lossy encoder re-allocated
bits globally and the overlap-add stretcher re-selected its correlation lag, so
the measured "dependency" was really the operator choosing a different mode. The
perturbation is now a fixed multiple of each context's peak.

**One declared bound was genuinely inadequate.** A short probe passes trivially
for large-footprint operators, because a 2577-sample declaration spans a whole
short source. Lengthening the probe until the declaration covered a fraction of
the source made the test able to fail, and silence removal failed: a
frame-granular selector reached 3277 source samples before a retained run's
start, against a guard then declared at 2048. That is under-declaration, the one
direction Proposition 4 does not forgive. The band is now 4096.

Both are reported in the manuscript rather than silently corrected, and the
episode produced a limitation worth having: **a fixed footprint bounds
dependency at an operating point, not across mode changes.** A change large
enough to restructure an encoder's decisions is not a representation-only
transformation of the interval it lands in.

## The build gate caught the author

Writing up those findings, four numbers were typed by hand: two reproducible
constants, and two measurements, one of which came from a configuration that no
longer exists. `check_numbers.py` failed the build. The response was not to
whitelist them but to make the quantity measurable: the containment experiment
now reports, per operator, the **maximum measured reach** beyond the nominal
footprint-free source range, so containment is the comparison of a measured
reach against a declared bound and both regenerate on every run.

| Operator | Declared | Measured reach | Headroom |
|---|---:|---:|---:|
| resample 16 to 8 kHz | 97 | 32 | 65 |
| transcode to MP3 | 2,304 | 1,555 | 749 |
| time stretch 1.10 | 2,577 | 1,906 | 671 |
| silence removal | 4,096 | 3,277 | 819 |

## Also fixed

The double-counted "declared footprint plus guard"; the support domain lifted to
$\mathcal{S} = \{\bot_\mu\} \cup [0,1]$ with $\bot_\mu \preceq s$, making
Propositions 2 to 4 formal rather than partly semantic; and "any conforming
validator" narrowed to the pipeline actually demonstrated with the official
tool.

## One incident worth recording

A pipeline run failed with 56 errors that were disk exhaustion, not defects:
roughly 1.2 GB of gitignored per-experiment working directories had accumulated
across the session and filled the volume. `run_all.sh` returned a failure rather
than passing silently, which is the correct behaviour under an error class that
had never been exercised. No data was lost: all 17 result files remained valid
and the tagged release was untouched.


---

# Round 7: a conceptual error of my own, and a missing paper with the problem's name on it

Eight points, all verified and all correct. Two were substantive.

## The kernel/guard claim was wrong, and my own data said so

The manuscript claimed that Section 7.4 bounds the guard column and Section 7.6
bounds the kernel column. The containment measurements contradict that:

| Operator | Analytical | Measured reach | Reach within analytical? |
|---|---:|---:|---|
| silence removal | 0 | 3,277 | no |
| time stretch 1.10 | 529 | 1,906 | no |
| transcode MP3 | 1,728 | 1,555 | yes |
| resample 16 to 8 kHz | 33 | 32 | yes |

For two operators the measured influence is contained only by the declaration as
a whole, so the containment experiment validates the **declared footprint** and
never the analytical column independently. This was a clean case of a sentence
written to describe a tidy separation that the experiment did not actually
establish, in a paper whose whole subject is not claiming more than the evidence
supports.

The columns are now **Analytical / Margin / Declared**, the text says Section 7.4
characterises mapping deviation and informs the margin while Section 7.6 tests
the declaration, and the caption states outright that for two operators the
reach exceeds the analytical radius.

## The mode-change limitation was indefensible as written

It said a change large enough to restructure an encoder's decisions "is not a
representation-only transformation". That is wrong: a transcoder is
representation-only whether or not its internal bit allocation is input-adaptive,
which is a property of the operator and not of the diagnostic perturbation. It
also said "no fixed footprint bounds that", which is literally false, since a
whole-asset footprint does.

Rewritten to what is actually supported: the measured footprints characterise
dependency around the tested operating points and do not establish a universal
support radius over every input-induced mode transition; the open question is the
size of a local radius rather than whether a bound exists; and an implementation
that cannot validate a local radius may declare whole-asset dependency, which
remains safe under Proposition 4 at the dilution cost already quantified.

## A directly relevant paper was missing

Gerhardt, Cuccovillo and Aichroth, *Audio Provenance Analysis in Heterogeneous
Media Sets*, CVPR 2024 Workshop on Media Forensics, pages 4387-4396. A paper
with the phrase "audio provenance analysis" in its title, absent from a
manuscript about audio provenance, is an obvious opening for any reviewer in
that community.

It is adjacency rather than duplication, and citing it strengthens the novelty
argument rather than weakening it. Their method reconstructs reuse and
parent-child relations from an unknown signal using partial matching and
phylogeny; this contract assumes signed evidence already exists and constrains
how a known operator may aggregate it. It now has a Related Work paragraph and a
Table 2 row saying exactly that.

## Five smaller corrections

The claim-evidence row said interval-model fidelity was checked "on every run",
where Section 7.4 says every PCM run plus a 100-clip subset for the coded
containers; the row now matches. The four probe signal contexts were counted but
never named, and are now described. The dilution caption said "declared guard
bands" where the radius is the declared footprint, which already includes the
margin. Theorem 1's proof still said "transitivity of $\le$" after the support
domain was lifted, and now uses $\preceq$. One sentence began lowercase.


---

# Round 8: two reviews of very unequal quality, and a defect underneath one of them

## The reviews sort out differently

Review A raised seven issues. Six were **already addressed** in the current text:
footprint locality with re-validation guidance, the oracle threat-to-validity
framing, the amplitude-normalisation dual reading, the silence-removal
re-declaration caveat and the dilution qualification. Its minor-flaws section was
worse than unhelpful: the claimed "Reply -> Replay" typo does not exist, the
claimed page-2 line-number artefact does not exist (no `lineno` package is
loaded), and two of its three "inconsistencies" quote the same string twice
("codec" vs "codec", "Figure 1" vs "Figure 1").

Review B's quantitative audit, by contrast, checked out line for line against the
result JSON: every dilution figure, 3,600/4,800 = 75% including which two
operators do not promote, 9,455/10,000, and the zero-event bounds.

## The defect underneath the applicability clause

Review B was right that clause (iii) read $A_y(\mu) \subseteq \bigcap A_x(\mu)$
where every sibling clause is an equality, while the abstract, both proofs and
the conclusion all say "intersected".

Verifying that surfaced something the review did not reach. Clause (ii)'s
antecedent never mentioned $A_y(\mu)$, so a channel narrowed to an empty scope
under (iii) would still be **required** to carry a value: a number declared
applicable nowhere. Nothing excluded it. P4 iterates $S$, P5 iterates $A$, and
the `Evidence` invariant rejected a missing key but not an empty scope. The bad
record was confirmed constructible.

Fixed at three levels: (iii) is now the equality with an explicit narrowing
allowance, (ii) carries the applicability condition, the constructor rejects an
empty scope, and a new conformance check `P8_channel_scope_agreement` runs over
the full enumeration (98,385 cases, total checks 787,443 -> 885,828). The
regression test fails when the invariant is reverted.

## Where the subagent over-reached

On lineage, the verification agent proposed redefining a lineage token as
asset-plus-range. That was wrong: temporal placement **is** carried, by the
per-interval decomposition, since every serialised record has its own `samples`
bounds. Redefining the token would duplicate that. The real defects were smaller
and different: the hedge "directly or reproducibly" was never defined and is
unachievable for `concat` and `silence_removal`, which serialise only `n_parts`
and `n_runs`, and the clause never said where placement lives. Repaired
accordingly.

Worth recording as a pattern: a verification agent that finds a real problem will
sometimes propose a fix scaled to its own analysis rather than to the problem.

## The typed-channel claim was false, the gap behind it real

Review B asserted the channels are not exercised concretely. They are:
`capture-support` aggregates 0.90 and 0.10 to 0.10 by minimum inside a
c2patool-validated `Trusted` manifest. But the manuscript named the channel
exactly once, so a reader could not have known. Now introduced properly, and
`CAPTURE_SUPPORT` is hoisted from seven duplicate definitions into one.

## Two defects the build could not see

**Doubled periods, 30 of 30 paragraph heads.** `elsarticle`'s `\paragraph`
appends its own period, so a heading already ending in one renders as two. The
source was correct; only the built PDF showed it. Caught by Review B, fixed here
and in the supplement, and `prose_audit.py` now extracts the rendered PDF and
fails on recurrence.

**A dangling supplement pointer**, which neither review pinned. The supplement's
two longtables carry no `\caption{}`, so `\thetable` is never used and there is
no Table S3 at all, only Section S3. `check_numbers.py` now resolves every
supplement pointer against what the supplement actually numbers.

## A reproducibility finding from running the pipeline repeatedly

Across nine measurements on one machine the absolute bookkeeping cost per
audio-minute spanned 0.954 to 1.362 ms, a spread of roughly 43%, while the ratio
to the boundary-only baseline stayed between 3.34 and 3.44, a spread of 3%. Both
arms are timed in the same process, so thermal state, frequency scaling and
competing load move them together and cancel in the quotient. The within-run
interquartile ranges do not capture this, because it is between-run variation.

The manuscript now says the ratio is the quantity to carry across machines and
that a reader reproducing the work should expect the ratio to survive and the
milliseconds not to. This also corrects a mistaken diagnosis made mid-session:
0.954 ms was the fast outlier, not a clean baseline, and the 1.31 ms figures
were typical rather than degraded.


---

# Round 9: a false proposition, and the check that was blind in the same way

## The counterexample was real, and the blind spot was threefold

A reviewer produced a counterexample to Proposition 4's support clause: with
$\Dy = \{x_1\}$ where channel $\mu$ is not applicable to $x_1$, the channel is
unavailable; enlarging to $\Dy' = \{x_1, x_2\}$ where $x_2$ declares $\mu$ with
value $v$ makes it $v$. Since $\bot_\mu \prec v$, enlarging the required-source
set strengthened the claim. It reproduces in the implementation.

The proof's gap was the sentence "enlarging $\Dy$ can only add members to
$\Dy^{\mu}$, and the minimum over a larger set is no larger", which silently
assumes $\Dy^{\mu} \neq \emptyset$. Going from empty to non-empty moves up.

What made this worth more than a one-paragraph repair is that
`P_footprint_monotone` had the identical gap: it compared a channel only when
present on both sides, `if mu in n.ev.S and v > n.ev.S[mu]`, so the one
transition that breaks the proposition was the one comparison it skipped. Proof,
check and implementation shared a single blind spot.

## The decision, and why the harder repair won

Two repairs were available. Weaken the proposition to channels already
applicable on $\Dy$, or strengthen requirement~(iv) so a channel is available
only when $\Dy^{\mu} = \Dy$.

The second was chosen. The first narrows a claim to fit a system that remains
unsound precisely in the regime the paper recommends: over-declaring the
dependency set can emit support derived from a source the output does not
depend on. The second makes the claim true, unifies (iv) with the
partial-subset principle it already states for applicable-but-unreported
sources, and costs nothing measured, since all 98,385 cases and 885,828 checks
pass identically under both rules.

The cost is expressiveness, and it is now stated in the paper rather than left
implicit: sources carrying different channel schemas yield no channel on a
shared interval rather than a partial one. That is conservatism where the
alternative was unsoundness.

A third option, separating "not applicable" from "applicable but unavailable" so
the states are incomparable, was rejected. It repairs the order theory without
repairing the semantics: over-declaring would still emit a value derived from a
non-dependency, and the model would look sound while keeping the hazard.

## The battery that would have caught it

The v1 enumeration cannot reach these cases: one channel over one scope, every
non-$\bot$ source declaring it, every $\bot$ source absorbed by~(iv$'$). A
synthetic battery over five scopes, disjoint, nested and partially overlapping,
enumerates 441 source-set enlargements. Under the repaired rule, zero
violations. Under the superseded rule, **80**, including the reviewer's exact
case. The battery measures both rules on every run, so the reason the rule
changed regenerates instead of being asserted.

## The calibration tool

The manuscript had said outright that neither calibration pass was implemented.
Both now are. Writing it exposed two flaws in its own design. A flat safety
constant recommended 608 samples for a resampler whose reach is 32, so the
margin is proportional with a floor. More seriously, the first version probed
six positions where the validation uses ten: a calibration that under-measures
relative to its own validation can recommend a declaration the validation then
rejects. With the positions matched, the tool's reaches equal the containment
experiment's on all seven operators, which is the cross-check that both measure
the same quantity.

It also separates requirement from policy. Containment of the measured reach is
soundness; the advisory margin is conservatism. Two shipped declarations sit
below the advisory while containing their reach, and are marked rather than
quietly raised, since raising them costs dilution and would launder a policy
preference as a safety finding.

## One claim that was not true

The code-availability statement said the artifacts "are public under the MIT
licence". There is no git remote; nothing has been published. The sentence now
describes what holds, MIT licensing and one-command reproduction, and defers the
URL rather than asserting availability a reader cannot act on.


---

# Round 10: the tool that had never been shown to fail

Two findings, both about code written in the previous round.

## The docstring overclaimed, in a paper about not overclaiming

The calibration tool's own documentation said its support pass "sweeps a
proportionate impulse across the input". It strikes ten positions out of
sixteen thousand, 0.061% of the input. "Sweep" implies exhaustive; this is a
probe at chosen positions. Both the tool and the manuscript now say so, along
with why those positions were chosen, the operators' own cut points and edges,
where an under-declaration surfaces first, and what the design cannot do, which
is discover a mode transition occurring only at an untested position.

## The tool had only ever certified, never rejected

The sharper finding. The calibration tool had run seven times and passed seven
times. Its ability to detect an under-declaration was assumed, never
demonstrated, which is the same defect as a conformance suite that has never
failed. Two rounds earlier this exact principle went into the transferable
checklist, "make sure the probe CAN fail before believing it passed", and it was
not applied to the tool that was written to enforce it.

There is now a `--self-test` that forces MP3's declared footprint to 1,554,
exactly one sample below its measured reach of 1,555, and fails unless the run
rejects it. It detects one sample outside, the tightest demonstration the
measurement allows, and it runs in the pipeline on every invocation.

## Smaller repairs from the same review

The advisory margin truncated where it should have taken a ceiling, differing by
one sample in three of four operators. Harmless while the margin is advisory, a
silent under-round if a caller ever promotes it to a declared bound. All 280
per-probe records are now retained rather than the maximum alone, so a reader can
see which position and context produced each reach; MP3's worst is the dense
context at position 8192. And the overhead ratio is computed from unrounded
medians, so dividing the two printed figures gives 3.41 where the paper reports
3.38; the text now says which.

## What remains outside the code

Three reviews have now flagged artifact access. There is still no git remote, so
the calibration tool cannot be run by anyone else, the repository URL cannot be
printed, and independent reproduction cannot begin. This is the only open item
that no amount of further work on the manuscript can close.


---

# Round 11: a stale artifact, and a stability claim resting on an unstable statistic

## The artifact drifted one round behind the paper

A reviewer cross-checked the manuscript's claims about the calibration tool
against the copy they had been sent, found no per-probe retention and no
self-test, and concluded that the manuscript overstated its artifact. That was
the correct reading of the evidence available to them, and the fault was
packaging, not prose: the features were added in round 10, the manuscript was
updated to describe them, and the file was never re-sent. Their hash
`d1c472c4` is the pre-round-10 version; the current file is `fcf9ed9b`.

The general rule this earns: **when a claim about an artifact changes, the
artifact ships with the claim.** A paper and its code drifting apart by a single
round is how an honest statement becomes an overstatement without anyone
intending it.

## The timing question, and what it exposed

The same reviewer asked which optimisation reduced the bookkeeping cost from
1.33 to 0.926 ms per audio-minute. None did. Six back-to-back runs gave 0.9025
to 0.9491; earlier in the same session the identical code gave 1.30 to 1.36. Two
tight clusters, far apart, separated by machine state rather than by code.

Answering that with a measurement rather than an assertion produced a defect of
its own. The first version measured dispersion as the min-max range over five
runs, and the manuscript said the ratio was tighter "by more than a factor of
three". Three successive measurements gave factors of 3.6, 2.5 and 1.4. The
direction held every time; the magnitude did not survive being measured again.

Two things were wrong. The prose asserted a relationship between two
regenerating macros, so the sentence contradicted its own table as soon as the
numbers refreshed; the number checker cannot catch that, because the claim lives
in the relationship rather than in any digit. And a range over five runs is set
by whichever single run happened to be worst, which makes it the wrong statistic
for an argument about stability.

It now reports the coefficient of variation over nine independent runs, which
uses every sample, and the manuscript says why that statistic was chosen. The
experiment checks its own prediction and reports failure if the ratio is ever
not the tighter quantity.

## Smaller items from the same review

The calibration tool gained `--keep-work` and now announces its cleanup rather
than deleting a directory silently. The overhead ratio's provenance, computed
from unrounded medians, is stated where the ratio appears.

## Standing item

Five reviews have now led with artifact access. There is still no git remote.


---

# Round 12: benchmark provenance, and a claim about a file the file did not keep

The review asked for CPU model, fixture size, warm-up policy and launch
details. Half of it already existed: repetitions, clips per repetition and
audio-minutes per repetition were recorded all along. Two things were genuinely
missing, and one of them was a claim the artifact did not honour.

## The processor was recorded as an architecture

`platform.processor()` returns `arm` on this machine and the preflight report
recorded `cpu: arm64`. That is not reproducible provenance for a timing result:
"arm64" spans parts that differ several-fold in single-core throughput. The
environment block now captures the model through `sysctl` on Darwin and
`/proc/cpuinfo` elsewhere, giving Apple M3 Max, 14 logical cores, 36 GiB.

The sharper half is that the manuscript already said "the exact processor,
operating-system build and every tool version are recorded in
\texttt{results/PREFLIGHT.txt}". The exact processor was not in that file. A
sentence describing an artifact had drifted from what the artifact contained,
which is the same failure as the stale calibration script one round earlier,
in a different direction: there the code lagged the claim, here the report did.

## The warm-up policy was unstated because there is none

The benchmark has no warm-up iteration; the first repetition sits inside the
median with the other twenty-nine. Rather than assert that this cannot matter,
the experiment now measures it: discarding the first repetition moves the median
by 0.08%, well under the run-to-run variation reported alongside. The policy and
the check are both stated, so a reader does not have to wonder whether a cold
iteration is buried in the figure.

Also recorded, because they are limitations rather than features: a single
process, launched with no processor-affinity or power-management control.

## Corroboration of the previous round

The same review observed the absolute cost moving 0.926 to 1.304 ms, +40.8%,
while the ratio held at 3.36 to 3.38, and accepted it as "exactly the pattern
expected if machine state affects both arms similarly". The stability experiment
added in the previous round is what made that legible rather than suspicious.

---

# Round 12: the reproduction happened, and it failed twice on purpose

The open item above is closed. The package was delivered directly rather than
through a remote, and D. A. Balderrama-Alvarez ran it twice on his own machine
(Linux on WSL2, x86_64, Python 3.14.4, FFmpeg 8.0.1, against macOS arm64,
Python 3.11.15, FFmpeg 9.0.1).

Eight of the ten compared result files came back with zero deterministic
differences and every headline count in the paper returned unchanged. The 189
differences that remain sit in two files and trace to one cause: his FFmpeg
build behaves differently from the one the footprints were calibrated against.
The MP3 encoder's measured reach is 4,317 source samples against a declared
2,304, putting 110 output samples outside the declared support; silence
removal's model-versus-FFmpeg deviation is 12,505 samples against a declared
margin of 4,096, because his `silenceremove` leaves 16,384 samples where the
reference leaves 13,312.

Both runs produced identical numbers, which is what makes them findings rather
than noise. They are reported in Section 7.11 as results, and the declarations
were not widened to absorb them: a table adjusted until two builds pass, tested
against neither, is the practice the paper argues against.

Two things worth recording about the process rather than the outcome. The first
package shipped `results/machine_readable/` populated with the author's own
results, so his failed experiments left those files in place and the comparison
reported a match that never happened; his first-run `C2_robustness.json` was the
author's file. The directory now ships empty, with a separate
`results/reference/` snapshot, and `verify_reproduction.py` detects the
inherited-file case. The second is that the classifier's environment-field list
originally matched on substrings, so `max` matched
`max_measured_reach_source_samples` and both of the findings above were reported
as expected environment variation by the one tool whose job is to decide what
counts as a real failure.

## What remains outside the code

The repository is still not published, so the URL cannot be printed and the
Zenodo DOIs cannot be assigned. That is now the only open item.
