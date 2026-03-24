from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class RunLogger:
    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.started_at = datetime.now()
        self.run_id = self.started_at.strftime("%Y%m%d_%H%M%S")
        self.log_path = self.logs_dir / f"run_{self.run_id}.log"
        self.file_events: list[dict[str, object]] = []

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def log_file_summary(self, payload: dict[str, object]) -> None:
        self.file_events.append(dict(payload))
        self.log("FILE " + json.dumps(payload, ensure_ascii=False, sort_keys=True))

    def write_run_report(self, output_dir: Path, *, preset: str, input_count: int) -> Path:
        report_dir = output_dir / "_runs" / self.run_id
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "report.txt"
        processed = sum(1 for event in self.file_events if event.get("status") == "processed")
        documents = sum(1 for event in self.file_events if event.get("type") == "document")
        duplicates = sum(1 for event in self.file_events if event.get("status") == "duplicate")
        unklar = sum(1 for event in self.file_events if event.get("status") == "unklar")
        errors = sum(1 for event in self.file_events if event.get("status") == "failed")
        fallbacks = sum(1 for event in self.file_events if event.get("fallback_used") is True)
        review_events = [
            event
            for event in self.file_events
            if event.get("status") in {"unklar", "failed"}
        ]

        lines = [
            f"Run ID: {self.run_id}",
            f"Date: {self.started_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Preset: {preset}",
            f"Input files: {input_count}",
            "",
        ]
        if review_events:
            lines.extend(
                [
                    "PRÜFBEDARF:",
                    f"Zu prüfen ({len(review_events)}):",
                ]
            )
            for event in review_events:
                lines.append(
                    f"- {event.get('filename') or '-'} → {self._report_notes(event)}"
                )
        else:
            lines.append("PRÜFBEDARF: keiner")
        lines.extend(
            [
                "",
                "SUMMARY:",
                f"Processed: {processed}",
                f"Documents: {documents}",
                f"Duplicates: {duplicates}",
                f"Unklar: {unklar}",
                f"Errors: {errors}",
                f"System Fallbacks: {fallbacks}",
                "",
                "DETAILS:",
                "",
            ]
        )

        for event in self.file_events:
            file_status = self._report_status(event)
            file_type = self._report_type(event)
            file_fallback = event.get("fallback_used") is True
            file_output = str(event.get("storage_path") or "-")
            file_notes = self._report_notes(event)
            lines.extend(
                [
                    f"Filename: {event.get('filename') or '-'}",
                    f"Status: {file_status}",
                    f"Type: {file_type}",
                    f"Fallback: {'yes' if file_fallback else 'no'}",
                    f"Output: {file_output}",
                    f"Notes: {file_notes}",
                    "",
                ]
            )

        report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        report_json_path = report_dir / "report.json"
        report_json_data = {
            "run_id": self.run_id,
            "date": self.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "preset": preset,
            "input_files": input_count,
            "summary": {
                "processed": processed,
                "documents": documents,
                "duplicates": duplicates,
                "unklar": unklar,
                "errors": errors,
                "system_fallbacks": fallbacks,
            },
            "files": [
                {
                    "filename": str(event.get("filename") or "-"),
                    "status": self._report_status(event),
                    "type": self._report_type(event),
                    "fallback": event.get("fallback_used") is True,
                    "output": str(event.get("storage_path") or "-"),
                    "notes": self._report_notes(event),
                }
                for event in self.file_events
            ],
        }
        report_json_path.write_text(
            json.dumps(report_json_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report_path

    def _report_status(self, event: dict[str, object]) -> str:
        status = str(event.get("status") or "").strip().lower()
        return "error" if status == "failed" else (status or "unknown")

    def _report_type(self, event: dict[str, object]) -> str:
        event_type = str(event.get("type") or "").strip().lower()
        if event_type == "unknown" and self._report_status(event) == "error":
            return "error"
        return event_type or "unknown"

    def _report_notes(self, event: dict[str, object]) -> str:
        notes: list[str] = []
        output_action = str(event.get("output_action") or "").strip().lower()
        if output_action == "new":
            notes.append("Neue Datei erstellt")
        elif output_action == "updated":
            notes.append("Bestehende Datei aktualisiert")
        elif output_action == "unchanged":
            notes.append("Datei unverändert übernommen")

        status = self._report_status(event)
        event_type = self._report_type(event)
        if status == "processed":
            notes.append("Rechnung korrekt verarbeitet")
        elif status == "document":
            notes.append("Dokument erkannt (keine Rechnung)")
        elif status == "duplicate":
            notes.append("Doppelte Datei im gleichen Lauf")
        elif status == "unklar":
            notes.append("Zuordnung nicht eindeutig möglich")
        elif status == "error":
            notes.append("Verarbeitung fehlgeschlagen")

        if event.get("fallback_used") is True:
            notes.append("System-Fallback verwendet")

        routing_decision = str(event.get("routing_decision") or "")
        if "Normalisierung=" in routing_decision:
            normalization = routing_decision.split("Normalisierung=", 1)[1]
            normalization = normalization.split("; Historischer Treffer", 1)[0].strip()
            if normalization and normalization != "ok":
                notes.append(normalization)

        error = str(event.get("error") or "").strip()
        if error:
            notes.append(error)

        return "; ".join(dict.fromkeys(notes)) if notes else "-"
