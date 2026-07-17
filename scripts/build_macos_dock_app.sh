#!/usr/bin/env bash
# Baut eine lokale macOS-Dock-App (native Wrapper), die den internen Launcher startet.
# Entry entspricht scripts/run_internal_launcher_flet085.sh → app_internal_launcher.py
#
# Single-Dock-Strategie (ohne den gescheiterten LSUIElement-am-View-Ansatz):
# - Äußerer Wrapper: LSUIElement=true (kein zweites Dock-Icon für den Stub)
# - Gebündelter Flet-Client: Name/Icon KI-Rechnungen, KEIN LSUIElement (sichtbares Fenster)
# - FletView-Bootstrap: Kaltstart aus dem Dock öffnet Outer-App (Python-Launcher),
#   Warm-Start mit page_url exec't das echte Flutter-Binary (kein leeres Fenster)
# - Entitlements der Quelle beim Re-Signieren erhalten (File-Picker)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
APP_NAME="KI-Rechnungen"
DIST_DIR="${PROJECT_ROOT}/dist"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"
BUNDLE_ID="de.kirechnungen.internal-launcher"
VIEW_BUNDLE_ID="de.kirechnungen.view"
LAUNCHER_SCRIPT="${PROJECT_ROOT}/scripts/run_internal_launcher_flet085.sh"
LAUNCHER_C="${PROJECT_ROOT}/scripts/macos_dock_launcher.c"
FLETVIEW_BOOTSTRAP_C="${PROJECT_ROOT}/scripts/macos_fletview_bootstrap.c"
ICON_ICNS="${PROJECT_ROOT}/resources/app_icon.icns"
ICON_PNG="${PROJECT_ROOT}/resources/app_icon.png"
APPICONSET_DIR="${PROJECT_ROOT}/build/flutter/macos/Runner/Assets.xcassets/AppIcon.appiconset"
ASSETS_XCASSETS_DIR="${PROJECT_ROOT}/build/flutter/macos/Runner/Assets.xcassets"
COPY_TO_DESKTOP="${COPY_TO_DESKTOP:-0}"
DESKTOP_APP_PATH="${HOME}/Desktop/${APP_NAME}.app"
PYTHON_BIN="${PROJECT_ROOT}/.venv-flet085/bin/python"
ENTRY_PY="${PROJECT_ROOT}/app_internal_launcher.py"

say() { printf '%s\n' "$1"; }
ok() { say "[OK] $1"; }
error() { say "[FEHLER] $1" >&2; exit 1; }

