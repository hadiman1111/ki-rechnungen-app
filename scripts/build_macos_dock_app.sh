#!/usr/bin/env bash
# Baut eine lokale macOS-Dock-App (native Wrapper), die den internen Launcher startet.
# Entry entspricht scripts/run_internal_launcher_flet085.sh → app_internal_launcher.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_NAME="KI-Rechnungen"
DIST_DIR="${PROJECT_ROOT}/dist"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"
BUNDLE_ID="de.kirechnungen.internal-launcher"
LAUNCHER_SCRIPT="${PROJECT_ROOT}/scripts/run_internal_launcher_flet085.sh"
LAUNCHER_C="${PROJECT_ROOT}/scripts/macos_dock_launcher.c"
ICON_ICNS="${PROJECT_ROOT}/resources/app_icon.icns"
COPY_TO_DESKTOP="${COPY_TO_DESKTOP:-0}"
DESKTOP_APP_PATH="${HOME}/Desktop/${APP_NAME}.app"
PYTHON_BIN="${PROJECT_ROOT}/.venv-flet085/bin/python"
ENTRY_PY="${PROJECT_ROOT}/app_internal_launcher.py"

say() { printf '%s\n' "$1"; }
ok() { say "[OK] $1"; }
error() { say "[FEHLER] $1" >&2; exit 1; }

# Escape for C string literals (-D macros).
c_escape() {
  python3 -c 'import sys; print(sys.argv[1].replace("\\", "\\\\").replace("\"", "\\\""))' "$1"
}

say "== macOS-Dock-App Wrapper =="
say "Projektwurzel: ${PROJECT_ROOT}"

command -v clang >/dev/null 2>&1 || error "clang fehlt (Xcode Command Line Tools / Xcode)."
[[ -x "${PYTHON_BIN}" ]] || error ".venv-flet085/bin/python fehlt."
[[ -f "${LAUNCHER_SCRIPT}" ]] || error "Launcher-Skript fehlt: ${LAUNCHER_SCRIPT}"
[[ -f "${ENTRY_PY}" ]] || error "app_internal_launcher.py fehlt."
[[ -f "${LAUNCHER_C}" ]] || error "Native Stub-Quelle fehlt: ${LAUNCHER_C}"
[[ -f "${ICON_ICNS}" ]] || error "Icon fehlt: ${ICON_ICNS}"

FLET_VERSION="$("${PYTHON_BIN}" -c 'import flet; print(flet.__version__)')"
[[ "${FLET_VERSION}" == 0.85.* ]] || error "Erwartet Flet 0.85.*, gefunden: ${FLET_VERSION}"
ok "Flet ${FLET_VERSION} in .venv-flet085"

mkdir -p "${DIST_DIR}"
rm -rf "${APP_PATH}"

CONTENTS="${APP_PATH}/Contents"
MACOS_DIR="${CONTENTS}/MacOS"
RESOURCES_DIR="${CONTENTS}/Resources"
mkdir -p "${MACOS_DIR}" "${RESOURCES_DIR}"

cp "${ICON_ICNS}" "${RESOURCES_DIR}/AppIcon.icns"

# Gebündelter Flet-Desktop-Client (ohne eigenes Dock-Icon / ohne Fisch-Identität)
FLET_VIEW_DIR="${RESOURCES_DIR}/FletView"
mkdir -p "${FLET_VIEW_DIR}"
say "Bereite gebündelten Flet-View-Client vor…"
CLIENT_APP="$("${PYTHON_BIN}" - <<'PY'
from pathlib import Path
from flet_desktop import ensure_client_cached

cache = ensure_client_cached()
apps = sorted(Path(cache).glob("*.app"))
if not apps:
    raise SystemExit("Kein Flet.app im Client-Cache gefunden")
print(apps[0])
PY
)"
[[ -d "${CLIENT_APP}" ]] || error "Flet-Client nicht gefunden: ${CLIENT_APP}"
ditto "${CLIENT_APP}" "${FLET_VIEW_DIR}/Flet.app"
VIEW_PLIST="${FLET_VIEW_DIR}/Flet.app/Contents/Info.plist"
[[ -f "${VIEW_PLIST}" ]] || error "Flet-View Info.plist fehlt"

# Identität anpassen + LSUIElement: Fenster sichtbar, kein zweites Dock-Icon
/usr/libexec/PlistBuddy -c "Set :CFBundleName ${APP_NAME}" "${VIEW_PLIST}"
if /usr/libexec/PlistBuddy -c "Print :CFBundleDisplayName" "${VIEW_PLIST}" >/dev/null 2>&1; then
  /usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName ${APP_NAME}" "${VIEW_PLIST}"
else
  /usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string ${APP_NAME}" "${VIEW_PLIST}"
