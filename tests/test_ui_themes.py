"""Theme refresh helpers and chrome widgets."""

from __future__ import annotations

import tkinter as tk

from ui.theme_manager import tokens_from_palette
from ui_chrome import DonutGauge
from ui_themes import CRYNET, ELITE, EUROCORP, UNATCO, normalize_theme_id, palette_to_color_globals


def test_palette_to_color_globals_includes_frame_tokens():
    colors = palette_to_color_globals(EUROCORP)
    assert colors["COLOR_ACCENT"] == EUROCORP.accent
    assert colors["COLOR_FRAME_LIGHT"] == EUROCORP.frame_light


def test_eurocorp_syndicate_palette_identity():
    """Eurocorp uses steel neutrals and restrained orange — not legacy cyan/neon."""
    r, g, b = (
        int(EUROCORP.accent[1:3], 16),
        int(EUROCORP.accent[3:5], 16),
        int(EUROCORP.accent[5:7], 16),
    )
    assert r > g > b
    assert EUROCORP.accent != "#38b6ff"
    assert EUROCORP.info != EUROCORP.accent
    assert EUROCORP.success != "#41ff9c"
    assert EUROCORP.bg == "#040405"


def test_tokens_from_palette_semantic_aliases():
    tokens = tokens_from_palette(ELITE)
    assert tokens.chrome_bg == ELITE.bg
    assert tokens.tab_selected_bg == ELITE.accent_dark
    assert tokens.dialog_bg == ELITE.bg
    assert tokens.dropdown_select_bg == ELITE.accent_dark


def test_crynet_palette_and_legacy_spirit_migration():
    assert CRYNET.bg == "#020304"
    assert CRYNET.accent == "#7fefff"
    assert CRYNET.text != CRYNET.accent
    assert normalize_theme_id("spirit_of_horizon") == "crynet"
    assert normalize_theme_id("sakura") == "crynet"


def test_crynet_hud_semantic_tokens():
    tokens = tokens_from_palette(CRYNET, "crynet")
    assert tokens.accent_holographic == CRYNET.accent
    assert tokens.text_technical == CRYNET.text
    assert tokens.border_illuminated == CRYNET.frame_light
    assert tokens.surface_hud == CRYNET.panel_alt
    assert tokens.overlay_glass == CRYNET.panel
    assert tokens.tab_idle_bg == CRYNET.bg
    assert tokens.tab_selected_fg == CRYNET.accent
    assert tokens.separator == CRYNET.frame_light
    assert tokens.idle_border == CRYNET.frame_light


def test_theme_dropdown_order():
    from ui_themes import THEME_IDS

    assert THEME_IDS[-2:] == ("new_eden", "red_phosphorous")
    assert "unatco" in THEME_IDS
    assert THEME_IDS.index("unatco") < THEME_IDS.index("new_eden")
    assert normalize_theme_id("deus_ex") == "unatco"
    assert normalize_theme_id("y2k") == "new_eden"
    assert normalize_theme_id("light") == "new_eden"
    assert normalize_theme_id("mirrors_edge") == "new_eden"
    assert "crynet" in THEME_IDS
    assert "spirit_of_horizon" not in THEME_IDS


def test_unatco_palette_and_tokens():
    assert UNATCO.bg == "#000000"
    assert UNATCO.text == "#ffffff"
    assert UNATCO.text != UNATCO.accent
    assert UNATCO.success == "#99ff00"
    assert UNATCO.button_fg == "#101010"
    tokens = tokens_from_palette(UNATCO, "unatco")
    assert tokens.tab_selected_bg == UNATCO.accent_dark
    assert tokens.tab_selected_fg == UNATCO.text
    assert tokens.selection_border == UNATCO.frame_light
    assert tokens.indicator_attention == UNATCO.success
    assert tokens.accent_holographic == UNATCO.info


def test_new_eden_palette():
    from ui_themes import NEW_EDEN

    assert NEW_EDEN.bg == "#ffffff"
    assert NEW_EDEN.accent == "#e4032e"
    assert NEW_EDEN.select_fg == "#ffffff"


def test_interactive_state_tokens():
    tokens = tokens_from_palette(EUROCORP)
    assert tokens.selection_border == EUROCORP.accent
    assert tokens.validation_border == EUROCORP.warn
    assert tokens.text_select_bg == EUROCORP.accent_dark


def test_donut_gauge_redraws_after_set_scheme():
    root = tk.Tk()
    root.withdraw()
    try:
        gauge = DonutGauge(
            root,
            size=40,
            track_color="#111111",
            fill_color="#222222",
            bg_color="#000000",
            text_color="#ffffff",
            muted_color="#888888",
            ring_width=4,
        )
        gauge.set_value(50.0)
        gauge.set_scheme(
            track_color="#aaaaaa",
            fill_color="#bbbbbb",
            bg_color="#cccccc",
            text_color="#dddddd",
            muted_color="#eeeeee",
        )
        assert gauge.cget("bg") == "#cccccc"
        ring_items = gauge.find_withtag("ring")
        assert ring_items
        assert gauge.itemcget(ring_items[0], "outline") == "#aaaaaa"
    finally:
        root.destroy()
