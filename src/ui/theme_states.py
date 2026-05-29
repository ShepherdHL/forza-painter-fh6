"""
Semantic interactive-state styling for runtime theme switching.

Components set declarative state attributes (``_theme_selection``, etc.) and
call :func:`refresh_widget` or rely on :class:`ThemeManager` to recompute
colors from the active token set — never from cached hex literals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from tkinter import Entry, Frame, Label, TclError, ttk

if TYPE_CHECKING:
    from ui.theme_manager import ThemeManager, ThemeTokens

SelectionState = Literal["selected", "idle", "none"]
EmphasisState = Literal["accent", "warn", "muted", "text"]
IndicatorStatus = Literal["available", "failed", "hidden", "default"]


def refresh_ttk_widgets(root, manager: ThemeManager) -> None:
    """Reconfigure ttk styles and nudge notebooks/comboboxes to repaint."""
    manager.configure_ttk()
    notebooks: list[ttk.Notebook] = []
    _collect_ttk(root, ttk.Notebook, notebooks)
    for notebook in notebooks:
        try:
            tabs = notebook.tabs()
            if not tabs:
                continue
            current = notebook.select()
            if len(tabs) > 1:
                alt = tabs[1] if tabs[0] == current else tabs[0]
                notebook.select(alt)
            notebook.select(current)
            notebook.update_idletasks()
        except (TclError, Exception):
            pass


def _collect_ttk(widget, ttk_type, out: list) -> None:
    try:
        if isinstance(widget, ttk_type):
            out.append(widget)
    except Exception:
        pass
    for child in widget.winfo_children():
        _collect_ttk(child, ttk_type, out)


def apply_frame_selection(frame: Frame, state: SelectionState, manager: ThemeManager) -> None:
    frame._theme_selection = state  # type: ignore[attr-defined]
    refresh_widget(frame, manager)


def apply_label_emphasis(label: Label, emphasis: EmphasisState, manager: ThemeManager) -> None:
    label._theme_emphasis = emphasis  # type: ignore[attr-defined]
    refresh_widget(label, manager)


def apply_label_selection(
    label: Label,
    state: SelectionState,
    manager: ThemeManager,
    *,
    secondary: bool = False,
) -> None:
    label._theme_selection = state  # type: ignore[attr-defined]
    label._theme_selection_secondary = secondary  # type: ignore[attr-defined]
    refresh_widget(label, manager)


def apply_entry_validation(entry: Entry, invalid: bool, manager: ThemeManager) -> None:
    entry._theme_invalid = invalid  # type: ignore[attr-defined]
    t = manager.tokens
    try:
        entry.configure(
            highlightthickness=1 if invalid else 0,
            highlightbackground=t.validation_border if invalid else t.idle_border,
            highlightcolor=t.focus_ring,
        )
    except TclError:
        pass


def apply_update_indicator(label: Label, status: IndicatorStatus, manager: ThemeManager, *, text: str = "") -> None:
    label._theme_indicator_status = status  # type: ignore[attr-defined]
    t = manager.tokens
    try:
        label.configure(text=text, bg=t.panel)
        if status == "available":
            label.configure(fg=t.indicator_attention)
        elif status == "failed":
            label.configure(fg=t.indicator_alert)
        elif status == "hidden":
            label.configure(fg=t.muted)
        else:
            label.configure(fg=t.muted)
    except TclError:
        pass


def refresh_widget(widget: Any, manager: ThemeManager) -> None:
    manager.apply_widget(widget)


def refresh_app_interactive_ui(app: Any, manager: ThemeManager) -> None:
    """Recompute all state-driven UI that may bypass the generic widget walker."""
    if hasattr(app, "_update_compare_column_headers"):
        app._update_compare_column_headers()
    if hasattr(app, "_highlight_preview_filter_cards"):
        app._highlight_preview_filter_cards()
    if hasattr(app, "_update_eco_preset_warning"):
        app._update_eco_preset_warning()
    if hasattr(app, "_refresh_update_indicator_theme"):
        app._refresh_update_indicator_theme()
    if hasattr(app, "_refresh_layer_count_entry_theme"):
        app._refresh_layer_count_entry_theme()
    if hasattr(app, "_paint_tab_strip"):
        app._paint_tab_strip()
    if hasattr(app, "text_vinyl"):
        app.text_vinyl.on_theme_changed()
    if hasattr(app, "tools_workspace"):
        app.tools_workspace.on_theme_changed()
    if hasattr(app, "hub_bar"):
        app.hub_bar.apply_theme(manager)
