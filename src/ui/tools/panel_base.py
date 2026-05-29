"""Shared helpers for isolated tool panels inside the Tools workspace."""

from __future__ import annotations

from typing import Any, Callable

from tkinter import BOTH, LEFT, RIGHT, X, Button, Frame, Label
from tkinter import ttk


class ToolPanel:
    """Base class for a single tool module (own state, no generation pipeline coupling)."""

    panel_id: str = ""
    tab_key: str = ""

    def __init__(self, app: Any) -> None:
        self.app = app

    @property
    def lang(self) -> str:
        return self.app.lang

    def _tr(self, key: str, **kwargs) -> str:
        from app import tr

        text = tr(self.lang, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    def _color(self, name: str) -> str:
        import app as app_module

        return getattr(app_module, name)

    def build(self, parent: Frame) -> None:
        raise NotImplementedError

    def on_tab_activated(self) -> None:
        pass

    def on_language_changed(self) -> None:
        pass

    def on_theme_changed(self) -> None:
        pass


def build_tool_hint(parent: Frame, app: Any, key: str) -> Label:
    hint = app._label(parent, key, anchor="w", justify="left", theme_role="hint")
    hint.pack(fill=X, pady=(0, 10))
    app._bind_wraplength(hint, parent)
    return hint


def build_resource_card(
    parent: Frame,
    app: Any,
    *,
    title_key: str,
    desc_key: str,
    url: str,
    action_key: str = "tools_open_link",
    badge_key: str | None = None,
    on_open: Callable[[], None] | None = None,
) -> Frame:
    """Recommendation / external-tool card with title, description, and launch action."""
    tokens = app.themes.tokens

    card = Frame(
        parent,
        bg=tokens.panel,
        highlightbackground=tokens.border,
        highlightthickness=1,
    )
    card.pack(fill=X, pady=(0, 8))

    body = Frame(card, bg=tokens.panel)
    body.pack(fill=X, padx=12, pady=10)

    header = Frame(body, bg=tokens.panel)
    header.pack(fill=X)
    from app import tr

    title = Label(
        header,
        text=tr(app.lang, title_key),
        anchor="w",
        bg=tokens.panel,
        fg=tokens.text,
        font=("Segoe UI", 10, "bold"),
    )
    title.pack(side=LEFT)
    app.translated.append((title, title_key, "text"))
    if badge_key:
        badge = Label(
            header,
            text=tr(app.lang, badge_key).upper(),
            anchor="e",
            bg=tokens.panel_alt,
            fg=tokens.info,
            font=("Segoe UI", 8, "bold"),
            padx=6,
            pady=2,
        )
        badge.pack(side=RIGHT)
        app.translated.append((badge, badge_key, "text"))

    desc = Label(
        body,
        text=tr(app.lang, desc_key),
        anchor="w",
        justify="left",
        wraplength=520,
        bg=tokens.panel,
        fg=tokens.muted,
        font=("Segoe UI", 9),
    )
    desc.pack(fill=X, pady=(6, 8))
    app.translated.append((desc, desc_key, "text"))
    app._bind_wraplength(desc, body)

    actions = Frame(body, bg=tokens.panel)
    actions.pack(fill=X)
    open_cmd = on_open if on_open is not None else (lambda u=url: app.root.after(0, lambda: __import__("webbrowser").open(u)))
    btn = app._button(actions, action_key, open_cmd)
    btn.pack(side=LEFT)
    return card
