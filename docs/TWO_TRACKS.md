# Two reproductions, two questions

This project asks two things that one run answers badly at once, and separating
them is not bookkeeping: it is what makes each answer readable.

**Does the implementation reproduce?** Best asked with the environment held
still, so that a difference has nothing to blame but the code.

**Do the declared kernel footprints transfer?** Can only be asked by changing
the environment, because a footprint is a claim about a particular build.

Running both at once is why an independent reproduction ended in `RUN FAILED`
while every contract-level count was in fact identical: the failure came from
the second question and had to be disentangled from the first by hand.

## Track A — the container

    docker build -t em-audio .
    docker run --rm -v "$PWD/out:/out" em-audio

FFmpeg, `c2patool`, Node and eSpeak NG are pinned in the image, so every run of
it sees the same tools. The comparison is against `results/reference_container/`,
frozen from a run of this same image, not against `results/reference/`, which
came from the author's macOS machine. Comparing a Linux container against a
macOS reference would rediscover the build-specific footprint findings and
report them as failures of the container.

What a deterministic difference means here is unambiguous: the implementation
did not reproduce. There is no environment left to explain it. That is a
stronger conformance claim than a native run can make.

It also runs identically on Windows through Docker Desktop, which matters
because the Windows native path has its own FFmpeg and `c2patool` problems, and
a validator should not have to become an expert in them to help.

## Track B — native

    pip install -r requirements.txt
    ./run_all.sh
    python3 tools/verify_reproduction.py

Your own FFmpeg, your own everything. This is what the independent reproduction
did and it is where the findings come from: on FFmpeg 8.0.1 the MP3 kernel
footprint measured a reach of 4,317 source samples against 2,304 declared, and
the silence-removal mapping deviation reached 12,505 against a declared margin
of 4,096. Both are reported in the paper as results.

A deterministic difference here is not automatically a defect. It is a
measurement, and the four readings to choose between are an environment
difference, a tool-version difference, an ambiguity in how the contract is
specified, or a genuine discrepancy.

## Which to run

Run Track B if you can. It is the one that produces findings, and disagreement
is the useful outcome.

Run Track A if you are on Windows, if installing five tools is more trouble than
it is worth, or if you want to check the conformance claim specifically.

Running both from one machine is the most useful of all, because the pair
separates the two questions on identical hardware.

## A note on pinning

The container pins `c2patool` to 0.27.15 rather than the newest release.
0.27.16 fails to embed a manifest in experiment E on both Linux and Windows,
while 0.27.15 is what the independent reproduction used and 0.27.2 is what the
reference machine used. Pinning the newest version of a dependency is not the
same as pinning a working one, and this is the kind of thing a pinned
environment exists to record.
