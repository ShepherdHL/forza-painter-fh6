"""Persist and resolve UI language (manual preference + OS locale detection)."""

from __future__ import annotations

import locale
import os
from pathlib import Path

from i18n import LANGUAGES

SUPPORTED_LANGUAGE_CODES = frozenset(LANGUAGES.values())
_LANGUAGE_CODE_TO_NAME = {code: name for name, code in LANGUAGES.items()}


def language_settings_path(root: Path) -> Path:
    return root / "runtime" / "settings" / "ui_language.txt"


def load_saved_language_code(root: Path) -> str | None:
    """Return a persisted user language code, or None when unset / invalid."""
    path = language_settings_path(root)
    try:
        code = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if code in SUPPORTED_LANGUAGE_CODES:
        return code
    return None


def save_language_code(root: Path, code: str) -> None:
    """Persist explicit user language choice (manual override)."""
    if code not in SUPPORTED_LANGUAGE_CODES:
        return
    path = language_settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code + "\n", encoding="utf-8")


def language_display_name(code: str) -> str:
    return _LANGUAGE_CODE_TO_NAME.get(code, "English")


def language_code_from_display(name: str) -> str:
    return LANGUAGES.get(name, "en")


def _system_locale_tag() -> str | None:
    if os.name == "nt":
        try:
            import ctypes

            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            primary = lang_id & 0x3FF
            sublang = (lang_id >> 10) & 0x3F
            # Map common Windows LCIDs to BCP-47 tags.
            if primary == 0x11:
                return "ja-JP"
            if primary == 0x12:
                return "ko-KR"
            if primary == 0x04:
                if sublang in (0x01, 0x0F, 0x10):
                    return "zh-TW"
                return "zh-CN"
            if primary == 0x09:
                return "en-US"
        except (AttributeError, OSError):
            pass

    for getter in (locale.getlocale, locale.getdefaultlocale):
        try:
            tag = getter()[0]
        except (TypeError, ValueError, AttributeError):
            continue
        if tag:
            return tag.replace("_", "-")
    return None


def normalize_locale_tag(tag: str | None) -> str:
    """Map OS / BCP-47 tags to supported app language codes; default English."""
    if not tag:
        return "en"
    normalized = tag.strip().lower().replace("_", "-")
    if not normalized:
        return "en"
    parts = normalized.split("-")
    lang = parts[0]
    region = parts[1] if len(parts) > 1 else ""
    script = parts[1] if len(parts) > 1 and parts[1] in ("hans", "hant") else ""
    if len(parts) > 2 and parts[2] in ("hans", "hant"):
        script = parts[2]

    if lang == "en":
        return "en"
    if lang == "ja":
        return "ja"
    if lang == "ko":
        return "ko"
    if lang == "zh":
        if script == "hant" or region in ("tw", "hk", "mo", "hant"):
            return "zh-tw"
        return "zh"
    return "en"


def detect_system_language_code() -> str:
    """Detect OS UI language; return a supported code or English."""
    try:
        return normalize_locale_tag(_system_locale_tag())
    except Exception:
        return "en"


def resolve_initial_language_code(root: Path) -> str:
    """
    Startup language resolution:
    1. Saved manual preference
    2. OS locale when supported
    3. English
    """
    saved = load_saved_language_code(root)
    if saved:
        return saved
    detected = detect_system_language_code()
    if detected in SUPPORTED_LANGUAGE_CODES:
        return detected
    return "en"
