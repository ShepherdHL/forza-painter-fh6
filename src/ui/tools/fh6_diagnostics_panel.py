"""FH6 memory / diagnostics utilities (migrated from the legacy tools tab layout)."""

from __future__ import annotations

from tkinter import BOTH, X, Frame

from ui.tools.panel_base import ToolPanel, build_tool_hint


class Fh6DiagnosticsToolPanel(ToolPanel):
    panel_id = "fh6_diagnostics"
    tab_key = "tools_panel_fh6"

    def build(self, parent: Frame) -> None:
        app = self.app
        scroll_area, body = app._make_vertical_scroll(parent)
        scroll_area.pack(fill=BOTH, expand=True, padx=10, pady=10)
        build_tool_hint(body, app, "tools_fh6_hint")

        form = Frame(body)
        form.pack(fill=X)
        app._field(form, "layer_count", app.layer_count, row=0)
        app._field(form, "snapshot_count", app.snapshot_count, row=1)
        app._field(form, "current_count", app.current_count, row=2)
        app._field(form, "table_address", app.inspect_table_value, row=3)
        runtime_entry = app._field(form, "runtime_folder", app.runtime_folder, row=4)
        runtime_entry.config(state="readonly")

        actions = Frame(body)
        actions.pack(fill=X, pady=8)
        tool_buttons = [
            ("diagnose", app.start_diagnose),
            ("auto_locate", app.start_auto_locate),
            ("save_snapshot", app.start_save_snapshot),
            ("compare_snapshot", app.start_compare_snapshot),
            ("inspect_table", app.start_inspect_table),
            ("open_runtime_folder", app.open_runtime_folder),
        ]
        for index, (key, command) in enumerate(tool_buttons):
            app._button(actions, key, command).grid(row=index // 3, column=index % 3, sticky="ew", padx=4, pady=4)
        for column in range(3):
            actions.columnconfigure(column, weight=1)
