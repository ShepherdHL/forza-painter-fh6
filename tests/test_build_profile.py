"""Tests for build_profile gates."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def profile_file(tmp_path: Path, monkeypatch):
    payload = {
        "variant_id": "test-variant",
        "label": "Test",
        "onefile": True,
        "disable_elevation": True,
        "disable_generator": True,
        "disable_networking": True,
        "disable_memory_scan": True,
    }
    path = tmp_path / "_build_profile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    import build_profile as bp

    monkeypatch.setattr(bp, "_profile_paths", lambda: [path])
    bp._PROFILE = None
    yield bp
    bp._PROFILE = None


def test_profile_flags(profile_file):
    bp = profile_file
    assert bp.elevation_disabled() is True
    assert bp.generator_disabled() is True
    assert bp.networking_disabled() is True
    assert bp.memory_scan_disabled() is True


def test_env_overrides_profile(profile_file, monkeypatch):
    bp = profile_file
    monkeypatch.setenv("FORZA_PAINTER_DISABLE_ELEVATION", "0")
    assert bp.elevation_disabled() is False


def test_updates_blocked_when_networking_disabled(profile_file, monkeypatch):
    import security_policy as sp

    monkeypatch.delenv("FORZA_PAINTER_CHECK_UPDATES", raising=False)
    assert not sp.updates_enabled()
