from __future__ import annotations

import base64
import json
import re
import shutil
import tempfile
import time
from pathlib import Path

import fitz
import pytesseract
from openai import OpenAI

from invoice_tool.models import ExtractedData
from invoice_tool.normalization import (
    NormalizationError,
    parse_amount_from_text,
    parse_card_endings_from_text,
    parse_invoice_date_from_text,
    parse_invoice_number_from_text,
    parse_supplier_from_text,
    normalize_invoice_date,
)
from invoice_tool.runtime import RuntimeEnvironmentError, load_openai_api_key


class ExtractionError(RuntimeError):
    pass


class StructuralExtractionError(ExtractionError):
    pass


def _debug_log(run_id: str, hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": "9e8b5c",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with Path("/Users/hadi_neu/Desktop/KI-Rechnungen-App/.cursor/debug-9e8b5c.log").open(
        "a", encoding="utf-8"
    ) as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def render_pdf_pages(pdf_path: Path, max_pages: int = 2) -> list[bytes]:
    pngs: list[bytes] = []
    with fitz.open(pdf_path) as document:
        page_limit = min(max_pages, len(document))
        for page_index in range(page_limit):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            pngs.append(pixmap.tobytes("png"))
    return pngs


def _extract_json_payload(text: str) -> dict:
    text = text.strip()
    if not text:
        # region agent log
        _debug_log(
            "15pdf-diagnose",
            "H3",
            "invoice_tool/extraction.py:_extract_json_payload",
            "OpenAI output empty before JSON parse",
            {"textLength": 0},
        )
        # endregion
        raise StructuralExtractionError("OpenAI-Antwort ist leer.")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        # region agent log
        _debug_log(
            "15pdf-diagnose",
            "H3",
            "invoice_tool/extraction.py:_extract_json_payload",
            "OpenAI output missing parseable JSON envelope",
            {"textLength": len(text), "start": start, "end": end},
        )
        # endregion
        raise StructuralExtractionError("OpenAI-Antwort enthaelt kein parsebares JSON.")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        # region agent log
        _debug_log(
            "15pdf-diagnose",
            "H3",
            "invoice_tool/extraction.py:_extract_json_payload",
            "OpenAI JSON decode failed",
            {
                "textLength": len(text),
                "error": str(exc),
                "errorPos": exc.pos,
                "errorLine": exc.lineno,
                "errorColumn": exc.colno,
                "maskedContext": re.sub(
                    r"[A-Za-z0-9ÄÖÜäöüß]",
                    "x",
                    text[max(0, exc.pos - 120) : min(len(text), exc.pos + 120)],
                ),
            },
        )
        # endregion
        raise StructuralExtractionError("OpenAI-Antwort ist kein gueltiges JSON.") from exc


