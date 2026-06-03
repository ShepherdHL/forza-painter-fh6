"""Tests for geometry JSON read cache and preview PNG cache."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from preview.geometry_preview_cache import (
    cached_drawable_shape_count,
    clear_geometry_preview_caches,
    drawable_shape_count_cached,
    get_cached_geometry_preview_png,
    read_json_cached,
    render_geometry_preview_png,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_geometry_preview_caches()
    yield
    clear_geometry_preview_caches()


def test_render_preview_png_cache_hit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "tiny.json"
    path.write_text(
        json.dumps(
            {
                "format": "forza_painter_text_trace_v1",
                "coordinate_model": "forza_painter_text_trace_v1",
                "shapes": [
                    {
                        "type": 0x100001,
                        "data": [128, 128, 25.6, 25.6, 0],
                        "color": [200, 40, 40, 255],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    calls = {"n": 0}

    def fake_build(p, max_size=None):
        calls["n"] += 1
        return b"\x89PNG\r\n\x1a\nfake"

    monkeypatch.setattr(
        "preview.geometry_render.build_geometry_preview_png",
        fake_build,
    )
    bounds = (120, 120)
    first = render_geometry_preview_png(path, bounds)
    second = render_geometry_preview_png(path, bounds)
    assert first == second == b"\x89PNG\r\n\x1a\nfake"
    assert calls["n"] == 1
    assert get_cached_geometry_preview_png(path, bounds) == first


def test_cache_invalidates_on_mtime_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "design.json"
    path.write_text(json.dumps({"shapes": []}), encoding="utf-8")
    calls = {"n": 0}

    def fake_build(p, max_size=None):
        calls["n"] += 1
        return f"v{calls['n']}".encode()

    monkeypatch.setattr(
        "preview.geometry_render.build_geometry_preview_png",
        fake_build,
    )
    first = render_geometry_preview_png(path, (80, 80))
    time.sleep(0.05)
    path.write_text(json.dumps({"shapes": [{"type": 1}]}), encoding="utf-8")
    second = render_geometry_preview_png(path, (80, 80))
    assert first != second
    assert calls["n"] == 2


def test_read_json_cached_reuses_payload(tmp_path: Path) -> None:
    path = tmp_path / "design.json"
    path.write_text(json.dumps({"format": "fh6_typecode_json_export_v1", "shapes": []}), encoding="utf-8")
    first = read_json_cached(path)
    second = read_json_cached(path)
    assert first is second


def test_drawable_shape_count_cache(tmp_path: Path) -> None:
    path = tmp_path / "trace.json"
    path.write_text(
        json.dumps(
            {
                "format": "forza_painter_text_trace_v1",
                "coordinate_model": "forza_painter_text_trace_v1",
                "shapes": [
                    {
                        "type": 0x100001,
                        "data": [128, 128, 12.8, 12.8, 0],
                        "color": [255, 0, 0, 255],
                    },
                    {
                        "type": 0x100001,
                        "data": [140, 128, 12.8, 12.8, 0],
                        "color": [0, 255, 0, 255],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    first = drawable_shape_count_cached(path)
    second = drawable_shape_count_cached(path)
    assert first == 2
    assert second == 2
    assert cached_drawable_shape_count(path) == 2
