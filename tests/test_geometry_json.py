from __future__ import annotations

import json
import pytest
from pathlib import Path

from geometry_json import (
    ShapeType,
    RECTANGLE,
    ROTATED_ELLIPSE,
    normalize_geometry_payload,
    drawable_shape_count,
)
from utils import clamp_byte


class TestShapeTypeEnum:
    def test_members(self):
        assert ShapeType.RECTANGLE == 1
        assert ShapeType.ROTATED_ELLIPSE == 16

    def test_backward_compat_aliases(self):
        assert RECTANGLE is ShapeType.RECTANGLE
        assert ROTATED_ELLIPSE is ShapeType.ROTATED_ELLIPSE


class TestNormalizeGeometryPayload:
    def test_rectangle_only(self):
        payload = [
            {"type": 1, "data": [0, 0, 100, 200], "color": [255, 0, 0, 255]},
        ]
        result = normalize_geometry_payload(payload)
        assert result["shapes"][0]["type"] == ShapeType.RECTANGLE

    def test_unsupported_shape_is_filtered(self):
        payload = [
            {"type": 99, "data": [0, 0, 10, 10], "color": [0, 0, 0, 255]},
        ]
        with pytest.raises(ValueError, match="supported shapes"):
            normalize_geometry_payload(payload)


class TestDrawableShapeCount:
    def test_counts_drawable_shapes(self, tmp_path: Path):
        payload = [
            {"type": 1, "data": [0, 0, 100, 200], "color": [0, 0, 0, 0]},
            {"type": 16, "data": [50, 50, 10, 10, 0], "color": [255, 0, 0, 255]},
            {"type": 1, "data": [70, 70, 10, 10], "color": [0, 0, 255, 255]},
        ]
        path = tmp_path / "test.json"
        path.write_text(json.dumps(payload))
        assert drawable_shape_count(path) == 2


class TestClampByte:
    def test_clamps_overflow(self):
        assert clamp_byte(300) == 255
