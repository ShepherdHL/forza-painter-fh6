"""Tests for FH6 type-code import shape filtering."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fh6_import_typecode_json import load_shapes
from fh6_typecode_json import typecode_shape_summary


def _write_shapes(path: Path, types: list[int]) -> None:
    payload = {
        "format": "fh6_test_typecode_v1",
        "shapes": [
            {
                "type": code,
                "data": [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0],
                "color": [255, 255, 255, 255],
            }
            for code in types
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_catalog_code_imports_without_experimental_flag() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "design.json"
        _write_shapes(path, [1048687, 1048697])  # Circle, Triangle
        shapes, skipped = load_shapes(path, allow_unknown_low_byte=False)
        assert len(shapes) == 2
        assert skipped == []


def test_unknown_code_skipped_in_standard_mode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "design.json"
        _write_shapes(path, [1048677, 0x100999])
        shapes, skipped = load_shapes(path, allow_unknown_low_byte=False)
        assert len(shapes) == 1
        assert len(skipped) == 1
        assert skipped[0]["type_code"] == 0x100999


def test_unknown_code_allowed_in_experimental_mode() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "design.json"
        _write_shapes(path, [1048677, 0x100999])
        shapes, skipped = load_shapes(path, allow_unknown_low_byte=True)
        assert len(shapes) == 2
        assert skipped == []


def test_typecode_shape_summary_counts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "design.json"
        _write_shapes(path, [1048677, 0x100999])
        summary = typecode_shape_summary(path, allow_unknown_low_byte=False)
        assert summary["total"] == 2
        assert summary["known"] == 1
        assert summary["unknown"] == 1
        assert summary["importable"] == 1
        assert summary["skipped"] == 1
