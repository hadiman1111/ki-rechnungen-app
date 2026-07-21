#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_VENV_PYTHON="${PROJECT_ROOT}/.venv-flet085/bin/python3"
BUILD_VENV_FLET="${PROJECT_ROOT}/.venv-flet085/bin/flet"
TEST_VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python3"
EXPECTED_FLET_VERSION="0.85.3"
MIN_PYTHON_VERSION="3.10"
EXPECTED_DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer"
BUILD_ARCH="${BUILD_ARCH:-arm64}"

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

resolve_build_python() {
  if [[ -x "${BUILD_VENV_PYTHON}" ]]; then
    printf '%s\n' "${BUILD_VENV_PYTHON}"
    return 0
  fi
  return 1
}

resolve_flet_cmd() {
  RESOLVED_PYTHON="$(resolve_build_python || true)"
  if [[ -n "${RESOLVED_PYTHON}" ]] && "${RESOLVED_PYTHON}" -c "import flet.cli" >/dev/null 2>&1; then
    FLET_CMD=("${RESOLVED_PYTHON}" -m flet.cli)
    return 0
  fi
  if [[ -x "${BUILD_VENV_FLET}" ]] && "${BUILD_VENV_FLET}" --help >/dev/null 2>&1; then
    FLET_CMD=("${BUILD_VENV_FLET}")
    return 0
  fi
  return 1
}

assert_build_toolchain() {
  local resolved_python resolved_flet resolved_flet_cli python_version major minor
  resolved_python="$(resolve_build_python || true)"
  if [[ -z "${resolved_python}" ]]; then
    error "Build-Python fehlt. Erwartet: ${BUILD_VENV_PYTHON}"
    return 1
  fi

  python_version="$("${resolved_python}" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
  major="$("${resolved_python}" -c 'import sys; print(sys.version_info.major)')"
  minor="$("${resolved_python}" -c 'import sys; print(sys.version_info.minor)')"
  say "Build-Python: ${resolved_python}"
  say "Build-Python-Version: ${python_version}"
  if [[ "${major}" -lt 3 || ( "${major}" -eq 3 && "${minor}" -lt 10 ) ]]; then
    error "Build-Python muss >= ${MIN_PYTHON_VERSION} sein, gefunden: ${python_version}"
    return 1
  fi

  resolved_flet="$("${resolved_python}" -c 'import importlib.metadata as m; print(m.version("flet"))' 2>/dev/null || true)"
  resolved_flet_cli="$("${resolved_python}" -c 'import importlib.metadata as m; print(m.version("flet-cli"))' 2>/dev/null || true)"
  say "Flet-Version: ${resolved_flet:-unbekannt}"
  say "Flet-CLI-Version: ${resolved_flet_cli:-unbekannt}"
  if [[ "${resolved_flet}" != "${EXPECTED_FLET_VERSION}" || "${resolved_flet_cli}" != "${EXPECTED_FLET_VERSION}" ]]; then
    error "Build erfordert Flet ${EXPECTED_FLET_VERSION} und flet-cli ${EXPECTED_FLET_VERSION} in .venv-flet085."
    return 1
  fi

  if ! resolve_flet_cmd; then
    error "Flet CLI fehlt in .venv-flet085."
    return 1
  fi
  ok "Flet-Buildkette verifiziert (${EXPECTED_FLET_VERSION})."
  return 0
}

section "macOS-Build-Assistent für KI-Rechnungen-App"
say "Projektwurzel: ${PROJECT_ROOT}"

section "Prüfe Projektstruktur"
if [[ -f "${PROJECT_ROOT}/pyproject.toml" ]]; then
  ok "pyproject.toml gefunden."
else
  error "pyproject.toml fehlt. Bitte das Skript im Projekt der KI-Rechnungen-App verwenden."
fi

if [[ -f "${PROJECT_ROOT}/app_main.py" ]]; then
  ok "Build-Einstiegspunkt gefunden: app_main.py"
else
  error "app_main.py fehlt. Der Flet-Build-Einstiegspunkt ist nicht vorhanden."
fi

if [[ -f "${PROJECT_ROOT}/invoice_tool/gui.py" ]]; then
  ok "UI-Datei gefunden: invoice_tool/gui.py"
else
  error "invoice_tool/gui.py fehlt. Die Desktop-UI ist nicht vorhanden."
fi

section "Prüfe Build-Umgebung (.venv-flet085)"
if [[ -d "${PROJECT_ROOT}/.venv-flet085" ]]; then
  ok ".venv-flet085 gefunden."
else
  error "Die Build-Umgebung .venv-flet085 fehlt."
fi

if ! assert_build_toolchain; then
  :
fi

if [[ -x "${TEST_VENV_PYTHON}" ]]; then
  ok "Test-Python in .venv ist verfügbar: ${TEST_VENV_PYTHON}"
else
  error "Test-Python in .venv fehlt. Erwartet wurde: ${TEST_VENV_PYTHON}"
fi

section "Prüfe Flet CLI (Build)"
if resolve_flet_cmd; then
  ok "Flet CLI für den Build ist verfügbar."
