from __future__ import annotations

LANGUAGES = {
    "English": "en",
    "中文": "zh",
    "中文 (繁體)": "zh-tw",
    "한국어": "ko",
}


def tr(text_map: dict, lang: str, key: str) -> str:
    if lang == "zh-tw":
        return (
            text_map.get("zh-tw", {}).get(key)
            or text_map.get("zh", {}).get(key)
            or text_map.get("en", {}).get(key, key)
        )
    return text_map.get(lang, {}).get(key, text_map.get("en", {}).get(key, key))


def eta_suffix(lang: str) -> str:
    return {"zh": "剩余", "zh-tw": "剩餘", "ko": "남음"}.get(lang, "left")
