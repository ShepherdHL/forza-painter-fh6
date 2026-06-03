"""Tests for generated JSON listing cache."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.modules.setdefault("cv2", MagicMock())

from generator_backend import (
    generated_jsons,
    invalidate_generated_jsons_cache,
)


@pytest.fixture(autouse=True)
def _clear_json_cache():
    invalidate_generated_jsons_cache()
    yield
    invalidate_generated_jsons_cache()


def test_generated_jsons_cache_hit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    image = tmp_path / "photo.png"
    image.write_bytes(b"png")
    json_dir = tmp_path / "json"
    json_dir.mkdir()
    (json_dir / "photo.json").write_text("{}", encoding="utf-8")
    calls = {"n": 0}

    def fake_scan(image_path: Path) -> list[Path]:
        calls["n"] += 1
        return [json_dir / "photo.json"]

    monkeypatch.setattr("generator_backend._scan_generated_jsons", fake_scan)
    first = generated_jsons(image)
    second = generated_jsons(image)
    assert len(first) == 1
    assert first == second
    assert calls["n"] == 1


def test_generated_jsons_cache_expires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    image = tmp_path / "photo.png"
    image.write_bytes(b"png")
    calls = {"n": 0}

    def fake_scan(image_path: Path) -> list[Path]:
        calls["n"] += 1
        return []

    monkeypatch.setattr("generator_backend._scan_generated_jsons", fake_scan)
    monkeypatch.setattr("generator_backend.GENERATED_JSON_CACHE_TTL_SECONDS", 0.01)
    generated_jsons(image)
    time.sleep(0.02)
    generated_jsons(image)
    assert calls["n"] == 2


def test_invalidate_generated_jsons_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    image = tmp_path / "photo.png"
    image.write_bytes(b"png")
    calls = {"n": 0}

    def fake_scan(image_path: Path) -> list[Path]:
        calls["n"] += 1
        return []

    monkeypatch.setattr("generator_backend._scan_generated_jsons", fake_scan)
    generated_jsons(image)
    invalidate_generated_jsons_cache(image)
    generated_jsons(image)
    assert calls["n"] == 2
