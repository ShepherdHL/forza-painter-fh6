from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ui_preferences import _default_preferences, load_ui_preferences


def test_default_write_workspace_signature_enabled():
    prefs = _default_preferences()
    assert prefs["write_workspace_signature"] is True


def test_load_ui_preferences_coerces_signature_flag(tmp_path, monkeypatch):
    settings_dir = tmp_path / "runtime" / "settings"
    settings_dir.mkdir(parents=True)
    prefs_path = settings_dir / "ui_preferences.json"
    prefs_path.write_text('{"write_workspace_signature": false}\n', encoding="utf-8")
    monkeypatch.setattr("ui_preferences.ROOT", tmp_path)
    monkeypatch.setattr("ui_preferences.PREFERENCES_PATH", prefs_path)
    loaded = load_ui_preferences()
    assert loaded["write_workspace_signature"] is False
