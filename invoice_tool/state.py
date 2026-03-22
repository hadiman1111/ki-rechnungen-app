from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path


class LockError(RuntimeError):
    pass


class DirectoryLock:
    def __init__(self, lock_path: Path, stale_after_seconds: int) -> None:
        self.lock_path = lock_path
        self.stale_after_seconds = stale_after_seconds

    def acquire(self) -> None:
        while True:
            try:
                self.lock_path.mkdir(parents=True, exist_ok=False)
                metadata = {
                    "pid": os.getpid(),
                    "created_at": time.time(),
                }
                (self.lock_path / "lock.json").write_text(
                    json.dumps(metadata, indent=2),
                    encoding="utf-8",
                )
                return
            except FileExistsError:
                if self._is_stale():
                    shutil.rmtree(self.lock_path, ignore_errors=True)
                    continue
                raise LockError(f"Lock ist bereits aktiv: {self.lock_path}")

    def release(self) -> None:
        shutil.rmtree(self.lock_path, ignore_errors=True)

    def _is_stale(self) -> bool:
        metadata_file = self.lock_path / "lock.json"
        if not metadata_file.exists():
            return True
        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return True
        created_at = metadata.get("created_at")
        if not isinstance(created_at, (int, float)):
            return True
        return (time.time() - float(created_at)) > self.stale_after_seconds

    def __enter__(self) -> "DirectoryLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


def ensure_runtime_dirs(base_state_dir: Path) -> None:
    (base_state_dir / "locks").mkdir(parents=True, exist_ok=True)
    base_state_dir.mkdir(parents=True, exist_ok=True)


def fingerprint_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_token(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:20]


def load_processed_state(state_file: Path) -> dict[str, dict]:
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_processed_state(state_file: Path, state: dict[str, dict]) -> None:
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
