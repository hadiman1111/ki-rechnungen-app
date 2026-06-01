"""Design-Token-Konstanten für die KI-Rechnungen-App UI.

Keine Flet-Imports, keine Laufzeit-Logik – nur Werte.
Alle Farben als Hex-Strings, Abstände als int (px), Radien als int (px).
"""

# ── Farben: Neutrale Töne ────────────────────────────────────────────────────
SURFACE   = "#ffffff"   # Karten / Panels
SURFACE_2 = "#faf9f6"   # sanfter Inset / Sidebars
CANVAS    = "#f6f5f2"   # App-Fläche
LINE      = "#e6e4df"   # Rahmen / Trennlinien
LINE_2    = "#efede8"   # feinere Trennlinie

# ── Farben: Text ─────────────────────────────────────────────────────────────
INK   = "#1c1c1e"   # Haupttext
INK_2 = "#3a3a3c"   # Sekundärtext
MUTED   = "#6b6b70"   # Nebentext
MUTED_2 = "#8e8e93"   # Sehr gedämpft

# ── Farben: Akzent (Blau – Eingang / primäre Aktion) ─────────────────────────
ACCENT      = "#2f6df2"
ACCENT_SOFT = "#eaf0fe"

# ── Farben: Erfolg (Grün – Ausgang / fertig) ─────────────────────────────────
OK      = "#1f9d55"
OK_SOFT = "#e6f4ec"

# ── Farben: Warnung (Amber – Prüfbedarf) ─────────────────────────────────────
WARN      = "#b46a00"
WARN_SOFT = "#fbf1de"
WARN_EDGE = "#ecd6a6"

# ── Farben: Fehler (Rot) ──────────────────────────────────────────────────────
ERR      = "#b3261e"
ERR_SOFT = "#fbeae8"

# ── Schrift ───────────────────────────────────────────────────────────────────
MONO_FONT     = "JetBrains Mono"   # für Pfade, Dateinamen, Zeitstempel
MONO_FALLBACK = "Menlo"

# ── Abstände (4er-Raster, in px) ─────────────────────────────────────────────
SP_4  = 4
SP_6  = 6
SP_8  = 8
SP_10 = 10
SP_12 = 12
SP_16 = 16
SP_24 = 24

# ── Border-Radien (in px) ─────────────────────────────────────────────────────
RADIUS_CHIP  = 5
RADIUS_INPUT = 8
RADIUS_CARD  = 10
RADIUS_PILL  = 999
