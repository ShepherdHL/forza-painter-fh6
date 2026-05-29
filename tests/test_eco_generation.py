from __future__ import annotations

from pathlib import Path

from eco_generation import ECO_PRESET_FRAGMENT, is_eco_experimental_preset, load_eco_generation_settings, save_eco_generation_settings, EcoGenerationSettings


def test_is_eco_experimental_preset_detects_eco_ini():
    setting = {"path": Path("config/settings/0. eco (experimental).ini")}
    assert is_eco_experimental_preset(setting)


def test_is_eco_experimental_preset_rejects_slow_ini():
    setting = {"path": Path("config/settings/4. slow (conserve shapes).ini")}
    assert not is_eco_experimental_preset(setting)


def test_eco_generation_settings_round_trip(tmp_path):
    save_eco_generation_settings(
        EcoGenerationSettings(cooldown_enabled=True, eco_preset_acknowledged=True),
        tmp_path,
    )
    loaded = load_eco_generation_settings(tmp_path)
    assert loaded.cooldown_enabled
    assert loaded.eco_preset_acknowledged


def test_eco_preset_fragment_is_lowercase_match():
    assert ECO_PRESET_FRAGMENT in "0. eco (experimental)".lower()
