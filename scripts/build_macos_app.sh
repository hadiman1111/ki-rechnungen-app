#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
VENV_FLET="${PROJECT_ROOT}/.venv/bin/flet"
GUI_FILE="${PROJECT_ROOT}/invoice_tool/gui.py"
EXPECTED_DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"

FAILED_CHECKS=0

say() {
  printf '%s\n' "$1"
}

ok() {
  say "[OK] $1"
}

hint() {
  say "[HINWEIS] $1"
}

error() {
  say "[FEHLER] $1"
  FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

section() {
  printf '\n'
  say "== $1 =="
}

section "macOS-Build-Assistent für KI-Rechnungen-App"
say "Projektwurzel: ${PROJECT_ROOT}"

section "Prüfe Projektstruktur"
if [[ -f "${PROJECT_ROOT}/pyproject.toml" ]]; then
  ok "pyproject.toml gefunden."
else
  error "pyproject.toml fehlt. Bitte das Skript im Projekt der KI-Rechnungen-App verwenden."
fi

if [[ -f "${GUI_FILE}" ]]; then
  ok "UI-Datei gefunden: invoice_tool/gui.py"
else
  error "invoice_tool/gui.py fehlt. Die Desktop-UI ist nicht vorhanden."
fi

section "Prüfe virtuelle Umgebung"
if [[ -d "${PROJECT_ROOT}/.venv" ]]; then
  ok ".venv gefunden."
else
  error "Die virtuelle Umgebung .venv fehlt. Bitte zuerst die Projektumgebung anlegen."
fi

if [[ -x "${VENV_PYTHON}" ]]; then
  ok "Python in der virtuellen Umgebung ist verfügbar."
else
  error "Python in .venv fehlt. Erwartet wurde: ${VENV_PYTHON}"
fi

section "Prüfe Flet CLI"
if [[ -x "${VENV_FLET}" ]]; then
  if "${VENV_FLET}" --help >/dev/null 2>&1; then
    ok "Flet CLI ist in der virtuellen Umgebung verfügbar."
  else
    error "Flet CLI wurde gefunden, konnte aber nicht gestartet werden. Bitte prüfe die Installation in .venv."
  fi
else
  error "Flet CLI fehlt in .venv. Installiere die Abhängigkeiten erneut, z. B. mit: ./.venv/bin/pip install -e ."
fi

section "Prüfe Xcode"
if [[ -d "/Applications/Xcode.app" ]]; then
  ok "Xcode ist installiert."
else
  error "Xcode ist nicht installiert. Bitte im App Store installieren."
fi

section "Prüfe xcode-select"
if command -v xcode-select >/dev/null 2>&1; then
  CURRENT_DEVELOPER_DIR="$(xcode-select -p 2>/dev/null || true)"
  if [[ "${CURRENT_DEVELOPER_DIR}" == "${EXPECTED_DEVELOPER_DIR}" ]]; then
    ok "xcode-select zeigt auf ${EXPECTED_DEVELOPER_DIR}."
  else
    error "Der aktive Developer-Pfad ist nicht korrekt gesetzt. Bitte ausführen: sudo xcode-select -s ${EXPECTED_DEVELOPER_DIR}"
  fi
else
  error "xcode-select ist nicht verfügbar. Bitte Xcode vollständig installieren."
fi

section "Prüfe CocoaPods"
if command -v pod >/dev/null 2>&1; then
  POD_VERSION="$(pod --version 2>/dev/null || true)"
  if [[ -n "${POD_VERSION}" ]]; then
    ok "CocoaPods ist installiert (${POD_VERSION})."
  else
    error "CocoaPods wurde gefunden, liefert aber keine Version. Bitte die Installation prüfen."
  fi
else
  error "CocoaPods fehlt. Installiere es z. B. mit: brew install cocoapods"
fi

section "Optionale Plattform-Hinweise"
ARCH="$(uname -m)"
if [[ "${ARCH}" == "arm64" ]]; then
  if /usr/bin/pgrep oahd >/dev/null 2>&1; then
    ok "Apple Silicon erkannt, Rosetta scheint verfügbar zu sein."
  else
    hint "Apple Silicon erkannt. Rosetta ist aktuell nicht aktiv. Das ist kein Abbruch, kann aber bei manchen Build-Toolchains hilfreich sein."
  fi
fi

if [[ "${FAILED_CHECKS}" -gt 0 ]]; then
  section "Build nicht gestartet"
  say "Es gibt ${FAILED_CHECKS} offene Voraussetzung(en)."
  say "Bitte behebe die oben genannten Punkte und starte das Skript danach erneut."
  exit 1
fi

section "Starte macOS-Build"
cd "${PROJECT_ROOT}"
say "Befehl: ${VENV_FLET} build macos invoice_tool/gui.py"
"${VENV_FLET}" build macos invoice_tool/gui.py

section "Suche Build-Ergebnis"
APP_PATH="$(
  /usr/bin/find "${PROJECT_ROOT}" \
    \( -path "${PROJECT_ROOT}/build" -o -path "${PROJECT_ROOT}/dist" \) \
    -type d -name '*.app' 2>/dev/null | /usr/bin/sort | /usr/bin/tail -n 1
)"

if [[ -n "${APP_PATH}" && -d "${APP_PATH}" ]]; then
  ok "Build erfolgreich abgeschlossen."
  say "App-Pfad: ${APP_PATH}"
  say "Nächster Schritt: Öffne die App im Finder oder starte sie mit: open \"${APP_PATH}\""
else
  section "Build abgeschlossen, aber keine .app gefunden"
  say "Bitte prüfe die Build-Ausgabe oben."
  say "Erwartet wurde eine .app-Datei unter build/ oder dist/."
  exit 1
fi
