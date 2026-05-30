"""Tests for pixel art geometry conversion."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pixel_art_geometry import (
    ColorGrid,
    FH6_SQUARE_TYPECODE,
    MergeMode,
    analyze_pixel_art,
    build_typecode_json_from_grid,
    estimate_layer_count,
    grid_from_svg,
    merge_rectangles,
    parse_hex_color,
    render_color_grid_preview,
)


def test_parse_hex_color_accepts_shorthand() -> None:
    assert parse_hex_color("#abc") == (170, 187, 204, 255)


def test_horizontal_merge_combines_row_pixels() -> None:
    grid = ColorGrid.from_flat(
        4,
        2,
        [
            (255, 0, 0, 255),
            (255, 0, 0, 255),
            None,
            (0, 255, 0, 255),
            (255, 0, 0, 255),
            None,
            None,
            None,
        ],
    )
    rects = merge_rectangles(grid, MergeMode.HORIZONTAL)
    assert len(rects) == 3
    assert estimate_layer_count(grid, MergeMode.HORIZONTAL) == 3


def test_grid_2d_merge_is_not_worse_than_both_axes() -> None:
    cells = []
    color_a = (10, 20, 30, 255)
    color_b = (40, 50, 60, 255)
    for y in range(4):
        for x in range(4):
            if x < 2:
                cells.append(color_a)
            else:
                cells.append(color_b if y >= 2 else None)
    grid = ColorGrid.from_flat(4, 4, cells)
    horizontal = len(merge_rectangles(grid, MergeMode.HORIZONTAL))
    vertical = len(merge_rectangles(grid, MergeMode.VERTICAL))
    grid2d = len(merge_rectangles(grid, MergeMode.GRID_2D))
    assert grid2d <= min(horizontal, vertical)


def test_build_typecode_json_uses_square_typecode() -> None:
    grid = ColorGrid.from_flat(2, 1, [(255, 128, 64, 255), (255, 128, 64, 255)])
    payload = build_typecode_json_from_grid(grid, MergeMode.HORIZONTAL)
    assert payload["format"] == "fh6_pixel_art_typecode_v1"
    assert len(payload["shapes"]) == 1
    shape = payload["shapes"][0]
    assert shape["type"] == FH6_SQUARE_TYPECODE
    assert shape["color"] == [255, 128, 64, 255]
    assert len(shape["data"]) >= 5


def test_grid_from_svg_reads_rect_elements(tmp_path: Path) -> None:
    svg = tmp_path / "sample.svg"
    svg.write_text(
        "\n".join(
            [
                '<svg xmlns="http://www.w3.org/2000/svg" width="2" height="2">',
                '<rect x="0" y="0" width="1" height="1" fill="#ff0000" />',
                '<rect x="1" y="1" width="1" height="1" fill="#00ff00" />',
                "</svg>",
            ]
        ),
        encoding="utf-8",
    )
    grid = grid_from_svg(svg)
    assert grid.width == 2 and grid.height == 2
    assert grid.get(0, 0) == (255, 0, 0, 255)
    assert grid.get(1, 1) == (0, 255, 0, 255)
    payload = build_typecode_json_from_grid(grid, MergeMode.AUTO)
    assert len(payload["shapes"]) == 2
    json.dumps(payload)


def test_analyze_pixel_art_from_grid() -> None:
    grid = ColorGrid.from_flat(
        3,
        2,
        [
            (255, 0, 0, 255),
            (255, 0, 0, 255),
            None,
            (0, 255, 0, 255),
            (0, 255, 0, 255),
            (0, 255, 0, 255),
        ],
    )
    stats = analyze_pixel_art(grid=grid, merge_mode=MergeMode.HORIZONTAL)
    assert stats["filled_pixels"] == 5
    assert stats["merged_layers"] == 2
    assert len(stats["color_counts"]) == 2
    assert stats["canvas_size"] == (3, 2)


def test_analyze_pixel_art_from_payload() -> None:
    grid = ColorGrid.from_flat(2, 1, [(10, 20, 30, 255), (10, 20, 30, 255)])
    payload = build_typecode_json_from_grid(grid, MergeMode.HORIZONTAL)
    stats = analyze_pixel_art(payload=payload)
    assert stats["filled_pixels"] == 2
    assert stats["merged_layers"] == 1
    assert (10, 20, 30) in stats["color_counts"]


def test_render_color_grid_preview_returns_png_bytes() -> None:
    grid = ColorGrid.from_flat(2, 2, [(255, 0, 0, 255), None, None, (0, 0, 255, 255)])
    data = render_color_grid_preview(grid, (32, 32))
    assert data is not None
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
