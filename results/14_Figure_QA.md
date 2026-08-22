# Figure QA

Checks that are run rather than asserted. `tools/figure_qa.py` renders each figure and inspects the result, because an annotation offset that reads correctly at one figure size collides silently at another.

## Automated checks

| check | rule |
|---|---|
| overlapping text | no two text elements in a panel may overlap by more than 6 pt^2 |
| text over data | no text may sit on a plotted line or marker |
| legibility after reduction | no drawn label below 6.4 pt, so a half-size reduction stays above ~3.2 pt |

Latest run:

```
[qa] fig3_promotion: clean (13 text elements)
[qa] fig4_corpus: clean (17 text elements)
[qa] fig5_containment: clean (13 text elements)
[qa] fig6_dilution: clean (16 text elements)
[qa] every figure clean: no overlapping text, no unreadable type
```

## Design rules applied by hand

- One semantic palette in `tools/figstyle.py`, used by every figure.
- No mark is distinguished by hue alone: hue always travels with a marker shape, a line style, or a direct label, so the set survives colour-vision deficiency and a greyscale printer.
- Policy roles are separated in luminance as well as hue, since luminance is what carries greyscale.
- Zeros are drawn as open marks. A zero-height bar is invisible, and an invisible zero reads as missing data rather than as the result it is.
- Direct labels are preferred to legends; where a panel is too small to hold an explanation without collision, the explanation goes to the caption instead of being shrunk.
- One operator naming scheme across every figure, table and caption.

## Output formats

| figure | PDF (bytes) | PNG (bytes) | SVG |
|---|---:|---:|---|
| `fig1_counterexample` | 54,663 | 170,783 | no |
| `fig2_architecture` | 20,036 | 96,869 | no |
| `fig3_promotion` | 27,189 | 190,503 | yes |
| `fig4_corpus` | 25,853 | 254,706 | yes |
| `fig5_containment` | 21,184 | 121,453 | yes |
| `fig6_dilution` | 23,764 | 201,388 | yes |
| `fig7_overhead` | 19,304 | 113,734 | no |

Vector PDF is what the manuscript includes; PNG previews are 300 dpi; SVG is provided for editing.
