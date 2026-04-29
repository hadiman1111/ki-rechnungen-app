"""Smoke Test Script for the Run Manager
=========================================

Runs the full verification pipeline in a single command:
1. pytest (unless --skip-pytest)
2. invoice_tool.run.run_once with a fresh snapshot (unless --skip-run)
3. Post-run structural checks
4. Summary report

Usage::

    PYTHONPATH=. ./.venv/bin/python scripts/run_smoke_test.py \\
        --source "/path/to/pdf/folder" \\
        --output "/tmp/ki-rechnungen-smoke"

Exit code: 0 = PASS, 1 = FAIL
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Dataclasses / result types
# ---------------------------------------------------------------------------

class SmokeResult:
    """Accumulates pass/fail flags and produces the final summary."""

    def __init__(self) -> None:
        self.pytest_status: str = "skipped"   # "passed" | "failed" | "skipped"
        self.run_executed: bool = False
        self.run_dir: Path | None = None
        self.source_unchanged: bool | None = None
        self.reports_complete: bool | None = None
        self.processed: int | str = "n/a"
        self.document: int | str = "n/a"
        self.duplicate: int | str = "n/a"
        self.unclear: int | str = "n/a"
        self.errors: int | str = "n/a"
        self._failures: list[str] = []

    def fail(self, reason: str) -> None:
        self._failures.append(reason)

    @property
    def ok(self) -> bool:
        return not self._failures

    def print_summary(self) -> None:
        print()
        print("=" * 50)
        print("SMOKE TEST RESULT")
        print("=" * 50)
        print(f"  pytest:           {self.pytest_status}")
        print(f"  run executed:     {'yes' if self.run_executed else 'no'}")
        print(f"  run_dir:          {self.run_dir or '—'}")
        print(f"  source unchanged: {'yes' if self.source_unchanged else ('no' if self.source_unchanged is False else 'n/a')}")
        print(f"  reports complete: {'yes' if self.reports_complete else ('no' if self.reports_complete is False else 'n/a')}")
        print(f"  processed:        {self.processed}")
        print(f"  document:         {self.document}")
        print(f"  duplicate:        {self.duplicate}")
        print(f"  unclear:          {self.unclear}")
        print(f"  errors:           {self.errors}")
        if self._failures:
            print()
            print("  FAILURES:")
            for f in self._failures:
                print(f"    - {f}")
        print()
        status = "PASS" if self.ok else "FAIL"
        print(f"  final status:     {status}")
        print("=" * 50)
        print()


# ---------------------------------------------------------------------------
# Source validation
# ---------------------------------------------------------------------------

def validate_source(source: Path) -> list[str]:
    """Return a list of error strings; empty = valid."""
    errors: list[str] = []
    if not source.exists():
        errors.append(f"source existiert nicht: {source}")
        return errors
    if not source.is_dir():
        errors.append(f"source ist kein Ordner: {source}")
        return errors
    pdfs = list_pdfs(source)
    if not pdfs:
        errors.append(f"source enthält keine PDF-Dateien: {source}")
    return errors


def list_pdfs(directory: Path) -> list[str]:
    """Return sorted list of PDF filenames in directory (not recursive)."""
    return sorted(
        p.name
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() == ".pdf"
    )


def check_source_unchanged(source: Path, original_names: list[str]) -> bool:
    """Return True if the source directory still has the same PDF names."""
    current_names = list_pdfs(source)
    return current_names == original_names


# ---------------------------------------------------------------------------
# Run structure checks
# ---------------------------------------------------------------------------

_REQUIRED_DIRS = ["input_snapshot", "output", "runtime", "logs"]
_REQUIRED_REPORTS = ["report.txt", "report.json", "decision_trace.jsonl", "routing_summary.csv"]


def check_run_structure(run_dir: Path) -> tuple[bool, list[str]]:
    """Check that run_dir has the expected structure.

    Returns (ok, missing_items).
    """
    missing: list[str] = []

    for d in _REQUIRED_DIRS:
        if not (run_dir / d).is_dir():
            missing.append(f"directory: {d}/")

    runs_dir = run_dir / "output" / "_runs"
    if not runs_dir.is_dir():
        missing.append("directory: output/_runs/")
        return False, missing

    run_subdirs = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    if not run_subdirs:
        missing.append("output/_runs/ has no subdirectory")
        return False, missing

    latest_run = run_subdirs[-1]
    for report in _REQUIRED_REPORTS:
        if not (latest_run / report).is_file():
            missing.append(f"report: output/_runs/{latest_run.name}/{report}")

    return len(missing) == 0, missing


def parse_report_summary(run_dir: Path) -> dict[str, int | str]:
    """Parse key metrics from the latest report.json in run_dir."""
    result: dict[str, int | str] = {
        "processed": "nicht gefunden",
        "document": "nicht gefunden",
        "duplicate": "nicht gefunden",
        "unclear": "nicht gefunden",
        "errors": "nicht gefunden",
    }
    runs_dir = run_dir / "output" / "_runs"
    if not runs_dir.is_dir():
        return result

    run_subdirs = sorted(p for p in runs_dir.iterdir() if p.is_dir())
    if not run_subdirs:
        return result

    report_path = run_subdirs[-1] / "report.json"
    if not report_path.is_file():
        return result

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return result

    summary = data.get("summary") or {}
    result["processed"] = summary.get("processed", "nicht gefunden")
    result["document"] = summary.get("documents", summary.get("document", "nicht gefunden"))
    result["duplicate"] = summary.get("duplicates", summary.get("duplicate", "nicht gefunden"))
    result["unclear"] = summary.get("unklar", summary.get("unclear", "nicht gefunden"))
    result["errors"] = summary.get("errors", "nicht gefunden")
    return result


# ---------------------------------------------------------------------------
# Pytest runner
# ---------------------------------------------------------------------------

def run_pytest() -> str:
    """Run pytest and return 'passed', 'failed', or 'error'."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            capture_output=False,
            text=True,
        )
        return "passed" if proc.returncode == 0 else "failed"
    except Exception as exc:
        print(f"[smoke] pytest konnte nicht ausgeführt werden: {exc}", file=sys.stderr)
        return "error"


