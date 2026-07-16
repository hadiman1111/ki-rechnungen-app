#!/usr/bin/env bash
# Startet den internen SOMAA-Verarbeitungslauncher (Flet 0.85).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="${ROOT}/.venv-flet085/bin/python"
APP_ENTRY="${ROOT}/app_internal_launcher.py"

if [[ ! -x "${VENV_PY}" ]]; then
  echo "FEHLER: ${VENV_PY} fehlt oder ist nicht ausführbar." >&2
  echo "Bitte .venv-flet085 im Repository-Root bereitstellen." >&2
  exit 1
fi

FLET_VERSION="$("${VENV_PY}" -c "import flet; print(flet.__version__)" 2>/dev/null || echo "unknown")"
if [[ "${FLET_VERSION}" != 0.85.* ]]; then
  echo "FEHLER: Erwartet Flet 0.85, gefunden: ${FLET_VERSION}" >&2
  exit 1
fi

cd "${ROOT}"
echo "Starte internen Launcher: ${VENV_PY} ${APP_ENTRY}"
exec "${VENV_PY}" "${APP_ENTRY}"
