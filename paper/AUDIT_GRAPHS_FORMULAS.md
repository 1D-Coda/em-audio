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