# ---------------------------------------------------------------------------
# CLI argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/run_smoke_test.py",
        description=(
            "Smoke test: runs pytest, executes the Run Manager, and verifies "
            "the output structure. Originals are never modified."
        ),
    )
    parser.add_argument(
        "--source",
        type=Path,
        metavar="DIR",
        help="Directory with PDF files to process (read-only).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        metavar="DIR",
        help="Base directory for smoke-test run subdirectories.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="FILE",
        help="Path to invoice_config.json. Defaults to ./invoice_config.json.",
    )
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        default=False,
        help="Skip the pytest step.",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        default=False,
        help="Skip the Run Manager step.",
    )
    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = SmokeResult()

    # --- pytest ---
    if args.skip_pytest:
        result.pytest_status = "skipped"
        print("[smoke] pytest übersprungen (--skip-pytest).")
    else:
        print("[smoke] Führe pytest aus …")
        result.pytest_status = run_pytest()
        if result.pytest_status != "passed":
            result.fail(f"pytest {result.pytest_status}")
            result.print_summary()
            return 1
        print(f"[smoke] pytest: {result.pytest_status}")

    # --- run manager ---
    if args.skip_run:
        print("[smoke] Run Manager übersprungen (--skip-run).")
        result.print_summary()
        return 0 if result.ok else 1

    # source and output required when run is not skipped
    if not args.source or not args.output:
        print(
            "[smoke] Fehler: --source und --output sind pflicht, wenn --skip-run nicht gesetzt ist.",
            file=sys.stderr,
        )
        return 1

    source = args.source.resolve()
    output = args.output.resolve()

    source_errors = validate_source(source)
    if source_errors:
        for err in source_errors:
            result.fail(err)
        result.print_summary()
        return 1

    original_names = list_pdfs(source)
    print(f"[smoke] Source: {source} ({len(original_names)} PDFs)")
    print(f"[smoke] Output base: {output}")
    output.mkdir(parents=True, exist_ok=True)

    # Import run_once; fall back to subprocess if unavailable
    try:
        from invoice_tool.run import run_once, RunError  # noqa: PLC0415
    except ImportError as exc:
        result.fail(f"invoice_tool.run konnte nicht importiert werden: {exc}")
        result.print_summary()
        return 1

    config_path = (
        args.config.resolve() if args.config is not None
        else Path("invoice_config.json").resolve()
    )

    print("[smoke] Starte Run Manager …")
    try:
        run_dir = run_once(source=source, output=output, config_path=config_path)
    except (RunError, Exception) as exc:
        result.fail(f"run_once fehlgeschlagen: {exc}")
        result.print_summary()
        return 1

    result.run_executed = True
    result.run_dir = run_dir
    print(f"[smoke] Run abgeschlossen: {run_dir}")

    # --- source unchanged ---
    result.source_unchanged = check_source_unchanged(source, original_names)
    if not result.source_unchanged:
        result.fail("source wurde verändert – Original-PDFs fehlen oder wurden umbenannt")

    # --- run structure ---
    structure_ok, missing = check_run_structure(run_dir)
    result.reports_complete = structure_ok
    if not structure_ok:
        for item in missing:
            result.fail(f"fehlend: {item}")

    # --- report summary ---
    metrics = parse_report_summary(run_dir)
    result.processed = metrics["processed"]
    result.document = metrics["document"]
    result.duplicate = metrics["duplicate"]
    result.unclear = metrics["unclear"]
    result.errors = metrics["errors"]

    if result.errors not in ("nicht gefunden", 0):
        result.fail(f"Run hatte {result.errors} Fehler")

    result.print_summary()
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