# Brand Flutter/macOS AppIcon.appiconset from resources/app_icon.png and compile Assets.car.
# Dock uses CFBundleIconName=AppIcon → Assets.car; replacing only AppIcon.icns is not enough.
brand_fletview_assets_car() {
  local view_app="$1"
  local view_resources="${view_app}/Contents/Resources"
  local compile_tmp
  local new_car
  local old_md5=""
  local new_md5=""

  [[ -f "${ICON_PNG}" ]] || error "Icon-PNG fehlt: ${ICON_PNG}"
  [[ -d "${view_resources}" ]] || error "FletView Resources fehlen: ${view_resources}"
  command -v sips >/dev/null 2>&1 || error "sips fehlt (macOS Image Tools)."
  xcrun --find actool >/dev/null 2>&1 || error "actool fehlt (Xcode Command Line Tools / Xcode)."

  mkdir -p "${APPICONSET_DIR}"
  if [[ ! -f "${APPICONSET_DIR}/Contents.json" ]]; then
    cat > "${APPICONSET_DIR}/Contents.json" <<'JSON'
{
    "info": {
        "version": 1,
        "author": "xcode"
    },
    "images": [
        { "size": "16x16", "idiom": "mac", "filename": "app_icon_16.png", "scale": "1x" },
        { "size": "16x16", "idiom": "mac", "filename": "app_icon_32.png", "scale": "2x" },
        { "size": "32x32", "idiom": "mac", "filename": "app_icon_32.png", "scale": "1x" },
        { "size": "32x32", "idiom": "mac", "filename": "app_icon_64.png", "scale": "2x" },
        { "size": "128x128", "idiom": "mac", "filename": "app_icon_128.png", "scale": "1x" },
        { "size": "128x128", "idiom": "mac", "filename": "app_icon_256.png", "scale": "2x" },
        { "size": "256x256", "idiom": "mac", "filename": "app_icon_256.png", "scale": "1x" },
        { "size": "256x256", "idiom": "mac", "filename": "app_icon_512.png", "scale": "2x" },
        { "size": "512x512", "idiom": "mac", "filename": "app_icon_512.png", "scale": "1x" },
        { "size": "512x512", "idiom": "mac", "filename": "app_icon_1024.png", "scale": "2x" }
    ]
}
JSON
  fi

  say "Brande AppIcon.appiconset aus ${ICON_PNG}…"
  local size
  for size in 16 32 64 128 256 512 1024; do
    sips -z "${size}" "${size}" "${ICON_PNG}" --out "${APPICONSET_DIR}/app_icon_${size}.png" >/dev/null \
      || error "sips fehlgeschlagen für app_icon_${size}.png"
  done
  ok "AppIcon.appiconset gebrandet (${APPICONSET_DIR})"

  if [[ -f "${view_resources}/Assets.car" ]]; then
    old_md5="$(md5 -q "${view_resources}/Assets.car")"
  fi

  compile_tmp="$(mktemp -d "${TMPDIR:-/tmp}/ki-appicon-XXXXXX")"
  say "Kompiliere Assets.car mit actool…"
  xcrun actool \
    --compile "${compile_tmp}" \
    --platform macosx \
    --minimum-deployment-target 11.0 \
    --app-icon AppIcon \
    --output-partial-info-plist "${compile_tmp}/assetcatalog_generated_info.plist" \
    "${ASSETS_XCASSETS_DIR}" >/dev/null \
    || error "actool Assets.car-Kompilierung fehlgeschlagen"

  new_car="${compile_tmp}/Assets.car"
  [[ -f "${new_car}" ]] || error "actool hat kein Assets.car erzeugt"
  new_md5="$(md5 -q "${new_car}")"
  [[ -n "${old_md5}" && "${new_md5}" == "${old_md5}" ]] \
    && error "Assets.car unverändert (noch Flet-Fisch-Katalog): ${new_md5}"

  cp "${new_car}" "${view_resources}/Assets.car"
  # Prefer project icns (richer), keep CFBundleIconName→Assets.car branded.
  cp "${ICON_ICNS}" "${view_resources}/AppIcon.icns"
  rm -rf "${compile_tmp}"
  ok "FletView Assets.car gebrandet (md5 ${old_md5:-none} → ${new_md5})"
}

# Escape for C string literals (-D macros).
c_escape() {
  python3 -c 'import sys; print(sys.argv[1].replace("\\", "\\\\").replace("\"", "\\\""))' "$1"
}

plist_set_or_add_string() {
  local plist="$1" key="$2" value="$3"
  if /usr/libexec/PlistBuddy -c "Print :${key}" "${plist}" >/dev/null 2>&1; then
    /usr/libexec/PlistBuddy -c "Set :${key} ${value}" "${plist}"
  else
    /usr/libexec/PlistBuddy -c "Add :${key} string ${value}" "${plist}"
  fi
}

say "== macOS-Dock-App Wrapper =="
say "Projektwurzel: ${PROJECT_ROOT}"

command -v clang >/dev/null 2>&1 || error "clang fehlt (Xcode Command Line Tools / Xcode)."
[[ -x "${PYTHON_BIN}" ]] || error ".venv-flet085/bin/python fehlt."
[[ -f "${LAUNCHER_SCRIPT}" ]] || error "Launcher-Skript fehlt: ${LAUNCHER_SCRIPT}"
[[ -f "${ENTRY_PY}" ]] || error "app_internal_launcher.py fehlt."
[[ -f "${LAUNCHER_C}" ]] || error "Native Stub-Quelle fehlt: ${LAUNCHER_C}"
[[ -f "${FLETVIEW_BOOTSTRAP_C}" ]] || error "FletView-Bootstrap-Quelle fehlt: ${FLETVIEW_BOOTSTRAP_C}"
[[ -f "${ICON_ICNS}" ]] || error "Icon fehlt: ${ICON_ICNS}"
[[ -f "${ICON_PNG}" ]] || error "Icon-PNG fehlt: ${ICON_PNG}"

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

