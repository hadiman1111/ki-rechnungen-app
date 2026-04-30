"""Local Development Assistant
==============================
Bündelt wiederkehrende Standardprüfungen und gibt am Ende immer ein
Entscheidungssignal nach Projektregeln aus.

Sicherheitsregeln (unveränderlich):
- Kein Push, kein Commit, kein Produktivlauf
- Keine Original-PDFs verändern
- Keine Änderung an office_rules.json, invoice_config.json oder Profil-Dateien
- Nur prüfen, vorhandene sichere Test-/Smoke-Test-Befehle ausführen, Berichte auswerten

Modi:
  --mode status          Git-Zustand prüfen
  --mode test            pytest ausführen
  --mode smoke-profile   Smoke-Test mit lokalem Profil ausführen
  --mode check-last-run  Letzten Run-Ordner prüfen
  --mode next            Automatische Standardsequenz (empfohlen)

Verwendung:
    PYTHONPATH=. ./.venv/bin/python scripts/dev_assistant.py --mode next
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Konstanten
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SMOKE_SOURCE = "260425_archiv Rechnungen"
SMOKE_OUTPUT = "/tmp/ki-rechnungen-auto-smoke-profile"
SMOKE_PROFILE = "profile_config.local.json"
BASELINE = (25, 1, 3, 1, 0)   # processed, documents, duplicates, unklar, errors
BASELINE_LABEL = "25,1,3,1,0"

SEPARATOR = "=" * 60


# ---------------------------------------------------------------------------
# Entscheidungssignal-Ausgabe
# ---------------------------------------------------------------------------

class Signal:
    WEITER    = "WEITER IN CURSOR"
    CHATGPT   = "CHATGPT FRAGEN"
    FREIGABE  = "NUTZERFREIGABE"
    STOPP     = "STOPP"


def print_signal(
    signal: str,
    *,
    modus: str = "Agent",
    chatgpt: str = "nein",
    empfehlung: str = "",
    begruendung: str = "",
    naechster_schritt: str = "",
    freigabefrage: str = "",
    frage_an_chatgpt: str = "",
) -> None:
    print()
    print(SEPARATOR)
    print(f"ENTSCHEIDUNGSSIGNAL: {signal}")

    if signal == Signal.WEITER:
        print(f"EMPFOHLENER MODUS: {modus}")
        print(f"CHATGPT NÖTIG: {chatgpt}")
        print("ZAUBERWORT: Weiter nach Projektregeln.")

    elif signal == Signal.CHATGPT:
        print(f"EMPFOHLENER MODUS: {modus}")
        print(f"CHATGPT NÖTIG: {chatgpt}")
        if frage_an_chatgpt:
            print(f"FRAGE AN CHATGPT: {frage_an_chatgpt}")

    elif signal == Signal.FREIGABE:
        print(f"EMPFOHLENER MODUS NACH FREIGABE: {modus}")
        print(f"CHATGPT NÖTIG: {chatgpt}")
        if freigabefrage:
            print(f"FREIGABEFRAGE: {freigabefrage}")
        if empfehlung:
            print(f"EMPFEHLUNG: {empfehlung}")
        if begruendung:
            print(f"BEGRÜNDUNG: {begruendung}")

    elif signal == Signal.STOPP:
        print(f"EMPFOHLENER MODUS: {modus}")
        print(f"CHATGPT NÖTIG: {chatgpt}")
        if begruendung:
            print(f"GRUND: {begruendung}")
        if naechster_schritt:
            print(f"NÄCHSTER SCHRITT: {naechster_schritt}")

    print(SEPARATOR)

    if signal in (Signal.FREIGABE, Signal.CHATGPT, Signal.STOPP):
        _beep()


def _beep() -> None:
    """Optional akustisches Signal auf macOS. Kein harter Fehler bei Fehlschlag."""
    try:
        subprocess.run(
            ["osascript", "-e", "beep"],
            capture_output=True,
            timeout=3,
        )
    except Exception:
        print("  [INFO] Akustisches Signal nicht verfügbar.")


# ---------------------------------------------------------------------------
# Mode: status
# ---------------------------------------------------------------------------

def run_status() -> dict:
    """Prüft Git-Zustand. Gibt dict mit Ergebnissen zurück."""
    print(f"\n{'─'*40}")
    print("GIT-STATUS")
    print(f"{'─'*40}")

    result: dict = {
        "branch": None,
        "last_commit": None,
        "ahead": 0,
        "behind": 0,
        "staged": [],
        "unstaged": [],
        "untracked": [],
        "clean": False,
        "error": None,
    }

    try:
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"])
        result["branch"] = branch
        print(f"Branch         : {branch}")

        last = _git(["log", "--oneline", "-1"])
        result["last_commit"] = last
        print(f"Letzter Commit : {last}")

        try:
            ahead_str  = _git(["rev-list", "--count", "origin/main..HEAD"])
            behind_str = _git(["rev-list", "--count", "HEAD..origin/main"])
            result["ahead"]  = int(ahead_str)
            result["behind"] = int(behind_str)
            print(f"Vor origin/main: {result['ahead']} Commit(s)")
            print(f"Hinter origin:   {result['behind']} Commit(s)")
        except Exception:
            print("origin/main   : kein Vergleich möglich")

        status_out = _git(["status", "--porcelain"])
        staged = unstaged = untracked = []
        if status_out:
            lines = status_out.splitlines()
            staged    = [l[3:] for l in lines if l[:2] in ("M ", "A ", "D ", "R ", "C ")]
            unstaged  = [l[3:] for l in lines if l[1] in ("M", "D") and l[0] == " "]
            untracked = [l[3:] for l in lines if l[:2] == "??"]
        result["staged"]    = staged
        result["unstaged"]  = unstaged
        result["untracked"] = untracked
        result["clean"]     = not bool(status_out.strip())

        print(f"Staged         : {staged or '–'}")
        print(f"Unstaged       : {unstaged or '–'}")
        print(f"Untracked      : {untracked or '–'}")
        print(f"Working Tree   : {'CLEAN ✓' if result['clean'] else 'NOT CLEAN ✗'}")

    except Exception as exc:
        result["error"] = str(exc)
        print(f"FEHLER: {exc}")

    return result


def _git(args: list[str]) -> str:
    proc = subprocess.run(
        ["git"] + args,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {args[0]} failed")
    return proc.stdout.strip()


# ---------------------------------------------------------------------------
# Mode: test
# ---------------------------------------------------------------------------

def run_tests() -> bool:
    """Führt pytest aus. Gibt True bei PASS zurück."""
    print(f"\n{'─'*40}")
    print("TESTS (pytest -q)")
    print(f"{'─'*40}")

    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable

    proc = subprocess.run(
        [python_exe, "-m", "pytest", "-q"],
        cwd=str(PROJECT_ROOT),
        capture_output=False,
        timeout=180,
    )
    passed = proc.returncode == 0
    print(f"\nTests: {'PASS ✓' if passed else 'FAIL ✗'}  (Exit-Code {proc.returncode})")
    return passed


# ---------------------------------------------------------------------------
# Mode: smoke-profile
# ---------------------------------------------------------------------------

def run_smoke_profile() -> bool:
    """Führt Smoke-Test mit lokalem Profil aus. Gibt True bei PASS zurück."""
    print(f"\n{'─'*40}")
    print("SMOKE-TEST mit lokalem Profil")
    print(f"{'─'*40}")

    profile_path = PROJECT_ROOT / SMOKE_PROFILE
    if not profile_path.exists():
        print(f"FEHLER: Lokales Profil nicht gefunden: {profile_path}")
        return False

    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable

    source_path = PROJECT_ROOT / SMOKE_SOURCE
    if not source_path.exists():
        print(f"FEHLER: Quellordner nicht gefunden: {source_path}")
        return False

    cmd = [
        python_exe,
        "scripts/run_smoke_test.py",
        "--source", str(source_path),
        "--output", SMOKE_OUTPUT,
        "--profile", SMOKE_PROFILE,
    ]
    print(f"Befehl: {' '.join(cmd)}")

    env = {"PYTHONPATH": str(PROJECT_ROOT)}
    import os
    full_env = {**os.environ, **env}

    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=full_env, timeout=600)
    passed = proc.returncode == 0
    print(f"\nSmoke-Test: {'PASS ✓' if passed else 'FAIL ✗'}  (Exit-Code {proc.returncode})")
    return passed


# ---------------------------------------------------------------------------
# Mode: check-last-run
# ---------------------------------------------------------------------------

def find_latest_run_dir(base_output: str) -> Optional[Path]:
    """Findet den neuesten Run-Ordner unter base_output."""
    base = Path(base_output)
    if not base.is_dir():
        return None
    candidates = sorted(
        [p for p in base.iterdir() if p.is_dir() and p.name[0].isdigit()],
        key=lambda p: p.name,
        reverse=True,
    )
    return candidates[0] if candidates else None


def run_check_last_run(base_output: str = SMOKE_OUTPUT) -> bool:
    """Prüft den letzten Run-Ordner. Gibt True bei PASS zurück."""
    print(f"\n{'─'*40}")
    print(f"CHECK LAST RUN  ({base_output})")
    print(f"{'─'*40}")

    run_dir = find_latest_run_dir(base_output)
    if run_dir is None:
        print(f"FEHLER: Kein Run-Ordner gefunden unter {base_output}")
        return False

    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    python_exe = str(venv_python) if venv_python.exists() else sys.executable

    cmd = [
        python_exe,
        "scripts/check_profile_run.py",
        "--run-dir", str(run_dir),
        "--baseline", BASELINE_LABEL,
    ]
    print(f"Run-Dir : {run_dir}")
    print(f"Befehl  : {' '.join(cmd)}")

    import os
    full_env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=full_env, timeout=30)
    passed = proc.returncode == 0
    return passed


# ---------------------------------------------------------------------------
# Smart-Skip: Smoke-Test nur ausführen wenn nötig
# ---------------------------------------------------------------------------

# Dateipfade, deren Änderung einen neuen Smoke-Test erfordert.
# Reine Docs/Regel-Dateien werden nicht berücksichtigt.
_SMOKE_RELEVANT_PATHS = (
    "invoice_tool/",
    "office_rules.json",
    "office_rules.schema.json",
    "profile_config.local.json",
    "scripts/run_smoke_test.py",
    "scripts/check_profile_run.py",
    "scripts/dev_assistant.py",
)


def _is_smoke_fresh(base_output: str = SMOKE_OUTPUT) -> bool:
    """True wenn kein smoke-relevanter Code seit dem letzten Run-Ordner geändert wurde.

    Logik:
    1. Neuesten Run-Ordner finden (Format YYYYMMDD_HHMMSS).
    2. Alle Commits seit dem Run-Zeitstempel prüfen.
    3. Nur wenn dabei Dateien in _SMOKE_RELEVANT_PATHS geändert wurden,
       gilt der Smoke als veraltet (→ False).
    4. Reine Docs-/Workflow-Commits werden ignoriert → Smart-Skip bleibt aktiv.
    """
    run_dir = find_latest_run_dir(base_output)
    if run_dir is None:
        return False

    from datetime import datetime
    try:
        run_time = datetime.strptime(run_dir.name, "%Y%m%d_%H%M%S")
    except ValueError:
        return False

    # Prüfe ob seit run_time code-relevante Commits existieren
    try:
        run_iso = run_time.strftime("%Y-%m-%dT%H:%M:%S")
        changed = _git([
            "log", "--name-only", "--format=", f"--since={run_iso}",
        ])
    except Exception:
        return False

    if not changed.strip():
        return True  # keine Commits seit Run → frisch

    changed_files = [line.strip() for line in changed.splitlines() if line.strip()]
    for path in changed_files:
        for relevant in _SMOKE_RELEVANT_PATHS:
            if path.startswith(relevant) or path == relevant:
                return False  # relevante Datei geändert → Smoke nötig

    return True  # nur Docs/Workflow-Änderungen → Skip


# ---------------------------------------------------------------------------
# Mode: next  (Hauptsequenz)
# ---------------------------------------------------------------------------

def run_next() -> None:
    """Automatische Standardsequenz: status → (smoke wenn nötig) → check → signal."""
    print(f"\n{'═'*60}")
    print(" DEV ASSISTANT – MODUS: NEXT")
    print(f"{'═'*60}")

    # 1. Git-Status
    status = run_status()

    if status.get("error"):
        print_signal(
            Signal.STOPP,
            modus="Ask",
            chatgpt="nein",
            begruendung=f"Git-Statusabfrage fehlgeschlagen: {status['error']}",
            naechster_schritt="Git-Zustand manuell prüfen.",
        )
        return

    if not status["clean"]:
        print_signal(
            Signal.STOPP,
            modus="Ask",
            chatgpt="nein",
            begruendung="Working Tree ist nicht clean (staged/unstaged/untracked Dateien vorhanden).",
            naechster_schritt="git status prüfen und Dateien bereinigen oder committen.",
        )
        return

    ahead = status.get("ahead", 0)
    if ahead > 0:
        print_signal(
            Signal.FREIGABE,
            modus="Agent",
            chatgpt="nein",
            freigabefrage=f"Soll ich {ahead} Commit(s) zu origin/main pushen?",
            empfehlung="freigeben",
            begruendung=(
                f"{ahead} lokale(r) Commit(s) bereit zum Push. "
                "Working Tree clean, kein Risiko bekannt."
            ),
        )
        return

    # 2. Smoke-Test (Smart-Skip: überspringen wenn Run nach letztem Commit)
    if _is_smoke_fresh():
        print(f"\n{'─'*40}")
        print("SMOKE-TEST")
        print(f"{'─'*40}")
        print("  [SKIP] Letzter Run-Ordner ist aktueller als HEAD-Commit.")
        print("         Smoke-Test wird übersprungen – check-last-run verifiziert stattdessen.")
        smoke_passed = True
    else:
        smoke_passed = run_smoke_profile()

    if not smoke_passed:
        print_signal(
            Signal.CHATGPT,
            modus="ChatGPT",
            chatgpt="ja",
            frage_an_chatgpt=(
                "Der Smoke-Test mit lokalem Profil ist fehlgeschlagen. "
                "Baseline war 25/1/3/1/0. Bitte Ursache analysieren: "
                "Regression in Routing-Regeln, Profil-Merge oder Dateinamen-Schema?"
            ),
        )
        return

    # 3. Letzten Run prüfen
    check_passed = run_check_last_run()

    if check_passed:
        print_signal(
            Signal.WEITER,
            modus="Agent",
            chatgpt="nein",
        )
    else:
        print_signal(
            Signal.CHATGPT,
            modus="ChatGPT",
            chatgpt="ja",
            frage_an_chatgpt=(
                "check_profile_run.py meldet FAIL obwohl Smoke-Test bestanden hat. "
                "Welches Artefakt fehlt oder ist ungültig?"
            ),
        )


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Local Development Assistant – bündelt Standardprüfungen."
    )
    parser.add_argument(
        "--mode",
        choices=["status", "test", "smoke-profile", "check-last-run", "next"],
        default="next",
        help="Modus (Standard: next)",
    )
    parser.add_argument(
        "--base-output",
        default=SMOKE_OUTPUT,
        help=f"Basisordner für check-last-run (Standard: {SMOKE_OUTPUT})",
    )
    args = parser.parse_args(argv)

    if args.mode == "status":
        status = run_status()
        if status["clean"]:
            print_signal(Signal.WEITER, modus="Agent", chatgpt="nein")
        else:
            print_signal(
                Signal.STOPP,
                modus="Ask",
                chatgpt="nein",
                begruendung="Working Tree nicht clean.",
                naechster_schritt="git status prüfen.",
            )
        return 0

    elif args.mode == "test":
        passed = run_tests()
        if passed:
            print_signal(Signal.WEITER, modus="Agent", chatgpt="nein")
            return 0
        else:
            print_signal(
                Signal.STOPP,
                modus="Ask oder ChatGPT",
                chatgpt="je nach Ursache",
                begruendung="Tests fehlgeschlagen.",
                naechster_schritt="Fehler analysieren, dann erneut testen.",
            )
            return 1

    elif args.mode == "smoke-profile":
        passed = run_smoke_profile()
        if passed:
            print_signal(Signal.WEITER, modus="Agent", chatgpt="nein")
            return 0
        else:
            print_signal(
                Signal.CHATGPT,
                modus="ChatGPT",
                chatgpt="ja",
                frage_an_chatgpt="Smoke-Test fehlgeschlagen. Ursache: Routing-Regression oder Merge-Fehler?",
            )
            return 1

    elif args.mode == "check-last-run":
        passed = run_check_last_run(args.base_output)
        if passed:
            print_signal(Signal.WEITER, modus="Agent", chatgpt="nein")
            return 0
        else:
            print_signal(
                Signal.STOPP,
                modus="Ask oder ChatGPT",
                chatgpt="je nach Grund",
                begruendung="Run-Verifikation fehlgeschlagen (NOK-Artefakt oder Baseline-Abweichung).",
                naechster_schritt="check_profile_run.py-Output analysieren.",
            )
            return 1

    elif args.mode == "next":
        run_next()
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