class OpenAIVisionExtractor:
    def __init__(self, api_key_path: Path, model: str) -> None:
        self.api_key_path = api_key_path
        self.model = model

    def extract(self, pdf_path: Path) -> ExtractedData:
        try:
            api_key = load_openai_api_key(self.api_key_path)
        except RuntimeEnvironmentError as exc:
            # region agent log
            _debug_log(
                "15pdf-diagnose",
                "H1",
                "invoice_tool/extraction.py:OpenAIVisionExtractor.extract",
                "OpenAI API key load failed",
                {"pdf": pdf_path.name, "model": self.model, "error": str(exc)},
            )
            # endregion
            raise StructuralExtractionError(str(exc)) from exc

        client = OpenAI(api_key=api_key)
        images = render_pdf_pages(pdf_path, max_pages=2)
        content = [
            {
                "type": "input_text",
                "text": (
                    "Analysiere hoechstens die bereitgestellten ersten zwei PDF-Seiten. "
                    "Gib ausschliesslich JSON mit folgenden Feldern zurueck: "
                    "invoice_date, supplier, amount, invoice_number, document_name, payment_method, "
                    "context_markers, document_type_indicators, card_endings, apple_pay_endings, "
                    "provider_mentions, address_fragments, raw_text_excerpt. "
                    "invoice_date soll das Rechnungsdatum sein, nicht Faelligkeit oder Leistungsdatum. "
                    "amount soll der finale Gesamtbetrag sein. "
                    "invoice_number soll nur gesetzt werden, wenn wirklich eine Rechnungsnummer erkennbar ist. "
                    "payment_method soll eine knappe Beschreibung wie card, transfer, cash, paypal oder unknown sein, falls erkennbar. "
                    "context_markers soll relevante Begriffe wie SOMAA, Event & Production, Architektur, Innenarchitektur enthalten. "
                    "document_type_indicators soll Begriffe wie donation, transfer proof, payment confirmation, bescheid enthalten, falls erkennbar. "
                    "document_name soll fuer Nicht-Rechnungen eine kurze englische oder deutsche Inhaltsbeschreibung mit hoechstens etwa fuenf Woertern liefern. "
                    "card_endings und apple_pay_endings muessen nur sichtbare vierstellige Endungen enthalten."
                ),
            }
        ]

        for image in images:
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{base64.b64encode(image).decode('ascii')}",
                }
            )

        # region agent log
        _debug_log(
            "15pdf-diagnose",
            "H2",
            "invoice_tool/extraction.py:OpenAIVisionExtractor.extract",
            "OpenAI request about to start",
            {"pdf": pdf_path.name, "model": self.model, "imageCount": len(images), "branch": "vision-json-primary"},
        )
        # endregion
        try:
            response = client.responses.create(
                model=self.model,
                input=[{"role": "user", "content": content}],
                max_output_tokens=800,
            )
        except Exception as exc:  # noqa: BLE001
            # region agent log
            _debug_log(
                "15pdf-diagnose",
                "H2",
                "invoice_tool/extraction.py:OpenAIVisionExtractor.extract",
                "OpenAI request raised exception",
                {"pdf": pdf_path.name, "model": self.model, "errorType": type(exc).__name__, "error": str(exc)},
            )
            # endregion
            raise StructuralExtractionError(f"OpenAI-Vision-Anfrage fehlgeschlagen: {exc}") from exc

        # region agent log
        _debug_log(
            "15pdf-diagnose",
            "H2",
            "invoice_tool/extraction.py:OpenAIVisionExtractor.extract",
            "OpenAI response received",
            {"pdf": pdf_path.name, "model": self.model, "outputTextLength": len(response.output_text or "")},
        )
        # endregion
        payload = _extract_json_payload(response.output_text)
        # region agent log
        _debug_log(
            "15pdf-diagnose",
            "H3",
            "invoice_tool/extraction.py:OpenAIVisionExtractor.extract",
            "OpenAI payload parsed",
            {"pdf": pdf_path.name, "keys": sorted(payload.keys())},
        )
        # endregion
        extracted = ExtractedData(
            invoice_date_raw=_string_or_none(payload.get("invoice_date")),
            supplier_raw=_string_or_none(payload.get("supplier")),
            amount_raw=_string_or_none(payload.get("amount")),
            invoice_number_raw=_string_or_none(payload.get("invoice_number")),
            document_name_raw=_string_or_none(payload.get("document_name")),
            payment_method_raw=_string_or_none(payload.get("payment_method")),
            card_endings=_list_of_strings(payload.get("card_endings")),
            apple_pay_endings=_list_of_strings(payload.get("apple_pay_endings")),
            provider_mentions=_list_of_strings(payload.get("provider_mentions")),
            address_fragments=_list_of_strings(payload.get("address_fragments")),
            context_markers=_list_of_strings(payload.get("context_markers")),
            document_type_indicators=_list_of_strings(payload.get("document_type_indicators")),
            raw_text=_string_or_none(payload.get("raw_text_excerpt")) or "",
            source_method="openai",
        )
        extracted = _enrich_from_raw_text(extracted)
        # region agent log
        _debug_log(
            "15pdf-diagnose",
            "H4",
            "invoice_tool/extraction.py:OpenAIVisionExtractor.extract",
            "OpenAI extraction normalized before structural check",
            {
                "pdf": pdf_path.name,
                "invoiceDateRaw": extracted.invoice_date_raw,
                "hasSupplier": bool(extracted.supplier_raw),
                "amountRaw": extracted.amount_raw,
                "hasRawText": bool(extracted.raw_text),
                "meaningful": _has_meaningful_content(extracted),
            },
        )
        # endregion
        if not _has_meaningful_content(extracted):
            # region agent log
            _debug_log(
                "15pdf-diagnose",
                "H4",
                "invoice_tool/extraction.py:OpenAIVisionExtractor.extract",
                "OpenAI extraction rejected by structural validation",
                {"pdf": pdf_path.name},
            )
            # endregion
            raise StructuralExtractionError("OpenAI-Daten sind technisch verwertbar, aber inhaltlich leer.")

        return extracted