# --- Gebündelter, gebrandeter Flet-Desktop-Client (sichtbar im Dock) ---
FLET_VIEW_DIR="${RESOURCES_DIR}/FletView"
mkdir -p "${FLET_VIEW_DIR}"
say "Bereite gebündelten Flet-View-Client vor…"

SOURCE_APP=""
if [[ -d "${PROJECT_ROOT}/build/macos/ki-rechnungen-app.app" ]]; then
  SOURCE_APP="${PROJECT_ROOT}/build/macos/ki-rechnungen-app.app"
  say "Quelle: build/macos/ki-rechnungen-app.app"
elif [[ -d "${PROJECT_ROOT}/build/macos/KI-Rechnungen.app" ]]; then
  SOURCE_APP="${PROJECT_ROOT}/build/macos/KI-Rechnungen.app"
  say "Quelle: build/macos/KI-Rechnungen.app"
else
  SOURCE_APP="$("${PYTHON_BIN}" - <<'PY'
from pathlib import Path
from flet_desktop import ensure_client_cached

cache = ensure_client_cached()
apps = sorted(Path(cache).glob("*.app"))
if not apps:
    raise SystemExit("Kein Flet.app im Client-Cache gefunden")
print(apps[0])
PY
)"
  say "Quelle: Flet-Client-Cache (${SOURCE_APP})"
fi
[[ -d "${SOURCE_APP}" ]] || error "Flet-Client nicht gefunden: ${SOURCE_APP}"

VIEW_APP="${FLET_VIEW_DIR}/${APP_NAME}.app"
ditto "${SOURCE_APP}" "${VIEW_APP}"
VIEW_PLIST="${VIEW_APP}/Contents/Info.plist"
[[ -f "${VIEW_PLIST}" ]] || error "Flet-View Info.plist fehlt"

# Branding — Fenster/Dock-Identität KI-Rechnungen, KEIN LSUIElement am View
plist_set_or_add_string "${VIEW_PLIST}" "CFBundleName" "${APP_NAME}"
plist_set_or_add_string "${VIEW_PLIST}" "CFBundleDisplayName" "${APP_NAME}"
plist_set_or_add_string "${VIEW_PLIST}" "CFBundleIdentifier" "${VIEW_BUNDLE_ID}"
/usr/libexec/PlistBuddy -c "Delete :LSUIElement" "${VIEW_PLIST}" 2>/dev/null || true
# Dock-Icon kommt bei Flutter/macOS aus CFBundleIconName=AppIcon → Assets.car.
# AppIcon.icns allein reicht nicht; Katalog neu branden und Assets.car ersetzen.
brand_fletview_assets_car "${VIEW_APP}"
plist_set_or_add_string "${VIEW_PLIST}" "CFBundleIconName" "AppIcon"
plist_set_or_add_string "${VIEW_PLIST}" "CFBundleIconFile" "AppIcon"
ok "Flet-View gebrandet (Name=${APP_NAME}, Bundle=${VIEW_BUNDLE_ID}, kein LSUIElement, Assets.car)"

# FletView-Bootstrap: Dock-Kaltstart → Outer-App; Flet-Warmstart → Real-Binary
VIEW_MACOS_DIR="${VIEW_APP}/Contents/MacOS"
VIEW_EXEC_NAME="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "${VIEW_PLIST}")"
[[ -n "${VIEW_EXEC_NAME}" ]] || error "CFBundleExecutable der FletView fehlt"
VIEW_REAL_BIN="${VIEW_MACOS_DIR}/${VIEW_EXEC_NAME}.real"
VIEW_BOOTSTRAP_BIN="${VIEW_MACOS_DIR}/${VIEW_EXEC_NAME}"
[[ -f "${VIEW_BOOTSTRAP_BIN}" ]] || error "FletView-Executable fehlt: ${VIEW_BOOTSTRAP_BIN}"
mv "${VIEW_BOOTSTRAP_BIN}" "${VIEW_REAL_BIN}"
say "Kompiliere FletView-Bootstrap (Dock-Relaunch)…"
clang -O2 -arch arm64 \
  -o "${VIEW_BOOTSTRAP_BIN}" \
  "${FLETVIEW_BOOTSTRAP_C}" \
  || error "clang FletView-Bootstrap fehlgeschlagen"
chmod +x "${VIEW_BOOTSTRAP_BIN}" "${VIEW_REAL_BIN}"
ok "FletView-Bootstrap: ${VIEW_BOOTSTRAP_BIN} (Real: ${VIEW_REAL_BIN})"

