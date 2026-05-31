"""Tests for kaomoji library."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kaomoji_library import filter_kaomoji, kaomoji_library, library_total, paginate_kaomoji


def test_kaomoji_library_not_empty() -> None:
    assert library_total() >= 40


def test_filter_kaomoji_finds_shrug() -> None:
    matches = filter_kaomoji("ツ")
    assert any("ツ" in item for item in matches)


def test_paginate_kaomoji_pages() -> None:
    items = list(kaomoji_library())
    page, index, total = paginate_kaomoji(items, 0)
    assert len(page) <= 24
    assert index == 0
    assert total >= 1
