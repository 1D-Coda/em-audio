# Third-party data and tool licences

All licence statements below were read from the primary source named, on the
access date given, and re-checked before submission.

## Captured-speech source

| Field | Value |
|---|---|
| Corpus | LibriSpeech ASR corpus, `dev-clean` subset (OpenSLR resource 12) |
| Primary licence text | `corpus/LibriSpeech/LICENSE.TXT`, shipped inside the archive |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| Verbatim | "LibriSpeech ASR corpus is licensed under a Creative Commons Attribution 4.0 International License." |
| Redistribution | Permitted, including of derived clips, with attribution |
| Citation | Panayotov, V., Chen, G., Povey, D., Khudanpur, S. (2015). LibriSpeech: an ASR corpus based on public domain audio books. ICASSP 2015 |
| Underlying material | LibriVox public-domain audiobook recordings |
| URL | https://www.openslr.org/12/ |
| Archive SHA-256 | `76f87d090650617fca0cac8f88b9416e0ebf80350acb97b343a85fa903728ab3` |
| Access date | 2026-08-19 |
| Login wall | None. Fetch is scripted in `tools/fetch_corpus.sh`. |

No speaker is identified, no voice is cloned, and no speaker-identity claim is
made anywhere in this work.  The corpus is used only as a source of genuinely
captured audio with a redistributable licence.

## Generated-speech source

| Field | Value |
|---|---|
| Generator | eSpeak NG 1.52.0, formant synthesis |
| Program licence | GPL-3.0-or-later |
| Output | Synthesised from fixed English phrases written for this study; no voice model of any real person and no third-party audio is used, so the generated segments are original material produced locally |
| Redistribution | The generated clips are redistributed under this repository's MIT licence |
| Determinism | Fixed voice (`en-us`), fixed speed/pitch per clip index, no randomness |

## Tools in the processing path

| Tool | Version | Licence | Role |
|---|---|---|---|
| FFmpeg | 9.0.1 | LGPL-2.1-or-later / GPL-2.0-or-later (this build is `--enable-gpl`) | the only software in the audio signal path |
| c2patool | 0.27.2 | MIT / Apache-2.0 | signing and validation of C2PA manifests |
| Node.js | 26.0.0 | MIT | second-language differential oracle |
| Python | 3.11.15 | PSF | reference implementation |

## Signing credential

The signed-transport experiments use a locally generated ECDSA P-256 test
credential (`tools/make_test_certs.sh`) with a locally configured trust anchor.
It is **not** on the C2PA Conformance Program trust list.  A `Trusted`
validation state in the results therefore means trusted under the declared
local anchor, not conformance-program trust, and the manuscript says so.
