#!/bin/sh
# PyADQL - pyadql turns an ADQL query into an AST
# Copyright (C) 2026 - Centre National d'Etudes Spatiales (Jean-Christophe Malapert for PDSSP)
# This file is part of PyADQL <https://gitlab.cnes.fr/pdssp/common/pyadql>
# SPDX-License-Identifier: Apache-2.0
#
# Regenerate the static PNG class diagrams used by docs/AST.md from their
# Mermaid sources in docs/images/ast/src/. These are pre-rendered (rather
# than left as ```mermaid fences) because the mkdocs-with-pdf export has no
# JS engine to render Mermaid at build time.
#
# PNG, not SVG: Mermaid class diagrams render member lists via an SVG
# <foreignObject> (real HTML/CSS, needed for text layout), which WeasyPrint
# (used by the PDF export) does not render at all -- the boxes and arrows
# show up in the PDF but every label is blank. Rasterizing to PNG sidesteps
# this because mermaid-cli screenshots the fully-rendered page with a real
# headless Chromium instead of relying on the SVG being interpreted later.
#
# Run this after editing any .mmd file, then commit the regenerated .png
# alongside it.
#
# Requires Node.js (uses `npx @mermaid-js/mermaid-cli` on the fly).
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/../docs/images/ast/src"
OUT_DIR="${SCRIPT_DIR}/../docs/images/ast"

for mmd in "${SRC_DIR}"/*.mmd; do
    name="$(basename "${mmd}" .mmd)"
    png="${OUT_DIR}/${name}.png"
    echo "Rendering ${name}.mmd -> ${name}.png"
    npx --yes @mermaid-js/mermaid-cli@latest -i "${mmd}" -o "${png}" -b white -s 3
done
