"""Tests that Forza font JSON preview uses the correct coordinate decode."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def test_forza_font_has_dedicated_preview_model() -> None:
    from preview.fh6_raster_preview import (
        FORZA_FONT_COORDINATE_MODEL,
        SCALED_TRACE_COORDINATE_MODELS,
    )
    from text_forza_fonts import FORZA_COORDINATE_MODEL

    assert FORZA_COORDINATE_MODEL == FORZA_FONT_COORDINATE_MODEL
    assert FORZA_COORDINATE_MODEL not in SCALED_TRACE_COORDINATE_MODELS


def test_forza_font_shape_scale_decodes_to_layout_size() -> None:
    try:
        from text_forza_fonts import build_typecode_from_forza_font
    except FileNotFoundError:
        return
    from preview.fh6_raster_preview import _forza_font_shape_pixels

    payload = build_typecode_from_forza_font("AB", font_index=1, font_size=120)
    shape = payload["shapes"][0]
    item = {
        "x": shape["data"][0],
        "y": shape["data"][1],
        "sx": shape["data"][2],
        "sy": shape["data"][3],
        "rotation": shape["data"][4],
        "type_code": shape["type"],
    }
    _px, _py, width, height, _rot = _forza_font_shape_pixels(item)
    assert 20.0 <= width <= 200.0
    assert 20.0 <= height <= 200.0


def test_forza_walker_bounds_span_multiple_glyphs() -> None:
    try:
        from text_forza_fonts import build_typecode_from_forza_font
    except FileNotFoundError:
        return
    from preview.fh6_raster_preview import _typecode_bounds
    from text_forza_fonts import FORZA_COORDINATE_MODEL
    from fh6_typecode_json import load_typecode_shapes

    payload = build_typecode_from_forza_font("AB", font_index=1, font_size=120)
    import json
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump(payload, handle)
        path = Path(handle.name)
    try:
        shapes, _skipped = load_typecode_shapes(path)
        min_x, _min_y, max_x, _max_y = _typecode_bounds(shapes, coordinate_model=FORZA_COORDINATE_MODEL)
        assert max_x - min_x > 40.0
    finally:
        path.unlink(missing_ok=True)
