"""Tests for FH6 text vinyl type-code JSON generation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from text_geometry import (
    SHAPE_MODE_CIRCLES,
    SHAPE_MODE_RECTANGLES,
    SHAPE_MODE_TRIANGLES,
    TEXT_TYPECODE_FORMAT,
    build_typecode_payload_from_mask,
    estimate_layer_count,
    is_text_typecode_payload,
)


def test_build_typecode_from_mask_circles() -> None:
    from PIL import Image

    mask = Image.new("L", (6, 6), 0)
    mask.putpixel((2, 2), 255)
    mask.putpixel((3, 2), 255)
    payload = build_typecode_payload_from_mask(
        mask,
        (200, 100, 50, 255),
        cell_size=1,
        shape_mode=SHAPE_MODE_CIRCLES,
    )
    assert payload["format"] == TEXT_TYPECODE_FORMAT
    assert len(payload["shapes"]) == 1
    assert payload["shapes"][0]["type"] == 1048687


def test_build_typecode_from_mask_rectangles_use_square() -> None:
    from PIL import Image

    mask = Image.new("L", (4, 4), 0)
    mask.putpixel((1, 1), 255)
    payload = build_typecode_payload_from_mask(
        mask,
        (255, 255, 255, 255),
        cell_size=1,
        shape_mode=SHAPE_MODE_RECTANGLES,
    )
    assert payload["shapes"][0]["type"] == 1048677


def test_build_typecode_from_mask_triangles() -> None:
    from PIL import Image

    mask = Image.new("L", (5, 3), 0)
    for x in range(5):
        mask.putpixel((x, 1), 255)
    payload = build_typecode_payload_from_mask(
        mask,
        (255, 255, 255, 255),
        cell_size=1,
        shape_mode=SHAPE_MODE_TRIANGLES,
    )
    assert payload["shapes"][0]["type"] == 1048697
    assert payload["shapes"][0]["data"][4] == 0.0


def test_estimate_layer_count_typecode_payload() -> None:
    payload = {"format": TEXT_TYPECODE_FORMAT, "shapes": [{"type": 1048677}, {"type": 1048687}]}
    assert is_text_typecode_payload(payload)
    assert estimate_layer_count(payload) == 2
