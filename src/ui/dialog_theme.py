"""Apply active theme tokens to modal Toplevel dialogs."""

from __future__ import annotations

from typing import Any

from tkinter import Button, Frame, Label, Text, TclError

from ui.theme_manager import ThemeManager, ThemeTokens


def resolve_tokens(root) -> ThemeTokens:
    try:
        master = root.winfo_toplevel()
        app = getattr(master, "_app_ref", None)
        if app is not None and hasattr(app, "themes"):
            return app.themes.tokens
    except Exception:
        pass
    from ui.theme_manager import tokens_from_palette
    from ui_themes import resolve_palette

    return tokens_from_palette(resolve_palette())


def style_toplevel(dialog, tokens: ThemeTokens | None = None) -> ThemeTokens:
    tokens = tokens or resolve_tokens(dialog)
    try:
        dialog.configure(bg=tokens.dialog_bg)
    except TclError:
        pass
    return tokens


def style_frame(frame: Frame, tokens: ThemeTokens) -> None:
    try:
        frame.configure(bg=tokens.dialog_bg)
    except TclError:
        pass


def style_heading_label(label: Label, tokens: ThemeTokens, *, font: tuple[str, ...] | None = None) -> None:
    try:
        label.configure(bg=tokens.dialog_bg, fg=tokens.dialog_text, font=font or ("Segoe UI", 13, "bold"))
    except TclError:
        pass


def style_body_text(text: Text, tokens: ThemeTokens) -> None:
    try:
        text.configure(
            bg=tokens.dialog_input,
            fg=tokens.dialog_text,
            insertbackground=tokens.dialog_text,
            selectbackground=tokens.dropdown_select_bg,
            selectforeground=tokens.dropdown_select_fg,
            relief="flat",
        )
    except TclError:
        pass


def style_dialog_button(button: Button, tokens: ThemeTokens, manager: ThemeManager | None = None) -> None:
    try:
        button.configure(
            bg=tokens.button,
            fg=tokens.button_fg,
            activebackground=tokens.button_active,
            activeforeground=tokens.button_active_fg,
            disabledforeground=tokens.muted,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=tokens.border,
            highlightcolor=tokens.focus_ring,
        )
    except TclError:
        pass
    if manager is not None:
        button._theme_managed = False  # type: ignore[attr-defined]


def apply_dialog_tree(dialog, manager: ThemeManager | None = None) -> None:
    tokens = style_toplevel(dialog, manager.tokens if manager else None)
    for child in dialog.winfo_children():
        _apply_dialog_widget(child, tokens, manager)


def _apply_dialog_widget(widget: Any, tokens: ThemeTokens, manager: ThemeManager | None) -> None:
    try:
        if isinstance(widget, Frame):
            style_frame(widget, tokens)
        elif isinstance(widget, Label):
            style_heading_label(widget, tokens, font=widget.cget("font"))
        elif isinstance(widget, Text):
            style_body_text(widget, tokens)
        elif isinstance(widget, Button):
            style_dialog_button(widget, tokens, manager)
    except TclError:
        pass
    for child in widget.winfo_children():
        _apply_dialog_widget(child, tokens, manager)
