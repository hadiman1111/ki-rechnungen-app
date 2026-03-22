from __future__ import annotations

import os
from pathlib import Path


class RuntimeEnvironmentError(RuntimeError):
    pass


def load_openai_api_key(env_file: Path) -> str:
    if not env_file.exists():
        raise RuntimeEnvironmentError(
            f"API-Key-Datei fehlt: {env_file}. OpenAI Vision kann nicht gestartet werden."
        )

    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "OPENAI_API_KEY":
            api_key = value.strip().strip('"').strip("'")
            if not api_key:
                break
            os.environ["OPENAI_API_KEY"] = api_key
            return api_key

    raise RuntimeEnvironmentError(
        f"OPENAI_API_KEY wurde in der Datei nicht gefunden: {env_file}"
    )
