"""Subprocess orchestration for the internal SOMAA launcher."""

from __future__ import annotations

import json
import re
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from invoice_tool.app_paths import project_root, user_support_dir

_RUN_DIR_PATTERN = re.compile(
    r"\[run\]\s+Lauf abgeschlossen\.\s+Technischer Run-Ordner:\s+(.+?)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class RunOutcome:
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    log_path: Path
    command: tuple[str, ...]
    started_at: datetime
    finished_at: datetime
    run_dir: Path | None = None


def internal_launcher_log_dir() -> Path:
    path = user_support_dir() / "internal-launcher" / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_run_dir_from_stdout(stdout: str) -> Path | None:
    match = _RUN_DIR_PATTERN.search(stdout or "")
    if not match:
        return None
    return Path(match.group(1))


class RunController:
    """Runs the verified backend CLI with an in-memory active-run lock."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        python_executable: Path | None = None,
        profile_path: Path,
    ) -> None:
        self._repo_root = (repo_root or project_root()).resolve()
        default_python = self._repo_root / ".venv-flet085" / "bin" / "python"
        self._python = (python_executable or default_python).expanduser()
        if not self._python.is_absolute():
            self._python = (Path.cwd() / self._python).resolve()
        self._profile_path = profile_path.resolve()
        self._lock = threading.Lock()
        self._active = False
        self._thread: threading.Thread | None = None

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    @property
    def python_executable(self) -> Path:
        return self._python

    @property
    def profile_path(self) -> Path:
        return self._profile_path

    def is_running(self) -> bool:
        with self._lock:
            return self._active

    def build_command(self, source: Path, output: Path) -> list[str]:
        return [
            str(self._python),
            "-m",
            "invoice_tool.run",
            "--source",
            str(source.resolve()),
            "--output",
            str(output.resolve()),
            "--profile",
            str(self._profile_path),
        ]

    def _write_log(
        self,
        *,
        command: tuple[str, ...],
        source: Path,
        output: Path,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_seconds: float,
        started_at: datetime,
        finished_at: datetime,
    ) -> Path:
        log_dir = internal_launcher_log_dir()
        stamp = started_at.strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"launcher_run_{stamp}.log"
        payload = {
            "timestamp": started_at.isoformat(),
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": duration_seconds,
            "source": str(source.resolve()),
            "output": str(output.resolve()),
            "profile_path": str(self._profile_path),
            "command": list(command),
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        }
        log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return log_path

    def _run_subprocess(self, source: Path, output: Path) -> RunOutcome:
        command = tuple(self.build_command(source, output))
        started_at = datetime.now(timezone.utc)
        proc = subprocess.run(
            list(command),
            cwd=str(self._repo_root),
            capture_output=True,
            text=True,
            shell=False,
        )
        finished_at = datetime.now(timezone.utc)
        duration = (finished_at - started_at).total_seconds()
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        log_path = self._write_log(
            command=command,
            source=source,
            output=output,
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            started_at=started_at,
            finished_at=finished_at,
        )
        return RunOutcome(
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            log_path=log_path,
            command=command,
            started_at=started_at,
            finished_at=finished_at,
            run_dir=parse_run_dir_from_stdout(stdout),
        )

    def execute(self, source: Path, output: Path) -> RunOutcome:
        """Synchronous execution (used by tests and acceptance harness)."""
        if self.is_running():
            raise RuntimeError("Es läuft bereits eine Verarbeitung.")
        with self._lock:
            self._active = True
        try:
            return self._run_subprocess(source, output)
        finally:
            with self._lock:
                self._active = False

    def start_async(
        self,
        source: Path,
        output: Path,
        *,
        on_complete: Callable[[RunOutcome], None],
    ) -> bool:
        """Start background run. Returns False when a run is already active."""
        with self._lock:
            if self._active:
                return False
            self._active = True

        def _worker() -> None:
            outcome: RunOutcome
            try:
                outcome = self._run_subprocess(source, output)
            except Exception as exc:
                started_at = datetime.now(timezone.utc)
                finished_at = started_at
                command = tuple(self.build_command(source, output))
                log_path = self._write_log(
                    command=command,
                    source=source,
                    output=output,
                    exit_code=1,
                    stdout="",
                    stderr=str(exc),
                    duration_seconds=0.0,
                    started_at=started_at,
                    finished_at=finished_at,
                )
                outcome = RunOutcome(
                    exit_code=1,
                    stdout="",
                    stderr=str(exc),
                    duration_seconds=0.0,
                    log_path=log_path,
                    command=command,
                    started_at=started_at,
                    finished_at=finished_at,
                )
            finally:
                with self._lock:
                    self._active = False
                    self._thread = None
            on_complete(outcome)

        thread = threading.Thread(target=_worker, name="internal-launcher-run", daemon=True)
        with self._lock:
            self._thread = thread
        thread.start()
        return True