fi
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier ${BUNDLE_ID}.view" "${VIEW_PLIST}"
/usr/libexec/PlistBuddy -c "Delete :LSUIElement" "${VIEW_PLIST}" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "${VIEW_PLIST}"
cp "${ICON_ICNS}" "${FLET_VIEW_DIR}/Flet.app/Contents/Resources/AppIcon.icns"
ok "Flet-View gebündelt (LSUIElement, Name=${APP_NAME})"

# Info.plist — Dock-Name KI-Rechnungen + TCC-Hinweise für Desktop-Projektpfad
cat > "${CONTENTS}/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>de</string>
	<key>CFBundleDisplayName</key>
	<string>${APP_NAME}</string>
	<key>CFBundleExecutable</key>
	<string>${APP_NAME}</string>
	<key>CFBundleIconFile</key>
	<string>AppIcon</string>
	<key>CFBundleIdentifier</key>
	<string>${BUNDLE_ID}</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>${APP_NAME}</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>0.1.1</string>
	<key>CFBundleVersion</key>
	<string>2</string>
	<key>LSMinimumSystemVersion</key>
	<string>11.0</string>
	<key>NSHighResolutionCapable</key>
	<true/>
	<key>NSDesktopFolderUsageDescription</key>
	<string>KI-Rechnungen benötigt Zugriff auf den Projektordner auf dem Desktop, um den internen Launcher zu starten.</string>
	<key>NSDocumentsFolderUsageDescription</key>
	<string>KI-Rechnungen kann Dokumentenordner nur nach manueller Auswahl in der UI verwenden.</string>
	<key>NSDownloadsFolderUsageDescription</key>
	<string>KI-Rechnungen kann den Downloads-Ordner nur nach manueller Auswahl in der UI verwenden.</string>
</dict>
</plist>
EOF

PROJECT_ROOT_C="$(c_escape "${PROJECT_ROOT}")"
PYTHON_BIN_C="$(c_escape "${PYTHON_BIN}")"
ENTRY_PY_C="$(c_escape "${ENTRY_PY}")"

say "Kompiliere nativen Dock-Stub…"
clang -O2 -arch arm64 \
  "-DPROJECT_ROOT=\"${PROJECT_ROOT_C}\"" \
  "-DPYTHON_BIN=\"${PYTHON_BIN_C}\"" \
  "-DENTRY_PY=\"${ENTRY_PY_C}\"" \
  -o "${MACOS_DIR}/${APP_NAME}" \
  "${LAUNCHER_C}"
ok "Native Executable: ${MACOS_DIR}/${APP_NAME}"
file "${MACOS_DIR}/${APP_NAME}"

chmod +x "${MACOS_DIR}/${APP_NAME}"
chmod +x "${LAUNCHER_SCRIPT}"

# Ad-hoc signieren (View zuerst, dann Outer-App)
if command -v codesign >/dev/null 2>&1; then
  codesign --force --deep --sign - "${FLET_VIEW_DIR}/Flet.app" >/dev/null 2>&1 || true
  codesign --force --deep --sign - "${APP_PATH}" >/dev/null 2>&1 || true
  ok "Ad-hoc codesign (Wrapper + FletView)"
fi

# Plist-Smoke
/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "${CONTENTS}/Info.plist" >/dev/null
/usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' "${CONTENTS}/Info.plist" >/dev/null
/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "${CONTENTS}/Info.plist" >/dev/null

ok "App gebaut: ${APP_PATH}"
say "CFBundleName=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "${CONTENTS}/Info.plist")"
say "CFBundleDisplayName=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' "${CONTENTS}/Info.plist")"
say "CFBundleExecutable=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "${CONTENTS}/Info.plist")"
say "IconFile=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIconFile' "${CONTENTS}/Info.plist")"
du -sh "${APP_PATH}"

if [[ "${COPY_TO_DESKTOP}" == "1" ]]; then
  rm -rf "${DESKTOP_APP_PATH}"
  ditto "${APP_PATH}" "${DESKTOP_APP_PATH}"
  xattr -cr "${DESKTOP_APP_PATH}" 2>/dev/null || true
  ok "Desktop-Kopie: ${DESKTOP_APP_PATH}"
fi

xattr -cr "${APP_PATH}" 2>/dev/null || true

say ""
say "Start (manuell): open \"${APP_PATH}\""
say "Log: ~/Library/Logs/KI-Rechnungen/dock-app.log"
say "Hinweis: Quelle/Ausgabe bleiben in der UI manuell wählbar; kein Auto-Lauf."
say "Hinweis: Beim ersten Start ggf. Desktop-Zugriff in macOS erlauben."
say "Hinweis: Flet-View ist als LSUIElement gebündelt — erwartet nur ein Dock-Icon „KI-Rechnungen“."
