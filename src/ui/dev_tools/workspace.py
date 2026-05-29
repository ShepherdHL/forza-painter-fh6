"""Dev Tools hub: FH6 memory diagnostics (legacy Bvzray tools tab, now its own hub)."""

from __future__ import annotations

from typing import Any

from tkinter import BOTH, Frame

from ui.tools.fh6_diagnostics_panel import Fh6DiagnosticsToolPanel


class DevToolsWorkspace:
    """Top-level Dev Tools tab content (memory snapshot, compare, table inspection)."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.panel = Fh6DiagnosticsToolPanel(app)
        self._host: Frame | None = None

    def build(self, tab: Frame) -> None:
        self._host = tab
        self._rebuild()

    def rebuild(self) -> None:
        if self._host is not None:
            self._rebuild()

    def _rebuild(self) -> None:
        tab = self._host
        if tab is None:
            return
        for child in list(tab.winfo_children()):
            child.destroy()

        app = self.app
        outer = Frame(tab)
        outer.pack(fill=BOTH, expand=True)

        scroll_area, body = app._make_vertical_scroll(outer)
        scroll_area.pack(fill=BOTH, expand=True, padx=10, pady=(10, 4))
        tab_hint = app._label(body, "dev_tools_tab_hint", anchor="w", justify="left", theme_role="hint")
        tab_hint.pack(fill="x", pady=(0, 8))
        app._bind_wraplength(tab_hint, body)

        panel_host = Frame(body)
        panel_host.pack(fill=BOTH, expand=True, pady=(0, 8))
        self.panel.build(panel_host)

        if hasattr(app, "_prune_stale_translated_widgets"):
            app._prune_stale_translated_widgets()
        if hasattr(app, "_apply_theme_recursive"):
            app._apply_theme_recursive(tab)
        if hasattr(app, "_apply_ui_fonts"):
            app._apply_ui_fonts()
        if hasattr(app, "_restore_ready_pane_layouts"):
            app.root.after(50, app._restore_ready_pane_layouts)

    def on_tab_activated(self) -> None:
        self.panel.on_tab_activated()

    def on_language_changed(self) -> None:
        self.panel.on_language_changed()