class TesseractExtractor:
    def __init__(self) -> None:
        if shutil.which("tesseract") is None:
            raise ExtractionError("Tesseract ist nicht installiert oder nicht im PATH verfuegbar.")

    def extract(self, pdf_path: Path) -> ExtractedData:
        images = render_pdf_pages(pdf_path, max_pages=2)
        text_chunks: list[str] = []

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            for index, image in enumerate(images, start=1):
                png_path = temp_path / f"page-{index}.png"
                png_path.write_bytes(image)
                text = pytesseract.image_to_string(str(png_path), lang="deu+eng")
                text_chunks.append(text)

        raw_text = "\n".join(text_chunks).strip()
        card_endings, apple_pay_endings = parse_card_endings_from_text(raw_text)
        extracted = ExtractedData(
            invoice_date_raw=parse_invoice_date_from_text(raw_text),
            supplier_raw=parse_supplier_from_text(raw_text),
            amount_raw=parse_amount_from_text(raw_text),
            invoice_number_raw=parse_invoice_number_from_text(raw_text),
            document_name_raw=None,
            payment_method_raw=None,
            card_endings=card_endings,
            apple_pay_endings=apple_pay_endings,
            provider_mentions=[],
            address_fragments=[],
            context_markers=[],
            document_type_indicators=[],
            raw_text=raw_text,
            source_method="tesseract",
        )
        extracted = _enrich_from_raw_text(extracted)
        if not _has_meaningful_content(extracted):
            raise StructuralExtractionError(
                "Tesseract-OCR konnte keine ausreichend verwertbaren Daten liefern."
            )

        return extracted


class ExtractionCoordinator:
    def __init__(self, primary: OpenAIVisionExtractor, fallback: TesseractExtractor | None = None) -> None:
        self.primary = primary
        self.fallback = fallback

    def extract(self, pdf_path: Path, *, log) -> ExtractedData:
        try:
            return self.primary.extract(pdf_path)
        except StructuralExtractionError as primary_error:
            # region agent log
            _debug_log(
                "15pdf-diagnose",
                "H5",
                "invoice_tool/extraction.py:ExtractionCoordinator.extract",
                "Fallback path activated after primary extraction failure",
                {"pdf": pdf_path.name, "error": str(primary_error), "fallbackAvailable": self.fallback is not None},
            )
            # endregion
            log(
                f"OpenAI-Vision war technisch oder strukturell unzureichend, Tesseract-Fallback wird versucht: {primary_error}"
            )

            if self.fallback is None:
                raise ExtractionError(
                    f"OpenAI-Vision fehlgeschlagen und kein Tesseract-Fallback verfuegbar: {primary_error}"
                ) from primary_error

            try:
                extracted = self.fallback.extract(pdf_path)
                extracted.fallback_used = True
                return extracted
            except ExtractionError as fallback_error:
                raise ExtractionError(
                    f"OpenAI-Vision fehlgeschlagen und Tesseract-Fallback ist nicht nutzbar: {fallback_error}"
                ) from fallback_error


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            result.append(item.strip().lower())
    return result


def _has_meaningful_content(extracted: ExtractedData) -> bool:
    return any(
        [
            extracted.invoice_date_raw,
            extracted.supplier_raw,
            extracted.amount_raw,
            extracted.invoice_number_raw,
            extracted.document_name_raw,
            extracted.payment_method_raw,
            extracted.card_endings,
            extracted.apple_pay_endings,
            extracted.provider_mentions,
            extracted.address_fragments,
            extracted.context_markers,
            extracted.document_type_indicators,
            extracted.raw_text,
        ]
    )


def _enrich_from_raw_text(extracted: ExtractedData) -> ExtractedData:
    if not extracted.raw_text:
        return extracted
    if (
        extracted.invoice_date_raw
        and extracted.supplier_raw
        and extracted.amount_raw
        and extracted.invoice_number_raw
        and _prefer_valid_date(extracted.invoice_date_raw, None) is not None
    ):
        return extracted
    parsed_date = parse_invoice_date_from_text(extracted.raw_text)
    return ExtractedData(
        invoice_date_raw=_prefer_valid_date(extracted.invoice_date_raw, parsed_date),
        supplier_raw=extracted.supplier_raw or parse_supplier_from_text(extracted.raw_text),
        amount_raw=extracted.amount_raw or parse_amount_from_text(extracted.raw_text),
        invoice_number_raw=extracted.invoice_number_raw or parse_invoice_number_from_text(extracted.raw_text),
        document_name_raw=extracted.document_name_raw,
        payment_method_raw=extracted.payment_method_raw,
        card_endings=extracted.card_endings,
        apple_pay_endings=extracted.apple_pay_endings,
        provider_mentions=extracted.provider_mentions,
        address_fragments=extracted.address_fragments,
        context_markers=extracted.context_markers,
        document_type_indicators=extracted.document_type_indicators,
        raw_text=extracted.raw_text,
        source_method=extracted.source_method,
        fallback_used=extracted.fallback_used,
    )


def _prefer_valid_date(primary: str | None, fallback: str | None) -> str | None:
    if primary:
        try:
            normalize_invoice_date(primary)
            return primary
        except NormalizationError:
            pass
    return fallback
