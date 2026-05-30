from __future__ import annotations

from pathlib import Path

from preset_preview import (
    effective_max_dimension,
    gpu_load_tier,
    preset_badge_prefix,
    preset_label_color,
    preset_label_with_badge,
    projected_layer_count,
)


def test_projected_layer_count_caps_at_stop_at():
    assert projected_layer_count(2400, 1800) == 1800
    assert projected_layer_count(1200, 1800) == 1200


def test_projected_layer_count_none_for_missing_estimate():
    assert projected_layer_count(None, 1800) is None
    assert projected_layer_count(0, 1800) is None


def test_gpu_load_tier():
    assert gpu_load_tier(30_000, 600) == "light"
    assert gpu_load_tier(120_000, 1400) == "moderate"
    assert gpu_load_tier(220_000, 2000) == "heavy"
    assert gpu_load_tier(1_000_000, 3000) == "extreme"


def test_effective_max_dimension_downscales_long_edge():
    assert effective_max_dimension(4000, 2000, 1400) == (1400, 700)


def test_bundled_preset_badges():
    assert preset_badge_prefix(Path("0. eco (experimental).ini"), {}, preset_index=0) == "🍃▁▂"
    assert preset_badge_prefix(Path("1. maximum speed.ini"), {}, preset_index=1) == "⚡▁▁"
    assert preset_badge_prefix(Path("2. fast.ini"), {}, preset_index=2) == "⏩▂▂"
    assert preset_badge_prefix(Path("3. normal.ini"), {}, preset_index=3) == "★▄▄▃"
    assert preset_badge_prefix(Path("6. maximum power.ini"), {}, preset_index=6) == "⚠▁▇▇"


def test_preset_label_with_badge():
    assert preset_label_with_badge("3. Normal", "★▄▄▃") == "★▄▄▃  3. Normal"
    assert preset_label_with_badge("3. Normal", "") == "3. Normal"


def test_preset_label_colors():
    assert preset_label_color(0) == "#32CD32"
    assert preset_label_color(3) == "#00BFFF"
    assert preset_label_color(6) == "#DE3163"
    assert preset_label_color(1) is None


def test_user_preset_badge_from_values():
    values = {"stopAt": "1800", "randomSamples": "120000", "maxResolution": "1400"}
    assert preset_badge_prefix(Path("user.ini"), values) == "▄▃▃"
