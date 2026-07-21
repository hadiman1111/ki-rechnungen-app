from __future__ import annotations

from pathlib import Path


def test_clean_app_artifacts_excludes_embedded_python_runtime() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_macos_app.sh"
    content = script.read_text(encoding="utf-8")

    assert "BUILD_VENV_PYTHON" in content
    assert ".venv-flet085" in content
    assert "assert_build_toolchain()" in content
    assert "EXPECTED_FLET_VERSION=\"0.85.3\"" in content
    assert "clean_app_artifacts()" in content
    assert "! -path '*/serious_python_darwin.framework/*'" in content
    assert "verify_embedded_python_runtime()" in content
    assert "stdlib/encodings" in content
