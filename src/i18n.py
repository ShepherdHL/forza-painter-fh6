from __future__ import annotations

import re

LANGUAGES = {
    "English": "en",
    "中文": "zh",
    "中文 (繁體)": "zh-tw",
    "日本語": "ja",
    "한국어": "ko",
}


def ui_font_name(lang: str) -> str:
    """Return a UI font family with reliable glyphs for the active locale."""
    if lang == "ja":
        return "Yu Gothic UI"
    if lang in ("zh", "zh-tw"):
        return "Microsoft YaHei UI"
    if lang == "ko":
        return "Malgun Gothic"
    return "Segoe UI"


_EXPERIMENTAL_TM_MARKERS = (
    "Experimental",
    "experimental",
    "实验性",
    "實驗性",
    "実験的",
    "실험적",
)


def mark_experimental_trademark(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    result = text
    for marker in _EXPERIMENTAL_TM_MARKERS:
        result = re.sub(
            rf"{re.escape(marker)}(?!\s*\(TM\)|™)",
            f"{marker}™",
            result,
        )
    return result


def tr(text_map: dict, lang: str, key: str) -> str:
    if lang == "zh-tw":
        return (
            text_map.get("zh-tw", {}).get(key)
            or text_map.get("zh", {}).get(key)
            or text_map.get("en", {}).get(key, key)
        )
    return text_map.get(lang, {}).get(key, text_map.get("en", {}).get(key, key))


def eta_suffix(lang: str) -> str:
    return {"zh": "剩余", "zh-tw": "剩餘", "ja": "残り", "ko": "남음"}.get(lang, "left")
