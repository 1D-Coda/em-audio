# Declaration of competing interest

The author declares no competing financial or personal interests.

The author is not employed by, funded by, or financially interested in any
organisation that develops, sells or plans to sell media-provenance,
content-authenticity or digital-forensics products, and no such organisation had
any role in the design, execution, analysis or reporting of this work.

The study is nevertheless constructed so that its central comparison cannot be
tilted by the author, and the following are stated for the reader's benefit
rather than as mitigations of a disclosed interest:

- No commercial product is evaluated, named, measured or compared against
  anywhere in this work.
- The comparison policy is a **constructed reference policy** derived from the
  C2PA specification's own definition of the `parentOf` ingredient
  relationship. It is not a description of the behaviour of any shipping
  product, and the manuscript states this in the Methods, in the caption of
  every affected figure, and in the claim-evidence boundary table.
- All audio processing is performed by stock FFmpeg through its command line,
  and all signing and validation by the official `c2patool`. Neither is authored
  or controlled by the author, so the artefacts that either do or do not exhibit
  the reported behaviour are produced outside the author's software.
- A non-conformance found in the author's **own** implementation during
  development, overlapping map pieces being aggregated independently so that an
  overlaid region received two separate claims instead of one mixed claim, is
  reported openly in the Results rather than quietly fixed.
- Every reported number is emitted by committed code into machine-readable
  files, converted into a LaTeX macro by a generator script, and used in the
  manuscript only through that macro; a checker script fails the build if any
  numeric result appears in the manuscript source outside the generated file.
- The independent reproduction reported in Section 7.11 was performed by a
  researcher at a public university who is not an author, has no relationship
  with the author beyond this reproduction, and reported two failures that are
  published as findings rather than resolved by adjusting the declarations that
  failed.

The corresponding "no competing interests" checkbox in the submission system
should be **ticked**, and this file may be attached as the declaration.
