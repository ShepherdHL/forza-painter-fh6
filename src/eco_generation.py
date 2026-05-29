"""
Experimental eco / cool-GPU generation helpers (preset detection, cooldown settings).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app_paths import ROOT

ECO_PRESET_FRAGMENT = "eco (experimental)"


@dataclass(frozen=True)
class EcoGenerationSettings:
    cooldown_enabled: bool = False
    eco_preset_acknowledged: bool = False


def is_eco_experimental_preset(setting) -> bool:
    path = setting.get("path") if hasattr(setting, "get") else setting["path"]
    return ECO_PRESET_FRAGMENT in Path(path).stem.lower()


def settings_path(root: Path | None = None) -> Path:
    return (root or ROOT) / "runtime" / "settings" / "eco_generation.json"


def load_eco_generation_settings(root: Path | None = None) -> EcoGenerationSettings:
    path = settings_path(root)
    if not path.is_file():
        return EcoGenerationSettings()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return EcoGenerationSettings()
    if not isinstance(payload, dict):
        return EcoGenerationSettings()
    return EcoGenerationSettings(
        cooldown_enabled=bool(payload.get("cooldown_enabled", False)),
        eco_preset_acknowledged=bool(payload.get("eco_preset_acknowledged", False)),
    )


def save_eco_generation_settings(settings: EcoGenerationSettings, root: Path | None = None) -> None:
    path = settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cooldown_enabled": settings.cooldown_enabled,
        "eco_preset_acknowledged": settings.eco_preset_acknowledged,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
