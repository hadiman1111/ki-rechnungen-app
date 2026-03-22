from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def normalize_for_matching(value: str) -> str:
    lowered = value.lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
    for source, target in replacements.items():
        lowered = lowered.replace(source, target)
    lowered = unicodedata.normalize("NFKD", lowered)
    lowered = lowered.encode("ascii", "ignore").decode("ascii")
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return re.sub(r"\s{2,}", " ", lowered).strip()


def compact_text(value: str) -> str:
    return normalize_for_matching(value).replace(" ", "")


def contains_fuzzy_phrase(text: str, phrase: str, threshold: float) -> bool:
    normalized_text = normalize_for_matching(text)
    normalized_phrase = normalize_for_matching(phrase)
    if not normalized_text or not normalized_phrase:
        return False

    compact_phrase = normalized_phrase.replace(" ", "")
    compact_source = normalized_text.replace(" ", "")
    if compact_phrase in compact_source:
        return True

    text_tokens = normalized_text.split()
    phrase_tokens = normalized_phrase.split()
    if not text_tokens or not phrase_tokens:
        return False

    window_sizes = {len(phrase_tokens)}
    if len(phrase_tokens) > 1:
        window_sizes.add(len(phrase_tokens) - 1)
    window_sizes.add(len(phrase_tokens) + 1)

    for window_size in sorted(size for size in window_sizes if size > 0):
        if window_size > len(text_tokens):
            continue
        for start_index in range(0, len(text_tokens) - window_size + 1):
            candidate = "".join(text_tokens[start_index : start_index + window_size])
            ratio = SequenceMatcher(None, candidate, compact_phrase).ratio()
            if ratio >= threshold:
                return True

    return False
