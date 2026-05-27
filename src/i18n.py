from __future__ import annotations

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
