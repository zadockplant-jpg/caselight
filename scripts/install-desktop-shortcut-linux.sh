#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
EXECUTABLE="${PROJECT_DIR}/dist/CaseLight"
ICON="${PROJECT_DIR}/assets/caselight.png"
TEMPLATE="${PROJECT_DIR}/packaging/caselight.desktop.in"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
APPLICATIONS_DIR="${XDG_DATA_HOME:-${HOME}/.local/share}/applications"
TEMPORARY="$(mktemp)"
trap 'rm -f -- "${TEMPORARY}"' EXIT

if [[ -z "${DESKTOP_DIR}" ]]; then
  DESKTOP_DIR="${HOME}/Desktop"
fi
if [[ ! -x "${EXECUTABLE}" ]]; then
  echo "CaseLight executable is missing: ${EXECUTABLE}" >&2
  echo "Run ./scripts/build-linux.sh first." >&2
  exit 1
fi

escape_sed_replacement() {
  printf '%s' "$1" | sed 's/[&|\\]/\\&/g'
}

sed \
  -e "s|@EXECUTABLE@|$(escape_sed_replacement "${EXECUTABLE}")|g" \
  -e "s|@ICON@|$(escape_sed_replacement "${ICON}")|g" \
  -e "s|@PROJECT_DIR@|$(escape_sed_replacement "${PROJECT_DIR}")|g" \
  "${TEMPLATE}" >"${TEMPORARY}"

install -Dm755 "${TEMPORARY}" "${APPLICATIONS_DIR}/caselight.desktop"
install -Dm755 "${TEMPORARY}" "${DESKTOP_DIR}/CaseLight.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${APPLICATIONS_DIR}" >/dev/null 2>&1 || true
fi

echo "Installed desktop shortcut: ${DESKTOP_DIR}/CaseLight.desktop"
echo "Installed application entry: ${APPLICATIONS_DIR}/caselight.desktop"
