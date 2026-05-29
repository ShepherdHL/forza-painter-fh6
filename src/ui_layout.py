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
    "text_horizontal": 0.58,
    "text_vertical": 0.78,
    "tools_color_horizontal": 0.62,
}


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
                merged[key] = min(0.92, max(0.08, ratio))
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


def apply_pane_ratio(paned, orient: str, ratio: float) -> None:
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
        paned.sashpos(0, int(total * min(0.92, max(0.08, ratio))))
    except Exception:
        pass
