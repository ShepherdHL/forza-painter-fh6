"""Modal help: tutorial and acknowledgements (replaces top-level tabs)."""

from __future__ import annotations

from typing import Callable

from tkinter import BOTH, END, Button, Frame, Text, Toplevel, ttk

from acknowledgements import get_acknowledgements
from ui.dialog_theme import (
    resolve_tokens,
    style_body_text,
    style_dialog_button,
    style_frame,
    style_toplevel,
)

TranslateFn = Callable[[str, str], str]


def _scrolled_text_dialog(root, title: str, body: str, close_label: str) -> None:
    tokens = resolve_tokens(root)
    dialog = Toplevel(root)
    dialog.title(title)
    dialog.transient(root)
    dialog.grab_set()
    style_toplevel(dialog, tokens)

    frame = Frame(dialog, bg=tokens.dialog_bg, padx=10, pady=10)
    frame.pack(fill=BOTH, expand=True)
    style_frame(frame, tokens)

    scroll = ttk.Scrollbar(frame, orient="vertical")
    scroll.pack(side="right", fill="y")
    widget = Text(frame, wrap="word", yscrollcommand=scroll.set)
    style_body_text(widget, tokens)
    widget.pack(side="left", fill=BOTH, expand=True)
    scroll.config(command=widget.yview)
    widget.insert("1.0", body)
    widget.config(state="disabled")

    close_btn = Button(dialog, text=close_label, command=dialog.destroy)
    style_dialog_button(close_btn, tokens)
    close_btn.pack(pady=(0, 10))
    dialog.geometry("720x520")
    dialog.minsize(480, 320)
    dialog.wait_window()


def show_tutorial_dialog(root, tr: TranslateFn, lang: str, tutorial_text: str) -> None:
    _scrolled_text_dialog(root, tr(lang, "tutorial_tab"), tutorial_text, tr(lang, "first_run_continue"))


def show_acknowledgements_dialog(root, tr: TranslateFn, lang: str) -> None:
    _scrolled_text_dialog(
        root,
        tr(lang, "acknowledgements_tab"),
        get_acknowledgements(lang),
        tr(lang, "first_run_continue"),
    )
