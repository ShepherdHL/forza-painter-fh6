"""Persist file-management behavior presets and custom options."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from app_paths import ROOT

PresetId = Literal["recommended", "keep_all", "minimal_disk", "custom"]

SETTINGS_PATH = ROOT / "runtime" / "settings" / "file_management.json"

PRESET_RECOMMENDED: PresetId = "recommended"
PRESET_KEEP_ALL: PresetId = "keep_all"
PRESET_MINIMAL_DISK: PresetId = "minimal_disk"
PRESET_CUSTOM: PresetId = "custom"

PRESET_IDS: tuple[PresetId, ...] = (
    PRESET_RECOMMENDED,
    PRESET_KEEP_ALL,
    PRESET_MINIMAL_DISK,
    PRESET_CUSTOM,
)


@dataclass
class FileManagementSettings:
    """Tiered cleanup and source-copy behavior."""

    preset: PresetId = PRESET_RECOMMENDED
    clear_ephemeral_on_exit: bool = True
    clear_session_cache_on_exit: bool = False
    copy_external_images: bool = True
    copy_trace_references: bool = True
    keep_filter_previews: bool = False

    def effective_clear_ephemeral_on_exit(self) -> bool:
        if self.preset == PRESET_RECOMMENDED:
            return True
        if self.preset == PRESET_KEEP_ALL:
            return False
        if self.preset == PRESET_MINIMAL_DISK:
            return True
        return self.clear_ephemeral_on_exit

    def effective_clear_session_cache_on_exit(self) -> bool:
        if self.preset == PRESET_RECOMMENDED:
            return False
        if self.preset == PRESET_KEEP_ALL:
            return False
        if self.preset == PRESET_MINIMAL_DISK:
            return True
        return self.clear_session_cache_on_exit

    def effective_copy_external_images(self) -> bool:
        if self.preset == PRESET_CUSTOM:
            return self.copy_external_images
        return True

    def effective_copy_trace_references(self) -> bool:
        if self.preset == PRESET_CUSTOM:
            return self.copy_trace_references
        return True

    def effective_keep_filter_previews(self) -> bool:
        if self.preset == PRESET_KEEP_ALL:
            return True
        if self.preset in (PRESET_RECOMMENDED, PRESET_MINIMAL_DISK):
            return False
        return self.keep_filter_previews


def _normalize_preset(value: str | None) -> PresetId:
    normalized = str(value or PRESET_RECOMMENDED).strip().lower()
    if normalized in PRESET_IDS:
        return normalized  # type: ignore[return-value]
    return PRESET_RECOMMENDED


def default_settings() -> FileManagementSettings:
    return FileManagementSettings()


def load_file_management_settings() -> FileManagementSettings:
    settings = default_settings()
    try:
        if SETTINGS_PATH.is_file():
            payload = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                settings.preset = _normalize_preset(payload.get("preset"))
                settings.clear_ephemeral_on_exit = bool(payload.get("clear_ephemeral_on_exit", True))
                settings.clear_session_cache_on_exit = bool(payload.get("clear_session_cache_on_exit", False))
                settings.copy_external_images = bool(payload.get("copy_external_images", True))
                settings.copy_trace_references = bool(payload.get("copy_trace_references", True))
                settings.keep_filter_previews = bool(payload.get("keep_filter_previews", False))
    except (OSError, json.JSONDecodeError):
        pass
    return settings


def save_file_management_settings(settings: FileManagementSettings) -> None:
    try:
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(settings)
        SETTINGS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def apply_preset(preset: PresetId) -> FileManagementSettings:
    settings = load_file_management_settings()
    settings.preset = preset
    if preset == PRESET_RECOMMENDED:
        settings.clear_ephemeral_on_exit = True
        settings.clear_session_cache_on_exit = False
        settings.copy_external_images = True
        settings.copy_trace_references = True
        settings.keep_filter_previews = False
    elif preset == PRESET_KEEP_ALL:
        settings.clear_ephemeral_on_exit = False
        settings.clear_session_cache_on_exit = False
        settings.copy_external_images = True
        settings.copy_trace_references = True
        settings.keep_filter_previews = True
    elif preset == PRESET_MINIMAL_DISK:
        settings.clear_ephemeral_on_exit = True
        settings.clear_session_cache_on_exit = True
        settings.copy_external_images = True
        settings.copy_trace_references = True
        settings.keep_filter_previews = False
    save_file_management_settings(settings)
    return settings
