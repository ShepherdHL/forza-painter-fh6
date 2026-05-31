"""UI layout ratio clamping keeps primary actions visible."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ui_layout import (
    DEFAULT_PANE_RATIOS,
    MIN_PANE_RATIOS,
    clamp_pane_ratio,
    enforce_pane_sash_bounds,
    load_ui_layout,
)


def test_clamp_pane_ratio_enforces_workspace_minimum():
    assert clamp_pane_ratio("main_vertical", 0.10) == MIN_PANE_RATIOS["main_vertical"]
    assert clamp_pane_ratio("main_vertical", 0.80) == 0.80


def test_clamp_pane_ratio_enforces_control_column_minimum():
    assert clamp_pane_ratio("generate_horizontal", 0.10) == MIN_PANE_RATIOS["generate_horizontal"]


def test_load_ui_layout_clamps_persisted_extremes(tmp_path):
    settings_dir = tmp_path / "runtime" / "settings"
    settings_dir.mkdir(parents=True)
    (settings_dir / "ui_layout.json").write_text(
        '{"main_vertical": 0.05, "generate_horizontal": 0.02}',
        encoding="utf-8",
    )
    loaded = load_ui_layout(tmp_path)
    assert loaded["main_vertical"] == MIN_PANE_RATIOS["main_vertical"]
    assert loaded["generate_horizontal"] == MIN_PANE_RATIOS["generate_horizontal"]


def test_export_game_horizontal_has_default():
    assert "export_game_horizontal" in DEFAULT_PANE_RATIOS


class _MockPaned:
    def __init__(self, *, total: int, sash_pos: int, vertical: bool = True) -> None:
        self._total = total
        self._sash_pos = sash_pos
        self._vertical = vertical

    def winfo_exists(self) -> bool:
        return True

    def update_idletasks(self) -> None:
        return None

    def winfo_height(self) -> int:
        return self._total if self._vertical else 0

    def winfo_width(self) -> int:
        return 0 if self._vertical else self._total

    def sashpos(self, _index: int, pos: int | None = None) -> int:
        if pos is None:
            return self._sash_pos
        self._sash_pos = pos
        return self._sash_pos


def test_enforce_pane_sash_bounds_snaps_below_minimum():
    paned = _MockPaned(total=1000, sash_pos=100)
    assert enforce_pane_sash_bounds(paned, "vertical", "main_vertical") is True
    assert paned.sashpos(0) == int(1000 * MIN_PANE_RATIOS["main_vertical"])


def test_enforce_pane_sash_bounds_leaves_valid_ratio():
    paned = _MockPaned(total=1000, sash_pos=700)
    assert enforce_pane_sash_bounds(paned, "vertical", "main_vertical") is False
    assert paned.sashpos(0) == 700
