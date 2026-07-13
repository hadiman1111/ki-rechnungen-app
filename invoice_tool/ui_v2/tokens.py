"""Design tokens for UI-v2 — no Flet imports.

Aligned with international SaaS patterns (8pt grid, WCAG AA contrast,
single-elevation surfaces, semantic color). References: Material 3, Apple HIG,
Carbon empty states, Stripe/Linear dashboard density.
"""

# --- Color: surfaces ---
BG = "#f3f2ef"
SIDEBAR_BG = "#1a1a1c"
SIDEBAR_BORDER = "#2d2d30"
SIDEBAR_TEXT = "#8e8e9a"
SIDEBAR_TEXT_HOVER = "#d4d4d8"
SIDEBAR_TEXT_ACTIVE = "#ffffff"
SIDEBAR_GROUP = "#46464e"
SIDEBAR_ACCENT_BG = "#252d42"
SIDEBAR_HOVER_BG = "#2a2a2e"
SURFACE = "#ffffff"
SURFACE_ELEVATED = "#ffffff"
SURFACE_SUBTLE = "#f8f7f4"
CANVAS = "#f3f2ef"

# --- Color: borders ---
LINE = "#e3e1dc"
LINE_STRONG = "#cdcbc4"

# --- Color: text ---
INK = "#1a1a1c"
INK_2 = "#3c3c40"
MUTED = "#636368"
MUTED_2 = "#8a8a90"
MUTED_LIGHT = "#8e8e96"
DISABLED = "#aeaeb2"

# --- Color: accent ---
ACCENT = "#2f6df2"
ACCENT_HOVER = "#2558c7"
ACCENT_SUBTLE = "#e8effd"
ACCENT_FAINT = "#f0f5fe"

# --- Color: semantic ---
SUCCESS = "#157a47"
SUCCESS_SOFT = "#e6f4ec"
WARN = "#9a5b00"
WARN_SOFT = "#faf0e0"
WARN_BORDER = "#e8c87a"
ERR = "#b3261e"
ERR_SOFT = "#fbeae8"

# --- Spacing scale (px) ---
SP_4 = 4
SP_8 = 8
SP_12 = 12
SP_16 = 16
SP_20 = 20
SP_24 = 24
SP_32 = 32
SP_40 = 40
SP_48 = 48

# --- Typography (px) ---
FONT_PRODUCT_LABEL = 18
FONT_PAGE_TITLE = 38
FONT_KPI_VALUE = 26
FONT_KPI_VALUE_LONG = 14
FONT_DETAIL_HEADER = 14
FONT_PAGE_DESC = 13
FONT_SECTION_TITLE = 15
FONT_CARD_TITLE = 14
FONT_BODY = 13
FONT_METADATA = 12
FONT_LABEL = 12
FONT_HELPER = 11
FONT_STATUS = 11
FONT_BUTTON = 13
FONT_NAV_GROUP = 10
FONT_NAV_ITEM = 13
FONT_MONO = 12

# --- Metadata layout ---
METADATA_LABEL_WIDTH = 168

# --- Radius (px) ---
RADIUS_INPUT = 8
RADIUS_BUTTON = 8
RADIUS_CARD = 10
RADIUS_PANEL = 12

# --- Layout widths (px) ---
NAV_WIDTH = 240
APP_MIN_WIDTH = 1280
PRODUCT_DISPLAY_NAME = "NAME.IT PRO"
CONTENT_MAX_WIDTH = 1200
FORM_MAX_WIDTH = 640
DETAIL_PANEL_MIN_WIDTH = 380
LIST_PANEL_MIN_WIDTH = 296
LIST_DETAIL_GAP = 12
LIST_DETAIL_MIN_HEIGHT = 372
LIST_DETAIL_EDIT_HEIGHT = 520
INPUT_CONTROL_HEIGHT = 34
WORKFLOW_PANEL_MIN_HEIGHT = 148
COMPACT_CARD_MIN_WIDTH = 200

# --- Shadows: restrained per design references ---
SHADOW_NONE = None
