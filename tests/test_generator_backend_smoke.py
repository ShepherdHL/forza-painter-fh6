"""Smoke tests for generator_backend imports used at app startup."""

from __future__ import annotations

import pytest

cv2 = pytest.importorskip("cv2")

from generator_backend import build_generator_command, load_settings
from generator_launch_options import GeneratorLaunchOptions
from preset_preview import preset_badge_prefix, preset_label_with_badge


def test_preset_preview_helpers_importable():
    assert callable(preset_badge_prefix)
    assert callable(preset_label_with_badge)


def test_load_settings_does_not_raise():
    profiles = load_settings()
    assert profiles
    assert all(hasattr(profile, "label") for profile in profiles)


def test_build_generator_command_with_backend_option(tmp_path, monkeypatch):
    monkeypatch.setattr("generator_backend.generator_available", lambda: True)
    monkeypatch.setattr("generator_backend.GENERATOR_EXE", tmp_path / "gen.exe")
    (tmp_path / "gen.exe").write_bytes(b"x")
    setting = {"path": tmp_path / "preset.ini"}
    setting["path"].write_text("[settings]\n", encoding="utf-8")
    from generator_capabilities import GeneratorCapabilities

    options = GeneratorLaunchOptions(
        backend="opencl",
        capabilities=GeneratorCapabilities(supports_backend=True),
    )
    cmd = build_generator_command(tmp_path / "img.png", setting, launch_options=options)
    assert "-backend" in cmd
    assert "opencl" in cmd
