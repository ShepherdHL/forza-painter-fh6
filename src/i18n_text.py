from __future__ import annotations

TEXT_PATCHES = {
    "zh-tw": {
        "title": None,  # filled at runtime from existing app title
        "subtitle": "將圖像轉換為 .JSON 檔案，並匯入 Forza Horizon 貼紙編輯器。",
        "header_kicker": "Forza Painter - 貼紙匯入/匯出套件",
        "header_build_prefix": "建置版本 - {version}；",
        "header_build_suffix": "{date}",
        "language": "語言",
        "layer_count": "模板圖層數",
        "layer_count_required": "請填寫模板圖層數。輸入遊戲中顯示的精確圖層數。",
        "step_template": "第 2 步 - 模板",
        "step_template_hint": "填寫遊戲裡目前模板顯示的真實圖層數。",
        "import_json": "匯入 JSON",
        "ready": "就緒",
        "running": "執行中",
        "done": "完成",
        "failed": "失敗",
        "stopped": "已停止",
        "locating": "正在安全定位 FH6 圖層表…請保持 Vinyl Group Editor 開啟，勿切換選單。",
        "located": "已定位目前 FH6 圖層表。",
    }
}


def apply_text_patches(text_map: dict, *, app_title_text: str) -> dict:
    out = {lang: dict(values) for lang, values in text_map.items()}
    for lang, patch in TEXT_PATCHES.items():
        target = out.setdefault(lang, {})
        for key, value in patch.items():
            if key == "title" and value is None:
                target[key] = app_title_text
            else:
                target[key] = value
    return out
