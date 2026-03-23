from __future__ import annotations

import sys
from pathlib import Path

from invoice_tool.config import ConfigError, load_app_config, load_office_rules
from invoice_tool.extraction import ExtractionCoordinator, OpenAIVisionExtractor, TesseractExtractor
from invoice_tool.processing import InvoiceProcessor, ProcessorError


def main() -> int:
    config_path = Path("invoice_config.json").resolve()

    try:
        config = load_app_config(config_path)
        office_rules = load_office_rules(
            config.regeln_datei,
            active_preset_override=config.aktives_preset,
        )
        try:
            fallback = TesseractExtractor()
        except Exception as exc:  # noqa: BLE001
            print(f"Tesseract-Fallback ist nicht verfuegbar: {exc}")
            fallback = None

        extractor = ExtractionCoordinator(
            primary=OpenAIVisionExtractor(config.api_key_pfad, config.openai_model),
            fallback=fallback,
        )
        processor = InvoiceProcessor(config, extractor, office_rules=office_rules)
        processor.process_all()
        return 0
    except (ConfigError, ProcessorError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
