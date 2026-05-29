"""
Preset-aware projections for Image Preview (no JSON generation required).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from eco_generation import is_eco_experimental_preset

GpuLoadTier = Literal["light", "moderate", "heavy", "extreme"]

# Bundled preset badges: marker first, then speed + detail + GPU bars (▁▇).
# Highlight colors for bundled presets (Eco, Normal, Maximum Power).
PRESET_LABEL_COLORS: dict[int, str] = {
    0: "#32CD32",  # lime green
    3: "#00BFFF",  # electric blue
    6: "#DE3163",  # cherry red
}


def preset_label_color(preset_index: int | None) -> str | None:
    if preset_index is None:
        return None
    return PRESET_LABEL_COLORS.get(preset_index)


_BUNDLED_BADGE_BY_INDEX: dict[int, str] = {
    0: "❄▁▂",
    1: "⚡▁▁",
    2: "⏩▂▂",
    3: "★▄▄▃",
    4: "◆▃▆▅",
    5: "✦▂▇▆",
    6: "⚠▁▇▇",
}


def _bar_for_speed(stop_at: int) -> str:
    if stop_at <= 500:
        return "▇"
    if stop_at <= 1000:
        return "▆"
    if stop_at <= 1500:
        return "▃"
    if stop_at <= 1800:
        return "▄"
    if stop_at <= 2500:
        return "▃"
    if stop_at <= 3000:
        return "▂"
    return "▁"


def _bar_for_detail(random_samples: int) -> str:
    if random_samples <= 35_000:
        return "▁"
    if random_samples <= 65_000:
        return "▂"
    if random_samples <= 95_000:
        return "▂"
    if random_samples <= 125_000:
        return "▃"
    if random_samples <= 230_000:
        return "▆"
    return "▇"


def _bar_for_gpu_tier(tier: GpuLoadTier) -> str:
    return {"light": "▁", "moderate": "▃", "heavy": "▅", "extreme": "▇"}[tier]


def _format_badge(speed: str, detail: str, gpu: str, suffix: str = "") -> str:
    return f"{speed}{detail}{gpu}{suffix}"


def preset_badge_prefix(
    path: Path | None,
    values: dict[str, str],
    *,
    preset_index: int | None = None,
    setting=None,
) -> str:
    """Return a language-neutral speed/detail/GPU badge for a preset row."""
    if setting is not None:
        badge = str(setting.get("badge_prefix", "") if hasattr(setting, "get") else setting["badge_prefix"])
        if badge:
            return badge
        path = setting.get("path") if hasattr(setting, "get") else setting["path"]
        values = preset_values_dict(setting)
        if preset_index is None:
            preset_index = _preset_index_from_path(Path(path)) if path else None

    if preset_index is not None and preset_index in _BUNDLED_BADGE_BY_INDEX:
        return _BUNDLED_BADGE_BY_INDEX[preset_index]

    stop_at = preset_setting_int(values, "stopAt")
    random_samples = preset_setting_int(values, "randomSamples")
    max_resolution = preset_setting_int(values, "maxResolution")
    speed = _bar_for_speed(stop_at)
    detail = _bar_for_detail(random_samples)
    if path is not None and is_eco_experimental_preset({"path": path}):
        gpu = "❄"
    else:
        gpu = _bar_for_gpu_tier(gpu_load_tier(random_samples, max_resolution))
    return _format_badge(speed, detail, gpu)


def preset_index_from_path(path: Path) -> int | None:
    import re

    match = re.match(r"^(\d+)", path.stem)
    return int(match.group(1)) if match else None


_preset_index_from_path = preset_index_from_path


def preset_label_with_badge(base_label: str, badge_prefix: str) -> str:
    badge = str(badge_prefix).strip()
    if not badge:
        return base_label
    return f"{badge}  {base_label}"


def preset_values_dict(setting) -> dict[str, str]:
    if setting is None:
        return {}
    if hasattr(setting, "get"):
        return dict(setting.get("values", {}) or {})
    return dict(setting.get("values", {}))


def preset_setting_int(values: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(str(values.get(key, default)).strip())
    except (TypeError, ValueError):
        return default


def preset_setting_name(setting) -> str:
    if setting is None:
        return "—"
    values = preset_values_dict(setting)
    display = str(values.get("displayName", "")).strip()
    if display:
        return display
    label = str(setting.get("label", "") if hasattr(setting, "get") else setting["label"])
    if ". " in label:
        return label.split(". ", 1)[1]
    return label or "—"


def gpu_load_tier(random_samples: int, max_resolution: int) -> GpuLoadTier:
    if random_samples >= 500_000 or max_resolution >= 2800:
        return "extreme"
    if random_samples >= 200_000 or max_resolution >= 2000:
        return "heavy"
    if random_samples >= 100_000 or max_resolution >= 1400:
        return "moderate"
    return "light"


def projected_layer_count(complexity_estimate: int | None, stop_at: int) -> int | None:
    if complexity_estimate is None or complexity_estimate <= 0:
        return None
    if stop_at <= 0:
        return complexity_estimate
    return min(complexity_estimate, stop_at)


def read_image_dimensions(path: Path) -> tuple[int, int] | None:
    path = Path(path)
    if not path.is_file():
        return None
    try:
        from utils import load_pillow

        loaded = load_pillow()
        if not loaded:
            return None
        Image, _ImageDraw = loaded
        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None


def effective_max_dimension(width: int, height: int, max_resolution: int) -> tuple[int, int]:
    if max_resolution <= 0 or width <= 0 or height <= 0:
        return width, height
    longest = max(width, height)
    if longest <= max_resolution:
        return width, height
    scale = max_resolution / float(longest)
    return max(1, int(round(width * scale))), max(1, int(round(height * scale)))
