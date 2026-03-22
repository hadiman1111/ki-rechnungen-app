from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class RunLogger:
    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.logs_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def log_file_summary(self, payload: dict[str, object]) -> None:
        self.log("FILE " + json.dumps(payload, ensure_ascii=False, sort_keys=True))
