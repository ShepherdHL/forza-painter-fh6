"""UI control and preference helpers for optional workspace SIGNATURE files."""

from __future__ import annotations

from tkinter import Checkbutton, Frame, StringVar

from ui.tooltip import ToolTip
from ui_preferences import load_ui_preferences, save_ui_preferences


def workspace_signature_enabled_from_prefs(prefs: dict | None = None) -> bool:
    if prefs is None:
        prefs = load_ui_preferences()
    return bool(prefs.get("write_workspace_signature", True))


def should_write_workspace_signature() -> bool:
    return workspace_signature_enabled_from_prefs()


def workspace_signature_string_var(prefs: dict | None = None) -> StringVar:
    enabled = workspace_signature_enabled_from_prefs(prefs)
    return StringVar(value="1" if enabled else "0")


def persist_workspace_signature_pref(app) -> None:
    prefs = getattr(app, "_ui_prefs", None)
    if not isinstance(prefs, dict):
        return
    variable = getattr(app, "workspace_signature_enabled", None)
    if variable is None:
        return
    prefs["write_workspace_signature"] = variable.get() == "1"
    save_ui_preferences(prefs)


def pack_workspace_signature_toggle(
    app,
    parent: Frame,
    *,
    tr,
    lang: str,
    pady: tuple[int, int] = (0, 6),
) -> Checkbutton:
    """Checkbox + hover tooltip; uses app.workspace_signature_enabled StringVar."""
    row = Frame(parent)
    row.pack(fill="x", padx=10, pady=pady)
    toggle = Checkbutton(
        row,
        text=tr(lang, "workspace_signature"),
        variable=app.workspace_signature_enabled,
        onvalue="1",
        offvalue="0",
        command=lambda: persist_workspace_signature_pref(app),
    )
    toggle.pack(anchor="w")
    app.translated.append((toggle, "workspace_signature", "text"))
    tooltip = ToolTip(toggle, tr(lang, "workspace_signature_tooltip"))
    app._workspace_signature_tooltips = getattr(app, "_workspace_signature_tooltips", [])
    app._workspace_signature_tooltips.append(tooltip)
    return toggle
