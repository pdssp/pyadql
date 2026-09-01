# -*- coding: utf-8 -*-
# PyADQL - pyadql turns an ADQL query into an AST
# Copyright (C) 2026 - Centre National d'Etudes Spatiales (Jean-Christophe Malapert for PDSSP)
# This file is part of PyADQL <https://gitlab.cnes.fr/pdssp/common/pyadql>
# SPDX-License-Identifier: Apache-2.0

ARG UV_VERSION="0.11.7-python3.12-trixie"
ARG PYTHON_VERSION="3.14.7-slim"


FROM artifactory.cnes.fr:443/docker-remote/astral/uv:${UV_VERSION} AS base

WORKDIR /app
RUN apt-get update -qq \
      && apt upgrade --yes \
      && apt-get clean all \
      && rm -rf /var/lib/apt/lists/*

FROM base AS builder
ARG PIP_INDEX_URL
ARG ARTIFACTORY_REPO_URL
WORKDIR /app

RUN apt-get update -qq \
      && apt upgrade --yes \
      && apt-get -y --no-install-recommends install \
         apt-utils \
         build-essential \
         ca-certificates \
         file \
         gdb \
         gfortran \
         git  \
         wget \
      && apt-get clean all \
      && rm -r /var/lib/apt/lists/*

COPY . .
RUN --mount=type=secret,id=cnes_cert \
      cat /run/secrets/cnes_cert > /usr/local/share/ca-certificates/cnes.crt && \
      update-ca-certificates && \
      make release && \
      VERSION=$(uv version | awk '{print $2}') && \
      pip install --extra-index-url ${ARTIFACTORY_REPO_URL} dist/pyadql-${VERSION}.tar.gz

FROM artifactory.cnes.fr:443/docker-remote/python:${PYTHON_VERSION} AS release
ARG BUILD_DATE
ARG VERSION
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Labels (based on OCI Image Format Specification)
LABEL \
    org.opencontainers.image.version=$VERSION \
    org.opencontainers.image.created=$BUILD_DATE \
    org.opencontainers.image.title="PyADQL" \
    org.opencontainers.image.ref.name="pyadql" \
    org.opencontainers.image.description="pyadql turns an ADQL query into an AST" \
    org.opencontainers.image.licenses="Apache V2.0" \
    org.opencontainers.image.source="https://gitlab.cnes.fr/pdssp/common/pyadql" \
    org.opencontainers.image.documentation="https://pdssp.pages.cnes.fr/common/pyadql" \
    org.opencontainers.image.vendor="PDSSP" \
    org.opencontainers.image.authors="Jean-Christophe Malapert <jean-christophe.malapert@cnes.fr>"

# Get the installed libraries and application from the ealier stage
COPY --from=builder /usr/local/ /usr/local/

# Regenerate the shared-library cache
RUN ldconfig

# Add user
RUN useradd -u 1000 -m appuser
USER appuser

ENTRYPOINT ["pyadql"]
