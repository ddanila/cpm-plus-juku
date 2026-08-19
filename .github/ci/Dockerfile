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
        git \
        python3 \
        python3-pexpect \
    && rm -rf /var/lib/apt/lists/*

ENV DEBIAN_FRONTEND=
