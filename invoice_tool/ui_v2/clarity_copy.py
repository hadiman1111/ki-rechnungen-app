"""Track-B UI-v2 clarity copy — shared honest product wording.

Single source for sandbox / non-productive / preview clarity after
copied-realistic sandbox validation. No processing-core imports,
no private defaults, no productive execution claims.
"""

from __future__ import annotations

# Required user-facing clarity (Prompt 9 / quality fixes after sandbox validation).
MSG_CLARITY_SANDBOX_COPIED_RUN = "Dies ist ein Sandbox-Lauf mit kopierten Daten."
MSG_CLARITY_NO_ORIGINAL_FOLDERS = "Originalordner werden nicht verwendet."
MSG_CLARITY_PRODUCTIVE_NOT_RELEASED = (
    "Produktive Verarbeitung ist noch nicht freigegeben."
)
MSG_CLARITY_UNCLEAR_STAYS_REVIEW = "Unklare Fälle bleiben zur Prüfung."
MSG_CLARITY_FILENAME_NOT_TRUTH = "Dateinamen sind keine Belegwahrheit."
MSG_CLARITY_EXPORT_PREVIEW = (
    "Export ist eine Vorschau, kein produktiver DATEV-/Cloud-Export."
)
MSG_CLARITY_BUCKETS_SEPARATED = (
    "Ergebnisse, Prüffälle und Fehler werden getrennt geführt."
)

TRACK_B_CLARITY_LINES = (
    MSG_CLARITY_SANDBOX_COPIED_RUN,
    MSG_CLARITY_NO_ORIGINAL_FOLDERS,
    MSG_CLARITY_PRODUCTIVE_NOT_RELEASED,
    MSG_CLARITY_UNCLEAR_STAYS_REVIEW,
    MSG_CLARITY_FILENAME_NOT_TRUTH,
    MSG_CLARITY_EXPORT_PREVIEW,
    MSG_CLARITY_BUCKETS_SEPARATED,
)

# Supporting honesty lines used next to the required clarity set.
MSG_CLARITY_EXPORT_FROM_REAL_RUN = (
    "Bericht und Export nutzen nur echte Laufergebnisse — "
    "ohne erfundene Produktivdaten."
)
MSG_CLARITY_SANDBOX_COPIED_DATA_ONLY = (
    "Verarbeitung ist nur mit kopierten Testdaten erlaubt."
)
MSG_CLARITY_COPIED_DATA_ONLY_REPORT = (
    "Sandbox-Validierung nutzt ausschließlich kopierte Testdaten."
)


def track_b_clarity_lines() -> tuple[str, ...]:
    """Return the seven required Track-B clarity lines in stable order."""

    return TRACK_B_CLARITY_LINES


def clarity_blob(*parts: str) -> str:
    """Join clarity parts for assertion helpers / report text."""

    return " ".join(part for part in parts if part and str(part).strip())


__all__ = (
    "MSG_CLARITY_BUCKETS_SEPARATED",
    "MSG_CLARITY_COPIED_DATA_ONLY_REPORT",
    "MSG_CLARITY_EXPORT_FROM_REAL_RUN",
    "MSG_CLARITY_EXPORT_PREVIEW",
    "MSG_CLARITY_FILENAME_NOT_TRUTH",
    "MSG_CLARITY_NO_ORIGINAL_FOLDERS",
    "MSG_CLARITY_PRODUCTIVE_NOT_RELEASED",
    "MSG_CLARITY_SANDBOX_COPIED_DATA_ONLY",
    "MSG_CLARITY_SANDBOX_COPIED_RUN",
    "MSG_CLARITY_UNCLEAR_STAYS_REVIEW",
    "TRACK_B_CLARITY_LINES",
    "clarity_blob",
    "track_b_clarity_lines",
)
