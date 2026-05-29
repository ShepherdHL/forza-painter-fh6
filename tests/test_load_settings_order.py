from __future__ import annotations

import pytest

cv2 = pytest.importorskip("cv2")

from generator_backend import load_settings
from image_tailored_preset import is_tailored_experimental_preset


def test_load_settings_puts_tailored_first_and_renumbers_eco():
    profiles = load_settings()
    assert profiles
    assert is_tailored_experimental_preset(profiles[0])
    assert profiles[0].label.startswith("🧪")
    assert "0." in profiles[0].label or "Tailored" in profiles[0].label
    eco = next(p for p in profiles if "eco" in p.path.stem.lower())
    assert eco.label.startswith("❄")
    assert "1. Eco" in eco.label or "1. eco" in eco.label.lower()
