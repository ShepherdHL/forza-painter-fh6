"""
UI color themes for the desktop app.

The desktop UI is locked to dark mode for readable text and inputs.
Other palettes remain in this module for a possible future UI overhaul.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal

ThemeId = Literal["system", "dark", "light", "sakura", "elite"]

THEME_IDS: tuple[str, ...] = ("system", "dark", "light", "sakura", "elite")
APP_THEME_ID: ThemeId = "dark"


@dataclass(frozen=True)
class Palette:
    bg: str
    panel: str
    panel_alt: str
    input: str
    text: str
    muted: str
    accent: str
    accent_dark: str
    warn: str
    border: str
    button: str
    button_active: str
    hint: str
    info: str
    success: str
    error: str
    preview_bg: str
    preview_fg: str
    select_fg: str = "#ffffff"
    button_active_fg: str = ""


# Desktop “tactical HUD” dark: deep charcoal, neon green + electric blue accents
# (Steam/Discord legibility + Syndicate-style mission readout flourishes).
DARK = Palette(
    bg="#07070b",
    panel="#101018",
    panel_alt="#17171f",
    input="#0d0f14",
    text="#eef1f8",
    muted="#8f96a8",
    accent="#38b6ff",
    accent_dark="#1e7db8",
    warn="#ffc14d",
    border="#2a3142",
    button="#1e2533",
    button_active="#283040",
    hint="#e0b24a",
    info="#5cc8ff",
    success="#41ff9c",
    error="#ff6b6b",
    preview_bg="#141820",
    preview_fg="#eef1f8",
)

LIGHT = Palette(
    bg="#eef1f6",
    panel="#ffffff",
    panel_alt="#e2e8f0",
    input="#ffffff",
    text="#0f1419",
    muted="#3d4f5f",
    accent="#0969da",
    accent_dark="#0550ae",
    warn="#6b4a00",
    border="#8b9cb3",
    button="#d8e0ea",
    button_active="#bcc8d6",
    hint="#6b4a00",
    info="#0550ae",
    success="#116329",
    error="#a40e26",
    preview_bg="#c8d2dc",
    preview_fg="#0f1419",
    select_fg="#ffffff",
    button_active_fg="#0f1419",
)

SAKURA = Palette(
    bg="#ffe8ee",
    panel="#ffffff",
    panel_alt="#ffd6e2",
    input="#fff8fa",
    text="#14060c",
    muted="#4a2230",
    accent="#9b1530",
    accent_dark="#c41e3a",
    warn="#6b0f28",
    border="#c76b82",
    button="#ffc8d6",
    button_active="#ffadc2",
    hint="#6b0f28",
    info="#9b1530",
    success="#1b5e40",
    error="#8b1028",
    preview_bg="#1f0c12",
    preview_fg="#ffe8ee",
    select_fg="#ffffff",
    button_active_fg="#14060c",
)

ELITE = Palette(
    bg="#000000",
    panel="#000000",
    panel_alt="#0a0a0a",
    input="#1a1a1a",
    text="#ff9d00",
    muted="#d48200",
    accent="#ff9d00",
    accent_dark="#ff9d00",
    warn="#ff9d00",
    border="#ff9d00",
    button="#1a1a1a",
    button_active="#ff9d00",
    hint="#ff9d00",
    info="#ff9d00",
    success="#ff9d00",
    error="#ff6a3d",
    preview_bg="#000000",
    preview_fg="#ff9d00",
    select_fg="#000000",
    button_active_fg="#000000",
)


def detect_system_dark_mode() -> bool:
    """True when the OS shell is using a dark appearance."""
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return int(value) == 0
        except OSError:
            pass
    return True


def resolve_palette(theme_id: str | None = None) -> Palette:
    """Return the palette used by the desktop app (always dark)."""
    return DARK


def theme_settings_path(root: Path) -> Path:
    return root / "runtime" / "settings" / "ui_theme.txt"


def load_saved_theme_id(root: Path) -> str:
    return APP_THEME_ID


def save_theme_id(root: Path, theme_id: str) -> None:
    path = theme_settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(APP_THEME_ID + "\n", encoding="utf-8")


def palette_to_color_globals(palette: Palette) -> Dict[str, str]:
    return {
        "COLOR_BG": palette.bg,
        "COLOR_PANEL": palette.panel,
        "COLOR_PANEL_ALT": palette.panel_alt,
        "COLOR_INPUT": palette.input,
        "COLOR_TEXT": palette.text,
        "COLOR_MUTED": palette.muted,
        "COLOR_ACCENT": palette.accent,
        "COLOR_ACCENT_DARK": palette.accent_dark,
        "COLOR_WARN": palette.warn,
        "COLOR_BORDER": palette.border,
        "COLOR_BUTTON": palette.button,
        "COLOR_BUTTON_ACTIVE": palette.button_active,
        "COLOR_BUTTON_ACTIVE_FG": palette.button_active_fg or palette.text,
        "COLOR_HINT": palette.hint,
        "COLOR_INFO": palette.info,
        "COLOR_SUCCESS": palette.success,
        "COLOR_ERROR": palette.error,
        "COLOR_PREVIEW_BG": palette.preview_bg,
        "COLOR_PREVIEW_FG": palette.preview_fg,
        "COLOR_SELECT_FG": palette.select_fg,
    }
