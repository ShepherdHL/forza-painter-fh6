"""Persist resizable UI pane ratios (ttk.PanedWindow sash positions)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

DEFAULT_PANE_RATIOS: Dict[str, float] = {
    "main_vertical": 0.74,
    "generate_horizontal": 0.58,
    "preview_horizontal": 0.58,
    "import_horizontal": 0.52,
    "import_photo_outer": 0.30,
    "import_photo_center": 0.72,
    "import_text_outer": 0.30,
    "import_text_center": 0.72,
    "text_horizontal": 0.58,
    "text_vertical": 0.78,
    "tools_color_horizontal": 0.62,
    "pixel_horizontal": 0.40,
    "pixel_file_compare_h": 0.50,
    "export_game_horizontal": 0.52,
}

# Lower bounds keep primary actions and the workspace visible after sash drags.
MIN_PANE_RATIOS: Dict[str, float] = {
    "main_vertical": 0.55,
    "generate_horizontal": 0.34,
    "preview_horizontal": 0.34,
    "import_horizontal": 0.34,
    "import_photo_outer": 0.22,
    "import_photo_center": 0.55,
    "import_text_outer": 0.22,
    "import_text_center": 0.55,
    "text_horizontal": 0.34,
    "tools_color_horizontal": 0.30,
    "pixel_horizontal": 0.22,
    "pixel_file_compare_h": 0.30,
    "export_game_horizontal": 0.34,
}


def clamp_pane_ratio(key: str, ratio: float) -> float:
    minimum = MIN_PANE_RATIOS.get(key, 0.08)
    return min(0.92, max(minimum, ratio))


def layout_settings_path(root: Path) -> Path:
    return root / "runtime" / "settings" / "ui_layout.json"


def load_ui_layout(root: Path) -> Dict[str, float]:
    path = layout_settings_path(root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return dict(DEFAULT_PANE_RATIOS)
        merged = dict(DEFAULT_PANE_RATIOS)
        for key, value in payload.items():
            if key in DEFAULT_PANE_RATIOS:
                try:
                    ratio = float(value)
                except (TypeError, ValueError):
                    continue
                merged[key] = clamp_pane_ratio(key, ratio)
        return merged
    except OSError:
        return dict(DEFAULT_PANE_RATIOS)


def save_ui_layout(root: Path, ratios: Dict[str, float]) -> None:
    path = layout_settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {key: round(float(ratios[key]), 4) for key in DEFAULT_PANE_RATIOS if key in ratios}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def pane_ratio(paned, orient: str) -> float | None:
    """Return sash ratio, or None when the paned window is not ready to measure."""
    try:
        if not paned.winfo_exists():
            return None
        paned.update_idletasks()
        if orient == "vertical":
            total = paned.winfo_height()
        else:
            total = paned.winfo_width()
        if total < 80:
            return None
        return min(0.92, max(0.08, paned.sashpos(0) / total))
    except Exception:
        return None


def apply_pane_ratio(paned, orient: str, ratio: float, *, layout_key: str | None = None) -> None:
    try:
        if not paned.winfo_exists():
            return
        paned.update_idletasks()
        if orient == "vertical":
            total = paned.winfo_height()
        else:
            total = paned.winfo_width()
        if total < 80:
            return
        if layout_key:
            ratio = clamp_pane_ratio(layout_key, ratio)
        else:
            ratio = min(0.92, max(0.08, ratio))
        paned.sashpos(0, int(total * ratio))
    except Exception:
        pass


def enforce_pane_sash_bounds(
    paned,
    orient: str,
    layout_key: str,
    *,
    epsilon: float = 0.002,
) -> bool:
    """Snap an out-of-range sash to its min/max ratio. Returns True when adjusted."""
    measured = pane_ratio(paned, orient)
    if measured is None:
        return False
    clamped = clamp_pane_ratio(layout_key, measured)
    if abs(measured - clamped) <= epsilon:
        return False
    apply_pane_ratio(paned, orient, clamped, layout_key=layout_key)
    return True
