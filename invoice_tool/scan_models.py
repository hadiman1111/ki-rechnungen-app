"""Registry of supported scan (recognition) models and their extractable features."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScanFeature:
    key: str
    label: str
    filename_supported: bool = True
    matching_supported: bool = True


@dataclass(frozen=True)
class ScanModel:
    id: str
    label: str
    document_domain: str
    features: tuple[ScanFeature, ...]

    def feature_keys(self) -> tuple[str, ...]:
        return tuple(feature.key for feature in self.features)

    def feature_labels(self) -> tuple[str, ...]:
        return tuple(feature.label for feature in self.features)

    def get_feature(self, key: str) -> ScanFeature | None:
        for feature in self.features:
            if feature.key == key:
                return feature
        return None


_RECHNUNGEN = ScanModel(
    id="rechnungen",
    label="Rechnungsdaten",
    document_domain="Rechnungen",
    features=(
        ScanFeature("invoice_date", "Rechnungsdatum"),
        ScanFeature("supplier", "Lieferant"),
        ScanFeature("amount", "Betrag"),
        ScanFeature("currency", "Währung"),
        ScanFeature("invoice_number", "Rechnungsnummer"),
        ScanFeature("document_type", "Dokumentart"),
        ScanFeature("payment_field", "Zahlung / Konto"),
        ScanFeature("project", "Projekt"),
        ScanFeature("art", "Kategorie", matching_supported=True),
    ),
)

_ANGEBOTE = ScanModel(
    id="angebote",
    label="Angebotsdaten",
    document_domain="Angebote",
    features=(
        ScanFeature("quote_date", "Angebotsdatum"),
        ScanFeature("provider", "Anbieter"),
        ScanFeature("quote_total", "Angebotssumme"),
        ScanFeature("quote_number", "Angebotsnummer"),
        ScanFeature("project", "Projekt"),
        ScanFeature("trade", "Gewerk"),
        ScanFeature("valid_until", "Gültigkeitsdatum"),
    ),
)

_FREITEXT = ScanModel(
    id="freitext-dokumente",
    label="Freitext-Dokumente",
    document_domain="Freitext-Dokumente",
    features=(
        ScanFeature("title", "Titel"),
        ScanFeature("author", "Autor"),
        ScanFeature("first_words", "erste Wörter"),
        ScanFeature("first_line", "erste Textzeile"),
        ScanFeature("language", "Sprache"),
        ScanFeature("creation_date", "Entstehungsdatum"),
        ScanFeature("collection", "Sammlung"),
    ),
)

SCAN_MODELS: dict[str, ScanModel] = {
    model.id: model for model in (_RECHNUNGEN, _ANGEBOTE, _FREITEXT)
}

DEFAULT_SCAN_MODEL_ID = "rechnungen"

# Neutral sample values for filename previews — no personal data.
NEUTRAL_PREVIEW_VALUES: dict[str, str] = {
    "invoice_date": "2026-07-08",
    "supplier": "musterfirma",
    "amount": "125,00",
    "currency": "eur",
    "invoice_number": "4711",
    "document_type": "rechnung",
    "payment_field": "beispielkonto",
    "project": "projekt-a",
    "art": "er",
    "quote_date": "2026-07-08",
    "provider": "musteranbieter",
    "quote_total": "9.800,00",
    "quote_number": "a-2026-001",
    "trade": "elektro",
    "valid_until": "2026-08-31",
    "title": "wanders-nachtlied",
    "author": "goethe",
    "first_words": "ueber-all",
    "first_line": "ueber-all-am-strande",
    "language": "de",
    "creation_date": "1780",
    "collection": "lyrik",
}


def get_scan_model(model_id: str | None) -> ScanModel:
    resolved = (model_id or "").strip() or DEFAULT_SCAN_MODEL_ID
    return SCAN_MODELS.get(resolved, _RECHNUNGEN)


def list_scan_models() -> list[ScanModel]:
    return list(SCAN_MODELS.values())


def matching_features(model: ScanModel) -> list[ScanFeature]:
    return [feature for feature in model.features if feature.matching_supported]


def filename_features(model: ScanModel) -> list[ScanFeature]:
    return [feature for feature in model.features if feature.filename_supported]
