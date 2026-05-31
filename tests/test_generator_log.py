from __future__ import annotations

from generator_log import friendly_generator_line


def test_friendly_generator_line_accepts_generic_progress():
    assert friendly_generator_line("[3/120] Added rectangle layer") == "Generated layer 3/120"
    assert friendly_generator_line("[1/50] Added rotated ellipse") == "Generated layer 1/50"


def test_friendly_generator_line_ignores_error_grid_setting_noise():
    assert friendly_generator_line("errorGridSize = 64") is None
    assert friendly_generator_line("Settings: errorGridSize=64 stopAt=200") == "Settings: errorGridSize=64 stopAt=200"


def test_friendly_generator_line_surfaces_real_failures():
    assert friendly_generator_line("OpenCL init failed: platform not found") == (
        "OpenCL init failed: platform not found"
    )
