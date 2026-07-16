#!/usr/bin/env bash
# Lokaler Einstieg: baut die macOS-Dock-App für den internen Launcher.
# Der vollständige Flet-Standalone-Build bleibt unter scripts/build_macos_app.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${ROOT}/scripts/build_macos_dock_app.sh" "$@"
