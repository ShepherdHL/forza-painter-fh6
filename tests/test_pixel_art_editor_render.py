"""Tests for incremental pixel-art editor rendering helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pixel_art_geometry import ColorGrid
from ui.pixel_art_workspace import PixelArtWorkspace


def _bare_workspace() -> PixelArtWorkspace:
    workspace = PixelArtWorkspace.__new__(PixelArtWorkspace)
    workspace.grid = ColorGrid.empty(4, 4)
    workspace._editor_render_key = None
    workspace._editor_pixel_items = {}
    workspace.active_tool = "pencil"
    workspace.cell_display_size = SimpleNamespace(get=lambda: "12")
    workspace._color = lambda name: "#101010" if name == "COLOR_PANEL_ALT" else "#202020"
    canvas = MagicMock()
    canvas.create_rectangle = MagicMock(
        side_effect=lambda *args, **kwargs: len(canvas.create_rectangle.call_args_list) + 1
    )
    workspace.editor_canvas = canvas
    return workspace


def test_render_editor_incremental_updates_single_cell() -> None:
    workspace = _bare_workspace()
    workspace._render_editor()
    initial_calls = workspace.editor_canvas.create_rectangle.call_count
    workspace.grid = workspace.grid.set(1, 1, (255, 0, 0, 255))
    workspace._render_editor(changed_cells=[(1, 1)])
    assert workspace.editor_canvas.create_rectangle.call_count == initial_calls + 1


def test_flood_fill_returns_changed_cells() -> None:
    workspace = _bare_workspace()
    workspace.active_tool = "fill"
    for x in range(2):
        workspace.grid = workspace.grid.set(x, 0, (10, 10, 10, 255))
    workspace._color_editor = SimpleNamespace(get_rgba=lambda: (20, 20, 20, 255))
    changed = workspace._apply_tool(0, 0)
    assert len(changed) == 2
