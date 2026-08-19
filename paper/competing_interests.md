# Declaration of competing interest

A. Urias is employed by and holds equity in Aurtech.

This relationship could be perceived as a competing interest, so the study is
constructed to keep the perception from becoming a substantive one:

- No product of Aurtech is evaluated, named, measured or compared against
  anywhere in this work.
- The comparison policy is a **constructed reference policy** derived from the
  C2PA specification's own definition of the `parentOf` ingredient
  relationship. It is not a description of the behaviour of any shipping
  product, and the manuscript states this in the Methods, in the caption of
  every affected figure, and in the claim–evidence boundary table.
- All audio processing is performed by stock FFmpeg through its command line,
  and all signing and validation by the official `c2patool`. Neither is authored
  or controlled by the author, so the artefacts that either do or do not exhibit
  the reported behaviour are produced outside the author's software.
- A non-conformance found in the author's **own** implementation during
  development — overlapping map pieces being aggregated independently, so that
  an overlaid region received two separate claims instead of one mixed claim —
  is reported openly in the Results rather than quietly fixed.
- Every reported number is emitted by committed code into machine-readable
  files, converted into a LaTeX macro by a generator script, and used in the
  manuscript only through that macro; a checker script fails the build if any
  numeric result appears in the manuscript source outside the generated file.

The author declares no other financial or non-financial competing interests.

The corresponding "no competing interests" checkbox in the submission system
should be left **unticked**; this declaration carries the disclosure.
