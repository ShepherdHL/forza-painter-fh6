"""File Management hub: presets, cleanup actions, and workspace overview."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    X,
    Y,
    BooleanVar,
    Frame,
    Listbox,
    StringVar,
    messagebox,
    ttk,
)
from tkinter import Checkbutton

from asset_workspace import (
    IMAGE_WORKSPACE_ROOT,
    TEXT_VINYL_WORKSPACE_ROOT,
    WorkspacePaths,
    clear_all_tier1,
    clear_all_tier2,
    clear_workspace_tier1,
    clear_workspace_tier2,
    folder_size_bytes,
    format_bytes,
    iter_workspaces,
    read_manifest,
    remove_workspace,
)
from file_management_settings import (
    PRESET_CUSTOM,
    PRESET_KEEP_ALL,
    PRESET_MINIMAL_DISK,
    PRESET_RECOMMENDED,
    FileManagementSettings,
    load_file_management_settings,
    save_file_management_settings,
)


class FileManagementWorkspace:
    """Hub tab for workspace cleanup presets and manual file actions."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self._settings = load_file_management_settings()
        self._workspace_rows: list[WorkspacePaths] = []
        self.preset_var = StringVar(value=self._settings.preset)
        self.clear_ephemeral_var = BooleanVar(value=self._settings.clear_ephemeral_on_exit)
        self.clear_session_var = BooleanVar(value=self._settings.clear_session_cache_on_exit)
        self.copy_images_var = BooleanVar(value=self._settings.copy_external_images)
        self.copy_trace_var = BooleanVar(value=self._settings.copy_trace_references)
        self.keep_filter_previews_var = BooleanVar(value=self._settings.keep_filter_previews)
        self.summary_var = StringVar(value="")
        self.workspace_list: Listbox | None = None
        self._custom_frame: Frame | None = None
        self._preset_combo: ttk.Combobox | None = None
        self._preset_label_map: dict[str, str] = {}

    def _tr(self, key: str, **kwargs) -> str:
        from app import tr

        text = tr(self.app.lang, key)
        if kwargs:
            return text.format(**kwargs)
        return text

    def build(self, tab: Frame) -> None:
        app = self.app
        scroll_area, body = app._make_vertical_scroll(tab)
        scroll_area.pack(fill=BOTH, expand=True, padx=10, pady=10)

        hint = app._label(body, "file_mgmt_tab_hint", anchor="w", justify="left", theme_role="hint")
        hint.pack(fill="x", pady=(0, 8))
        app._bind_wraplength(hint, body)

        preset_box = ttk.LabelFrame(body, text=self._tr("file_mgmt_preset_section"))
        app.translated.append((preset_box, "file_mgmt_preset_section", "text"))
        preset_box.pack(fill="x", pady=(0, 8))
        preset_hint = app._label(preset_box, "file_mgmt_preset_hint", anchor="w", justify="left", theme_role="hint")
        preset_hint.pack(fill="x", padx=10, pady=(8, 4))
        app._bind_wraplength(preset_hint, preset_box)
        preset_row = Frame(preset_box)
        preset_row.pack(fill="x", padx=10, pady=(0, 8))
        app._label(preset_row, "file_mgmt_preset_label", anchor="w").pack(side=LEFT)
        self._preset_label_map = {
            self._tr("file_mgmt_preset_recommended"): PRESET_RECOMMENDED,
            self._tr("file_mgmt_preset_keep_all"): PRESET_KEEP_ALL,
            self._tr("file_mgmt_preset_minimal_disk"): PRESET_MINIMAL_DISK,
            self._tr("file_mgmt_preset_custom"): PRESET_CUSTOM,
        }
        self._preset_combo = ttk.Combobox(
            preset_row,
            textvariable=self.preset_var,
            values=list(self._preset_label_map.keys()),
            state="readonly",
            width=34,
        )
        self._preset_combo.pack(side=LEFT, padx=(8, 0))
        self._preset_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)

        self._custom_frame = Frame(preset_box)
        self._custom_frame.pack(fill="x", padx=10, pady=(0, 10))
        self._add_toggle(self._custom_frame, "file_mgmt_clear_ephemeral", self.clear_ephemeral_var)
        self._add_toggle(self._custom_frame, "file_mgmt_clear_session", self.clear_session_var)
        self._add_toggle(self._custom_frame, "file_mgmt_copy_images", self.copy_images_var)
        self._add_toggle(self._custom_frame, "file_mgmt_copy_trace", self.copy_trace_var)
        self._add_toggle(self._custom_frame, "file_mgmt_keep_filter_previews", self.keep_filter_previews_var)

        actions_box = ttk.LabelFrame(body, text=self._tr("file_mgmt_actions_section"))
        app.translated.append((actions_box, "file_mgmt_actions_section", "text"))
        actions_box.pack(fill="x", pady=(0, 8))
        actions_hint = app._label(actions_box, "file_mgmt_actions_hint", anchor="w", justify="left", theme_role="hint")
        actions_hint.pack(fill="x", padx=10, pady=(8, 4))
        app._bind_wraplength(actions_hint, actions_box)
        row1 = Frame(actions_box)
        row1.pack(fill="x", padx=10, pady=(0, 4))
        app._button(row1, "file_mgmt_clear_temp", self.clear_temporary_cache).pack(side=LEFT)
        app._button(row1, "file_mgmt_clear_session_btn", self.clear_session_cache).pack(side=LEFT, padx=8)
        app._button(row1, "file_mgmt_clear_all_cache", self.clear_all_caches).pack(side=LEFT)
        row2 = Frame(actions_box)
        row2.pack(fill="x", padx=10, pady=(0, 10))
        app._button(row2, "file_mgmt_open_image_workspace", self.open_image_workspace_root).pack(side=LEFT)
        app._button(row2, "file_mgmt_open_text_workspace", self.open_text_workspace_root).pack(side=LEFT, padx=8)
        app._button(row2, "file_mgmt_remove_workspace", self.remove_selected_workspace).pack(side=RIGHT)

        overview_box = ttk.LabelFrame(body, text=self._tr("file_mgmt_overview_section"))
        app.translated.append((overview_box, "file_mgmt_overview_section", "text"))
        overview_box.pack(fill=BOTH, expand=True, pady=(0, 8))
        overview_hint = app._label(
            overview_box, "file_mgmt_overview_hint", anchor="w", justify="left", theme_role="hint"
        )
        overview_hint.pack(fill="x", padx=10, pady=(8, 4))
        app._bind_wraplength(overview_hint, overview_box)
        list_row = Frame(overview_box)
        list_row.pack(fill=BOTH, expand=True, padx=10, pady=(0, 4))
        self.workspace_list = Listbox(list_row, height=8)
        self.workspace_list.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_row, orient="vertical", command=self.workspace_list.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.workspace_list.configure(yscrollcommand=scrollbar.set)
        summary = app._label(overview_box, "file_mgmt_summary_placeholder", anchor="w", theme_role="muted")
        summary.config(textvariable=self.summary_var)
        summary.pack(fill="x", padx=10, pady=(0, 10))

        self._sync_preset_combo()
        self._refresh_custom_visibility()
        self.refresh_overview()

    def _add_toggle(self, parent: Frame, key: str, variable: BooleanVar) -> None:
        toggle = Checkbutton(
            parent,
            text=self._tr(key),
            variable=variable,
            command=self._on_custom_toggle,
            anchor="w",
            justify="left",
        )
        toggle.pack(fill="x", pady=2)
        self.app.translated.append((toggle, key, "text"))

    def _preset_display(self, preset_id: str) -> str:
        mapping = {
            PRESET_RECOMMENDED: "file_mgmt_preset_recommended",
            PRESET_KEEP_ALL: "file_mgmt_preset_keep_all",
            PRESET_MINIMAL_DISK: "file_mgmt_preset_minimal_disk",
            PRESET_CUSTOM: "file_mgmt_preset_custom",
        }
        return self._tr(mapping.get(preset_id, "file_mgmt_preset_custom"))

    def _sync_preset_combo(self) -> None:
        if self._preset_combo is None:
            return
        labels = [self._tr("file_mgmt_preset_recommended"), self._tr("file_mgmt_preset_keep_all"),
                  self._tr("file_mgmt_preset_minimal_disk"), self._tr("file_mgmt_preset_custom")]
        self._preset_label_map = {
            labels[0]: PRESET_RECOMMENDED,
            labels[1]: PRESET_KEEP_ALL,
            labels[2]: PRESET_MINIMAL_DISK,
            labels[3]: PRESET_CUSTOM,
        }
        self._preset_combo["values"] = labels
        display = self._preset_display(self._settings.preset)
        if display in labels:
            self.preset_var.set(display)

    def _refresh_custom_visibility(self) -> None:
        if self._custom_frame is None:
            return
        show = self._settings.preset == PRESET_CUSTOM
        if show:
            self._custom_frame.pack(fill="x", padx=10, pady=(0, 10))
        else:
            self._custom_frame.pack_forget()

    def _collect_settings(self) -> FileManagementSettings:
        preset = PRESET_RECOMMENDED
        if self._preset_combo is not None:
            preset = self._preset_label_map.get(self.preset_var.get().strip(), PRESET_RECOMMENDED)
        return FileManagementSettings(
            preset=preset,
            clear_ephemeral_on_exit=bool(self.clear_ephemeral_var.get()),
            clear_session_cache_on_exit=bool(self.clear_session_var.get()),
            copy_external_images=bool(self.copy_images_var.get()),
            copy_trace_references=bool(self.copy_trace_var.get()),
            keep_filter_previews=bool(self.keep_filter_previews_var.get()),
        )

    def _persist_settings(self) -> None:
        self._settings = self._collect_settings()
        save_file_management_settings(self._settings)

    def settings(self) -> FileManagementSettings:
        return load_file_management_settings()

    def _on_preset_changed(self, _event=None) -> None:
        preset = self._preset_label_map.get(self.preset_var.get().strip(), PRESET_RECOMMENDED)
        self._settings.preset = preset
        if preset == PRESET_RECOMMENDED:
            self.clear_ephemeral_var.set(True)
            self.clear_session_var.set(False)
            self.copy_images_var.set(True)
            self.copy_trace_var.set(True)
            self.keep_filter_previews_var.set(False)
        elif preset == PRESET_KEEP_ALL:
            self.clear_ephemeral_var.set(False)
            self.clear_session_var.set(False)
            self.copy_images_var.set(True)
            self.copy_trace_var.set(True)
            self.keep_filter_previews_var.set(True)
        elif preset == PRESET_MINIMAL_DISK:
            self.clear_ephemeral_var.set(True)
            self.clear_session_var.set(True)
            self.copy_images_var.set(True)
            self.copy_trace_var.set(True)
            self.keep_filter_previews_var.set(False)
        self._refresh_custom_visibility()
        self._persist_settings()
        self.app.log_line(self._tr("file_mgmt_preset_applied", preset=self.preset_var.get()))

    def _on_custom_toggle(self) -> None:
        if self._settings.preset != PRESET_CUSTOM:
            self._settings.preset = PRESET_CUSTOM
            self.preset_var.set(self._preset_display(PRESET_CUSTOM))
        self._persist_settings()

    def refresh_overview(self) -> None:
        if self.workspace_list is None:
            return
        self.workspace_list.delete(0, END)
        self._workspace_rows = iter_workspaces()
        total_bytes = 0
        for paths in self._workspace_rows:
            size = folder_size_bytes(paths.root)
            total_bytes += size
            manifest = read_manifest(paths) or {}
            label = manifest.get("label") or manifest.get("source_original") or paths.workspace_id
            kind_key = "file_mgmt_kind_image" if paths.kind == "image" else "file_mgmt_kind_text"
            line = f"{self._tr(kind_key)}  {label}  ({format_bytes(size)})"
            self.workspace_list.insert(END, line)
        legacy = folder_size_bytes(IMAGE_WORKSPACE_ROOT) + folder_size_bytes(TEXT_VINYL_WORKSPACE_ROOT)
        self.summary_var.set(
            self._tr(
                "file_mgmt_summary",
                workspaces=len(self._workspace_rows),
                total=format_bytes(total_bytes or legacy),
            )
        )

    def _selected_workspace(self) -> WorkspacePaths | None:
        if self.workspace_list is None:
            return None
        selection = list(self.workspace_list.curselection())
        if not selection:
            return None
        index = selection[0]
        if index < 0 or index >= len(self._workspace_rows):
            return None
        return self._workspace_rows[index]

    def clear_temporary_cache(self) -> None:
        removed = clear_all_tier1(include_legacy=True)
        self.refresh_overview()
        self.app.log_line(self._tr("file_mgmt_cleared_temp", count=removed))

    def clear_session_cache(self) -> None:
        removed = clear_all_tier2(include_legacy=True)
        self.refresh_overview()
        self.app.log_line(self._tr("file_mgmt_cleared_session", count=removed))

    def clear_all_caches(self) -> None:
        if not messagebox.askyesno(
            self._tr("file_mgmt_confirm_clear_title"),
            self._tr("file_mgmt_confirm_clear_body"),
            parent=self.app.root,
        ):
            return
        removed = clear_all_tier1(include_legacy=True) + clear_all_tier2(include_legacy=True)
        self.refresh_overview()
        self.app.log_line(self._tr("file_mgmt_cleared_all", count=removed))

    def remove_selected_workspace(self) -> None:
        paths = self._selected_workspace()
        if paths is None:
            self.app.log_line(self._tr("file_mgmt_no_workspace_selected"))
            return
        if not messagebox.askyesno(
            self._tr("file_mgmt_confirm_remove_title"),
            self._tr("file_mgmt_confirm_remove_body", name=paths.workspace_id),
            parent=self.app.root,
        ):
            return
        if remove_workspace(paths):
            self.refresh_overview()
            self.app.log_line(self._tr("file_mgmt_removed_workspace", name=paths.workspace_id))
        else:
            self.app.log_line(self._tr("file_mgmt_remove_failed", name=paths.workspace_id))

    def clear_selected_workspace_cache(self) -> None:
        paths = self._selected_workspace()
        if paths is None:
            self.app.log_line(self._tr("file_mgmt_no_workspace_selected"))
            return
        removed = clear_workspace_tier1(paths) + clear_workspace_tier2(paths)
        self.refresh_overview()
        self.app.log_line(self._tr("file_mgmt_cleared_workspace", name=paths.workspace_id, count=removed))

    @staticmethod
    def _open_folder(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)  # type: ignore[attr-defined]

    def open_image_workspace_root(self) -> None:
        self._open_folder(IMAGE_WORKSPACE_ROOT)

    def open_text_workspace_root(self) -> None:
        self._open_folder(TEXT_VINYL_WORKSPACE_ROOT)

    def on_tab_activated(self) -> None:
        self._settings = load_file_management_settings()
        self.clear_ephemeral_var.set(self._settings.clear_ephemeral_on_exit)
        self.clear_session_var.set(self._settings.clear_session_cache_on_exit)
        self.copy_images_var.set(self._settings.copy_external_images)
        self.copy_trace_var.set(self._settings.copy_trace_references)
        self.keep_filter_previews_var.set(self._settings.keep_filter_previews)
        self._sync_preset_combo()
        self._refresh_custom_visibility()
        self.refresh_overview()

    def on_language_changed(self) -> None:
        self._sync_preset_combo()

    def on_theme_changed(self) -> None:
        pass
