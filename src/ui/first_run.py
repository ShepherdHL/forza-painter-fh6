"""First-launch welcome for trust and safety orientation."""

from __future__ import annotations

from typing import Callable

from tkinter import BOTH, Button, Frame, Label, Text, Toplevel, X, LEFT, RIGHT
from tkinter import messagebox

from ui.dialog_theme import (
    resolve_tokens,
    style_body_text,
    style_dialog_button,
    style_frame,
    style_heading_label,
    style_toplevel,
)
from ui.safety_viewer import show_safety_guide

TranslateFn = Callable[[str, str], str]


def show_first_run_welcome(root, tr: TranslateFn, lang: str) -> None:
    tokens = resolve_tokens(root)
    dialog = Toplevel(root)
    dialog.title(tr(lang, "first_run_title"))
    dialog.transient(root)
    dialog.grab_set()
    style_toplevel(dialog, tokens)

    body = Frame(dialog, bg=tokens.dialog_bg, padx=16, pady=12)
    body.pack(fill=BOTH, expand=True)
    style_frame(body, tokens)

    title = Label(
        body,
        text=tr(lang, "first_run_title"),
        anchor="w",
        justify="left",
        wraplength=520,
    )
    style_heading_label(title, tokens, font=("Segoe UI", 13, "bold"))
    title.pack(fill=X, pady=(0, 8))

    text = Text(body, height=12, width=68, wrap="word", padx=8, pady=8)
    style_body_text(text, tokens)
    text.pack(fill=BOTH, expand=True)
    text.insert("1.0", tr(lang, "first_run_body"))
    text.config(state="disabled")

    actions = Frame(body, bg=tokens.dialog_bg)
    actions.pack(fill=X, pady=(10, 0))
    style_frame(actions, tokens)

    def open_safety() -> None:
        show_safety_guide(root, tr, lang, ask_language=True)

    safety_btn = Button(actions, text=tr(lang, "memory_consent_open_safety"), command=open_safety)
    style_dialog_button(safety_btn, tokens)
    safety_btn.pack(side=LEFT)
    continue_btn = Button(actions, text=tr(lang, "first_run_continue"), command=dialog.destroy)
    style_dialog_button(continue_btn, tokens)
    continue_btn.pack(side=RIGHT)

    dialog.update_idletasks()
    try:
        dialog.minsize(560, 400)
    except Exception:
        pass
    dialog.wait_window()
