FROM ghcr.io/ddanila/8080-cosim-smoke-kit@sha256:060cf153f9a4332fc58c7577e86f98d305b5848d60bf62bd4934591e8fc1c830 AS cosim-smoke

FROM ubuntu:24.04

LABEL org.opencontainers.image.source="https://github.com/ddanila/cpm-plus-juku"
LABEL org.opencontainers.image.description="Reproducible build environment for cpm-plus-juku"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install --no-install-recommends --yes \
        bison \
        build-essential \
        ca-certificates \
        cpmtools \
        file \
        git \
        libncurses-dev \
        python3 \
        python3-pexpect \
    && rm -rf /var/lib/apt/lists/*

COPY --from=cosim-smoke /opt/8080-cosim /opt/8080-cosim

ENV JUKU_COSIM_ROOT=/opt/8080-cosim
ENV JUKU_COSIM_TRACE=/opt/8080-cosim/bin/trace
ENV DEBIAN_FRONTEND=
