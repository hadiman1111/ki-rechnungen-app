"""Runtime path resolution for repository development and Flet standalone builds."""

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

APP_SUPPORT_DIR_NAME = "KI-Rechnungen"
INVOICE_CONFIG_FILENAME = "invoice_config.json"
OFFICE_RULES_FILENAME = "office_rules.json"
PROFILE_LOCAL_FILENAME = "profile_config.local.json"
PROFILE_STATE_FILENAME = "profile_state.json"
PROFILES_SUBDIR = "profiles"
BUNDLE_RESOURCES_DIRNAME = "ki-rechnungen"


def is_standalone_bundle() -> bool:
    return os.getenv("FLET_PLATFORM") is not None


def macos_app_bundle_root() -> Path | None:
    if sys.platform != "darwin":
        return None

    candidate = Path(sys.executable).resolve()
    for path in (candidate, *candidate.parents):
        if path.suffix == ".app":
            return path
        if path.name == "MacOS" and path.parent.name == "Contents":
            return path.parent.parent
    return None


def bundled_resources_root() -> Path | None:
    bundle = macos_app_bundle_root()
    if bundle is None:
        return None

    root = bundle / "Contents" / "Resources" / BUNDLE_RESOURCES_DIRNAME
    return root if root.is_dir() else None


def bundled_defaults_dir() -> Path | None:
    root = bundled_resources_root()
    if root is None:
        return None

    defaults = root / "defaults"
    return defaults if defaults.is_dir() else None


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def user_support_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / APP_SUPPORT_DIR_NAME


def run_support_root() -> Path:
    """Root for technical per-run artifacts under Application Support."""
    return user_support_dir() / "runs"


def create_run_support_dir(*, run_id: str | None = None) -> tuple[Path, str]:
    """Create an isolated run directory under Application Support/runs/.

    Returns:
        (run_dir, run_id) where run_id is the timestamp folder name.
    """
    root = run_support_root()
    root.mkdir(parents=True, exist_ok=True)

    resolved_run_id = run_id or _timestamp()
    candidate = root / resolved_run_id
    if not candidate.exists():
        candidate.mkdir()
        return candidate, resolved_run_id

    index = 2
    while True:
        suffixed_id = f"{resolved_run_id}_{index}"
        suffixed = root / suffixed_id
        if not suffixed.exists():
            suffixed.mkdir()
            return suffixed, suffixed_id
        index += 1


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_existing(path: Path) -> None:
    if not path.exists():
        return
    backup = path.with_name(f"{path.name}.backup-{_timestamp()}")
    shutil.copy2(path, backup)


def _ensure_directories_for_config(config_path: Path) -> None:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    base_dir = config_path.parent.resolve()
    for key in ("eingangsordner", "ausgangsordner", "runtime_ordner", "log_ordner"):
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        expanded = os.path.expandvars(os.path.expanduser(value))
        path = Path(expanded)
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        path.mkdir(parents=True, exist_ok=True)


def _seed_user_file(target: Path, source: Path) -> None:
    if target.exists() or not source.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def ensure_user_config_layout() -> Path:
    """Ensure user-writable config exists under Application Support."""
    if not is_standalone_bundle():
        return project_root()

    support = user_support_dir()
    support.mkdir(parents=True, exist_ok=True)

    defaults = bundled_defaults_dir()
    if defaults is None:
        extracted = Path.cwd()
        fallback_config = extracted / INVOICE_CONFIG_FILENAME
        fallback_rules = extracted / OFFICE_RULES_FILENAME
        if fallback_config.is_file() and fallback_rules.is_file():
            defaults = extracted

    config_path = support / INVOICE_CONFIG_FILENAME
    rules_path = support / OFFICE_RULES_FILENAME

    if defaults is not None:
        _seed_user_file(rules_path, defaults / OFFICE_RULES_FILENAME)
        _seed_user_file(config_path, defaults / INVOICE_CONFIG_FILENAME)

    if config_path.exists():
        _ensure_directories_for_config(config_path)

    for subdir in ("inbox", "outbox", "runtime", "logs"):
        (support / subdir).mkdir(parents=True, exist_ok=True)

    return support


def resolve_invoice_config_path() -> Path:
    if is_standalone_bundle():
        ensure_user_config_layout()
        return user_support_dir() / INVOICE_CONFIG_FILENAME
    return (project_root() / INVOICE_CONFIG_FILENAME).resolve()


