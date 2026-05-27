"""
Centralized UI color themes for the desktop app.

Themes are token palettes consumed via module-level COLOR_* globals on ``app``
and ttk style configuration. Add a new ``Palette`` entry and i18n label to
extend the set without touching individual widgets.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Literal

ThemeId = Literal[
    "eurocorp",
    "elite",
    "red_phosphorous",
    "y2k",
    "spirit_of_horizon",
]

THEME_IDS: tuple[str, ...] = (
    "eurocorp",
    "elite",
    "red_phosphorous",
    "y2k",
    "spirit_of_horizon",
)

DEFAULT_THEME_ID: ThemeId = "eurocorp"

# Maps persisted legacy ids to the current catalog.
_LEGACY_THEME_IDS: dict[str, str] = {
    "dark": "eurocorp",
    "system": "eurocorp",
    "light": "y2k",
    "sakura": "spirit_of_horizon",
}


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
    frame_light: str = ""
    frame_dark: str = ""
    sash: str = ""


def _with_frame_tokens(
    palette: Palette,
    *,
    frame_light: str,
    frame_dark: str,
    sash: str,
) -> Palette:
    return replace(
        palette,
        frame_light=frame_light,
        frame_dark=frame_dark,
        sash=sash,
    )


# Current default appearance (formerly "dark").
EUROCORP = _with_frame_tokens(
    Palette(
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
    ),
    frame_light="#3d4a5c",
    frame_dark="#1a1f2a",
    sash="#1f2633",
)

ELITE = Palette(
    bg="#0a0a0a",
    panel="#111111",
    panel_alt="#1a0f00",
    input="#1a0f00",
    text="#ffa040",
    muted="#cc7700",
    accent="#ff8c00",
    accent_dark="#ff6a00",
    warn="#ffb347",
    border="#cc5500",
    button="#1a1208",
    button_active="#ff7a00",
    hint="#ff9d00",
    info="#ff8c00",
    success="#ffb84d",
    error="#ff6a3d",
    preview_bg="#0a0a0a",
    preview_fg="#ffa040",
    select_fg="#0a0a0a",
    button_active_fg="#0a0a0a",
    frame_light="#cc5500",
    frame_dark="#1a0f00",
    sash="#1a0f00",
)

RED_PHOSPHOROUS = Palette(
    bg="#0d0000",
    panel="#110000",
    panel_alt="#1a0000",
    input="#1a0000",
    text="#ff4444",
    muted="#cc3333",
    accent="#ff1a1a",
    accent_dark="#cc0000",
    warn="#ff6666",
    border="#800000",
    button="#1a0000",
    button_active="#cc0000",
    hint="#ff6666",
    info="#ff1a1a",
    success="#ff5555",
    error="#ff3333",
    preview_bg="#0d0000",
    preview_fg="#ff4444",
    select_fg="#0d0000",
    button_active_fg="#0d0000",
    frame_light="#800000",
    frame_dark="#1a0000",
    sash="#1a0000",
)

Y2K = Palette(
    bg="#e8f4f8",
    panel="#ffffff",
    panel_alt="#d0eaf5",
    input="#ffffff",
    text="#003344",
    muted="#336677",
    accent="#00aaff",
    accent_dark="#00cc66",
    warn="#007799",
    border="#66ccff",
    button="#d0eaf5",
    button_active="#b8e0f0",
    hint="#008866",
    info="#00aaff",
    success="#00cc66",
    error="#cc3366",
    preview_bg="#c8e8f4",
    preview_fg="#003344",
    select_fg="#ffffff",
    button_active_fg="#003344",
    frame_light="#99ddff",
    frame_dark="#b0d8ec",
    sash="#b8e0f0",
)

SPIRIT_OF_HORIZON = Palette(
    bg="#f9f5f5",
    panel="#ffffff",
    panel_alt="#fff0f2",
    input="#ffffff",
    text="#1a1a1a",
    muted="#5c4a4e",
    accent="#e8002d",
    accent_dark="#c40024",
    warn="#b80028",
    border="#f4a7b9",
    button="#fff0f2",
    button_active="#ffd6de",
    hint="#f4a7b9",
    info="#0099e6",
    success="#e8002d",
    error="#c40024",
    preview_bg="#fff0f2",
    preview_fg="#1a1a1a",
    select_fg="#ffffff",
    button_active_fg="#1a1a1a",
    frame_light="#f4a7b9",
    frame_dark="#ffd6de",
    sash="#ffd6de",
)

_PALETTES: dict[str, Palette] = {
    "eurocorp": EUROCORP,
    "elite": ELITE,
    "red_phosphorous": RED_PHOSPHOROUS,
    "y2k": Y2K,
    "spirit_of_horizon": SPIRIT_OF_HORIZON,
}


def normalize_theme_id(theme_id: str | None) -> str:
    raw = (theme_id or "").strip().lower()
    if not raw:
        return DEFAULT_THEME_ID
    if raw in _PALETTES:
        return raw
    return _LEGACY_THEME_IDS.get(raw, DEFAULT_THEME_ID)


def resolve_palette(theme_id: str | None = None) -> Palette:
    return _PALETTES[normalize_theme_id(theme_id)]


def theme_settings_path(root: Path) -> Path:
    return root / "runtime" / "settings" / "ui_theme.txt"


def load_saved_theme_id(root: Path) -> str:
    path = theme_settings_path(root)
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return DEFAULT_THEME_ID
    return normalize_theme_id(raw)


def save_theme_id(root: Path, theme_id: str) -> None:
    path = theme_settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalize_theme_id(theme_id) + "\n", encoding="utf-8")


def palette_to_color_globals(palette: Palette) -> Dict[str, str]:
    frame_light = palette.frame_light or palette.border
    frame_dark = palette.frame_dark or palette.panel_alt
    sash = palette.sash or palette.button
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
        "COLOR_FRAME_LIGHT": frame_light,
        "COLOR_FRAME_DARK": frame_dark,
        "COLOR_SASH": sash,
    }
