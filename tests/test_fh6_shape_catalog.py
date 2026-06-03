"""Tests for FH6 shape catalog CSV loading."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fh6_shape_catalog import (
    TYPECODE_BASE,
    catalog_csv_path,
    get_primitive_type_code,
    get_square_type_code,
    load_catalog,
    preview_style_for_type_code,
)


def test_catalog_csv_exists() -> None:
    path = catalog_csv_path()
    assert path.is_file()


def test_catalog_loads_expected_volume() -> None:
    catalog = load_catalog()
    assert catalog.row_count >= 1300
    assert len(catalog.known_type_codes) >= 1300


def test_primitive_codes_match_csv() -> None:
    catalog = load_catalog()
    square = catalog.get(1048677)
    circle = catalog.get(1048687)
    triangle = catalog.get(1048697)
    assert square is not None and square.shape_name == "Square"
    assert circle is not None and circle.shape_name == "Circle"
    assert triangle is not None and triangle.shape_name == "Triangle"


def test_encoding_rule_holds_for_samples() -> None:
    catalog = load_catalog()
    for code in (1048677, 1050677, 1050477):
        entry = catalog.get(code)
        assert entry is not None
        assert entry.type_code == TYPECODE_BASE + entry.shape_word


def test_square_type_code_helper() -> None:
    assert get_square_type_code() == 1048677


def test_primitive_type_code_lookup() -> None:
    assert get_primitive_type_code("Circle") == 1048687
    assert get_primitive_type_code("Triangle") == 1048697
    assert get_primitive_type_code("Ellipse") == 1048715


def test_preview_styles_for_primitives() -> None:
    assert preview_style_for_type_code(1048677) == "square"
    assert preview_style_for_type_code(1048687) == "circle"
    assert preview_style_for_type_code(1048697) == "triangle"
    assert preview_style_for_type_code(1048715) == "ellipse"
    assert preview_style_for_type_code(1048709) == "ring"


def test_duplicate_codes_reported() -> None:
    catalog = load_catalog()
    assert 1051803 in catalog.duplicate_type_codes
