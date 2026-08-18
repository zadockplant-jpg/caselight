#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ENV="${XDG_CACHE_HOME:-${HOME}/.cache}/caselight-build"

python3 -m venv "${BUILD_ENV}"
"${BUILD_ENV}/bin/python" -m pip install --upgrade pip
"${BUILD_ENV}/bin/python" -m pip install "${PROJECT_DIR}[build]"
cd "${PROJECT_DIR}"
"${BUILD_ENV}/bin/pyinstaller" --noconfirm --clean CaseLight.spec
echo "Built ${PROJECT_DIR}/dist/CaseLight"
