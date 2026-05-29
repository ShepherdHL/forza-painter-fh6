"""Self-contained Text vinyl tab: UI, state, previews, and generation workers."""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Any

from tkinter import BOTH, END, HORIZONTAL, LEFT, RIGHT, X, Frame, Label, Listbox, PhotoImage, StringVar, filedialog, ttk
from tkinter import Checkbutton, Entry

from app_paths import ROOT
from asset_workspace import TEXT_VINYL_WORKSPACE_ROOT, text_vinyl_workspace, write_manifest, workspace_source_file
from mandarin_chars import text_contains_hangul
from text_char_libraries import (
    LIBRARY_HANGUL,
    LIBRARY_HANZI,
    LIBRARY_HIRAGANA,
    LIBRARY_KANJI,
    LIBRARY_KATAKANA,
    LIBRARY_LATIN,
)
from text_fonts import (
    SCRIPT_CHINESE,
    SCRIPT_JAPANESE,
    SCRIPT_KOREAN,
    SCRIPT_UNIVERSAL,
    TEXT_SCRIPT_IDS,
    coverage_message_key,
    discover_fonts_for_script,
    filter_font_labels,
    format_missing_chars,
    recommend_font_label_for_text,
    validate_text_coverage,
)
from text_geometry import (
    build_geometry_from_text,
    build_geometry_from_text_image,
    estimate_layer_count,
    normalize_text_shape_mode,
    TEXT_SHAPE_MODES,
    write_geometry_json,
)
from ui.char_grid_picker import CharGridPicker
from ui.color_values_editor import ColorValuesEditor

_JAPANESE_CHAR_LIBRARIES = (
    (LIBRARY_HIRAGANA, "text_char_library_hiragana"),
    (LIBRARY_KATAKANA, "text_char_library_katakana"),
    (LIBRARY_KANJI, "text_char_library_kanji"),
)


