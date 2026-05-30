from __future__ import annotations

import shared_color_palette as palette_module
import ui_preferences


def test_shared_palette_push_dedupes_and_trims(monkeypatch, tmp_path):
    prefs_path = tmp_path / "ui_preferences.json"
    monkeypatch.setattr(ui_preferences, "PREFERENCES_PATH", prefs_path)

    shared = palette_module.SharedColorPalette()
    shared.push(10, 20, 30, 255)
    shared.push(40, 50, 60, 255)
    shared.push(10, 20, 30, 255)

    colors = shared.saved_colors()
    assert colors[0] == (10, 20, 30, 255)
    assert colors[1] == (40, 50, 60, 255)
    assert len(colors) == 2


def test_shared_palette_persists_to_preferences(monkeypatch, tmp_path):
    prefs_path = tmp_path / "ui_preferences.json"
    monkeypatch.setattr(ui_preferences, "PREFERENCES_PATH", prefs_path)

    shared = palette_module.SharedColorPalette()
    shared.push(1, 2, 3, 255)

    reloaded = palette_module.SharedColorPalette()
    assert reloaded.saved_colors()[0] == (1, 2, 3, 255)
    assert palette_module.get_last_color() == (1, 2, 3, 255)


def test_shared_palette_notifies_listeners():
    shared = palette_module.SharedColorPalette()
    seen: list[tuple[tuple[int, int, int, int], str]] = []

    def listener(rgba, source):
        seen.append((rgba, source))

    shared.subscribe(listener)
    shared.push(9, 8, 7, 255, persist=False, source="push")
    shared.recall((9, 8, 7, 255))

    assert seen[0] == ((9, 8, 7, 255), "push")
    assert seen[1] == ((9, 8, 7, 255), "recall")
