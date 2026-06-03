"""Self-contained Text vinyl tab: UI, state, previews, and generation workers."""

from __future__ import annotations

import os
import re
import threading
from pathlib import Path
from typing import Any

from tkinter import BOTH, END, HORIZONTAL, LEFT, RIGHT, X, Button, Checkbutton, Entry, Frame, Label, Listbox, PhotoImage, StringVar, filedialog, ttk

from app_paths import ROOT
from asset_workspace import TEXT_VINYL_WORKSPACE_ROOT, text_vinyl_workspace, write_manifest, workspace_source_file
from ui.workspace_signature_option import pack_workspace_signature_toggle
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
    SCRIPT_KAOMOJI,
    SCRIPT_KOREAN,
    SCRIPT_UNIVERSAL,
    TEXT_SCRIPT_IDS,
    DiscoveredFont,
    FontRecommendation,
    clear_font_discovery_cache,
    coverage_message_key,
    default_fonts_for_script,
    discover_fonts_for_script_cached,
    filter_font_labels,
    format_missing_chars,
    recommend_font_for_text,
    validate_text_coverage,
)
from pixel_art_geometry import FH6_BOUNDARY_LAYERS
from text_forza_fonts import (
    forza_font_label,
    is_forza_latin_text,
    list_forza_font_labels,
    parse_forza_font_label,
)
from text_geometry import (
    build_typecode_from_text_image,
    build_typecode_from_text_with_options,
    estimate_layer_count,
    estimate_typed_text_layers,
    normalize_text_shape_mode,
    normalize_trace_cell_size,
    template_hint_for_shape_mode,
    TEXT_SHAPE_MODES,
    write_text_design_json,
)
from text_vinyl_presets import PRESET_ORDER, get_preset
from ui.char_grid_picker import CharGridPicker
from ui.color_values_editor import ColorValuesEditor
from ui.kaomoji_picker import KaomojiPicker

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
        self._coverage_generation = 0
        self._last_font_recommendation: FontRecommendation | None = None
        self._layer_estimate_signature: tuple | None = None
        self._fonts_deep_scanned: set[str] = set()
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
        self.text_cell_size = StringVar(value="1")
        self.text_shape_mode = StringVar(value="rectangles")
        self.text_preset_id = StringVar(value="custom")
        self.text_use_forza_font = StringVar(value="0")
        self.text_forza_font_choice = StringVar(value="Forza Font 1")
        self.text_fit_layer_budget = StringVar(value="0")
        self.text_extra_shapes = StringVar(value="0")
        self.text_max_drawable_layers = StringVar(value="1800")
        self.text_layer_estimate = StringVar(value="")
        self._layer_estimate_job = None
        self._applying_preset = False
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
        self._coverage_apply_button: Button | None = None

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

        left, action_host = app._prepare_sticky_column(left_outer)
        scroll_options_hint = app._label(
            left, "text_scroll_options_hint", anchor="w", justify="left", theme_role="hint"
        )
        scroll_options_hint.pack(fill="x", pady=(0, 8))
        app._bind_wraplength(scroll_options_hint, left)
        tab_hint = app._label(left, "text_tab_hint", anchor="w", justify="left", theme_role="hint")
        tab_hint.pack(fill="x", pady=(0, 8))
        app._bind_wraplength(tab_hint, left)

        self.text_script_notebook = ttk.Notebook(left, style="Script.TNotebook")
        self.text_script_notebook.pack(fill=BOTH, expand=True, pady=(0, 8))
        self.text_script_notebook.bind("<<NotebookTabChanged>>", lambda _event: self._on_script_tab_changed())

        for script in TEXT_SCRIPT_IDS:
            panel_frame = Frame(self.text_script_notebook)
            self.text_script_notebook.add(panel_frame, text=self._tr(self._script_tab_key(script)))
            self._build_script_panel(panel_frame, script)

        self._build_options_panel(left)

        outputs_box = ttk.LabelFrame(left, text=self._tr("text_outputs"))
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

        action_box = ttk.LabelFrame(action_host, text=self._tr("text_generate_action"))
        app.translated.append((action_box, "text_generate_action", "text"))
        action_box.pack(fill="x")
        pack_workspace_signature_toggle(
            app,
            action_box,
            tr=lambda _lang, key: self._tr(key),
            lang=app.lang,
            pady=(8, 4),
        )
        action_row = Frame(action_box)
        action_row.pack(fill="x", padx=10, pady=(0, 12))
        app._button(action_row, "text_font_refresh", self.refresh_fonts).pack(side=LEFT)
        app._button(
            action_row,
            "text_generate_typed",
            self.start_generate_typed,
            font=("Segoe UI", 12, "bold"),
            height=2,
        ).pack(side=LEFT, padx=8, fill="x", expand=True)

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
        self._trace_cell_entry = Entry(opts, textvariable=self.text_cell_size, width=8)
        self._trace_cell_entry.grid(row=0, column=3, sticky="w")
        app._label(opts, "text_preset").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        self._preset_label_to_id: dict[str, str] = {}
        self._preset_id_to_label: dict[str, str] = {}
        self.text_preset_combo = ttk.Combobox(opts, state="readonly", width=22)
        self._refresh_preset_combo()
        self.text_preset_combo.grid(row=1, column=1, columnspan=3, sticky="w", pady=(6, 0))
        self.text_preset_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_preset_selected())
        app._label(opts, "text_shape_mode").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        self.text_shape_combo = ttk.Combobox(
            opts,
            textvariable=self.text_shape_mode,
            width=18,
            state="readonly",
        )
        self._shape_mode_label_to_mode: dict[str, str] = {}
        self._shape_mode_mode_to_label: dict[str, str] = {}
        self._refresh_shape_mode_combo()
        self.text_shape_combo.grid(row=2, column=1, columnspan=3, sticky="w", pady=(6, 0))
        self.text_shape_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_generation_option_changed())
        self.text_template_hint_label = app._label(opts, "text_template_hint", anchor="w", theme_role="info")
        self.text_template_hint_label.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        app._bind_wraplength(self.text_template_hint_label, opts, padding=8)
        text_shape_hint = app._label(opts, "text_shape_mode_hint", anchor="w", theme_role="muted")
        text_shape_hint.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(4, 0))
        app._bind_wraplength(text_shape_hint, opts, padding=8)

        forza_row = Frame(opts)
        forza_row.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        self._forza_font_toggle = Checkbutton(
            forza_row,
            text=self._tr("text_use_forza_font"),
            variable=self.text_use_forza_font,
            onvalue="1",
            offvalue="0",
            command=self._on_forza_font_toggle,
        )
        self._forza_font_toggle.pack(side=LEFT)
        app.translated.append((self._forza_font_toggle, "text_use_forza_font", "text"))
        app._label(forza_row, "text_forza_font").pack(side=LEFT, padx=(12, 4))
        self.text_forza_font_combo = ttk.Combobox(
            forza_row,
            textvariable=self.text_forza_font_choice,
            values=list_forza_font_labels(),
            state="readonly",
            width=14,
        )
        self.text_forza_font_combo.pack(side=LEFT)
        self.text_forza_font_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_generation_option_changed())

        budget_row = Frame(opts)
        budget_row.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        self._fit_budget_toggle = Checkbutton(
            budget_row,
            text=self._tr("text_fit_layer_budget"),
            variable=self.text_fit_layer_budget,
            onvalue="1",
            offvalue="0",
            command=self._on_generation_option_changed,
        )
        self._fit_budget_toggle.pack(side=LEFT)
        app.translated.append((self._fit_budget_toggle, "text_fit_layer_budget", "text"))
        app._label(budget_row, "text_max_drawable_layers").pack(side=LEFT, padx=(12, 4))
        Entry(budget_row, textvariable=self.text_max_drawable_layers, width=8).pack(side=LEFT)

        extra_row = Frame(opts)
        extra_row.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        self._extra_shapes_toggle = Checkbutton(
            extra_row,
            text=self._tr("text_extra_shapes"),
            variable=self.text_extra_shapes,
            onvalue="1",
            offvalue="0",
            command=self._on_extra_shapes_toggle,
        )
        self._extra_shapes_toggle.pack(side=LEFT)
        app.translated.append((self._extra_shapes_toggle, "text_extra_shapes", "text"))
        self._extra_shapes_hint = app._label(
            extra_row, "text_extra_shapes_hint", anchor="w", theme_role="muted"
        )
        self._extra_shapes_hint.pack(side=LEFT, padx=(12, 0))
        app._bind_wraplength(self._extra_shapes_hint, opts, padding=8)

        self.text_layer_estimate_label = app._label(
            opts, "text_layer_estimate_idle", anchor="w", theme_role="info", justify="left"
        )
        self.text_layer_estimate_label.grid(row=8, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        app._bind_wraplength(self.text_layer_estimate_label, opts, padding=8)

        color_section = Frame(opts)
        color_section.grid(row=9, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        app._label(color_section, "text_color", anchor="w").pack(anchor="w")
        self._color_editor = ColorValuesEditor(color_section, app, include_alpha=True, editable=True)
        self._color_editor.frame.pack(fill=X, pady=(4, 0))
        text_color_hint = app._label(color_section, "text_color_hint", anchor="w", theme_role="muted")
        text_color_hint.pack(fill=X, pady=(4, 0))
        app._bind_wraplength(text_color_hint, color_section, padding=8)
        app._label(opts, "text_cell_hint", anchor="w", theme_role="muted").grid(
            row=10, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )
        self._forza_mode_hint = app._label(opts, "text_forza_font_hint", anchor="w", theme_role="muted")
        self._forza_mode_hint.grid(row=11, column=0, columnspan=4, sticky="w", pady=(4, 0))
        app._bind_wraplength(self._forza_mode_hint, opts, padding=8)
        coverage_row = Frame(opts)
        coverage_row.grid(row=12, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        coverage_row.columnconfigure(0, weight=1)
        self.text_coverage_label = app._label(
            coverage_row, "text_coverage_ok", anchor="w", theme_role="text", justify="left"
        )
        self.text_coverage_label.grid(row=0, column=0, sticky="ew")
        self._coverage_apply_button = app._button(
            coverage_row,
            "text_apply_recommended_font",
            self.apply_recommended_font,
        )
        self._coverage_apply_button.grid(row=0, column=1, sticky="e", padx=(8, 0))
        opts.columnconfigure(0, weight=1)
        app._bind_wraplength(self.text_coverage_label, opts, padding=8)
        self.update_shape_hint()
        self._wire_generation_option_traces()
        self._update_forza_controls_state()
        self._schedule_layer_estimate()

    def _wire_generation_option_traces(self) -> None:
        for var in (
            self.text_font_size,
            self.text_cell_size,
            self.text_shape_mode,
            self.text_use_forza_font,
            self.text_forza_font_choice,
            self.text_fit_layer_budget,
            self.text_extra_shapes,
            self.text_max_drawable_layers,
        ):
            var.trace_add("write", lambda *_args: self._on_generation_option_changed())

    def _refresh_preset_combo(self) -> None:
        self._preset_label_to_id.clear()
        self._preset_id_to_label.clear()
        labels: list[str] = []
        for preset_id in PRESET_ORDER:
            label = self._tr(get_preset(preset_id).label_key)
            labels.append(label)
            self._preset_label_to_id[label] = preset_id
            self._preset_id_to_label[preset_id] = label
        if self.text_preset_combo is not None:
            self.text_preset_combo.configure(values=labels)
            current = self.text_preset_id.get()
            self.text_preset_combo.set(self._preset_id_to_label.get(current, labels[0]))

    def _on_preset_selected(self) -> None:
        if self.text_preset_combo is None:
            return
        label = self.text_preset_combo.get().strip()
        preset_id = self._preset_label_to_id.get(label, "custom")
        self._applying_preset = True
        try:
            self.text_preset_id.set(preset_id)
            preset = get_preset(preset_id)
            if preset.id != "custom":
                self.text_shape_mode.set(preset.shape_mode)
                self._refresh_shape_mode_combo()
                self.text_cell_size.set(str(preset.cell_size))
                self.text_use_forza_font.set("1" if preset.use_forza_font else "0")
                self.text_forza_font_choice.set(forza_font_label(preset.forza_font_index))
                self.text_fit_layer_budget.set("1" if preset.fit_layer_budget else "0")
                self.text_extra_shapes.set("1" if preset.extra_shapes else "0")
            self._update_forza_controls_state()
            self.update_shape_hint()
            self._schedule_layer_estimate()
        finally:
            self._applying_preset = False

    def _on_forza_font_toggle(self) -> None:
        if self.text_use_forza_font.get() == "1":
            self.text_extra_shapes.set("0")
            self.text_preset_id.set("forza_latin" if self.text_preset_id.get() == "custom" else self.text_preset_id.get())
            if self.text_preset_combo is not None:
                label = self._preset_id_to_label.get("forza_latin")
                if label:
                    self.text_preset_combo.set(label)
        self._update_forza_controls_state()
        self._on_generation_option_changed()

    def _on_extra_shapes_toggle(self) -> None:
        if self.text_extra_shapes.get() == "1":
            self.text_use_forza_font.set("0")
            if self.text_preset_id.get() == "custom" and self.text_preset_combo is not None:
                label = self._preset_id_to_label.get("smooth_cjk_extra")
                if label:
                    self.text_preset_combo.set(label)
                    self.text_preset_id.set("smooth_cjk_extra")
        self._update_forza_controls_state()
        self._on_generation_option_changed()

    def _on_generation_option_changed(self) -> None:
        if not self._applying_preset and self.text_preset_id.get() != "custom":
            if self.text_preset_combo is not None:
                self.text_preset_combo.set(self._preset_id_to_label.get("custom", ""))
            self.text_preset_id.set("custom")
        self.update_shape_hint()
        self._schedule_layer_estimate()

    def _generation_options(self) -> dict:
        try:
            max_layers = int(self.text_max_drawable_layers.get().strip() or "1800")
        except ValueError:
            max_layers = 1800
        max_layers = max(1, min(max_layers, 2996))
        use_forza = self.text_use_forza_font.get() == "1" and self.active_script() == SCRIPT_UNIVERSAL
        extra_shapes = self.text_extra_shapes.get() == "1" and not use_forza
        try:
            forza_index = parse_forza_font_label(self.text_forza_font_choice.get())
        except ValueError:
            forza_index = 1
        return {
            "font_size": int(self.text_font_size.get().strip() or "120"),
            "cell_size": normalize_trace_cell_size(self.text_cell_size.get().strip() or "1"),
            "shape_mode": self._resolve_shape_mode(),
            "use_forza_font": use_forza,
            "forza_font_index": forza_index,
            "fit_layer_budget": self.text_fit_layer_budget.get() == "1" and not use_forza,
            "max_drawable_layers": max_layers,
            "extra_shapes": extra_shapes,
        }

    def _update_forza_controls_state(self) -> None:
        universal = self.active_script() == SCRIPT_UNIVERSAL
        use_forza = self.text_use_forza_font.get() == "1"
        enabled_forza = universal and use_forza
        if hasattr(self, "text_forza_font_combo"):
            self.text_forza_font_combo.configure(state="readonly" if enabled_forza else "disabled")
        if hasattr(self, "_forza_font_toggle"):
            if not universal:
                self._forza_font_toggle.configure(state="disabled")
            else:
                self._forza_font_toggle.configure(state="normal")
        if hasattr(self, "_fit_budget_toggle"):
            self._fit_budget_toggle.configure(state="disabled" if use_forza and universal else "normal")
        if hasattr(self, "text_shape_combo"):
            if enabled_forza:
                self.text_shape_combo.configure(state="disabled")
            elif self.text_extra_shapes.get() == "1":
                self.text_shape_combo.configure(state="disabled")
            else:
                self.text_shape_combo.configure(state="readonly")
        if hasattr(self, "_trace_cell_entry"):
            self._trace_cell_entry.configure(state="disabled" if enabled_forza else "normal")
        if hasattr(self, "_extra_shapes_toggle"):
            self._extra_shapes_toggle.configure(state="disabled" if enabled_forza else "normal")
        if hasattr(self, "_forza_mode_hint"):
            key = (
                "text_forza_font_hint"
                if universal
                else "text_forza_font_universal_only"
            )
            self._forza_mode_hint.configure(text=self._tr(key))

    def _schedule_layer_estimate(self) -> None:
        if self.closed:
            return
        if self._layer_estimate_job is not None:
            try:
                self.root.after_cancel(self._layer_estimate_job)
            except Exception:
                pass
        self.text_layer_estimate.set(self._tr("text_layer_estimate_working"))
        self._layer_estimate_job = self.root.after(550, self._start_layer_estimate)

    def _start_layer_estimate(self) -> None:
        self._layer_estimate_job = None
        script = self.active_script()
        panel = self._panel(script)
        text = panel["input"].get().strip()
        if not text:
            self._layer_estimate_signature = None
            self._set_layer_estimate_message("text_layer_estimate_idle")
            return
        try:
            font_path = self._resolve_font_path(script)
        except Exception:
            font_path = None
        options = self._generation_options()
        signature = (
            script,
            text,
            str(font_path) if font_path else "",
            options["font_size"],
            options["cell_size"],
            options["shape_mode"],
            options["use_forza_font"],
            options["forza_font_index"],
            options["fit_layer_budget"],
            options["max_drawable_layers"],
            options["extra_shapes"],
        )
        if signature == self._layer_estimate_signature:
            return
        self._layer_estimate_signature = signature
        threading.Thread(
            target=self._layer_estimate_worker,
            args=(text, font_path, options),
            daemon=True,
        ).start()

    def _layer_estimate_worker(self, text: str, font_path: Path | None, options: dict) -> None:
        try:
            if options["use_forza_font"]:
                if not is_forza_latin_text(text):
                    self.queue.put(("text_layer_estimate", ("unsupported", 0, 1)))
                    return
                from text_forza_fonts import unsupported_forza_chars

                missing = unsupported_forza_chars(text, font_index=options["forza_font_index"])
                if missing:
                    self.queue.put(("text_layer_estimate", ("forza_missing", len(missing), 1)))
                    return
            layers, cell_used = estimate_typed_text_layers(
                text,
                font_path=font_path,
                font_size=options["font_size"],
                cell_size=options["cell_size"],
                shape_mode=options["shape_mode"],
                use_forza_font=options["use_forza_font"],
                forza_font_index=options["forza_font_index"],
                fit_layer_budget=options["fit_layer_budget"],
                max_drawable_layers=options["max_drawable_layers"],
                extra_shapes=options["extra_shapes"],
            )
            self.queue.put(("text_layer_estimate", ("ok", layers, cell_used)))
        except Exception as exc:
            self.queue.put(("text_layer_estimate", ("error", str(exc), 0)))

    def _set_layer_estimate_message(self, key: str, **kwargs) -> None:
        if self.text_layer_estimate_label is not None:
            self.text_layer_estimate_label.configure(text=self._tr(key).format(**kwargs))

    def handle_layer_estimate(self, result: tuple) -> None:
        kind = result[0]
        if kind == "ok":
            layers = int(result[1])
            cell_used = int(result[2])
            template_need = layers + FH6_BOUNDARY_LAYERS
            cell_note = ""
            if self.text_fit_layer_budget.get() == "1" and self.text_use_forza_font.get() != "1":
                cell_note = self._tr("text_layer_estimate_cell").format(cell=cell_used)
            mode_note = ""
            if self.text_use_forza_font.get() == "1":
                mode_note = " " + self._tr("text_layer_estimate_forza_mode")
            elif self.text_extra_shapes.get() == "1":
                mode_note = " " + self._tr("text_layer_estimate_extra_shapes")
            self._set_layer_estimate_message(
                "text_layer_estimate_ok",
                layers=layers,
                template=template_need,
                cell_note=cell_note,
                mode_note=mode_note,
            )
            return
        if kind == "unsupported":
            self._set_layer_estimate_message("text_layer_estimate_forza_latin_only")
            return
        if kind == "forza_missing":
            self._set_layer_estimate_message("text_layer_estimate_forza_missing", count=result[1])
            return
        if kind == "error":
            self._set_layer_estimate_message("text_layer_estimate_error", error=result[1])
            return
        self._set_layer_estimate_message("text_layer_estimate_idle")

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
            widgets["char_library_specs"] = [(LIBRARY_LATIN, "text_char_library_latin", True)]
            self._build_char_library_shell(parent, script)
        elif script == SCRIPT_JAPANESE:
            widgets["char_library_specs"] = list(_JAPANESE_CHAR_LIBRARIES)
            self._build_char_library_shell(parent, script)
        elif script == SCRIPT_KOREAN:
            widgets["char_library_specs"] = [(LIBRARY_HANGUL, "text_char_library_hangul", True)]
            self._build_char_library_shell(parent, script)
        elif script == SCRIPT_CHINESE:
            widgets["char_library_specs"] = [(LIBRARY_HANZI, "text_char_library_hanzi", True)]
            self._build_char_library_shell(parent, script)
        elif script == SCRIPT_KAOMOJI:
            widgets["char_library_specs"] = ("kaomoji",)
            self._build_char_library_shell(parent, script)

    def _build_char_library_shell(self, parent: Frame, script: str) -> None:
        app = self.app
        widgets = self._panel(script)["widgets"]
        host = Frame(parent)
        host._theme_surface = "panel"  # type: ignore[attr-defined]
        host.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        widgets["char_library_host"] = host
        widgets["char_library_deployed"] = False

        bar = Frame(host)
        bar._theme_surface = "panel"  # type: ignore[attr-defined]
        bar.pack(fill=X, padx=10, pady=(0, 6))
        show_btn = app._button(
            bar,
            "text_char_library_show",
            lambda s=script: self._deploy_char_library(s),
        )
        show_btn.pack(side=LEFT)
        widgets["char_library_show_bar"] = bar
        widgets["char_library_show_btn"] = show_btn
        body = Frame(host)
        body._theme_surface = "panel"  # type: ignore[attr-defined]
        widgets["char_library_body"] = body

    def _deploy_char_library(self, script: str) -> None:
        widgets = self._panel(script)["widgets"]
        if widgets.get("char_library_deployed"):
            return

        body = widgets.get("char_library_body")
        specs = widgets.get("char_library_specs")
        if body is None:
            return

        try:
            show_bar = widgets.get("char_library_show_bar")
            if show_bar is not None:
                show_bar.pack_forget()

            body.pack(fill=BOTH, expand=True)
            body._theme_surface = "panel"  # type: ignore[attr-defined]
            widgets["char_library_deployed"] = True
            try:
                self.app.themes.apply_widget(body)
            except Exception:
                pass
            if specs == ("kaomoji",):
                picker = self._build_kaomoji_picker(body, script)
                picker.ensure_loaded()
                return

            if script == SCRIPT_JAPANESE and specs:
                kana_notebook = ttk.Notebook(body, style="Script.TNotebook")
                kana_notebook.pack(fill=BOTH, expand=True)
                widgets["kana_notebook"] = kana_notebook
                for library_id, label_key in specs:
                    tab_frame = Frame(kana_notebook)
                    kana_notebook.add(tab_frame, text=self._tr(label_key))
                    picker = self._build_char_library(
                        tab_frame,
                        script,
                        library_id,
                        label_key,
                        framed=False,
                    )
                    picker.ensure_loaded()
                return

            if specs and len(specs) == 1:
                library_id, label_key, framed = specs[0]
                picker = self._build_char_library(body, script, library_id, label_key, framed=framed)
                picker.ensure_loaded()
                return

            raise RuntimeError(f"No character library spec for script {script!r}")
        except Exception as exc:
            widgets["char_library_deployed"] = False
            body.pack_forget()
            show_bar = widgets.get("char_library_show_bar")
            if show_bar is not None:
                show_bar.pack(fill=X, padx=10, pady=(0, 6))
            self.app.log_line(self._tr("text_log_char_library_failed").format(error=exc))

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
        picker.frame.pack(fill=BOTH, expand=True)
        self._panel(script)["widgets"]["char_pickers"].append(picker)
        return picker

    def _build_kaomoji_picker(self, parent: Frame, script: str) -> KaomojiPicker:
        picker = KaomojiPicker(
            parent,
            self.app,
            on_insert=lambda value, s=script: self._insert_kaomoji(s, value),
            label_key="text_char_library_kaomoji",
        )
        picker.frame.pack(fill=BOTH, expand=True)
        widgets = self._panel(script)["widgets"]
        widgets.setdefault("char_pickers", []).append(picker)
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

    def _insert_kaomoji(self, script: str, kaomoji: str) -> None:
        panel = self._panel(script)
        panel["input"].set(kaomoji)
        if self.text_script_notebook is not None:
            try:
                self.text_script_notebook.select(TEXT_SCRIPT_IDS.index(script))
            except ValueError:
                pass
        self._schedule_coverage_check()
        threading.Thread(
            target=self._apply_kaomoji_font_recommendation_worker,
            args=(kaomoji, script),
            daemon=True,
        ).start()

    def _apply_kaomoji_font_recommendation_worker(self, kaomoji: str, script: str) -> None:
        discovered = tuple(self._panel(script)["discovered"])
        recommendation = recommend_font_for_text(kaomoji, script=script, fonts=discovered)
        if not recommendation.label:
            return

        def _apply() -> None:
            if self.app.closed:
                return
            self.apply_recommended_font(recommendation=recommendation, script=script)

        self.app.root.after(0, _apply)

    def refresh_char_pickers(self) -> None:
        for script in TEXT_SCRIPT_IDS:
            widgets = self._panel(script)["widgets"]
            if not widgets.get("char_library_deployed"):
                continue
            for picker in widgets.get("char_pickers", []):
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
        self._schedule_coverage_check()
        self._refresh_shape_mode_combo()
        self._refresh_preset_combo()
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
        self._schedule_coverage_check()

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

    @staticmethod
    def _merge_discovered_fonts(
        existing: tuple[DiscoveredFont, ...],
        incoming: tuple[DiscoveredFont, ...],
    ) -> tuple[DiscoveredFont, ...]:
        by_path: dict[Path, DiscoveredFont] = {font.path: font for font in existing}
        for font in incoming:
            if not font.path.exists():
                continue
            prev = by_path.get(font.path)
            if prev is None or font.score > prev.score:
                by_path[font.path] = font
        return tuple(sorted(by_path.values(), key=lambda item: (-item.score, item.display_name.lower())))

    def refresh_fonts(self, *, full_rescan: bool = True) -> None:
        if full_rescan:
            clear_font_discovery_cache()
            self._fonts_deep_scanned.clear()
        tier1 = {
            script: tuple(font for font in default_fonts_for_script(script) if font.path.exists())
            for script in TEXT_SCRIPT_IDS
        }
        self.apply_fonts_by_script(tier1, merge=False)
        self.app.log_line(self._tr("text_log_scanning_fonts"))
        threading.Thread(
            target=self._refresh_fonts_worker,
            args=(self.active_script(), full_rescan),
            daemon=True,
        ).start()

    def _refresh_fonts_worker(self, priority_script: str, full_rescan: bool) -> None:
        try:
            order = [priority_script] + [s for s in TEXT_SCRIPT_IDS if s != priority_script]
            fonts_by_script: dict[str, tuple[DiscoveredFont, ...]] = {}
            for script in order:
                fonts = tuple(
                    font
                    for font in discover_fonts_for_script_cached(script, deep_scan=True)
                    if font.path.exists()
                )
                fonts_by_script[script] = fonts
                self._fonts_deep_scanned.add(script)
                self.queue.put(("text_fonts_ready", ({script: fonts}, True, False)))
            if fonts_by_script:
                self.queue.put(("text_fonts_ready", (fonts_by_script, True, True)))
        except Exception as exc:
            self.queue.put(("log", self._tr("text_log_font_scan_failed").format(error=exc)))

    def _schedule_font_scan_for_script(self, script: str) -> None:
        if script in self._fonts_deep_scanned:
            return
        threading.Thread(target=self._scan_one_script_fonts_worker, args=(script,), daemon=True).start()

    def _scan_one_script_fonts_worker(self, script: str) -> None:
        try:
            fonts = tuple(
                font
                for font in discover_fonts_for_script_cached(script, deep_scan=True)
                if font.path.exists()
            )
            self._fonts_deep_scanned.add(script)
            self.queue.put(("text_fonts_ready", ({script: fonts}, True, False)))
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
        if labels and current not in labels:
            panel["font_choice"].set(labels[0])
        elif not labels:
            panel["font_choice"].set("")

    def apply_fonts_by_script(self, fonts_by_script: dict, *, merge: bool = True, log: bool = True) -> None:
        total = 0
        for script in TEXT_SCRIPT_IDS:
            fonts = tuple(fonts_by_script.get(script, ()))
            if not fonts:
                continue
            panel = self._panel(script)
            if merge and panel["discovered"]:
                panel["discovered"] = self._merge_discovered_fonts(panel["discovered"], fonts)
            else:
                panel["discovered"] = fonts
            self._refresh_script_font_combo(script)
            total += len(fonts)
        if log:
            if total:
                self.app.log_line(
                    self._tr("text_log_fonts_loaded").format(
                        latin=len(fonts_by_script.get("universal", ())),
                        japanese=len(fonts_by_script.get("japanese", ())),
                        kaomoji=len(fonts_by_script.get("kaomoji", ())),
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
        if script == self.active_script():
            self._schedule_layer_estimate()

    def _on_script_tab_changed(self) -> None:
        self._schedule_font_scan_for_script(self.active_script())
        self._schedule_coverage_check()
        self._update_forza_controls_state()
        self._schedule_layer_estimate()

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

    def _shape_template_hint(
        self,
        shape_mode: str | None = None,
        *,
        extra_shapes: bool | None = None,
    ) -> str:
        options = self._generation_options()
        mode = normalize_text_shape_mode(shape_mode or options["shape_mode"])
        use_extra = options["extra_shapes"] if extra_shapes is None else extra_shapes
        engine_hint = template_hint_for_shape_mode(mode, extra_shapes=use_extra)
        if use_extra:
            return engine_hint
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
        self._coverage_job = self.root.after(350, self._start_coverage_check)

    def _start_coverage_check(self) -> None:
        self._coverage_job = None
        if not self.app._widget_alive(self.text_coverage_label):
            return
        script = self.active_script()
        panel = self._panel(script)
        text = panel["input"].get().strip()
        self._last_font_recommendation = None
        if self._coverage_apply_button is not None:
            self._coverage_apply_button.config(state="disabled")
        if not text:
            self.text_coverage_label.config(text="", fg=self.app.themes.fg("muted"))
            return
        try:
            font_path = self._resolve_font_path(script)
        except Exception as exc:
            self.text_coverage_label.config(text=str(exc), fg=self.app.themes.fg("error"))
            return

        self._coverage_generation += 1
        generation = self._coverage_generation
        discovered = tuple(panel["discovered"])
        selected = panel["font_choice"].get().strip()
        threading.Thread(
            target=self._coverage_check_worker,
            args=(generation, script, text, font_path, discovered, selected),
            daemon=True,
        ).start()

    def _coverage_check_worker(
        self,
        generation: int,
        script: str,
        text: str,
        font_path: Path,
        discovered: tuple[DiscoveredFont, ...],
        selected: str,
    ) -> None:
        try:
            ok, missing = validate_text_coverage(text, font_path)
            recommendation = None
            if not ok or script == SCRIPT_KAOMOJI:
                recommendation = recommend_font_for_text(text, script=script, fonts=discovered)
            elif text_contains_hangul(text) and "[KR]" not in selected.upper():
                recommendation = recommend_font_for_text(text, script=script, fonts=discovered)
            self.queue.put(
                (
                    "text_coverage_ready",
                    {
                        "generation": generation,
                        "script": script,
                        "text": text,
                        "ok": ok,
                        "missing": missing,
                        "recommendation": recommendation,
                    },
                )
            )
        except Exception as exc:
            self.queue.put(
                (
                    "text_coverage_ready",
                    {
                        "generation": generation,
                        "script": script,
                        "text": text,
                        "error": str(exc),
                    },
                )
            )

    def handle_coverage_ready(self, payload: dict) -> None:
        if payload.get("generation") != self._coverage_generation:
            return
        if not self.app._widget_alive(self.text_coverage_label):
            return
        if payload.get("error"):
            self.text_coverage_label.config(text=payload["error"], fg=self.app.themes.fg("error"))
            return

        script = payload.get("script") or self.active_script()
        panel = self._panel(script)
        if panel["input"].get().strip() != payload.get("text", ""):
            return

        text = payload["text"]
        missing = payload.get("missing") or []
        ok = bool(payload.get("ok"))
        recommendation = payload.get("recommendation")
        self._last_font_recommendation = recommendation
        selected = panel["font_choice"].get().strip()

        if ok:
            message = self._tr(coverage_message_key(text, True, missing))
            if (
                recommendation is not None
                and recommendation.label
                and text_contains_hangul(text)
                and "[KR]" not in selected.upper()
            ):
                message = self._tr("text_coverage_suggest_kr").format(font=recommendation.label)
                fg = self.app.themes.fg("hint")
            else:
                fg = self.app.themes.fg("success")
            self.text_coverage_label.config(text=message, fg=fg)
            return

        key = coverage_message_key(text, False, missing)
        message = self._tr(key).format(
            count=len(missing),
            chars=format_missing_chars(missing),
        )
        if recommendation is not None and recommendation.label:
            if recommendation.complete:
                message = f"{message} {self._tr('text_coverage_suggest_font').format(font=recommendation.label)}"
            else:
                message = self._tr("text_coverage_partial").format(
                    covered=recommendation.covered,
                    total=recommendation.total,
                    font=recommendation.label,
                    chars=format_missing_chars(missing),
                )
        if (
            recommendation is not None
            and recommendation.font is not None
            and recommendation.label
            and recommendation.label != selected
            and self._coverage_apply_button is not None
        ):
            self._coverage_apply_button.config(state="normal")
        self.text_coverage_label.config(text=message, fg=self.app.themes.fg("error"))

    def update_coverage_status(self) -> None:
        self._schedule_coverage_check()

    def apply_recommended_font(
        self,
        recommendation: FontRecommendation | None = None,
        script: str | None = None,
    ) -> None:
        script = script or self.active_script()
        rec = recommendation or self._last_font_recommendation
        if rec is None or rec.font is None or not rec.label:
            return
        panel = self._panel(script)
        panel["font_path"].set("")
        if rec.label in panel["font_by_label"]:
            panel["font_choice"].set(rec.label)
        else:
            discovered = tuple(panel["discovered"])
            if rec.font not in discovered:
                panel["discovered"] = discovered + (rec.font,)
                self._refresh_script_font_combo(script)
            panel["font_choice"].set(rec.label)
        self.update_coverage_status()

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
        options = self._generation_options()
        if options["use_forza_font"]:
            if script != SCRIPT_UNIVERSAL:
                self.app.log_line(self._tr("text_log_forza_universal_only"))
                return
            if not is_forza_latin_text(text):
                self.app.log_line(self._tr("text_log_forza_latin_only"))
                return
            font_path = None
        else:
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

    def finish_json(
        self,
        payload,
        output: Path,
        shape_mode: str | None = None,
        extra_shapes: bool = False,
    ) -> None:
        write_text_design_json(output, payload)
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
        if shape_mode or extra_shapes:
            self.app.log_line(
                self._shape_template_hint(shape_mode, extra_shapes=extra_shapes)
            )
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
        added = self.app.add_text_import_paths(paths, navigate=True)
        if added:
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
        bounds = self.app._preview_bounds(label)
        slot = self.app._geometry_preview_slot_for_label(label)

        def on_ready(png_bytes) -> None:
            if not self.app._widget_alive(label):
                return
            if not png_bytes:
                label.config(
                    image="",
                    text=self._tr("preview_unavailable"),
                    bg=preview_bg,
                    fg=preview_fg,
                )
                label.image = None
                return
            image = PhotoImage(data=png_bytes)
            label.config(image=image, text="", bg=preview_bg)
            label.image = image

        self.app.schedule_geometry_json_preview(slot, path, bounds, on_ready)

    def _typed_worker(self, text: str, font_path: Path | None) -> None:
        try:
            self.queue.put(("log", self._tr("text_generating")))
            color = self._parse_color()
            options = self._generation_options()
            payload, cell_used = build_typecode_from_text_with_options(
                text,
                color=color,
                font_path=font_path,
                font_size=options["font_size"],
                cell_size=options["cell_size"],
                shape_mode=options["shape_mode"],
                use_forza_font=options["use_forza_font"],
                forza_font_index=options["forza_font_index"],
                fit_layer_budget=options["fit_layer_budget"],
                max_drawable_layers=options["max_drawable_layers"],
                extra_shapes=options["extra_shapes"],
            )
            if cell_used != options["cell_size"]:
                self.queue.put(("text_cell_size_applied", str(cell_used)))
            shape_mode = options["shape_mode"]
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
            self.queue.put(
                ("text_json_done", (payload, output, shape_mode, options["extra_shapes"]))
            )
        except Exception as exc:
            self.queue.put(("log", f"{self._tr('text_failed')}: {exc}"))
            self.queue.put(("status", self._tr("failed")))

    def _trace_worker(self, path: str) -> None:
        try:
            self.queue.put(("log", self._tr("text_generating")))
            color = self._parse_color()
            options = self._generation_options()
            cell_size = options["cell_size"]
            shape_mode = options["shape_mode"]
            extra_shapes = options["extra_shapes"]
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
            payload = build_typecode_from_text_image(
                trace_input,
                color=color,
                cell_size=cell_size,
                invert=self.text_invert.get() == "1",
                shape_mode=shape_mode,
                extra_shapes=extra_shapes,
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
            self.queue.put(("text_json_done", (payload, output, shape_mode, extra_shapes)))
        except Exception as exc:
            self.queue.put(("log", f"{self._tr('text_failed')}: {exc}"))
            self.queue.put(("status", self._tr("failed")))