class TextVinylWorkspace:
    """Text vinyl tool module hosted by App (shared queue, theme, import bridge)."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.json_files: list[Path] = []
        self._reference_preview_path: Path | None = None
        self._json_preview_path: Path | None = None
        self._reference_preview_job = None
        self._json_preview_job = None
        self._coverage_job = None
        self.text_panels = {
            script: {
                "input": StringVar(),
                "font_choice": StringVar(),
                "font_path": StringVar(),
                "font_search": StringVar(),
                "discovered": (),
                "font_by_label": {},
                "widgets": {},
            }
            for script in TEXT_SCRIPT_IDS
        }
        self.text_font_size = StringVar(value="120")
        self.text_cell_size = StringVar(value="4")
        self.text_shape_mode = StringVar(value="rectangles")
        self.text_image_path = StringVar()
        self._color_editor: ColorValuesEditor | None = None
        self.text_invert = StringVar(value="0")
        self.text_script_notebook: ttk.Notebook | None = None
        self.text_json_list: Listbox | None = None
        self.text_reference_preview_label: Label | None = None
        self.text_json_preview_label: Label | None = None
        self.text_shape_combo: ttk.Combobox | None = None
        self.text_template_hint_label: Label | None = None
        self.text_coverage_label: Label | None = None

    @property
    def lang(self) -> str:
        return self.app.lang

    @property
    def root(self):
        return self.app.root

    @property
    def closed(self) -> bool:
        return self.app.closed

    @property
    def queue(self):
        return self.app.queue

    def _tr(self, key: str) -> str:
        from app import tr

        return tr(self.lang, key)

    def _color(self, name: str) -> str:
        import app as app_module

        return getattr(app_module, name)

    def _preview_renderers(self):
        from app import render_geometry_json, render_source_image

        return render_source_image, render_geometry_json

    def build(self, tab: Frame) -> None:
        app = self.app
        paned = app._create_paned(tab, orient=HORIZONTAL, layout_key="text_horizontal", padx=10, pady=10)
        left_outer = Frame(paned)
        right = Frame(paned)
        paned.add(left_outer, weight=3)
        paned.add(right, weight=2)

        scroll_area, body = app._make_vertical_scroll(left_outer)
        scroll_area.pack(fill=BOTH, expand=True, padx=0, pady=10)
        scroll_options_hint = app._label(
            body, "text_scroll_options_hint", anchor="w", justify="left", theme_role="hint"
        )
        scroll_options_hint.pack(fill="x", pady=(0, 8))
        app._bind_wraplength(scroll_options_hint, body)
        tab_hint = app._label(body, "text_tab_hint", anchor="w", justify="left", theme_role="hint")
        tab_hint.pack(fill="x", pady=(0, 8))
        app._bind_wraplength(tab_hint, body)

        self.text_script_notebook = ttk.Notebook(body, style="Script.TNotebook")
        self.text_script_notebook.pack(fill=BOTH, expand=True, pady=(0, 8))
        self.text_script_notebook.bind("<<NotebookTabChanged>>", lambda _event: self._on_script_tab_changed())

        for script in TEXT_SCRIPT_IDS:
            panel_frame = Frame(self.text_script_notebook)
            self.text_script_notebook.add(panel_frame, text=self._tr(self._script_tab_key(script)))
            self._build_script_panel(panel_frame, script)

        self._build_options_panel(body)

        outputs_box = ttk.LabelFrame(body, text=self._tr("text_outputs"))
        app.translated.append((outputs_box, "text_outputs", "text"))
        outputs_box.pack(fill="x", pady=(0, 8))
        outputs_hint = app._label(outputs_box, "text_outputs_hint", anchor="w", justify="left", theme_role="hint")
        outputs_hint.pack(fill="x", padx=10, pady=(8, 4))
        app._bind_wraplength(outputs_hint, outputs_box)
        outputs_row = Frame(outputs_box)
        outputs_row.pack(fill="x", padx=10, pady=(0, 4))
        app._button(outputs_row, "text_add_json", self.add_json).pack(side=LEFT)
        app._button(outputs_row, "text_remove_json", self.remove_selected_json).pack(side=LEFT, padx=8)
        app._button(outputs_row, "text_send_to_import", self.send_to_import).pack(side=RIGHT)
        app._button(outputs_row, "text_open_vinyl_folder", self.open_output_folder).pack(side=RIGHT, padx=(0, 8))
        list_body = Frame(outputs_box)
        list_body.pack(fill="x", padx=10, pady=(0, 10))
        self.text_json_list = Listbox(list_body, height=5)
        self.text_json_list.pack(fill="x", expand=True)
        self.text_json_list.bind("<<ListboxSelect>>", self._preview_selected_json)

        ref_box = ttk.LabelFrame(right, text=self._tr("text_reference_image"))
        app.translated.append((ref_box, "text_reference_image", "text"))
        ref_box.pack(fill=BOTH, expand=True, pady=(0, 8))
        ref_row = Frame(ref_box)
        ref_row.pack(fill="x", padx=10, pady=8)
        Entry(ref_row, textvariable=self.text_image_path).pack(side=LEFT, fill="x", expand=True)
        app._button(ref_row, "text_browse_image", self.browse_reference_image).pack(side=LEFT, padx=8)
        ref_actions = Frame(ref_box)
        ref_actions.pack(fill="x", padx=10, pady=(0, 6))
        invert_toggle = Checkbutton(
            ref_actions,
            text=self._tr("text_invert"),
            variable=self.text_invert,
            onvalue="1",
            offvalue="0",
        )
        invert_toggle.pack(side=LEFT)
        app.translated.append((invert_toggle, "text_invert", "text"))
        app._button(ref_actions, "text_trace_image", self.start_trace).pack(side=LEFT)
        app._label(ref_box, "text_reference_preview", anchor="w", font=("Segoe UI", 10, "bold")).pack(fill="x", padx=10)
        preview_t = app.themes.tokens
        self.text_reference_preview_label = Label(
            ref_box,
            text=self._tr("preview_hint"),
            bg=preview_t.preview_bg,
            fg=preview_t.preview_fg,
        )
        self.text_reference_preview_label.pack(fill=BOTH, expand=True, padx=10, pady=(4, 10))
        self.text_reference_preview_label.bind("<Configure>", lambda _e: self._schedule_reference_preview_refresh())

        json_box = ttk.LabelFrame(right, text=self._tr("text_json_preview"))
        app.translated.append((json_box, "text_json_preview", "text"))
        json_box.pack(fill=BOTH, expand=True)
        self.text_json_preview_label = Label(
            json_box,
            text=self._tr("preview_hint"),
            bg=preview_t.preview_bg,
            fg=preview_t.preview_fg,
        )
        self.text_json_preview_label.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.text_json_preview_label.bind("<Configure>", lambda _e: self._schedule_json_preview_refresh())

        self.text_image_path.trace_add("write", lambda *_args: self._schedule_reference_preview_refresh())
        self._on_script_tab_changed()

    def _build_options_panel(self, parent: Frame) -> None:
        app = self.app
        shared = ttk.LabelFrame(parent, text=self._tr("text_options"))
        app.translated.append((shared, "text_options", "text"))
        shared.pack(fill="x", pady=(0, 8))
        opts = Frame(shared)
        opts.pack(fill="x", padx=10, pady=8)
        app._label(opts, "text_font_size").grid(row=0, column=0, sticky="w", padx=(0, 8))
        Entry(opts, textvariable=self.text_font_size, width=8).grid(row=0, column=1, sticky="w")
        app._label(opts, "text_cell_size").grid(row=0, column=2, sticky="w", padx=(16, 8))
        Entry(opts, textvariable=self.text_cell_size, width=8).grid(row=0, column=3, sticky="w")
        app._label(opts, "text_shape_mode").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        self.text_shape_combo = ttk.Combobox(
            opts,
            textvariable=self.text_shape_mode,
            width=18,
            state="readonly",
        )
        self._shape_mode_label_to_mode: dict[str, str] = {}
        self._shape_mode_mode_to_label: dict[str, str] = {}
        self._refresh_shape_mode_combo()
        self.text_shape_combo.grid(row=1, column=1, columnspan=3, sticky="w", pady=(6, 0))
        self.text_shape_combo.bind("<<ComboboxSelected>>", lambda _event: self.update_shape_hint())
        self.text_template_hint_label = app._label(opts, "text_template_hint", anchor="w", theme_role="info")
        self.text_template_hint_label.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        app._bind_wraplength(self.text_template_hint_label, opts, padding=8)
        text_shape_hint = app._label(opts, "text_shape_mode_hint", anchor="w", theme_role="muted")
        text_shape_hint.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(4, 0))
        app._bind_wraplength(text_shape_hint, opts, padding=8)
        color_section = Frame(opts)
        color_section.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        app._label(color_section, "text_color", anchor="w").pack(anchor="w")
        self._color_editor = ColorValuesEditor(color_section, app, include_alpha=True, editable=True)
        self._color_editor.frame.pack(fill=X, pady=(4, 0))
        text_color_hint = app._label(color_section, "text_color_hint", anchor="w", theme_role="muted")
        text_color_hint.pack(fill=X, pady=(4, 0))
        app._bind_wraplength(text_color_hint, color_section, padding=8)
        app._label(opts, "text_cell_hint", anchor="w", theme_role="muted").grid(
            row=5, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )
        self.text_coverage_label = app._label(opts, "text_coverage_ok", anchor="w", theme_role="text", justify="left")
        self.text_coverage_label.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        opts.columnconfigure(0, weight=1)
        app._bind_wraplength(self.text_coverage_label, opts, padding=8)
        self.update_shape_hint()

        actions = Frame(shared)
        actions.pack(fill="x", padx=10, pady=(0, 10))
        app._button(actions, "text_font_refresh", self.refresh_fonts).pack(side=LEFT)
        app._button(actions, "text_generate_typed", self.start_generate_typed).pack(side=LEFT, padx=8)

    def _build_script_panel(self, parent: Frame, script: str) -> None:
        app = self.app
        panel = self._panel(script)
        widgets = panel["widgets"]

        hint = app._label(parent, self._script_hint_key(script), anchor="w", justify="left", theme_role="muted")
        hint.pack(fill="x", padx=10, pady=(10, 6))
        app._bind_wraplength(hint, parent, padding=20)
        widgets["hint"] = hint

        typed = ttk.LabelFrame(parent, text=self._tr("text_input"))
        typed.pack(fill="x", padx=10, pady=(0, 8))
        Entry(typed, textvariable=panel["input"]).pack(fill="x", padx=10, pady=8)
        panel["input"].trace_add("write", lambda *_args, s=script: self._on_input_changed(s))

        font_box = Frame(typed)
        font_box.pack(fill="x", padx=10, pady=(0, 6))
        font_box.columnconfigure(1, weight=1)
        app._label(font_box, "text_font_search").grid(row=0, column=0, sticky="w")
        font_search = Entry(font_box, textvariable=panel["font_search"], width=28)
        font_search.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        font_search.bind("<KeyRelease>", lambda _event, s=script: self._on_font_search_changed(s))

        app._label(font_box, "text_font").grid(row=1, column=0, sticky="w", pady=(6, 0))
        font_combo = ttk.Combobox(font_box, textvariable=panel["font_choice"], state="readonly")
        font_combo.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))
        font_combo.bind("<<ComboboxSelected>>", lambda _event, s=script: self._on_font_selected(s))
        widgets["font_combo"] = font_combo

        font_actions = Frame(typed)
        font_actions.pack(fill="x", padx=10, pady=(0, 10))
        app._button(font_actions, "text_font_browse", lambda s=script: self.browse_font(s)).pack(side=LEFT)

        widgets["char_pickers"] = []
        if script == SCRIPT_UNIVERSAL:
            self._build_char_library(parent, script, LIBRARY_LATIN, "text_char_library_latin")
        elif script == SCRIPT_JAPANESE:
            kana_notebook = ttk.Notebook(parent, style="Script.TNotebook")
            kana_notebook.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
            widgets["kana_notebook"] = kana_notebook
            for library_id, label_key in _JAPANESE_CHAR_LIBRARIES:
                tab_frame = Frame(kana_notebook)
                kana_notebook.add(tab_frame, text=self._tr(label_key))
                self._build_char_library(
                    tab_frame,
                    script,
                    library_id,
                    label_key,
                    framed=False,
                )
        elif script == SCRIPT_KOREAN:
            self._build_char_library(parent, script, LIBRARY_HANGUL, "text_char_library_hangul")
        elif script == SCRIPT_CHINESE:
            self._build_char_library(parent, script, LIBRARY_HANZI, "text_char_library_hanzi")

    def _build_char_library(
        self,
        parent: Frame,
        script: str,
        library_id: str,
        label_key: str,
        *,
        framed: bool = True,
    ) -> CharGridPicker:
        picker = CharGridPicker(
            parent,
            self.app,
            library_id,
            label_key=label_key,
            on_insert=lambda char, s=script: self._insert_char(s, char),
            framed=framed,
        )
        picker.frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        self._panel(script)["widgets"]["char_pickers"].append(picker)
        return picker

    def _insert_char(self, script: str, char: str) -> None:
        panel = self._panel(script)
        panel["input"].set(panel["input"].get() + char)
        if self.text_script_notebook is not None:
            try:
                self.text_script_notebook.select(TEXT_SCRIPT_IDS.index(script))
            except ValueError:
                pass
        self._schedule_coverage_check()

    def refresh_char_pickers(self) -> None:
        for script in TEXT_SCRIPT_IDS:
            for picker in self._panel(script)["widgets"].get("char_pickers", []):
                picker.refresh()

    def on_tab_activated(self) -> None:
        self._schedule_reference_preview_refresh()
        self._schedule_json_preview_refresh()

    def on_language_changed(self) -> None:
        if self.text_script_notebook is not None:
            for index, script in enumerate(TEXT_SCRIPT_IDS):
                self.text_script_notebook.tab(index, text=self._tr(self._script_tab_key(script)))
            for script in TEXT_SCRIPT_IDS:
                hint = self._panel(script)["widgets"].get("hint")
                if hint is not None:
                    hint.config(text=self._tr(self._script_hint_key(script)))
        self.update_shape_hint()
        self.update_coverage_status()
        self._refresh_shape_mode_combo()
        for script in TEXT_SCRIPT_IDS:
            widgets = self._panel(script)["widgets"]
            kana_notebook = widgets.get("kana_notebook")
            if kana_notebook is not None:
                for index, (_library_id, label_key) in enumerate(_JAPANESE_CHAR_LIBRARIES):
                    try:
                        kana_notebook.tab(index, text=self._tr(label_key))
                    except Exception:
                        pass
            for picker in widgets.get("char_pickers", []):
                picker.on_language_changed()

    def update_theme_hints(self) -> None:
        self.update_shape_hint()
        self.update_coverage_status()

    def _preview_colors(self) -> tuple[str, str]:
        t = self.app.themes.tokens
        return t.preview_bg, t.preview_fg

    def on_theme_changed(self) -> None:
        self.update_theme_hints()
        self.refresh_char_pickers()
        if self._reference_preview_path is not None:
            self.set_reference_preview(self._reference_preview_path)
        if getattr(self, "_json_preview_path", None) is not None:
            self.set_json_preview(self._json_preview_path)

    @staticmethod
    def _script_tab_key(script: str) -> str:
        return f"text_script_{script}"

    @staticmethod
    def _script_hint_key(script: str) -> str:
        return f"text_script_hint_{script}"

    def active_script(self) -> str:
        if self.text_script_notebook is None:
            return SCRIPT_CHINESE
        index = self.text_script_notebook.index(self.text_script_notebook.select())
        return TEXT_SCRIPT_IDS[index]

    def _panel(self, script: str | None = None) -> dict:
        return self.text_panels[script or self.active_script()]

    def _resolve_font_path(self, script: str | None = None) -> Path:
        script = script or self.active_script()
        panel = self._panel(script)
        browse = panel["font_path"].get().strip()
        if browse:
            path = Path(browse)
            if path.exists():
                return path.resolve()
            raise FileNotFoundError(f"Font not found: {path}")

        selection = panel["font_choice"].get().strip()
        if selection in panel["font_by_label"]:
            return panel["font_by_label"][selection]

        if selection:
            path = Path(selection)
            if path.exists():
                return path.resolve()

        discovered = panel["discovered"]
        if discovered:
            return discovered[0].path

        from text_fonts import find_font_for_text

        return find_font_for_text(panel["input"].get(), script=script)

    def refresh_fonts(self) -> None:
        quick = {
            script: tuple(
                font for font in discover_fonts_for_script(script, deep_scan=False) if font.path.exists()
            )
            for script in TEXT_SCRIPT_IDS
        }
        if any(quick.values()):
            self.apply_fonts_by_script(quick)
        self.app.log_line(self._tr("text_log_scanning_fonts"))
        threading.Thread(target=self._refresh_fonts_worker, daemon=True).start()

    def _refresh_fonts_worker(self) -> None:
        try:
            fonts_by_script = {
                script: tuple(
                    font for font in discover_fonts_for_script(script, deep_scan=True) if font.path.exists()
                )
                for script in TEXT_SCRIPT_IDS
            }
            self.queue.put(("text_fonts_ready", fonts_by_script))
        except Exception as exc:
            self.queue.put(("log", self._tr("text_log_font_scan_failed").format(error=exc)))

    def _refresh_script_font_combo(self, script: str) -> None:
        panel = self._panel(script)
        widgets = panel["widgets"]
        combo = widgets.get("font_combo")
        if combo is None:
            return

        filtered = filter_font_labels(panel["discovered"], panel["font_search"].get())
        panel["font_by_label"] = {font.label: font.path for font in filtered}
        labels = [font.label for font in filtered]
        combo["values"] = labels

        current = panel["font_choice"].get().strip()
        browse = panel["font_path"].get().strip()
        if browse:
            return
        if labels and current not in labels:
            panel["font_choice"].set(labels[0])
        elif not labels:
            panel["font_choice"].set("")

    def apply_fonts_by_script(self, fonts_by_script: dict) -> None:
        total = 0
        for script in TEXT_SCRIPT_IDS:
            fonts = tuple(fonts_by_script.get(script, ()))
            panel = self._panel(script)
            panel["discovered"] = fonts
            self._refresh_script_font_combo(script)
            total += len(fonts)
        if total:
            self.app.log_line(
                self._tr("text_log_fonts_loaded").format(
                    latin=len(fonts_by_script.get("universal", ())),
                    japanese=len(fonts_by_script.get("japanese", ())),
                    korean=len(fonts_by_script.get("korean", ())),
                    chinese=len(fonts_by_script.get("chinese", ())),
                )
            )
        else:
            self.app.log_line(self._tr("text_log_no_fonts"))
        self._schedule_coverage_check()

    def browse_font(self, script: str | None = None) -> None:
        script = script or self.active_script()
        panel = self._panel(script)
        path = filedialog.askopenfilename(
            title=self._tr("text_dialog_select_font"),
            filetypes=[("Fonts", "*.ttf;*.ttc;*.otf"), ("All files", "*.*")],
        )
        if not path:
            return
        panel["font_path"].set(path)
        panel["font_choice"].set(Path(path).name)
        self._schedule_coverage_check()

    def _on_font_selected(self, script: str | None = None) -> None:
        panel = self._panel(script)
        panel["font_path"].set("")
        self._schedule_coverage_check()

    def _on_font_search_changed(self, script: str) -> None:
        self._refresh_script_font_combo(script)

    def _on_input_changed(self, script: str) -> None:
        self._schedule_coverage_check()

    def _on_script_tab_changed(self) -> None:
        self._schedule_coverage_check()

    def _resolve_shape_mode(self) -> str:
        value = self.text_shape_mode.get().strip()
        if value in self._shape_mode_label_to_mode:
            return self._shape_mode_label_to_mode[value]
        return normalize_text_shape_mode(value)

    def _refresh_shape_mode_combo(self) -> None:
        current_mode = normalize_text_shape_mode(self.text_shape_mode.get())
        labels: list[str] = []
        self._shape_mode_label_to_mode.clear()
        self._shape_mode_mode_to_label.clear()
        for mode in TEXT_SHAPE_MODES:
            label = self._tr(f"text_shape_{mode}")
            labels.append(label)
            self._shape_mode_label_to_mode[label] = mode
            self._shape_mode_mode_to_label[mode] = label
        if self.text_shape_combo is not None:
            self.text_shape_combo["values"] = labels
        display = self._shape_mode_mode_to_label.get(current_mode, labels[0] if labels else "")
        self.text_shape_mode.set(display)

    def _shape_template_hint(self, shape_mode: str | None = None) -> str:
        mode = normalize_text_shape_mode(shape_mode or self._resolve_shape_mode())
        if mode in ("ellipses", "circles", "triangles", "mixed"):
            return self._tr("text_template_hint_sphere")
        return self._tr("text_template_hint_rectangle")

    def update_shape_hint(self) -> None:
        if self.text_template_hint_label is None:
            return
        hint = self._shape_template_hint()
        self.text_template_hint_label.config(
            text=self._tr("text_template_hint").format(hint=hint),
            fg=self._color("COLOR_INFO"),
        )

    def _schedule_coverage_check(self) -> None:
        if self._coverage_job is not None:
            try:
                self.root.after_cancel(self._coverage_job)
            except Exception:
                pass
        self._coverage_job = self.root.after(250, self.update_coverage_status)

    def update_coverage_status(self) -> None:
        if not self.app._widget_alive(self.text_coverage_label):
            return
        script = self.active_script()
        panel = self._panel(script)
        text = panel["input"].get().strip()
        if not text:
            self.text_coverage_label.config(text="", fg=self.app.themes.fg("muted"))
            return
        try:
            font_path = self._resolve_font_path(script)
        except Exception as exc:
            self.text_coverage_label.config(text=str(exc), fg=self.app.themes.fg("error"))
            return
        ok, missing = validate_text_coverage(text, font_path)
        if ok:
            message = self._tr(coverage_message_key(text, True, missing))
            suggest = recommend_font_label_for_text(text, script=script)
            selected = panel["font_choice"].get().strip()
            if suggest and text_contains_hangul(text) and "[KR]" not in selected.upper():
                message = self._tr("text_coverage_suggest_kr").format(font=suggest)
                fg = self.app.themes.fg("hint")
            else:
                fg = self.app.themes.fg("success")
            self.text_coverage_label.config(text=message, fg=fg)
        else:
            key = coverage_message_key(text, False, missing)
            self.text_coverage_label.config(
                text=self._tr(key).format(
                    count=len(missing),
                    chars=format_missing_chars(missing),
                ),
                fg=self.app.themes.fg("error"),
            )

    def _parse_color(self) -> tuple[int, int, int, int]:
        if self._color_editor is None:
            return 255, 255, 255, 255
        try:
            return self._color_editor.get_rgba()
        except ValueError as exc:
            raise ValueError(self._tr("text_color_invalid")) from exc

    def browse_reference_image(self) -> None:
        path = filedialog.askopenfilename(
            title=self._tr("text_dialog_select_reference_image"),
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"), ("All files", "*.*")],
        )
        if path:
            self.text_image_path.set(path)
            self._schedule_reference_preview_refresh()

    def start_generate_typed(self) -> None:
        script = self.active_script()
        panel = self._panel(script)
        text = panel["input"].get().strip()
        if not text:
            self.app.log_line(self._tr("text_log_enter_text"))
            return
        try:
            font_path = self._resolve_font_path(script)
        except Exception as exc:
            self.app.log_line(f"{self._tr('text_failed')}: {exc}")
            return
        self.app.status.set(self._tr("running"))
        threading.Thread(target=self._typed_worker, args=(text, font_path), daemon=True).start()

    def start_trace(self) -> None:
        path = self.text_image_path.get().strip()
        if not path:
            self.app.log_line(self._tr("text_log_choose_trace_image"))
            return
        self.app.status.set(self._tr("running"))
        threading.Thread(target=self._trace_worker, args=(path,), daemon=True).start()

    @staticmethod
    def output_path(stem: str, *, mode: str = "typed", identity: str | None = None) -> Path:
        safe = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff-]+", "_", stem, flags=re.UNICODE).strip("_")
        if not safe:
            safe = "text_vinyl"
        identity = identity or stem or safe
        paths = text_vinyl_workspace(mode, identity).ensure()
        return paths.json_finals / f"{safe[:48]}.json"

    def finish_json(self, payload, output: Path, shape_mode: str | None = None) -> None:
        write_geometry_json(output, payload)
        layers = estimate_layer_count(payload)
        try:
            import json
            from datetime import datetime, timezone

            root = output.parent.parent
            if root.parent == TEXT_VINYL_WORKSPACE_ROOT:
                manifest_path = root / "manifest.json"
                body: dict = {}
                if manifest_path.is_file():
                    body = json.loads(manifest_path.read_text(encoding="utf-8"))
                body.setdefault("workspace_id", root.name)
                body.setdefault("kind", "text_vinyl")
                body.update(
                    {
                        "label": output.name,
                        "layers": layers,
                        "shape_mode": shape_mode or "",
                        "output": str(output),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
                manifest_path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
        if output not in self.json_files:
            self.json_files.append(output)
        self.render_json_list()
        self.set_json_preview(output)
        self.app.log_line(self._tr("text_done").format(layers=layers, path=output))
        if shape_mode:
            self.app.log_line(self._shape_template_hint(shape_mode))
        self.app.status.set(self._tr("done"))

    def render_json_list(self) -> None:
        if self.text_json_list is None:
            return
        self.text_json_list.delete(0, END)
        for path in self.json_files:
            self.text_json_list.insert(END, self.app._json_list_display(path))

    def add_json(self) -> None:
        files = filedialog.askopenfilenames(
            title=self._tr("text_dialog_add_json"),
            filetypes=[("Geometry JSON", "*.json"), ("All files", "*.*")],
        )
        if not files:
            return
        added = 0
        for raw in files:
            path = Path(raw)
            if path.suffix.lower() != ".json" or not path.exists():
                continue
            if path not in self.json_files:
                self.json_files.append(path)
                added += 1
        if added:
            self.render_json_list()
            self.set_json_preview(self.json_files[-1])
            self.text_json_list.selection_clear(0, END)
            self.text_json_list.selection_set(len(self.json_files) - 1)

    def remove_selected_json(self) -> None:
        if self.text_json_list is None:
            return
        selection = list(self.text_json_list.curselection())
        if not selection:
            return
        for index in reversed(selection):
            del self.json_files[index]
        self.render_json_list()
        if self.json_files:
            self.text_json_list.selection_set(0)
            self.set_json_preview(self.json_files[0])
        else:
            self._json_preview_path = None
            self.set_json_preview(None)

    def send_to_import(self) -> None:
        if self.text_json_list is None:
            return
        selection = list(self.text_json_list.curselection())
        paths = [self.json_files[index] for index in selection] if selection else list(self.json_files)
        if not paths:
            self.app.log_line(self._tr("text_log_no_json_to_send"))
            return
        added = 0
        for path in paths:
            if path not in self.app.json_files:
                self.app.json_files.append(path)
                added += 1
            if path not in self.app.outputs:
                self.app.outputs.append(path)
        if added:
            self.app._render_json_list()
            self.app.json_list.selection_clear(0, END)
            self.app.json_list.selection_set(len(self.app.json_files) - 1)
            self.app.show_json_preview(self.app.json_files[-1])
            self.app._update_import_layer_info(self.app.json_files[-1])
            self.app.log_line(self._tr("text_log_added_json_import").format(count=added))
        else:
            self.app.log_line(self._tr("text_log_json_already_import"))

    def open_output_folder(self) -> None:
        from asset_workspace import TEXT_VINYL_WORKSPACE_ROOT

        TEXT_VINYL_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        os.startfile(TEXT_VINYL_WORKSPACE_ROOT)  # type: ignore[attr-defined]

    def _preview_selected_json(self, _event=None) -> None:
        if self.text_json_list is None:
            return
        selection = list(self.text_json_list.curselection())
        if not selection:
            return
        self.set_json_preview(self.json_files[selection[0]])

    def _schedule_reference_preview_refresh(self) -> None:
        if self.text_reference_preview_label is None or self.closed:
            return
        if self._reference_preview_job is not None:
            try:
                self.root.after_cancel(self._reference_preview_job)
            except Exception:
                pass
        self._reference_preview_job = self.root.after(180, self._refresh_reference_preview)

    def _refresh_reference_preview(self) -> None:
        self._reference_preview_job = None
        raw = self.text_image_path.get().strip()
        path = Path(raw) if raw else None
        self.set_reference_preview(path)

    def set_reference_preview(self, path: Path | None) -> None:
        if self.text_reference_preview_label is None:
            return
        self._reference_preview_path = Path(path) if path else None
        label = self.text_reference_preview_label
        preview_bg, preview_fg = self._preview_colors()
        if path is None or not path.exists():
            label.config(image="", text=self._tr("preview_hint"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        render_source_image, _render_geometry_json = self._preview_renderers()
        data = render_source_image(path, self.app._preview_bounds(label))
        if not data:
            label.config(image="", text=self._tr("preview_unavailable"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        image = PhotoImage(data=data)
        label.config(image=image, text="", bg=preview_bg)
        label.image = image

    def _schedule_json_preview_refresh(self) -> None:
        if self.text_json_preview_label is None or self.closed:
            return
        if self._json_preview_job is not None:
            try:
                self.root.after_cancel(self._json_preview_job)
            except Exception:
                pass
        self._json_preview_job = self.root.after(180, self._refresh_json_preview)

    def _refresh_json_preview(self) -> None:
        self._json_preview_job = None
        path = self._json_preview_path
        if path is not None:
            self.set_json_preview(path)

    def set_json_preview(self, path: Path | None) -> None:
        if self.text_json_preview_label is None:
            return
        label = self.text_json_preview_label
        preview_bg, preview_fg = self._preview_colors()
        if path is None:
            self._json_preview_path = None
            label.config(image="", text=self._tr("preview_hint"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        path = Path(path)
        self._json_preview_path = path
        if not path.exists():
            label.config(image="", text=self._tr("preview_unavailable"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        _render_source_image, render_geometry_json = self._preview_renderers()
        data = render_geometry_json(path, self.app._preview_bounds(label))
        if not data:
            label.config(image="", text=self._tr("preview_unavailable"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        image = PhotoImage(data=data)
        label.config(image=image, text="", bg=preview_bg)
        label.image = image

    def _typed_worker(self, text: str, font_path: Path) -> None:
        try:
            self.queue.put(("log", self._tr("text_generating")))
            color = self._parse_color()
            font_size = int(self.text_font_size.get().strip() or "120")
            cell_size = int(self.text_cell_size.get().strip() or "4")
            shape_mode = self._resolve_shape_mode()
            payload = build_geometry_from_text(
                text,
                color=color,
                font_path=font_path,
                font_size=font_size,
                cell_size=cell_size,
                shape_mode=shape_mode,
            )
            paths = text_vinyl_workspace("typed", text).ensure()
            write_manifest(
                paths,
                {
                    "label": text[:48],
                    "mode": "typed",
                    "source_original": text[:120],
                },
            )
            output = self.output_path(text[:12], mode="typed", identity=text)
            self.queue.put(("text_json_done", (payload, output, shape_mode)))
        except Exception as exc:
            self.queue.put(("log", f"{self._tr('text_failed')}: {exc}"))
            self.queue.put(("status", self._tr("failed")))

    def _trace_worker(self, path: str) -> None:
        try:
            self.queue.put(("log", self._tr("text_generating")))
            color = self._parse_color()
            cell_size = int(self.text_cell_size.get().strip() or "4")
            shape_mode = self._resolve_shape_mode()
            source = Path(path)
            identity = str(source.resolve()) if source.exists() else path
            paths = text_vinyl_workspace("trace", identity).ensure()
            from file_management_settings import load_file_management_settings

            trace_input = source
            if source.exists() and load_file_management_settings().effective_copy_trace_references():
                import shutil

                destination = workspace_source_file(paths, source.suffix or ".png")
                try:
                    if not destination.exists() or source.stat().st_mtime > destination.stat().st_mtime:
                        shutil.copy2(source, destination)
                    trace_input = destination
                except OSError:
                    trace_input = source
            payload = build_geometry_from_text_image(
                trace_input,
                color=color,
                cell_size=cell_size,
                invert=self.text_invert.get() == "1",
                shape_mode=shape_mode,
            )
            output = self.output_path(source.stem, mode="trace", identity=identity)
            write_manifest(
                paths,
                {
                    "label": source.name,
                    "mode": "trace",
                    "source_original": identity,
                    "shape_mode": shape_mode,
                },
            )
            self.queue.put(("text_json_done", (payload, output, shape_mode)))
        except Exception as exc:
            self.queue.put(("log", f"{self._tr('text_failed')}: {exc}"))
            self.queue.put(("status", self._tr("failed")))
