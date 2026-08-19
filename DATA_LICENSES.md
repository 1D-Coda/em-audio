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

## Supplementary neural-TTS voice (robustness arm, experiment C2)

| Field | Value |
|---|---|
| Engine | Piper, `piper-tts` 1.7.0 (PyPI), VITS architecture |
| Engine licence | MIT |
| Voice | `en_US-ljspeech-medium`, model card `piper_version` 1.0.0 |
| Voice sample rate | 22 050 Hz (resampled to 16 kHz by stock ffmpeg before use) |
| Voice training data | LJ Speech Dataset (Keith Ito, 2017) |
| Training-data licence | Public domain. Verbatim from the dataset page: "This dataset is in the public domain in the US (and most likely other countries as well)." |
| Training-data provenance | LibriVox recordings by Linda Johnson (2016-17) of seven non-fiction books published 1884-1964; both the recordings and the source texts are public domain |
| Licence URL | https://keithito.com/LJ-Speech-Dataset/ |
| Access date | 2026-08-19 |
| Model SHA-256 | `6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22` (`en_US-ljspeech-medium.onnx`) |
| Config SHA-256 | `141d612cc0a95ed7efc1ca936b845c2364967f2e9217c5dbfcf69fc4d6c65860` (`en_US-ljspeech-medium.onnx.json`) |
| Retrieval | `tools/fetch_voice.sh`, which calls `python3 -m piper.download_voices en_US-ljspeech-medium` and verifies both checksums. The 63 MB model is fetched rather than committed. |
| Role | generates the synthetic middle segment of the 50-clip neural arm |
| Rejected alternative | the `lessac` voices were considered and rejected: their Blizzard 2013 training data is the property of Voice Factory International Inc. and Lessac Technologies Inc. under a restrictive licence, which fails the corpus gate |

No voice of any identified living person is cloned, and no speaker-identity
claim is made anywhere in this work.

## Supplementary noise source (robustness arm, experiment C2)

Pink noise generated locally by stock ffmpeg, seeded per clip index so the arm
is deterministic. No third-party material. The exact generation and mix, as
executed:

```
ffmpeg -i <clip> \
  -f lavfi -i "anoisesrc=r=16000:colour=pink:amplitude=0.12:seed=<clip index>" \
  -filter_complex "[1:a]volume=-18dB[nz];\
                   [0:a][nz]amix=inputs=2:duration=first:normalize=0[out]" \
  -map "[out]" -c:a pcm_s16le <output>
```

The noise is modelled as a second generated-derived source covering the whole
clip, so under the contract every captured segment becomes mixed ancestry and
the generated segment stays generated.

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
