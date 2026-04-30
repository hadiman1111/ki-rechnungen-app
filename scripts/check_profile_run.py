"""
Prüft einen fertig verarbeiteten Run-Ordner und gibt ein PASS/FAIL-Urteil aus.

Verwendung:
    PYTHONPATH=. ./.venv/bin/python scripts/check_profile_run.py \
        --run-dir "<RUN_DIR>" \
        --baseline "25,1,3,1,0"

    RUN_DIR ist der Wurzelordner des Laufs (enthält runtime_rules.json,
    profile_snapshot.json, input_snapshot/, output/_runs/<RUN_ID>/).

Baseline-Format: processed,documents,duplicates,unklar,errors
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _ok(label: str, detail: str = "") -> None:
    suffix = f"  {detail}" if detail else ""
    print(f"  [OK ] {label}{suffix}")


def _warn(label: str, detail: str = "") -> None:
    suffix = f"  {detail}" if detail else ""
    print(f"  [WRN] {label}{suffix}")


def _fail(label: str, detail: str = "") -> None:
    suffix = f"  {detail}" if detail else ""
    print(f"  [NOK] {label}{suffix}")


def _find_run_report_dir(run_dir: Path) -> Optional[Path]:
    """Sucht das einzige _runs/<RUN_ID>-Unterverzeichnis."""
    runs_root = run_dir / "output" / "_runs"
    if not runs_root.is_dir():
        return None
    candidates = [p for p in runs_root.iterdir() if p.is_dir()]
    return candidates[0] if len(candidates) == 1 else None


def _load_json(path: Path) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Prüfroutinen
# ---------------------------------------------------------------------------

def check_report(report_dir: Path) -> tuple:
    path = report_dir / "report.json"
    ok = True
    if not path.exists():
        _fail("report.json", "Datei fehlt")
        return None, False
    data = _load_json(path)
    if data is None:
        _fail("report.json", "Ungültiges JSON")
        return None, False
    if "summary" not in data or "files" not in data:
        _fail("report.json", "Fehlende Felder 'summary' oder 'files'")
        ok = False
    else:
        _ok("report.json")
    return data, ok


def check_runtime_rules(run_dir: Path) -> tuple:
    path = run_dir / "runtime_rules.json"
    if not path.exists():
        _fail("runtime_rules.json", "Datei fehlt")
        return None, False
    data = _load_json(path)
    if data is None:
        _fail("runtime_rules.json", "Ungültiges JSON")
        return None, False
    _ok("runtime_rules.json")
    return data, True


def check_profile_snapshot(run_dir: Path, profile_applied: bool) -> bool:
    path = run_dir / "profile_snapshot.json"
    if profile_applied:
        if not path.exists():
            _fail("profile_snapshot.json", "Profil aktiv, aber Snapshot fehlt")
            return False
        if _load_json(path) is None:
            _fail("profile_snapshot.json", "Ungültiges JSON")
            return False
        _ok("profile_snapshot.json")
    else:
        if path.exists():
            _warn("profile_snapshot.json", "Vorhanden, obwohl kein Profil aktiv")
        else:
            _ok("profile_snapshot.json", "nicht erwartet (kein Profil)")
    return True


def check_decision_trace(report_dir: Path) -> tuple:
    path = report_dir / "decision_trace.jsonl"
    if not path.exists():
        _fail("decision_trace.jsonl", "Datei fehlt")
        return [], False
    entries = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except Exception as exc:
        _fail("decision_trace.jsonl", str(exc))
        return [], False
    _ok("decision_trace.jsonl", f"{len(entries)} Einträge")
    return entries, True


def check_routing_summary(report_dir: Path) -> bool:
    path = report_dir / "routing_summary.csv"
    if not path.exists():
        _fail("routing_summary.csv", "Datei fehlt")
        return False
    _ok("routing_summary.csv")
    return True


# ---------------------------------------------------------------------------
# Meta-Ausgabe
# ---------------------------------------------------------------------------

def print_meta(meta: dict) -> None:
    print()
    print("Meta (runtime_rules.json):")
    print(f"  profile_applied     : {meta.get('profile_applied')}")
    generated = meta.get("generated_sections", [])
    prepended = meta.get("prepended_sections", [])
    protected = meta.get("protected_sections", [])
    print(f"  generated_sections  : {', '.join(generated) if generated else '–'}")
    print(f"  prepended_sections  : {', '.join(prepended) if prepended else '–'}")
    print(f"  protected_sections  : {', '.join(protected) if protected else '–'}")
    print(f"  merge_strategy      : {meta.get('merge_strategy', '–')}")


# ---------------------------------------------------------------------------
# Laufwerte & Baseline
# ---------------------------------------------------------------------------

def print_summary(summary: dict, baseline: Optional[tuple]) -> bool:
    processed  = summary.get("processed", 0)
    documents  = summary.get("documents", 0)
    duplicates = summary.get("duplicates", 0)
    unklar     = summary.get("unklar", 0)
    errors     = summary.get("errors", 0)
    fallbacks  = summary.get("system_fallbacks", 0)

    print()
    print("Laufwerte:")
    print(f"  processed  : {processed}")
    print(f"  documents  : {documents}")
    print(f"  duplicates : {duplicates}")
    print(f"  unklar     : {unklar}")
    print(f"  errors     : {errors}")
    fallback_note = "  ← Primär-Extraktion (OpenAI) nicht verfügbar, Fallback genutzt" if fallbacks > 0 else ""
    print(f"  fallbacks  : {fallbacks}{fallback_note}")

    if baseline is None:
        return True

    expected = baseline
    actual   = (processed, documents, duplicates, unklar, errors)
    match    = actual == expected

    print()
    print("Baseline-Vergleich:")
    labels = ["processed", "documents", "duplicates", "unklar", "errors"]
    baseline_ok = True
    for label, exp, got in zip(labels, expected, actual):
        if exp == got:
            _ok(label, f"{got} == {exp}")
        else:
            _fail(label, f"{got} != {exp} (erwartet)")
            baseline_ok = False
    return baseline_ok


# ---------------------------------------------------------------------------
# Unklar-Fälle
# ---------------------------------------------------------------------------

def print_unklar(entries: list[dict]) -> None:
    unklar = [e for e in entries if e.get("final_status") == "unklar"]
    print()
    print(f"Unklar-Fälle ({len(unklar)}):")
    if not unklar:
        print("  – keine")
        return
    for e in unklar:
        print(f"  Datei    : {e.get('original_filename', '?')}")
        print(f"  art      : {e.get('final_art', '?')}")
        print(f"  payment  : {e.get('final_payment_field', '?')}")
        print(f"  final_assignment_rule: {e.get('final_assignment_rule_name', '?')}")
        print(f"  Grund    : {e.get('account_match_reason', '?')}")
        conflicts = e.get("conflicts") or []
        if conflicts:
            print(f"  Konflikte: {'; '.join(conflicts)}")
        print()


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prüft einen Run-Ordner auf Vollständigkeit und optionale Baseline."
    )
    parser.add_argument(
        "--run-dir", required=True,
        help="Wurzelordner des Laufs (enthält runtime_rules.json, output/, …)"
    )
    parser.add_argument(
        "--baseline", default=None,
        help="Erwartete Laufwerte als 'processed,documents,duplicates,unklar,errors'"
    )
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"FEHLER: Run-Ordner nicht gefunden: {run_dir}")
        return 2

    report_dir = _find_run_report_dir(run_dir)
    if report_dir is None:
        print(f"FEHLER: Kein eindeutiges _runs/<RUN_ID>-Verzeichnis unter {run_dir}/output/_runs/")
        return 2

    run_id = report_dir.name
    print(f"Run-ID  : {run_id}")
    print(f"Run-Dir : {run_dir}")
    print()

    baseline: Optional[tuple] = None
    if args.baseline:
        try:
            parts = [int(x.strip()) for x in args.baseline.split(",")]
            if len(parts) != 5:
                raise ValueError
            baseline = tuple(parts)  # type: ignore[assignment]
        except ValueError:
            print("FEHLER: --baseline muss 5 kommagetrennte Ganzzahlen haben (processed,documents,duplicates,unklar,errors)")
            return 2

    # --- Artefakt-Prüfungen ---
    print("Artefakte:")
    report_data, report_ok    = check_report(report_dir)
    rt_data, rt_ok            = check_runtime_rules(run_dir)
    trace_entries, trace_ok   = check_decision_trace(report_dir)
    routing_ok                = check_routing_summary(report_dir)

    meta: dict = {}
    profile_applied = False
    if rt_data:
        meta = rt_data.get("_meta", {})
        profile_applied = bool(meta.get("profile_applied", False))

    snapshot_ok = check_profile_snapshot(run_dir, profile_applied)

    # --- Meta ---
    if meta:
        print_meta(meta)

    # --- Laufwerte ---
    baseline_ok = True
    if report_data and "summary" in report_data:
        baseline_ok = print_summary(report_data["summary"], baseline)
    else:
        print("\nLaufwerte: nicht verfügbar (report.json fehlt oder ungültig)")

    # --- Unklar-Fälle ---
    if trace_entries:
        print_unklar(trace_entries)

    # --- PASS/FAIL ---
    all_ok = report_ok and rt_ok and trace_ok and routing_ok and snapshot_ok and baseline_ok

    print("=" * 60)
    if all_ok:
        print("ERGEBNIS: PASS")
        print()
        print("ENTSCHEIDUNGSSIGNAL: WEITER IN CURSOR")
        print("EMPFOHLENER MODUS: Agent")
        print("CHATGPT NÖTIG: nein")
        print("ZAUBERWORT: Weiter nach Projektregeln.")
    else:
        print("ERGEBNIS: FAIL")
        print()
        print("ENTSCHEIDUNGSSIGNAL: STOPP")
        print("EMPFOHLENER MODUS: Ask oder ChatGPT")
        print("CHATGPT NÖTIG: je nach Grund")
        print("GRUND: Mindestens eine Prüfung fehlgeschlagen (siehe NOK oben)")
        print("NÄCHSTER SCHRITT: Fehlschläge beheben, dann erneut prüfen")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
