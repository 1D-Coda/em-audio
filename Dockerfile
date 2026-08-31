# A pinned environment for the reproduction, and the reason there are two of them.
#
# The project asks two questions that a single reproduction run answers badly at
# once. Whether the *implementation* reproduces is a question about the code, and
# it is best asked with the environment held still. Whether the *declared kernel
# footprints* transfer is a question about the environment, and it can only be
# asked by changing it. Running one experiment for both means a failure of the
# second muddies the reading of the first, which is what happened: an
# independent run ended in RUN FAILED for build-specific declarations while
# every contract-level count was in fact identical.
#
# This image fixes the environment so the first question gets a clean answer.
# Every deterministic output must match, on any host, with no environment
# available as an explanation. Run it natively instead when you want to ask the
# second question, which is the more interesting one and the one that produces
# findings.
#
#   docker build -t em-audio .
#   docker run --rm -v "$PWD/out:/out" em-audio
#
# Works the same on Windows, macOS and Linux, which is the point: the Windows
# native path has failures of its own in FFmpeg and c2patool, and a validator on
# Windows should not have to become an expert in them to help.

FROM debian:bookworm-20250630-slim

ARG FFMPEG_TAG=autobuild-2026-08-30-13-12
ARG FFMPEG_FILE=ffmpeg-N-126335-gb32f8d1c23-linux64-gpl.tar.xz
# 0.27.15, not the newest. 0.27.16 fails to embed a manifest in experiment E on
# both Linux and Windows, while 0.27.15 is what the independent reproduction
# used successfully and 0.27.2 is what the reference machine used. Pinning the
# newest release of a dependency is not the same as pinning a working one.
ARG C2PATOOL_VERSION=0.27.15
ARG NODE_MAJOR=22

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONHASHSEED=0 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl xz-utils git \
        python3 python3-pip python3-venv \
        espeak-ng \
        openssl \
    && rm -rf /var/lib/apt/lists/*

# FFmpeg: a static build pinned by release tag rather than the distribution's,
# which moves. The exact build is part of what this image specifies.
RUN curl -fsSL "https://github.com/BtbN/FFmpeg-Builds/releases/download/${FFMPEG_TAG}/${FFMPEG_FILE}" \
      -o /tmp/ffmpeg.tar.xz \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /tmp \
    && install -m755 /tmp/ffmpeg-*/bin/ffmpeg /usr/local/bin/ffmpeg \
    && install -m755 /tmp/ffmpeg-*/bin/ffprobe /usr/local/bin/ffprobe \
    && rm -rf /tmp/ffmpeg*

RUN curl -fsSL "https://github.com/contentauth/c2pa-rs/releases/download/c2patool-v${C2PATOOL_VERSION}/c2patool-v${C2PATOOL_VERSION}-x86_64-unknown-linux-gnu.tar.gz" \
      -o /tmp/c2patool.tar.gz \
    && tar -xzf /tmp/c2patool.tar.gz -C /tmp \
    && install -m755 "$(find /tmp -name c2patool -type f | head -1)" /usr/local/bin/c2patool \
    && rm -rf /tmp/c2patool*

RUN curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" -o /tmp/node.sh \
    && bash /tmp/node.sh && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* /tmp/node.sh

WORKDIR /work
COPY requirements.txt /work/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /work/requirements.txt

COPY . /work
RUN chmod +x /work/run_all.sh /work/tools/*.sh

# results/machine_readable ships empty in a reproduction so that an experiment
# which fails cannot leave a shipped file in place and have the comparison
# report a match that never happened.
RUN rm -f /work/results/machine_readable/*.json || true

ENTRYPOINT ["/work/tools/container_entrypoint.sh"]
