"""Semantic design tokens for the KI-Rechnungen desktop UI.

All visual constants live here or in ``ui_tokens.py``. Page modules must
import semantic names from this module instead of raw hex values.
"""

from __future__ import annotations

from invoice_tool import ui_tokens as _t

# ── Colors ───────────────────────────────────────────────────────────────────
COLOR_PRIMARY = _t.ACCENT
COLOR_PRIMARY_HOVER = "#2559d4"
COLOR_PRIMARY_PRESSED = "#1e4bb8"
COLOR_SECONDARY = _t.INK_2
COLOR_PAGE_BG = _t.BG
COLOR_SURFACE = _t.SURFACE
COLOR_SURFACE_ALT = _t.SURFACE_2
COLOR_CANVAS = _t.CANVAS
COLOR_TEXT_PRIMARY = _t.INK
COLOR_TEXT_SECONDARY = _t.INK_2
COLOR_TEXT_MUTED = _t.MUTED
COLOR_TEXT_MUTED_2 = _t.MUTED_2
COLOR_BORDER = _t.LINE
COLOR_BORDER_SUBTLE = _t.LINE_2
COLOR_FOCUS = _t.ACCENT
COLOR_SUCCESS = _t.OK
COLOR_SUCCESS_SOFT = _t.OK_SOFT
COLOR_WARNING = _t.WARN
COLOR_WARNING_SOFT = _t.WARN_SOFT
COLOR_ERROR = _t.ERR
COLOR_ERROR_SOFT = _t.ERR_SOFT
COLOR_DISABLED = _t.MUTED_2
COLOR_NAV_ACTIVE_BG = _t.ACCENT_SOFT

# ── Typography ─────────────────────────────────────────────────────────────────
FONT_MONO = _t.MONO_FONT
FONT_MONO_FALLBACK = _t.MONO_FALLBACK
FONT_SIZE_PAGE_TITLE = 28
FONT_SIZE_SECTION_TITLE = 18
FONT_SIZE_CARD_TITLE = 15
FONT_SIZE_BODY = 13
FONT_SIZE_CAPTION = 11
FONT_SIZE_META = 10

# ── Spacing (8-point rhythm) ───────────────────────────────────────────────────
SPACE_XXS = _t.SP_4
SPACE_XS = _t.SP_6
SPACE_SM = _t.SP_8
SPACE_MD = _t.SP_12
SPACE_LG = _t.SP_16
SPACE_XL = _t.SP_24
SPACE_XXL = _t.SP_32

# ── Layout ─────────────────────────────────────────────────────────────────────
NAV_WIDTH = 240
CONTENT_MAX_WIDTH = 1120
CARD_PADDING = SPACE_LG
PANEL_PADDING = SPACE_XL
CONTROL_HEIGHT = 40
CONTROL_HEIGHT_SM = 34
APP_MIN_WIDTH = _t.APP_SHELL_WIDTH

# ── Borders & radii ────────────────────────────────────────────────────────────
BORDER_WIDTH = 1
BORDER_WIDTH_STRONG = 2
RADIUS_SM = _t.RADIUS_CHIP
RADIUS_MD = _t.RADIUS_INPUT
RADIUS_LG = _t.RADIUS_CARD
RADIUS_PILL = _t.RADIUS_PILL
RADIUS_WORKSPACE_CARD = _t.FOLDER_CARD_RADIUS

# ── Shadows (subtle, low elevation) ────────────────────────────────────────────
SHADOW_NONE = None
SHADOW_SM = "0 1px 2px rgba(28,28,30,0.06)"

# ── Responsive breakpoints ─────────────────────────────────────────────────────
BREAKPOINT_WIDE = 1100
BREAKPOINT_MEDIUM = 860
BREAKPOINT_NARROW = 640

# ── Component-specific ─────────────────────────────────────────────────────────
WORKSPACE_CARD_HEIGHT = _t.FOLDER_CARD_HEIGHT
WORKSPACE_CENTER_WIDTH = _t.CENTER_COL_WIDTH

# Re-export raw tokens for tests that assert central usage.
RAW_TOKENS_MODULE = "invoice_tool.ui_theme"
