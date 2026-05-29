"""
Centralized UI color themes for the desktop app.

Themes are token palettes consumed by :class:`ui.theme_manager.ThemeManager` and
legacy ``COLOR_*`` module globals on ``app`` (kept in sync for migration).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Literal

ThemeId = Literal[
    "eurocorp",
    "elite",
    "crynet",
    "unatco",
    "new_eden",
    "red_phosphorous",
]

THEME_IDS: tuple[str, ...] = (
    "eurocorp",
    "elite",
    "crynet",
    "unatco",
    "new_eden",
    "red_phosphorous",
)

DEFAULT_THEME_ID: ThemeId = "eurocorp"

# Maps persisted legacy ids to the current catalog.
_LEGACY_THEME_IDS: dict[str, str] = {
    "dark": "eurocorp",
    "system": "eurocorp",
    "light": "new_eden",
    "y2k": "new_eden",
    "mirrors_edge": "new_eden",
    "sakura": "crynet",
    "spirit_of_horizon": "crynet",
    "deus_ex": "unatco",
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
    button_fg: str = ""
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


# Default theme — Syndicate (2012) Eurocorp: matte black, steel graphite, restrained
# tactical orange accents (not neon cyberpunk).
EUROCORP = _with_frame_tokens(
    Palette(
        bg="#040405",
        panel="#0a0b0e",
        panel_alt="#121418",
        input="#08090c",
        text="#e8ebf0",
        muted="#70788a",
        accent="#cc6a2e",
        accent_dark="#8f4a1a",
        warn="#a8844a",
        border="#262a32",
        button="#14171c",
        button_active="#1e2229",
        hint="#94704a",
        info="#5c7082",
        success="#6d848c",
        error="#b8544c",
        preview_bg="#0c0d10",
        preview_fg="#e8ebf0",
        select_fg="#e8ebf0",
    ),
    frame_light="#353a44",
    frame_dark="#0c0e12",
    sash="#181b22",
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

# New Eden-inspired light mode: white fields, cherry-red accents, high contrast.
NEW_EDEN = _with_frame_tokens(
    Palette(
        bg="#ffffff",
        panel="#ffffff",
        panel_alt="#f4f4f4",
        input="#ffffff",
        text="#141414",
        muted="#5c5c5c",
        accent="#e4032e",
        accent_dark="#c90025",
        warn="#b80f22",
        border="#e0e0e0",
        button="#f2f2f2",
        button_active="#fde8ec",
        hint="#8a3040",
        info="#1a8cff",
        success="#1f8a4c",
        error="#c90025",
        preview_bg="#fafafa",
        preview_fg="#141414",
        select_fg="#ffffff",
        button_active_fg="#141414",
    ),
    frame_light="#f0f0f0",
    frame_dark="#e5e5e5",
    sash="#ebebeb",
)

# Crysis 2 / CryNet Systems HUD — near-black field, cool readable text, restrained
# ice-cyan holographic accents (not oversaturated neon).
CRYNET = _with_frame_tokens(
    Palette(
        bg="#020304",
        panel="#060a10",
        panel_alt="#0a1018",
        input="#040810",
        text="#c8dce8",
        muted="#5a7284",
        accent="#7fefff",
        accent_dark="#1a4858",
        warn="#8ec4dc",
        border="#1a3848",
        button="#081018",
        button_active="#122028",
        hint="#6a98a8",
        info="#7fefff",
        success="#5a9aa8",
        error="#d06070",
        preview_bg="#060a10",
        preview_fg="#c8dce8",
        select_fg="#020304",
        button_active_fg="#7fefff",
    ),
    frame_light="#3a6878",
    frame_dark="#040810",
    sash="#142028",
)

# UNATCO terminal — black field, navy title chrome, muted holo-green panels,
# lime status accents and cyan instrumentation (government computer interfaces).
UNATCO = _with_frame_tokens(
    Palette(
        bg="#000000",
        panel="#252525",
        panel_alt="#2a3830",
        input="#0a0a0a",
        text="#ffffff",
        muted="#bbbbbb",
        accent="#283868",
        accent_dark="#101830",
        warn="#888888",
        border="#505050",
        button="#888888",
        button_active="#aaaaaa",
        hint="#707070",
        info="#48b0c8",
        success="#99ff00",
        error="#c06060",
        preview_bg="#141414",
        preview_fg="#ffffff",
        select_fg="#ffffff",
        button_active_fg="#101010",
        button_fg="#101010",
    ),
    frame_light="#aaaaaa",
    frame_dark="#1a1a1a",
    sash="#404040",
)

_PALETTES: dict[str, Palette] = {
    "eurocorp": EUROCORP,
    "elite": ELITE,
    "crynet": CRYNET,
    "unatco": UNATCO,
    "new_eden": NEW_EDEN,
    "red_phosphorous": RED_PHOSPHOROUS,
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
        "COLOR_BUTTON_FG": palette.button_fg or palette.text,
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
