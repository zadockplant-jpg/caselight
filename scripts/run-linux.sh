#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/caselight/runtime"

if [[ ! -x "${RUNTIME_DIR}/bin/python" ]]; then
  python3 -m venv "${RUNTIME_DIR}"
  "${RUNTIME_DIR}/bin/python" -m pip install --upgrade pip
fi
"${RUNTIME_DIR}/bin/python" -m pip install --quiet -e "${PROJECT_DIR}"
exec "${RUNTIME_DIR}/bin/python" -m caselight "$@"