# Entitlements der Quelle erhalten (verhindert File-Picker ENTITLEMENT_NOT_FOUND).
# Wichtig: `codesign -d --entitlements FILE` schreibt hier Text-Dump; XML kommt via `:-`.
ENT_TMP="$(mktemp)"
cleanup_ent() { rm -f "${ENT_TMP}"; }
trap cleanup_ent EXIT
if codesign -d --entitlements :- "${SOURCE_APP}" 2>/dev/null > "${ENT_TMP}" \
  && [[ -s "${ENT_TMP}" ]] \
  && plutil -lint "${ENT_TMP}" >/dev/null 2>&1; then
  codesign --force --deep --sign - --entitlements "${ENT_TMP}" "${VIEW_APP}" >/dev/null 2>&1 \
    || error "codesign FletView mit Entitlements fehlgeschlagen"
  ok "FletView ad-hoc signiert (Entitlements der Quelle)"
else
  # Fallback: minimale Desktop-Entitlements für File-Picker + Netzwerk
  cat > "${ENT_TMP}" <<'ENT'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>com.apple.security.app-sandbox</key>
	<false/>
	<key>com.apple.security.cs.allow-jit</key>
	<true/>
	<key>com.apple.security.files.user-selected.read-write</key>
	<true/>
	<key>com.apple.security.network.client</key>
	<true/>
	<key>com.apple.security.network.server</key>
	<true/>
</dict>
</plist>
ENT
  codesign --force --deep --sign - --entitlements "${ENT_TMP}" "${VIEW_APP}" >/dev/null 2>&1 \
    || error "codesign FletView (Fallback-Entitlements) fehlgeschlagen"
  ok "FletView ad-hoc signiert (Fallback-Entitlements inkl. File-Picker)"
fi

# Info.plist — äußerer Wrapper: Dock-unsichtbar (LSUIElement), Stub startet nur den Launcher
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
	<string>0.1.2</string>
	<key>CFBundleVersion</key>
	<string>3</string>
	<key>LSMinimumSystemVersion</key>
	<string>11.0</string>
	<key>LSUIElement</key>
	<true/>
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

# Outer wrapper ad-hoc signieren — ohne --deep, sonst verliert der View seine Entitlements.
# View danach erneut mit Entitlements signieren (Reihenfolge: innen → außen).
if command -v codesign >/dev/null 2>&1; then
  codesign --force --sign - "${MACOS_DIR}/${APP_NAME}" >/dev/null 2>&1 || true
  codesign --force --deep --sign - --entitlements "${ENT_TMP}" "${VIEW_APP}" >/dev/null 2>&1 \
    || error "codesign FletView (Nachzeichen) fehlgeschlagen"
  codesign --force --sign - "${APP_PATH}" >/dev/null 2>&1 || true
  ok "Ad-hoc codesign (Wrapper; FletView mit Entitlements)"
fi

# Plist-Smoke
/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "${CONTENTS}/Info.plist" >/dev/null
/usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' "${CONTENTS}/Info.plist" >/dev/null
/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "${CONTENTS}/Info.plist" >/dev/null
/usr/libexec/PlistBuddy -c 'Print :LSUIElement' "${CONTENTS}/Info.plist" >/dev/null
/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "${VIEW_PLIST}" >/dev/null
if /usr/libexec/PlistBuddy -c 'Print :LSUIElement' "${VIEW_PLIST}" >/dev/null 2>&1; then
  error "FletView darf kein LSUIElement haben (Fenster würde verschwinden)"
fi

ok "App gebaut: ${APP_PATH}"
say "CFBundleName=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleName' "${CONTENTS}/Info.plist")"
say "CFBundleDisplayName=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleDisplayName' "${CONTENTS}/Info.plist")"
say "CFBundleExecutable=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "${CONTENTS}/Info.plist")"
say "Wrapper LSUIElement=$(/usr/libexec/PlistBuddy -c 'Print :LSUIElement' "${CONTENTS}/Info.plist")"
say "View Bundle=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "${VIEW_PLIST}")"
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
say "Hinweis: Sichtbares Dock-Icon ist der gebrandete Flet-View (KI-Rechnungen)."
say "Hinweis: Dock-Kaltstart des Views öffnet Outer-App → Python-Launcher (kein leeres Fenster)."
