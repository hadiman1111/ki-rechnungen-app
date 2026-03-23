from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from invoice_tool.config import ConfigError, load_app_config, load_office_rules
from invoice_tool.extraction import ExtractionCoordinator, OpenAIVisionExtractor, TesseractExtractor
from invoice_tool.processing import InvoiceProcessor, ProcessorError


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


def main() -> int:
    config_path = Path("invoice_config.json").resolve()

    try:
        config = load_app_config(config_path)
        office_rules = load_office_rules(
            config.regeln_datei,
            active_preset_override=config.aktives_preset,
        )
        # region agent log
        _debug_log(
            "15pdf-diagnose",
            "H6",
            "invoice_tool/__main__.py:main",
            "Workspace main entry reached",
            {
                "moduleFile": __file__,
                "cwd": str(Path.cwd()),
                "configPath": str(config_path),
                "model": config.openai_model,
            },
        )
        # endregion
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
