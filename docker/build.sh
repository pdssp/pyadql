#!/bin/sh
# PyADQL - pyadql turns an ADQL query into an AST
# Copyright (C) 2026 - Centre National d'Etudes Spatiales (Jean-Christophe Malapert for PDSSP)
# This file is part of PyADQL <https://gitlab.cnes.fr/pdssp/common/pyadql>
# SPDX-License-Identifier: Apache-2.0
docker build -t pdssp/pyadql -f docker/Dockerfile --build-arg UV_LOCK="$( stat uv.lock )" .
