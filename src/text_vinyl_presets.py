"""Named presets for Text vinyl generation options."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from text_geometry import (
    SHAPE_MODE_ELLIPSES,
    SHAPE_MODE_MIXED,
    SHAPE_MODE_RECTANGLES,
)


@dataclass(frozen=True)
class TextVinylPreset:
    id: str
    label_key: str
    shape_mode: str
    cell_size: int
    use_forza_font: bool = False
    forza_font_index: int = 1
    fit_layer_budget: bool = False
    extra_shapes: bool = False


TEXT_VINYL_PRESETS: Dict[str, TextVinylPreset] = {
    "custom": TextVinylPreset(
        id="custom",
        label_key="text_preset_custom",
        shape_mode=SHAPE_MODE_RECTANGLES,
        cell_size=1,
    ),
    "efficient_cjk": TextVinylPreset(
        id="efficient_cjk",
        label_key="text_preset_efficient_cjk",
        shape_mode=SHAPE_MODE_RECTANGLES,
        cell_size=6,
        fit_layer_budget=True,
    ),
    "sharp_cjk": TextVinylPreset(
        id="sharp_cjk",
        label_key="text_preset_sharp_cjk",
        shape_mode=SHAPE_MODE_MIXED,
        cell_size=2,
    ),
    "soft_cjk": TextVinylPreset(
        id="soft_cjk",
        label_key="text_preset_soft_cjk",
        shape_mode=SHAPE_MODE_ELLIPSES,
        cell_size=3,
    ),
    "forza_latin": TextVinylPreset(
        id="forza_latin",
        label_key="text_preset_forza_latin",
        shape_mode=SHAPE_MODE_RECTANGLES,
        cell_size=1,
        use_forza_font=True,
        forza_font_index=1,
    ),
    "smooth_cjk_extra": TextVinylPreset(
        id="smooth_cjk_extra",
        label_key="text_preset_smooth_cjk_extra",
        shape_mode=SHAPE_MODE_RECTANGLES,
        cell_size=2,
        fit_layer_budget=False,
        extra_shapes=True,
    ),
}

PRESET_ORDER: List[str] = [
    "custom",
    "efficient_cjk",
    "sharp_cjk",
    "soft_cjk",
    "smooth_cjk_extra",
    "forza_latin",
]


def get_preset(preset_id: str) -> TextVinylPreset:
    return TEXT_VINYL_PRESETS.get(preset_id) or TEXT_VINYL_PRESETS["custom"]