else
  error "Flet CLI fehlt in .venv-flet085."
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

bundle_defaults_into_app() {
  local app_path="$1"
  local resources_root="${app_path}/Contents/Resources/ki-rechnungen"
  local defaults_dir="${resources_root}/defaults"

  mkdir -p "${defaults_dir}"
  cp "${PROJECT_ROOT}/resources/standalone/invoice_config.json" "${defaults_dir}/invoice_config.json"
  cp "${PROJECT_ROOT}/office_rules.json" "${defaults_dir}/office_rules.json"
  ok "Standardkonfigurationen nach ${defaults_dir} kopiert."
}

bundle_tesseract_into_app() {
  local app_path="$1"
  local cmd=("${TEST_VENV_PYTHON}" "${PROJECT_ROOT}/scripts/bundle_tesseract.py" "${app_path}")
  say "Befehl: ${cmd[*]}"
  if ! "${cmd[@]}"; then
    error "Tesseract-Bündelung fehlgeschlagen."
    return 1
  fi
  ok "Tesseract in die App eingebettet."
}

clean_app_artifacts() {
  local app_path="$1"
  local removed=0

  # Never delete bytecode inside Flet/Serious-Python runtime bundles: the embedded
  # Python 3.12 stdlib is shipped mostly as __pycache__/*.pyc. Removing those
  # files breaks startup with "no codec search functions registered".
  while IFS= read -r path; do
    rm -rf "${path}"
    removed=$((removed + 1))
  done < <(
    /usr/bin/find "${app_path}" \
      \( -name '__pycache__' -o -name '.pycache' -o -name '*.pyc' \) \
      ! -path '*/serious_python_darwin.framework/*' \
      ! -path '*/Python.framework/*' \
      2>/dev/null
  )

  if [[ "${removed}" -gt 0 ]]; then
    ok "Entwicklungsartefakte entfernt: ${removed} Pfade (Runtime-Bundles ausgenommen)."
  else
    ok "Keine zusätzlichen __pycache__/.pyc-Artefakte gefunden."
  fi
}

verify_embedded_python_runtime() {
  local app_path="$1"
  local py_res="${app_path}/Contents/Frameworks/serious_python_darwin.framework/Versions/A/Resources/python.bundle/Contents/Resources"
  local encodings_dir="${py_res}/stdlib/encodings"
  local stdlib_dir="${py_res}/stdlib"

  if [[ ! -d "${encodings_dir}" ]]; then
    error "Embedded Python encodings fehlen unter ${encodings_dir}."
    return 1
  fi

  local encodings_count
  encodings_count="$(/usr/bin/find "${encodings_dir}" -type f \( -name '*.py' -o -name '*.pyc' \) 2>/dev/null | /usr/bin/wc -l | /usr/bin/tr -d ' ')"
  if [[ "${encodings_count}" -lt 1 ]]; then
    error "Embedded Python encodings/ ist leer – vermutlich durch Bereinigung der Runtime-Bytecode-Dateien zerstört."
    return 1
  fi

  if [[ -d "${stdlib_dir}" ]]; then
    local stdlib_runtime_count
    stdlib_runtime_count="$(/usr/bin/find "${stdlib_dir}" -type f \( -name '*.py' -o -name '*.pyc' \) 2>/dev/null | /usr/bin/wc -l | /usr/bin/tr -d ' ')"
    if [[ "${stdlib_runtime_count}" -lt 50 ]]; then
      error "Embedded Python stdlib wirkt abgeschnitten (${stdlib_runtime_count} Laufzeitdateien unter ${stdlib_dir})."
      return 1
    fi
  fi

  ok "Embedded Python runtime verifiziert (${encodings_count} encodings-Dateien)."
  return 0
}

adhoc_sign_app() {
  local app_path="$1"
  local tess_root="${app_path}/Contents/Resources/ki-rechnungen/tesseract"
  if [[ -d "${tess_root}/lib" ]]; then
    while IFS= read -r lib_path; do
      codesign --force --sign - "${lib_path}"
    done < <(/usr/bin/find "${tess_root}/lib" -name '*.dylib' 2>/dev/null)
  fi
  if [[ -x "${tess_root}/bin/tesseract" ]]; then
    codesign --force --sign - "${tess_root}/bin/tesseract"
  fi
  codesign --force --deep --sign - "${app_path}"
  ok "App ad-hoc signiert."
}

backup_existing_app() {
  local app_path="$1"
  if [[ ! -d "${app_path}" ]]; then
    return 0
  fi
  local backup_path="${app_path}.backup-$(date +%Y%m%d_%H%M%S)"
  mv "${app_path}" "${backup_path}"
  ok "Vorhandene App gesichert nach: ${backup_path}"
}

section "Gezielte Tests vor dem Build"
cd "${PROJECT_ROOT}"
TARGETED_TEST_CMD=("${TEST_VENV_PYTHON}" -m pytest -q tests/test_gui_startup.py)
say "Befehl: ${TARGETED_TEST_CMD[*]}"
if ! "${TARGETED_TEST_CMD[@]}"; then
  error "Gezielte GUI-Startup-Tests fehlgeschlagen."
  exit 1
