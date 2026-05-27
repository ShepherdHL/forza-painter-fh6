"""Tools workspace container: hosts independent tool panels in a nested notebook."""

from __future__ import annotations

from typing import Any

from tkinter import BOTH, Frame, ttk

from ui.tools.background_removal_panel import BackgroundRemovalToolPanel
from ui.tools.color_picker_panel import ColorPickerToolPanel
from ui.tools.fh6_diagnostics_panel import Fh6DiagnosticsToolPanel
from ui.tools.panel_base import ToolPanel


class ToolsWorkspace:
    """Modular utility suite tab (isolated from Generate JSON / Text Vinyl pipelines)."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.panels: list[ToolPanel] = [
            ColorPickerToolPanel(app),
            BackgroundRemovalToolPanel(app),
            Fh6DiagnosticsToolPanel(app),
        ]
        self._notebook: ttk.Notebook | None = None
        self._panel_frames: dict[str, Frame] = {}

    def build(self, tab: Frame) -> None:
        app = self.app
        outer = Frame(tab)
        outer.pack(fill=BOTH, expand=True)

        scroll_area, body = app._make_vertical_scroll(outer)
        scroll_area.pack(fill=BOTH, expand=True, padx=10, pady=(10, 4))
        tab_hint = app._label(body, "tools_tab_hint", anchor="w", justify="left", theme_role="hint")
        tab_hint.pack(fill="x", pady=(0, 8))
        app._bind_wraplength(tab_hint, body)

        self._notebook = ttk.Notebook(body, style="Script.TNotebook")
        self._notebook.pack(fill=BOTH, expand=True, pady=(0, 8))
        self._notebook.bind("<<NotebookTabChanged>>", lambda _e: self._on_panel_changed())

        for panel in self.panels:
            panel_frame = Frame(self._notebook)
            self._notebook.add(panel_frame, text=self._tr(panel.tab_key))
            self._panel_frames[panel.panel_id] = panel_frame
            panel.build(panel_frame)

    def _tr(self, key: str) -> str:
        from app import tr

        return tr(self.app.lang, key)

    def _active_panel(self) -> ToolPanel | None:
        if self._notebook is None:
            return None
        try:
            index = int(self._notebook.index(self._notebook.select()))
        except Exception:
            return None
        if index < 0 or index >= len(self.panels):
            return None
        return self.panels[index]

    def _on_panel_changed(self) -> None:
        panel = self._active_panel()
        if panel is not None:
            panel.on_tab_activated()

    def on_tab_activated(self) -> None:
        panel = self._active_panel()
        if panel is not None:
            panel.on_tab_activated()

    def on_language_changed(self) -> None:
        if self._notebook is None:
            return
        for index, panel in enumerate(self.panels):
            try:
                self._notebook.tab(index, text=self._tr(panel.tab_key))
            except Exception:
                pass
            panel.on_language_changed()
