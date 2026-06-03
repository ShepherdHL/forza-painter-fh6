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
        from preview.geometry_preview_cache import read_json_cached

        payload = read_json_cached(path)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
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


def _count_shape_types(raw_shapes: list) -> tuple[int, int, int]:
    from fh6_shape_catalog import is_known_type_code

    known = 0
    unknown = 0
    for shape in raw_shapes:
        if not isinstance(shape, dict):
            continue
        try:
            shape_type = int(shape.get("type", 0))
        except (TypeError, ValueError):
            unknown += 1
            continue
        if is_known_type_code(shape_type):
            known += 1
        else:
            unknown += 1
    return known, unknown, len(raw_shapes)


def typecode_shape_count(path, *, allow_unknown_low_byte: bool = True) -> int:
    from fh6_import_typecode_json import load_shapes

    shapes, _skipped = load_shapes(path, allow_unknown_low_byte=allow_unknown_low_byte)
    return len(shapes)


def typecode_shape_summary(path, *, allow_unknown_low_byte: bool = False) -> dict[str, int]:
    from fh6_import_typecode_json import load_shapes

    from preview.geometry_preview_cache import read_json_cached

    payload = read_json_cached(path)
    raw_shapes = payload.get("shapes")
    if not isinstance(raw_shapes, list):
        raw_shapes = []
    known_in_file, unknown_in_file, total = _count_shape_types(raw_shapes)
    shapes, skipped = load_shapes(path, allow_unknown_low_byte=allow_unknown_low_byte)
    importable = len(shapes)
    skipped_count = len(skipped)
    return {
        "total": int(total),
        "known": int(known_in_file),
        "unknown": int(unknown_in_file),
        "importable": int(importable),
        "skipped": int(skipped_count),
        # Back-compat for older UI format strings.
        "supported": int(importable),
        "unsupported": int(skipped_count),
    }


def load_typecode_shapes(path, *, allow_unknown_low_byte: bool = True):
    from fh6_import_typecode_json import load_shapes

    return load_shapes(path, allow_unknown_low_byte=allow_unknown_low_byte)
