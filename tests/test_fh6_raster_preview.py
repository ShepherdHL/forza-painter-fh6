"""Tests for FH6-accurate legacy JSON raster preview."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from geometry_json import ShapeType, normalize_geometry_payload
from preview.fh6_raster_preview import (
    _scaled_trace_shape_pixels,
    compensated_ellipse_size,
    flatten_rgba_on_checkerboard,
    render_legacy_geometry_rgba,
    render_typecode_geometry_preview,
)


class TestCompensatedEllipseSize:
    def test_small_ellipse_unchanged(self):
        w, h = compensated_ellipse_size(40.0, 30.0)
        assert w == pytest.approx(40.0)
        assert h == pytest.approx(30.0)

    def test_large_high_aspect_shrinks(self):
        w, h = compensated_ellipse_size(320.0, 40.0)
        assert w < 320.0
        assert h < 40.0


class TestAlphaCompositing:
    def test_semi_transparent_layer_blends(self):
        payload = [
            {"type": 1, "data": [0, 0, 20, 20], "color": [0, 0, 0, 0]},
            {"type": 1, "data": [10, 10, 20, 20], "color": [200, 0, 0, 255]},
            {"type": 1, "data": [10, 10, 10, 10], "color": [0, 0, 200, 128]},
        ]
        shapes = normalize_geometry_payload(payload)["shapes"]
        rendered = render_legacy_geometry_rgba(shapes, 20, 20, 1.0)
        assert rendered is not None
        rgb, alpha = rendered
        flat = flatten_rgba_on_checkerboard(rgb, alpha, tile=4)
        center = tuple(int(v) for v in flat[10, 10])
        assert center[0] > 0
        assert center[2] > 0
        assert center[0] < 200 or center[2] < 200


class TestLegacyShapeTypes:
    def test_rotated_rectangle_normalized(self):
        payload = [
            {"type": 1, "data": [0, 0, 40, 40], "color": [0, 0, 0, 0]},
            {"type": 2, "data": [20, 20, 30, 10, 45], "color": [0, 255, 0, 255]},
        ]
        shapes = normalize_geometry_payload(payload)["shapes"]
        assert shapes[1]["type"] == ShapeType.ROTATED_RECTANGLE
        assert len(shapes[1]["data"]) == 5

    def test_axis_ellipse_is_type_8(self):
        payload = [
            {"type": 1, "data": [0, 0, 20, 20], "color": [0, 0, 0, 0]},
            {"type": 8, "data": [10, 10, 12.5, 8.0], "color": [255, 0, 0, 255]},
        ]
        shapes = normalize_geometry_payload(payload)["shapes"]
        assert shapes[1]["type"] == ShapeType.ELLIPSE
        rendered = render_legacy_geometry_rgba(shapes, 20, 20, 1.0)
        assert rendered is not None


class TestScaledTraceTypecodePreview:
    def test_text_trace_shape_decodes_to_pixel_units(self):
        item = {
            "x": 478.08,
            "y": 39.04,
            "sx": 0.01,
            "sy": 0.13,
            "rotation": 0.0,
        }
        px, py, pw, ph, rot = _scaled_trace_shape_pixels(item)
        assert pw == pytest.approx(1.0)
        assert ph == pytest.approx(13.0)
        assert px == pytest.approx(373.5)
        assert py == pytest.approx(30.5)

    def test_text_trace_preview_renders_visible_pixels(self, tmp_path: Path):
        payload = {
            "format": "fh6_text_typecode_v1",
            "coordinate_model": "forza_painter_text_trace_v1",
            "shapes": [
                {
                    "type": 1048677,
                    "data": [80.0, 40.0, 0.13, 0.13, 0.0, 0.0, 0],
                    "color": [0, 255, 0, 255],
                },
                {
                    "type": 1048677,
                    "data": [90.0, 40.0, 0.13, 0.13, 0.0, 0.0, 0],
                    "color": [0, 255, 0, 255],
                },
            ],
        }
        path = tmp_path / "text.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        image = render_typecode_geometry_preview(path, max_size=(200, 200), skipped_badge=False)
        assert image is not None
        pixels = list(image.getdata())
        greenish = sum(1 for r, g, b in pixels if g > 150 and r < 100)
        assert greenish > 20


class TestFloatGeometryPreserved:
    def test_ellipse_fractional_size_kept(self):
        payload = [
            {"type": 1, "data": [0, 0, 10, 10], "color": [0, 0, 0, 0]},
            {"type": 16, "data": [5, 5, 10.4, 8.2, 0], "color": [255, 0, 0, 255]},
        ]
        shapes = normalize_geometry_payload(payload)["shapes"]
        assert shapes[1]["data"][2] == pytest.approx(10.4)
        assert shapes[1]["data"][3] == pytest.approx(8.2)