fi
ok "Gezielte GUI-Startup-Tests bestanden."

BUILD_UI_VERIFY_CMD=("${BUILD_VENV_PYTHON}" "${PROJECT_ROOT}/scripts/verify_gui_startup_flet085.py")
say "Befehl: ${BUILD_UI_VERIFY_CMD[*]}"
if ! "${BUILD_UI_VERIFY_CMD[@]}"; then
  error "Flet-0.85-Startup-Verifikation fehlgeschlagen."
  exit 1
fi
ok "Flet-0.85-Startup-Verifikation bestanden."

section "Vollständige Testsuite vor dem Build"
FULL_TEST_CMD=("${TEST_VENV_PYTHON}" -m pytest -q)
say "Befehl: ${FULL_TEST_CMD[*]}"
if ! "${FULL_TEST_CMD[@]}"; then
  error "Vollständige Tests vor dem Build fehlgeschlagen."
  exit 1
fi
ok "Vollständige Tests vor dem Build bestanden."

section "Sichere vorhandenen Build"
TARGET_APP_PATH="${PROJECT_ROOT}/build/macos/KI-Rechnungen.app"
backup_existing_app "${TARGET_APP_PATH}"

section "Starte macOS-Build"
BUILD_CMD=("${FLET_CMD[@]}" build macos . --arch "${BUILD_ARCH}" --clear-cache --yes)
say "Befehl: ${BUILD_CMD[@]}"
if ! "${BUILD_CMD[@]}"; then
  error "Flet-Build fehlgeschlagen."
  exit 1
fi

section "Suche Build-Ergebnis"
CANONICAL_APP_PATH="${PROJECT_ROOT}/build/macos/KI-Rechnungen.app"
if [[ -d "${CANONICAL_APP_PATH}" ]]; then
  APP_PATH="${CANONICAL_APP_PATH}"
else
  APP_PATH="$(
    /usr/bin/find "${PROJECT_ROOT}/build" \
      -type d -name 'KI-Rechnungen.app' 2>/dev/null | /usr/bin/sort | /usr/bin/tail -n 1
  )"
fi

if [[ -z "${APP_PATH}" || ! -d "${APP_PATH}" ]]; then
  APP_PATH="$(
    /usr/bin/find "${PROJECT_ROOT}/build" \
      -type d -name '*.app' 2>/dev/null | /usr/bin/sort | /usr/bin/tail -n 1
  )"
fi

if [[ -z "${APP_PATH}" || ! -d "${APP_PATH}" ]]; then
  section "Build abgeschlossen, aber keine .app gefunden"
  say "Bitte prüfe die Build-Ausgabe oben."
  say "Erwartet wurde eine .app-Datei unter build/."
  exit 1
fi

section "Post-Build: Ressourcen und Bereinigung"
bundle_defaults_into_app "${APP_PATH}"
if ! bundle_tesseract_into_app "${APP_PATH}"; then
  exit 1
fi
clean_app_artifacts "${APP_PATH}"
if ! verify_embedded_python_runtime "${APP_PATH}"; then
  exit 1
fi
adhoc_sign_app "${APP_PATH}"

section "Architektur und Größe"
/usr/bin/file "${APP_PATH}/Contents/MacOS/KI-Rechnungen"
lipo -info "${APP_PATH}/Contents/MacOS/KI-Rechnungen" || true
du -sh "${APP_PATH}"

section "Tests nach dem Build"
POST_BUILD_TEST_CMD=("${TEST_VENV_PYTHON}" -m pytest -q)
say "Befehl: ${POST_BUILD_TEST_CMD[*]}"
if ! "${POST_BUILD_TEST_CMD[@]}"; then
  error "Tests nach dem Build fehlgeschlagen."
  exit 1
fi
ok "Tests nach dem Build bestanden."

section "Neutraler Smoke-Test"
NEUTRAL_DIR="$(mktemp -d "/tmp/ki-rechnungen-standalone-test.XXXXXX")"
NEUTRAL_APP="${NEUTRAL_DIR}/KI-Rechnungen.app"
ditto "${APP_PATH}" "${NEUTRAL_APP}"
ok "Neutrale Testkopie erstellt: ${NEUTRAL_APP}"

SMOKE_CMD=("${TEST_VENV_PYTHON}" "${PROJECT_ROOT}/scripts/standalone_smoke_test.py" "${NEUTRAL_APP}")
say "Befehl: ${SMOKE_CMD[*]}"
if ! "${SMOKE_CMD[@]}"; then
  error "Standalone-Smoke-Test fehlgeschlagen."
  exit 1
fi

section "Build erfolgreich abgeschlossen"
ok "App-Pfad: ${APP_PATH}"
ok "Neutrale Testkopie: ${NEUTRAL_APP}"
say "Gatekeeper-Hinweis: spctl --assess --type execute \"${NEUTRAL_APP}\" (erwartet bei ad-hoc Signatur oft 'rejected')"