def _migrate_legacy_profile_storage(support: Path) -> None:
    """Import legacy project-local profiles into Application Support once.

    Never overwrites existing Application Support files. Legacy project-local
    files are left in place as a read-only migration source.
    """
    legacy_root = project_root()
    if legacy_root.resolve() == support.resolve():
        return

    _seed_user_file(support / PROFILE_LOCAL_FILENAME, legacy_root / PROFILE_LOCAL_FILENAME)

    legacy_profiles = legacy_root / PROFILES_SUBDIR
    support_profiles = support / PROFILES_SUBDIR
    support_profiles.mkdir(parents=True, exist_ok=True)
    if legacy_profiles.is_dir():
        for path in sorted(legacy_profiles.glob("*.json")):
            _seed_user_file(support_profiles / path.name, path)

    _seed_user_file(support / PROFILE_STATE_FILENAME, legacy_root / PROFILE_STATE_FILENAME)


def ensure_profile_storage_layout() -> Path:
    """Ensure mutable user profiles live under Application Support.

    Development and standalone execution both use the same canonical location.
    Legacy project-local profiles are imported on first run without overwriting
    newer Application Support data.
    """
    support = user_support_dir()
    support.mkdir(parents=True, exist_ok=True)
    (support / PROFILES_SUBDIR).mkdir(parents=True, exist_ok=True)
    _migrate_legacy_profile_storage(support)
    return support


def profile_storage_dir() -> Path:
    """Directory containing mutable user profiles."""
    if is_standalone_bundle():
        ensure_user_config_layout()
    return ensure_profile_storage_layout()


def sanitize_profile_display_name(name: str) -> str:
    """Public helper for user-visible profile labels."""
    return _sanitize_profile_display_name(name)


def list_profile_entries() -> list[tuple[str, Path, str]]:
    """Return available profiles as (id, path, display_name)."""
    root = profile_storage_dir()
    entries: list[tuple[str, Path, str]] = []
    seen: set[str] = set()

    default = root / PROFILE_LOCAL_FILENAME
    if default.is_file():
        label = _profile_display_name(default, fallback="Lokales Profil")
        entries.append(("local", default, label))
        seen.add("local")

    profiles_dir = root / PROFILES_SUBDIR
    if profiles_dir.is_dir():
        for path in sorted(profiles_dir.glob("*.json")):
            profile_id = path.stem
            if profile_id in seen:
                continue
            label = _profile_display_name(path, fallback=profile_id)
            entries.append((profile_id, path, label))
            seen.add(profile_id)

    return entries


def _sanitize_profile_display_name(name: str) -> str:
    """Remove technical migration suffixes from user-visible profile labels."""
    cleaned = name.strip()
    for suffix in (
        " – Lokale Arbeitskopie",
        " - Lokale Arbeitskopie",
        " (Lokale Arbeitskopie)",
        " – lokale Arbeitskopie",
    ):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
    return cleaned or "Profil"


def _profile_display_name(path: Path, *, fallback: str) -> str:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _sanitize_profile_display_name(fallback)
    if isinstance(data, dict):
        name = data.get("profile_name")
        if isinstance(name, str) and name.strip():
            return _sanitize_profile_display_name(name)
    return _sanitize_profile_display_name(fallback)


def resolve_active_profile_id() -> str:
    state_path = profile_storage_dir() / PROFILE_STATE_FILENAME
    if state_path.is_file():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        active = data.get("active_profile_id") if isinstance(data, dict) else None
        if isinstance(active, str) and active.strip():
            return active.strip()
    return "local"


def set_active_profile_id(profile_id: str) -> Path:
    """Persist the active profile selection and return the state file path."""
    profile_id = profile_id.strip()
    if not profile_id:
        raise ValueError("profile_id darf nicht leer sein.")

    known = {entry_id for entry_id, _, _ in list_profile_entries()}
    if profile_id not in known:
        raise ValueError(f"Unbekanntes Profil: {profile_id}")

    state_path = profile_storage_dir() / PROFILE_STATE_FILENAME
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"active_profile_id": profile_id}
    state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return state_path


def resolve_profile_path() -> Path | None:
    active_id = resolve_active_profile_id()
    entries = list_profile_entries()
    for entry_id, path, _ in entries:
        if entry_id == active_id:
            return path
    if entries:
        return entries[0][1]
    return None


def get_tesseract_paths() -> tuple[Path, Path] | None:
    root = bundled_resources_root()
    if root is None:
        return None

    tess_root = root / "tesseract"
    binary = tess_root / "bin" / "tesseract"
    tessdata = tess_root / "share" / "tessdata"
    if binary.is_file() and tessdata.is_dir():
        return binary, tessdata
    return None


def configure_tesseract_runtime() -> Path | None:
    """Configure pytesseract for a bundled Tesseract binary when available."""
    bundled = get_tesseract_paths()
    if bundled is None:
        return None

    binary, tessdata = bundled
    os.environ["TESSDATA_PREFIX"] = str(tessdata.resolve()) + os.sep

    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = str(binary.resolve())
    return binary.resolve()


def save_user_json(path: Path, data: dict) -> None:
    """Persist user-editable JSON without overwriting an existing file silently."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        _backup_existing(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
