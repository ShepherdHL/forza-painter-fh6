"""
Runtime build profile baked in at PyInstaller build time (_build_profile.json).

Used by the Defender comparative matrix and for compile-time feature gates.
Environment variables with the same names override the baked file for dev testing.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BuildProfile:
    variant_id: str = "dev"
    label: str = "development"
    onefile: bool = False
    disable_elevation: bool = False
    disable_generator: bool = False
    disable_networking: bool = False
    disable_memory_scan: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "label": self.label,
            "onefile": self.onefile,
            "disable_elevation": self.disable_elevation,
            "disable_generator": self.disable_generator,
            "disable_networking": self.disable_networking,
            "disable_memory_scan": self.disable_memory_scan,
        }


_PROFILE: BuildProfile | None = None


def _profile_paths() -> list[Path]:
    paths: list[Path] = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            paths.append(Path(meipass) / "_build_profile.json")
        paths.append(Path(sys.executable).resolve().parent / "_build_profile.json")
    else:
        paths.append(Path(__file__).resolve().parent / "_build_profile.json")
    return paths


def _env_flag(name: str) -> bool | None:
    raw = os.environ.get(name, "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return None


def _load_json_profile() -> dict[str, Any] | None:
    for path in _profile_paths():
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                return payload
    return None


def get_build_profile() -> BuildProfile:
    global _PROFILE
    if _PROFILE is not None:
        return _PROFILE

    payload = _load_json_profile() or {}
    _PROFILE = BuildProfile(
        variant_id=str(payload.get("variant_id", "dev")),
        label=str(payload.get("label", "development")),
        onefile=bool(payload.get("onefile", getattr(sys, "frozen", False))),
        disable_elevation=bool(payload.get("disable_elevation", False)),
        disable_generator=bool(payload.get("disable_generator", False)),
        disable_networking=bool(payload.get("disable_networking", False)),
        disable_memory_scan=bool(payload.get("disable_memory_scan", False)),
    )
    return _PROFILE


def elevation_disabled() -> bool:
    env = _env_flag("FORZA_PAINTER_DISABLE_ELEVATION")
    if env is not None:
        return env
    return get_build_profile().disable_elevation


def generator_disabled() -> bool:
    env = _env_flag("FORZA_PAINTER_DISABLE_GENERATOR")
    if env is not None:
        return env
    return get_build_profile().disable_generator


def networking_disabled() -> bool:
    env = _env_flag("FORZA_PAINTER_DISABLE_NETWORKING")
    if env is not None:
        return env
    return get_build_profile().disable_networking


def memory_scan_disabled() -> bool:
    env = _env_flag("FORZA_PAINTER_DISABLE_MEMORY_SCAN")
    if env is not None:
        return env
    return get_build_profile().disable_memory_scan


def matrix_variant_id() -> str:
    return get_build_profile().variant_id
