from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from invoice_tool.internal_launcher.run_controller import RunController, parse_run_dir_from_stdout


def test_build_command_exact_args(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    python = repo / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\n", encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")

    controller = RunController(
        repo_root=repo,
        python_executable=python,
        profile_path=profile,
    )
    source = tmp_path / "in"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    command = controller.build_command(source, output)
    assert command[0] == str(python)
    assert command[1:3] == ["-m", "invoice_tool.run"]
    assert "--source" in command
    assert "--output" in command
    assert "--profile" in command
    assert str(source.resolve()) in command
    assert str(output.resolve()) in command
    assert str(profile.resolve()) in command


def test_no_shell_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    python = repo / "py"
    python.write_text("", encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    controller = RunController(repo_root=repo, python_executable=python, profile_path=profile)

    captured: dict[str, object] = {}

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured["shell"] = kwargs.get("shell")
        captured["cwd"] = kwargs.get("cwd")
        captured["args"] = args[0]
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "[run] Lauf abgeschlossen. Technischer Run-Ordner: /tmp/run"
        mock.stderr = ""
        return mock

    monkeypatch.setattr("invoice_tool.internal_launcher.run_controller.subprocess.run", _fake_run)
    source = tmp_path / "in"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()
    controller.execute(source, output)
    assert captured["shell"] is False
    assert captured["cwd"] == str(repo.resolve())


def test_active_run_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    python = repo / "py"
    python.write_text("", encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    controller = RunController(repo_root=repo, python_executable=python, profile_path=profile)

    started = threading.Event()
    release = threading.Event()

    def _slow_run(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        started.set()
        release.wait(timeout=2)
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        return mock

    monkeypatch.setattr("invoice_tool.internal_launcher.run_controller.subprocess.run", _slow_run)
    source = tmp_path / "in"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    done: list[bool] = []

    def _worker() -> None:
        controller.execute(source, output)
        done.append(True)

    thread = threading.Thread(target=_worker)
    thread.start()
    assert started.wait(timeout=2)
    assert controller.is_running()
    with pytest.raises(RuntimeError):
        controller.execute(source, output)
    release.set()
    thread.join(timeout=3)
    assert done
    assert not controller.is_running()


def test_second_async_start_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    python = repo / "py"
    python.write_text("", encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    controller = RunController(repo_root=repo, python_executable=python, profile_path=profile)

    release = threading.Event()

    def _slow_run(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        release.wait(timeout=2)
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        return mock

    monkeypatch.setattr("invoice_tool.internal_launcher.run_controller.subprocess.run", _slow_run)
    source = tmp_path / "in"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()

    assert controller.start_async(source, output, on_complete=lambda _o: None)
    assert not controller.start_async(source, output, on_complete=lambda _o: None)
    release.set()
    time.sleep(0.2)


def test_exit_code_and_capture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    python = repo / "py"
    python.write_text("", encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text("{}", encoding="utf-8")
    controller = RunController(repo_root=repo, python_executable=python, profile_path=profile)

    def _fail_run(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        mock = MagicMock()
        mock.returncode = 1
        mock.stdout = ""
        mock.stderr = "Fehler: test"
        return mock

    monkeypatch.setattr("invoice_tool.internal_launcher.run_controller.subprocess.run", _fail_run)
    source = tmp_path / "in"
    output = tmp_path / "out"
    source.mkdir()
    output.mkdir()
    outcome = controller.execute(source, output)
    assert outcome.exit_code == 1
    assert outcome.stderr == "Fehler: test"
    assert outcome.log_path.is_file()
    payload = json.loads(outcome.log_path.read_text(encoding="utf-8"))
    assert payload["exit_code"] == 1


def test_parse_run_dir_from_stdout() -> None:
    stdout = (
        "[run] Lauf abgeschlossen. Technischer Run-Ordner: "
        "/Users/test/Library/Application Support/KI-Rechnungen/runs/20260714_120000"
    )
    assert parse_run_dir_from_stdout(stdout) == Path(
        "/Users/test/Library/Application Support/KI-Rechnungen/runs/20260714_120000"
    )
