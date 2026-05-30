from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from text_fonts import (
    _name_looks_latin,
    missing_glyphs,
    recommend_font_label_for_text,
    validate_text_coverage,
)


def test_name_looks_latin_rejects_icon_fonts() -> None:
    assert not _name_looks_latin("SegoeIcons (TrueType)")
    assert not _name_looks_latin("Segoe MDL2 Assets")
    assert not _name_looks_latin("Webdings")


def test_name_looks_latin_accepts_text_faces() -> None:
    assert _name_looks_latin("Segoe UI (TrueType)")
    assert _name_looks_latin("Arial (TrueType)")
    assert _name_looks_latin("Calibri")


def test_missing_glyphs_checks_latin_characters() -> None:
    fake_path = Path("C:/Windows/Fonts/example.ttf")

    def fake_has_glyph(_path: Path, char: str, size: int = 48) -> bool:
        return char.lower() != "x"

    with patch("text_fonts.font_has_glyph", side_effect=fake_has_glyph):
        missing = missing_glyphs("Phoenix", fake_path)

    assert missing == ["x"]


def test_validate_text_coverage_reports_latin_gaps() -> None:
    fake_path = Path("C:/Windows/Fonts/example.ttf")

    with patch("text_fonts.font_has_glyph", return_value=False):
        ok, missing = validate_text_coverage("Phoenix", fake_path)

    assert not ok
    assert "P" in missing


def test_recommend_font_label_for_text_prefers_covering_font(monkeypatch) -> None:
    from text_fonts import SCRIPT_UNIVERSAL, DiscoveredFont

    good = DiscoveredFont("Arial", Path("C:/Windows/Fonts/arial.ttf"), ("latin",), 100)
    bad = DiscoveredFont("Bad Font", Path("C:/Windows/Fonts/bad.ttf"), ("latin",), 50)

    def fake_discover(script: str, deep_scan: bool = False):
        assert script == SCRIPT_UNIVERSAL
        return (good, bad)

    def fake_covers(font, text: str) -> bool:
        return font is good

    monkeypatch.setattr("text_fonts.discover_fonts_for_script", fake_discover)
    monkeypatch.setattr("text_fonts._font_covers_text", fake_covers)

    assert recommend_font_label_for_text("Phoenix", script=SCRIPT_UNIVERSAL) == good.label
