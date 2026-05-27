"""Detect and summarize Kloudy-style FH6 type-code geometry JSON."""

from __future__ import annotations

import json
from pathlib import Path

from geometry_json import RECTANGLE, ROTATED_ELLIPSE

TYPECODE_BASE = 0x100000
GENERATED_SHAPE_TYPES = {int(RECTANGLE), int(ROTATED_ELLIPSE)}


def is_typecode_geometry_json(path) -> bool:
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    fmt = str(payload.get("format", "")).lower()
    if "typecode" in fmt:
        return True
    shapes = payload.get("shapes")
    if not isinstance(shapes, list):
        return False
    for shape in shapes:
        if not isinstance(shape, dict):
            continue
        try:
            shape_type = int(shape.get("type", 0))
        except (TypeError, ValueError):
            continue
        if shape_type >= TYPECODE_BASE:
            return True
        if shape_type not in GENERATED_SHAPE_TYPES and shape_type not in (0,):
            return True
    return False


def typecode_shape_count(path, *, allow_unknown_low_byte: bool = True) -> int:
    from fh6_import_typecode_json import load_shapes

    shapes, _skipped = load_shapes(path, allow_unknown_low_byte=allow_unknown_low_byte)
    return len(shapes)


def typecode_shape_summary(path, *, allow_unknown_low_byte: bool = False) -> dict[str, int]:
    from fh6_import_typecode_json import load_shapes

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_shapes = payload.get("shapes")
    total = len(raw_shapes) if isinstance(raw_shapes, list) else 0
    shapes, skipped = load_shapes(path, allow_unknown_low_byte=allow_unknown_low_byte)
    supported = len(shapes)
    unsupported = len(skipped)
    return {
        "total": int(total),
        "supported": int(supported),
        "unsupported": int(unsupported),
    }


def load_typecode_shapes(path, *, allow_unknown_low_byte: bool = True):
    from fh6_import_typecode_json import load_shapes

    return load_shapes(path, allow_unknown_low_byte=allow_unknown_low_byte)
