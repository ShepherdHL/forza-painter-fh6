"""Tests for ui_language locale normalization and resolution."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ui_language import (  # noqa: E402
    detect_system_language_code,
    load_saved_language_code,
    normalize_locale_tag,
    resolve_initial_language_code,
    save_language_code,
)


def test_normalize_locale_tag():
    assert normalize_locale_tag("en-US") == "en"
    assert normalize_locale_tag("ja-JP") == "ja"
    assert normalize_locale_tag("ko-KR") == "ko"
    assert normalize_locale_tag("zh-CN") == "zh"
    assert normalize_locale_tag("zh-TW") == "zh-tw"
    assert normalize_locale_tag("zh-Hant") == "zh-tw"
    assert normalize_locale_tag("fr-FR") == "en"
    assert normalize_locale_tag(None) == "en"


def test_saved_preference_overrides_detection():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        save_language_code(root, "ja")
        assert load_saved_language_code(root) == "ja"
        assert resolve_initial_language_code(root) == "ja"


def test_auto_detect_when_no_saved_preference():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        code = resolve_initial_language_code(root)
        assert code in {"en", "zh", "zh-tw", "ja", "ko"}
        detected = detect_system_language_code()
        assert detected in {"en", "zh", "zh-tw", "ja", "ko"}
