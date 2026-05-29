"""In-app safety guide viewer with language selection (avoids opening .md in an editor)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from tkinter import BOTH, END, Button, Frame, Label, Text, Toplevel, X, LEFT, RIGHT, ttk

from app_paths import RESOURCE_ROOT, ROOT
from ui.dialog_theme import (
    resolve_tokens,
    style_body_text,
    style_dialog_button,
    style_frame,
    style_heading_label,
    style_toplevel,
)

TranslateFn = Callable[[str, str], str]

SAFETY_FILES = {
    "en": "SAFETY.md",
    "zh": "SAFETY.zh-CN.md",
    "ja": "SAFETY.ja.md",
    "ko": "SAFETY.ko.md",
}


def resolve_safety_path(locale: str) -> Optional[Path]:
    name = SAFETY_FILES.get(locale) or SAFETY_FILES["en"]
    for base in (ROOT, RESOURCE_ROOT):
        candidate = Path(base) / "docs" / name
        if candidate.is_file():
            return candidate
    if locale != "en":
        return resolve_safety_path("en")
    return None


def load_safety_text(locale: str) -> str:
    path = resolve_safety_path(locale)
    if path is None:
        return "Safety guide file was not found."
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"Could not read safety guide: {exc}"


def _locale_from_app_lang(app_lang: str) -> str:
    lang = (app_lang or "en").lower()
    if lang.startswith("zh"):
        return "zh"
    if lang == "ja":
        return "ja"
    if lang == "ko":
        return "ko"
    return "en"


def _pick_language_dialog(root, tr: TranslateFn, app_lang: str) -> Optional[str]:
    tokens = resolve_tokens(root)
    dialog = Toplevel(root)
    dialog.title(tr(app_lang, "safety_pick_language_title"))
    dialog.transient(root)
    dialog.grab_set()
    style_toplevel(dialog, tokens)

    body = Frame(dialog, bg=tokens.dialog_bg, padx=16, pady=12)
    body.pack(fill=BOTH, expand=True)
    style_frame(body, tokens)

    prompt = Label(
        body,
        text=tr(app_lang, "safety_pick_language_prompt"),
        anchor="w",
        justify="left",
        font=("Segoe UI", 10),
        wraplength=420,
    )
    style_heading_label(prompt, tokens, font=("Segoe UI", 10))
    prompt.pack(fill=X, pady=(0, 10))

    choice = {"value": _locale_from_app_lang(app_lang)}

    def set_locale(code: str) -> None:
        choice["value"] = code
        dialog.destroy()

    row = Frame(body, bg=tokens.dialog_bg)
    row.pack(fill=X)
    style_frame(row, tokens)
    for code, key in (("en", "safety_lang_en"), ("zh", "safety_lang_zh"), ("ja", "safety_lang_ja"), ("ko", "safety_lang_ko")):
        btn = Button(row, text=tr(app_lang, key), command=lambda c=code: set_locale(c))
        style_dialog_button(btn, tokens)
        btn.pack(side=LEFT, padx=(0, 6), pady=4)

    actions = Frame(body, bg=tokens.dialog_bg)
    actions.pack(fill=X, pady=(12, 0))
    style_frame(actions, tokens)
    cancel_btn = Button(actions, text=tr(app_lang, "memory_consent_cancel"), command=dialog.destroy)
    style_dialog_button(cancel_btn, tokens)
    cancel_btn.pack(side=RIGHT)

    dialog.update_idletasks()
    try:
        dialog.minsize(460, 120)
    except Exception:
        pass
    dialog.wait_window()
    return choice["value"]


def _show_safety_text_dialog(root, tr: TranslateFn, app_lang: str, locale: str, text: str) -> None:
    tokens = resolve_tokens(root)
    title = tr(app_lang, "help_safety")
    lang_label = tr(app_lang, f"safety_lang_{locale}" if locale in SAFETY_FILES else "safety_lang_en")

    dialog = Toplevel(root)
    dialog.title(f"{title} — {lang_label}")
    dialog.transient(root)
    dialog.grab_set()
    style_toplevel(dialog, tokens)

    frame = Frame(dialog, bg=tokens.dialog_bg, padx=10, pady=10)
    frame.pack(fill=BOTH, expand=True)
    style_frame(frame, tokens)

    scroll = ttk.Scrollbar(frame, orient="vertical")
    scroll.pack(side="right", fill="y")
    widget = Text(frame, wrap="word", yscrollcommand=scroll.set, padx=8, pady=8)
    style_body_text(widget, tokens)
    widget.pack(side="left", fill=BOTH, expand=True)
    scroll.config(command=widget.yview)
    widget.insert("1.0", text)
    widget.config(state="disabled")

    actions = Frame(dialog, bg=tokens.dialog_bg)
    actions.pack(fill=X, pady=(0, 10), padx=10)
    style_frame(actions, tokens)

    def pick_other() -> None:
        dialog.destroy()
        show_safety_guide(root, tr, app_lang, ask_language=True)

    other_btn = Button(actions, text=tr(app_lang, "safety_pick_other_language"), command=pick_other)
    style_dialog_button(other_btn, tokens)
    other_btn.pack(side=LEFT)
    close_btn = Button(actions, text=tr(app_lang, "first_run_continue"), command=dialog.destroy)
    style_dialog_button(close_btn, tokens)
    close_btn.pack(side=RIGHT)

    dialog.geometry("720x520")
    dialog.minsize(480, 320)
    dialog.wait_window()


def show_safety_guide(root, tr: TranslateFn, app_lang: str, *, ask_language: bool = True) -> None:
    """Show safety guide in-app. If ask_language, prompt for locale first."""
    locale = _pick_language_dialog(root, tr, app_lang) if ask_language else _locale_from_app_lang(app_lang)
    if locale is None:
        return
    text = load_safety_text(locale)
    _show_safety_text_dialog(root, tr, app_lang, locale, text)


def show_safety_guide_for_app_lang(root, tr: TranslateFn, app_lang: str) -> None:
    """Open safety guide in the user's UI language without a picker (consent / first-run)."""
    show_safety_guide(root, tr, app_lang, ask_language=False)
