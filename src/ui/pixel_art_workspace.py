"""Pixel Art tab: file conversion, mini editor, and handmade JSON output."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from tkinter import BOTH, BOTTOM, END, HORIZONTAL, LEFT, RIGHT, VERTICAL, X, Y, Canvas, Frame, Label, Listbox, PhotoImage, StringVar, filedialog, messagebox, ttk
from tkinter import Checkbutton, Entry

from asset_workspace import PIXEL_ART_WORKSPACE_ROOT
from pixel_art_geometry import (
    MAX_DRAWABLE_LAYERS,
    MAX_EDITOR_DIMENSION,
    MAX_IMPORT_DIMENSION,
    ColorGrid,
    MergeMode,
    analyze_pixel_art,
    build_typecode_json_from_grid,
    build_typecode_json_from_path,
    estimate_layer_count,
    layer_budget_message,
    merge_mode_choices,
    parse_hex_color,
    read_source_dimensions,
    render_color_grid_preview,
    write_typecode_json,
)
from ui.color_values_editor import ColorValuesEditor

JSON_PREVIEW_MIN_HEIGHT = 240
PREVIEW_MIN_HEIGHT = 260
MODE_TAB_KEYS = ("pixel_subtab_file", "pixel_subtab_editor", "pixel_subtab_preview")


class PixelArtWorkspace:
    """Pixel art conversion and editor hosted by App."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.json_files: list[Path] = []
        self._grid_for_path: dict[Path, ColorGrid] = {}
        self._source_preview_path: Path | None = None
        self._json_preview_path: Path | None = None
        self._preview_art_path: Path | None = None
        self._source_preview_job = None
        self._json_preview_job = None
        self._preview_art_job = None
        self._undo_stack: list[tuple[int, int, tuple]] = []
        self._redo_stack: list[tuple[int, int, tuple]] = []

        self.source_path = StringVar()
        self.merge_mode = StringVar(value=MergeMode.AUTO.value)
        self.max_colors = StringVar(value="0")
        self.alpha_threshold = StringVar(value="128")
        self.color_tolerance = StringVar(value="0")
        self.target_width = StringVar()
        self.target_height = StringVar()
        self.jpeg_background = StringVar(value="#FFFFFF")
        self.use_jpeg_background = StringVar(value="0")

        self.editor_width = StringVar(value="64")
        self.editor_height = StringVar(value="64")
        self.cell_display_size = StringVar(value="12")
        self.layer_estimate = StringVar(value="")

        self.grid = ColorGrid.empty(64, 64)
        self.active_tool = "pencil"
        self._drag_paint = False
        self._active_mode_index = 0

        self.mode_notebook: ttk.Notebook | None = None
        self.json_list: Listbox | None = None
        self.source_preview_label: Label | None = None
        self.json_preview_label: Label | None = None
        self.preview_art_label: Label | None = None
        self.stats_text: Label | None = None
        self.stats_disclaimer: Label | None = None
        self.editor_canvas: Canvas | None = None
        self.merge_combo: ttk.Combobox | None = None
        self.layer_estimate_label: Label | None = None
        self._color_editor: ColorValuesEditor | None = None

        self.right_host: Frame | None = None
        self.file_view: Frame | None = None
        self.editor_view: Frame | None = None
        self.preview_view: Frame | None = None

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

    def _preview_bounds(self, label: Label | None, *, min_height: int = 0) -> tuple[int, int]:
        if label is None:
            return 640, max(min_height, 480)
        return self.app._label_preview_bounds(label, min_height=min_height)

    def build(self, tab: Frame) -> None:
        app = self.app
        paned = app._create_paned(tab, orient=HORIZONTAL, layout_key="pixel_horizontal", padx=10, pady=10)
        left_outer = Frame(paned)
        right = Frame(paned)
        paned.add(left_outer, weight=1)
        paned.add(right, weight=3)

        scroll_area, body = app._make_vertical_scroll(left_outer)
        scroll_area.pack(fill=BOTH, expand=True, padx=0, pady=10)

        tab_hint = app._label(body, "pixel_tab_hint", anchor="w", justify="left", theme_role="hint")
        tab_hint.pack(fill="x", pady=(0, 4))
        app._bind_wraplength(tab_hint, body)

        credit = app._label(body, "pixel_credit_endarz", anchor="w", justify="left", theme_role="muted")
        credit.pack(fill="x", pady=(0, 4))
        app._bind_wraplength(credit, body)

        size_hint = app._label(body, "pixel_png_size_hint", anchor="w", justify="left", theme_role="info")
        size_hint.pack(fill="x", pady=(0, 8))
        app._bind_wraplength(size_hint, body)

        self.mode_notebook = ttk.Notebook(body, style="Script.TNotebook")
        self.mode_notebook.pack(fill=BOTH, expand=True, pady=(0, 8))
        self.mode_notebook.bind("<<NotebookTabChanged>>", self._on_mode_tab_changed)

        file_tab = Frame(self.mode_notebook)
        editor_tab = Frame(self.mode_notebook)
        preview_tab = Frame(self.mode_notebook)
        self.mode_notebook.add(file_tab, text=self._tr("pixel_subtab_file"))
        self.mode_notebook.add(editor_tab, text=self._tr("pixel_subtab_editor"))
        self.mode_notebook.add(preview_tab, text=self._tr("pixel_subtab_preview"))
        self._build_file_panel(file_tab)
        self._build_editor_panel(editor_tab)
        self._build_preview_panel(preview_tab)

        outputs_box = ttk.LabelFrame(body, text=self._tr("pixel_outputs"))
        app.translated.append((outputs_box, "pixel_outputs", "text"))
        outputs_box.pack(fill="x", pady=(0, 8))
        outputs_hint = app._label(outputs_box, "pixel_outputs_hint", anchor="w", justify="left", theme_role="hint")
        outputs_hint.pack(fill="x", padx=10, pady=(8, 4))
        app._bind_wraplength(outputs_hint, outputs_box)
        outputs_row = Frame(outputs_box)
        outputs_row.pack(fill="x", padx=10, pady=(0, 4))
        app._button(outputs_row, "pixel_add_json", self.add_json).pack(side=LEFT)
        app._button(outputs_row, "pixel_remove_json", self.remove_selected_json).pack(side=LEFT, padx=8)
        app._button(outputs_row, "pixel_send_to_import", self.send_to_handmade_import).pack(side=RIGHT)
        app._button(outputs_row, "pixel_open_folder", self.open_output_folder).pack(side=RIGHT, padx=(0, 8))
        list_body = Frame(outputs_box)
        list_body.pack(fill="x", padx=10, pady=(0, 10))
        self.json_list = Listbox(list_body, height=5)
        self.json_list.pack(fill="x", expand=True)
        self.json_list.bind("<<ListboxSelect>>", self._on_json_list_select)

        self.right_host = Frame(right)
        self.right_host.pack(fill=BOTH, expand=True)
        self._build_right_views(self.right_host)
        self._show_right_view(0)
        self._refresh_layer_estimate()

    def _build_right_views(self, parent: Frame) -> None:
        app = self.app
        preview_t = app.themes.tokens

        self.file_view = Frame(parent)
        self._build_file_compare_pane(self.file_view)

        self.editor_view = Frame(parent)
        editor_box = ttk.LabelFrame(self.editor_view, text=self._tr("pixel_editor_canvas"))
        app.translated.append((editor_box, "pixel_editor_canvas", "text"))
        editor_box.pack(fill=BOTH, expand=True)
        canvas_row = Frame(editor_box)
        canvas_row.pack(fill=BOTH, expand=True, padx=10, pady=10)
        scroll_y = ttk.Scrollbar(canvas_row, orient="vertical")
        scroll_x = ttk.Scrollbar(canvas_row, orient="horizontal")
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.pack(side=BOTTOM, fill=X)
        self.editor_canvas = Canvas(
            canvas_row,
            bg=preview_t.preview_bg,
            highlightthickness=1,
            highlightbackground=self._color("COLOR_BORDER"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set,
        )
        self.editor_canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scroll_y.config(command=self.editor_canvas.yview)
        scroll_x.config(command=self.editor_canvas.xview)
        self.editor_canvas.bind("<Button-1>", self._on_editor_press)
        self.editor_canvas.bind("<B1-Motion>", self._on_editor_drag)
        self.editor_canvas.bind("<ButtonRelease-1>", self._on_editor_release)
        self.editor_canvas.bind("<Configure>", lambda _e: self._render_editor())

        self.preview_view = Frame(parent)
        preview_box = ttk.LabelFrame(self.preview_view, text=self._tr("pixel_json_preview"))
        app.translated.append((preview_box, "pixel_json_preview", "text"))
        preview_box.pack(fill=BOTH, expand=True, pady=(0, 8))
        self.preview_art_label = Label(
            preview_box,
            text=self._tr("preview_hint"),
            bg=preview_t.preview_bg,
            fg=preview_t.preview_fg,
        )
        self.preview_art_label.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.preview_art_label.bind("<Configure>", lambda _e: self._schedule_preview_art_refresh())

        stats_box = ttk.LabelFrame(self.preview_view, text=self._tr("pixel_stats_title"))
        app.translated.append((stats_box, "pixel_stats_title", "text"))
        stats_box.pack(fill=X, padx=0, pady=(0, 4))
        self.stats_text = app._label(stats_box, "pixel_stats_none", anchor="nw", justify="left", theme_role="info")
        self.stats_text.pack(fill=X, padx=10, pady=(10, 4))
        app._bind_wraplength(self.stats_text, stats_box)
        self.stats_disclaimer = app._label(
            stats_box,
            "pixel_stats_preview_note",
            anchor="nw",
            justify="left",
            theme_role="muted",
        )
        self.stats_disclaimer.pack(fill=X, padx=10, pady=(0, 10))
        app._bind_wraplength(self.stats_disclaimer, stats_box)

        self.source_path.trace_add("write", lambda *_args: self._schedule_source_preview_refresh())

    def _build_file_compare_pane(self, parent: Frame) -> None:
        app = self.app
        preview_t = app.themes.tokens

        paned = app._create_paned(parent, orient=HORIZONTAL, layout_key="pixel_file_compare_h", padx=0, pady=0)
        source_box = ttk.LabelFrame(paned, text=self._tr("pixel_source_preview"))
        app.translated.append((source_box, "pixel_source_preview", "text"))
        json_box = ttk.LabelFrame(paned, text=self._tr("pixel_json_preview"))
        app.translated.append((json_box, "pixel_json_preview", "text"))
        paned.add(source_box, weight=1)
        paned.add(json_box, weight=1)

        self.source_preview_label = Label(
            source_box,
            text=self._tr("preview_hint"),
            bg=preview_t.preview_bg,
            fg=preview_t.preview_fg,
        )
        self.source_preview_label.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.source_preview_label.bind("<Configure>", lambda _e: self._schedule_source_preview_refresh())

        self.json_preview_label = Label(
            json_box,
            text=self._tr("preview_hint"),
            bg=preview_t.preview_bg,
            fg=preview_t.preview_fg,
        )
        self.json_preview_label.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.json_preview_label.bind("<Configure>", lambda _e: self._schedule_json_preview_refresh())

    def _build_file_panel(self, parent: Frame) -> None:
        app = self.app
        box = ttk.LabelFrame(parent, text=self._tr("pixel_file_source"))
        app.translated.append((box, "pixel_file_source", "text"))
        box.pack(fill="x", padx=4, pady=4)
        row = Frame(box)
        row.pack(fill="x", padx=10, pady=8)
        Entry(row, textvariable=self.source_path).pack(side=LEFT, fill="x", expand=True)
        app._button(row, "pixel_browse_file", self.browse_source_file).pack(side=LEFT, padx=8)

        opts = ttk.LabelFrame(parent, text=self._tr("pixel_convert_options"))
        app.translated.append((opts, "pixel_convert_options", "text"))
        opts.pack(fill="x", padx=4, pady=4)
        grid = Frame(opts)
        grid.pack(fill="x", padx=10, pady=8)

        app._label(grid, "pixel_merge_mode").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.merge_combo = ttk.Combobox(
            grid,
            textvariable=self.merge_mode,
            values=merge_mode_choices(),
            width=16,
            state="readonly",
        )
        self.merge_combo.grid(row=0, column=1, sticky="w")
        self.merge_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_layer_estimate_from_source())

        app._label(grid, "pixel_max_colors").grid(row=0, column=2, sticky="w", padx=(16, 8))
        Entry(grid, textvariable=self.max_colors, width=8).grid(row=0, column=3, sticky="w")

        app._label(grid, "pixel_alpha_threshold").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        Entry(grid, textvariable=self.alpha_threshold, width=8).grid(row=1, column=1, sticky="w", pady=(6, 0))

        app._label(grid, "pixel_target_width").grid(row=1, column=2, sticky="w", padx=(16, 8), pady=(6, 0))
        Entry(grid, textvariable=self.target_width, width=8).grid(row=1, column=3, sticky="w", pady=(6, 0))

        app._label(grid, "pixel_target_height").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        Entry(grid, textvariable=self.target_height, width=8).grid(row=2, column=1, sticky="w", pady=(6, 0))

        app._label(grid, "pixel_color_tolerance").grid(row=2, column=2, sticky="w", padx=(16, 8), pady=(6, 0))
        Entry(grid, textvariable=self.color_tolerance, width=8).grid(row=2, column=3, sticky="w", pady=(6, 0))

        bg_row = Frame(grid)
        bg_row.grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))
        bg_toggle = Checkbutton(
            bg_row,
            text=self._tr("pixel_use_jpeg_background"),
            variable=self.use_jpeg_background,
            onvalue="1",
            offvalue="0",
        )
        bg_toggle.pack(side=LEFT)
        app.translated.append((bg_toggle, "pixel_use_jpeg_background", "text"))
        Entry(bg_row, textvariable=self.jpeg_background, width=10).pack(side=LEFT, padx=(8, 0))

        hint = app._label(opts, "pixel_file_hint", anchor="w", justify="left", theme_role="muted")
        hint.pack(fill="x", padx=10, pady=(0, 8))
        app._bind_wraplength(hint, opts)

        actions = Frame(parent)
        actions.pack(fill="x", padx=4, pady=(4, 8))
        app._button(actions, "pixel_convert_file", self.start_convert_file).pack(side=LEFT)
        self.layer_estimate_label = app._label(actions, "pixel_layer_estimate", anchor="w", theme_role="info")
        self.layer_estimate_label.pack(side=LEFT, padx=(12, 0))

    def _build_editor_panel(self, parent: Frame) -> None:
        app = self.app
        toolbar = ttk.LabelFrame(parent, text=self._tr("pixel_editor_tools"))
        app.translated.append((toolbar, "pixel_editor_tools", "text"))
        toolbar.pack(fill="x", padx=4, pady=4)

        size_row = Frame(toolbar)
        size_row.pack(fill="x", padx=10, pady=(8, 4))
        app._label(size_row, "pixel_canvas_width").pack(side=LEFT)
        Entry(size_row, textvariable=self.editor_width, width=6).pack(side=LEFT, padx=(4, 12))
        app._label(size_row, "pixel_canvas_height").pack(side=LEFT)
        Entry(size_row, textvariable=self.editor_height, width=6).pack(side=LEFT, padx=(4, 12))
        app._button(size_row, "pixel_resize_canvas", self.resize_canvas).pack(side=LEFT)

        tool_row = Frame(toolbar)
        tool_row.pack(fill="x", padx=10, pady=(0, 4))
        app._button(tool_row, "pixel_tool_pencil", lambda: self._set_tool("pencil")).pack(side=LEFT)
        app._button(tool_row, "pixel_tool_eraser", lambda: self._set_tool("eraser")).pack(side=LEFT, padx=(6, 0))
        app._button(tool_row, "pixel_tool_fill", lambda: self._set_tool("fill")).pack(side=LEFT, padx=(6, 0))
        app._button(tool_row, "pixel_import_png_editor", self.import_png_to_editor).pack(side=LEFT, padx=(12, 0))
        app._button(tool_row, "pixel_clear_canvas", self.clear_canvas).pack(side=LEFT, padx=(6, 0))

        zoom_row = Frame(toolbar)
        zoom_row.pack(fill="x", padx=10, pady=(0, 8))
        app._label(zoom_row, "pixel_cell_zoom").pack(side=LEFT)
        Entry(zoom_row, textvariable=self.cell_display_size, width=6).pack(side=LEFT, padx=(4, 12))
        app._button(zoom_row, "pixel_apply_zoom", self._render_editor).pack(side=LEFT)

        color_section = Frame(toolbar)
        color_section.pack(fill="x", padx=10, pady=(0, 8))
        app._label(color_section, "text_color", anchor="w").pack(anchor="w")
        self._color_editor = ColorValuesEditor(color_section, app, include_alpha=False, editable=True)
        self._color_editor.frame.pack(fill=X, pady=(4, 0))

        footer = Frame(parent)
        footer.pack(fill="x", padx=4, pady=(0, 8))
        app._button(footer, "pixel_generate_editor", self.start_generate_from_editor).pack(side=LEFT)
        app._label(footer, "pixel_layer_estimate", textvariable=self.layer_estimate, anchor="w", theme_role="info").pack(
            side=LEFT, padx=(12, 0)
        )

    def _build_preview_panel(self, parent: Frame) -> None:
        app = self.app
        hint = app._label(parent, "pixel_preview_hint", anchor="w", justify="left", theme_role="hint")
        hint.pack(fill="x", padx=8, pady=8)
        app._bind_wraplength(hint, parent)

    def _on_mode_tab_changed(self, _event=None) -> None:
        if self.mode_notebook is None:
            return
        try:
            index = self.mode_notebook.index(self.mode_notebook.select())
        except Exception:
            index = 0
        self._active_mode_index = index
        self._show_right_view(index)
        if index == 1:
            self._render_editor()

    def _show_right_view(self, index: int) -> None:
        for frame in (self.file_view, self.editor_view, self.preview_view):
            if frame is not None:
                frame.pack_forget()
        target = {0: self.file_view, 1: self.editor_view, 2: self.preview_view}.get(index, self.file_view)
        if target is not None:
            target.pack(fill=BOTH, expand=True)

    def _active_color(self) -> tuple[int, int, int, int]:
        if self._color_editor is None:
            return (255, 255, 255, 255)
        r, g, b, _a = self._color_editor.get_rgba()
        return r, g, b, 255

    def _set_tool(self, tool: str) -> None:
        self.active_tool = tool

    def on_tab_activated(self) -> None:
        self._refresh_layer_estimate()
        self._show_right_view(self._active_mode_index)

    def on_language_changed(self) -> None:
        if self.mode_notebook is not None:
            for index, key in enumerate(MODE_TAB_KEYS):
                self.mode_notebook.tab(index, text=self._tr(key))
        self._refresh_layer_estimate()
        self._refresh_stats_panel()

    def on_theme_changed(self) -> None:
        self.update_theme_hints()

    def update_theme_hints(self) -> None:
        preview_bg, preview_fg = self._preview_colors()
        for label in (
            self.source_preview_label,
            self.json_preview_label,
            self.preview_art_label,
        ):
            if label is not None:
                label.configure(bg=preview_bg, fg=preview_fg)
        if self.editor_canvas is not None:
            self.editor_canvas.configure(
                bg=preview_bg,
                highlightbackground=self._color("COLOR_BORDER"),
            )
        self._render_editor()

    def _preview_colors(self) -> tuple[str, str]:
        tokens = self.app.themes.tokens
        return tokens.preview_bg, tokens.preview_fg

    def _check_source_dimensions(self, path: Path) -> None:
        try:
            width, height = read_source_dimensions(path)
        except Exception:
            return
        if width > MAX_IMPORT_DIMENSION or height > MAX_IMPORT_DIMENSION:
            self.app.log_line(self._tr("pixel_log_oversized_source"))

    def browse_source_file(self) -> None:
        path = filedialog.askopenfilename(
            title=self._tr("pixel_dialog_open_file"),
            filetypes=[
                (self._tr("pixel_file_filter"), "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.gif;*.svg"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.source_path.set(path)
            self._check_source_dimensions(Path(path))
            self._refresh_layer_estimate_from_source()

    def import_png_to_editor(self) -> None:
        path = filedialog.askopenfilename(
            title=self._tr("pixel_dialog_open_file"),
            filetypes=[
                (self._tr("pixel_file_filter"), "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.gif;*.svg"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            grid = self._load_grid_from_file(Path(path))
        except Exception as exc:
            messagebox.showerror(self._tr("pixel_failed"), str(exc))
            return
        if grid.width > MAX_EDITOR_DIMENSION or grid.height > MAX_EDITOR_DIMENSION:
            messagebox.showerror(
                self._tr("pixel_failed"),
                self._tr("pixel_editor_size_limit").format(limit=MAX_EDITOR_DIMENSION),
            )
            return
        self.grid = grid
        self.editor_width.set(str(grid.width))
        self.editor_height.set(str(grid.height))
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._render_editor()
        self._refresh_layer_estimate()
        if self.mode_notebook is not None:
            self.mode_notebook.select(1)
            self._on_mode_tab_changed()

    def resize_canvas(self) -> None:
        try:
            width = int(self.editor_width.get().strip())
            height = int(self.editor_height.get().strip())
        except ValueError:
            messagebox.showerror(self._tr("pixel_failed"), self._tr("pixel_invalid_canvas_size"))
            return
        if width <= 0 or height <= 0 or width > MAX_EDITOR_DIMENSION or height > MAX_EDITOR_DIMENSION:
            messagebox.showerror(
                self._tr("pixel_failed"),
                self._tr("pixel_editor_size_limit").format(limit=MAX_EDITOR_DIMENSION),
            )
            return
        if self.grid.filled_pixel_count() > 0:
            if not messagebox.askyesno(self._tr("pixel_resize_canvas"), self._tr("pixel_resize_confirm")):
                return
        self.grid = ColorGrid.empty(width, height)
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._render_editor()
        self._refresh_layer_estimate()

    def clear_canvas(self) -> None:
        if self.grid.filled_pixel_count() == 0:
            return
        if not messagebox.askyesno(self._tr("pixel_clear_canvas"), self._tr("pixel_clear_confirm")):
            return
        self._push_undo()
        self.grid = ColorGrid.empty(self.grid.width, self.grid.height)
        self._render_editor()
        self._refresh_layer_estimate()

    def _parse_optional_int(self, value: str) -> int | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        return int(raw)

    def _parse_file_options(self) -> dict:
        max_colors = int(self.max_colors.get().strip() or "0")
        alpha_threshold = int(self.alpha_threshold.get().strip() or "128")
        color_tolerance = int(self.color_tolerance.get().strip() or "0")
        target_width = self._parse_optional_int(self.target_width.get())
        target_height = self._parse_optional_int(self.target_height.get())
        background = None
        if self.use_jpeg_background.get() == "1":
            background = parse_hex_color(self.jpeg_background.get())
        return {
            "max_colors": max_colors,
            "alpha_threshold": alpha_threshold,
            "color_tolerance": color_tolerance,
            "target_width": target_width,
            "target_height": target_height,
            "background_color": background,
        }

    def _load_grid_from_file(self, path: Path) -> ColorGrid:
        from pixel_art_geometry import load_color_grid

        options = self._parse_file_options()
        return load_color_grid(path, **options)

    def _refresh_layer_estimate_from_source(self) -> None:
        raw = self.source_path.get().strip()
        if not raw:
            self._set_layer_estimate_text(None)
            return
        path = Path(raw)
        if not path.exists():
            self._set_layer_estimate_text(None)
            return
        self._check_source_dimensions(path)
        try:
            grid = self._load_grid_from_file(path)
            count = estimate_layer_count(grid, self.merge_mode.get())
            self._set_layer_estimate_text(count)
        except Exception:
            self._set_layer_estimate_text(None)

    def _refresh_layer_estimate(self) -> None:
        count = estimate_layer_count(self.grid, self.merge_mode.get())
        self._set_layer_estimate_text(count)

    def _set_layer_estimate_text(self, count: int | None) -> None:
        if count is None:
            text = self._tr("pixel_layer_estimate_unknown")
        else:
            text = self._tr("pixel_layer_estimate_value").format(
                message=layer_budget_message(count),
            )
        self.layer_estimate.set(text)
        if self.layer_estimate_label is not None:
            self.layer_estimate_label.config(text=text)

    def _cache_grid_for_output(self, output: Path, grid: ColorGrid) -> None:
        self._grid_for_path[Path(output)] = grid.copy()

    def start_convert_file(self) -> None:
        raw = self.source_path.get().strip()
        if not raw:
            self.app.log_line(self._tr("pixel_log_choose_file"))
            return
        path = Path(raw)
        if not path.exists():
            self.app.log_line(self._tr("pixel_log_missing_file"))
            return
        self.app.status.set(self._tr("pixel_generating"))
        threading.Thread(target=self._convert_file_worker, args=(path,), daemon=True).start()

    def _convert_file_worker(self, path: Path) -> None:
        try:
            grid = self._load_grid_from_file(path)
            payload = build_typecode_json_from_grid(grid, self.merge_mode.get())
            output = self.output_path(path.stem)
            write_typecode_json(output, payload)
            layers = len(payload["shapes"])
            self.queue.put(("pixel_json_done", (output, layers, grid)))
        except Exception as exc:
            self.queue.put(("pixel_json_done", (None, str(exc), None)))

    def start_generate_from_editor(self) -> None:
        if self.grid.filled_pixel_count() == 0:
            self.app.log_line(self._tr("pixel_log_empty_canvas"))
            return
        self.app.status.set(self._tr("pixel_generating"))
        threading.Thread(target=self._generate_editor_worker, daemon=True).start()

    def _generate_editor_worker(self) -> None:
        try:
            grid = self.grid.copy()
            payload = build_typecode_json_from_grid(grid, self.merge_mode.get())
            output = self.output_path("editor")
            write_typecode_json(output, payload)
            layers = len(payload["shapes"])
            self.queue.put(("pixel_json_done", (output, layers, grid)))
        except Exception as exc:
            self.queue.put(("pixel_json_done", (None, str(exc), None)))

    def finish_json(self, output: Path | None, layers_or_error: int | str, grid: ColorGrid | None = None) -> None:
        if output is None:
            messagebox.showerror(self._tr("pixel_failed"), str(layers_or_error))
            self.app.log_line(self._tr("pixel_failed_detail").format(error=layers_or_error))
            self.app.status.set(self._tr("pixel_failed"))
            return
        if grid is not None:
            self._cache_grid_for_output(output, grid)
        if output not in self.json_files:
            self.json_files.append(output)
        self.render_json_list()
        if self.json_list is not None:
            self.json_list.selection_clear(0, END)
            self.json_list.selection_set(len(self.json_files) - 1)
        self._on_json_list_select()
        self.app.log_line(self._tr("pixel_done").format(layers=layers_or_error, path=output.name))
        self.app.status.set(self._tr("done"))

    def output_path(self, stem: str) -> Path:
        PIXEL_ART_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stem)[:48] or "pixel"
        base = PIXEL_ART_WORKSPACE_ROOT / f"{safe}.pixel.json"
        if not base.exists():
            return base
        index = 2
        while True:
            candidate = PIXEL_ART_WORKSPACE_ROOT / f"{safe}.{index}.pixel.json"
            if not candidate.exists():
                return candidate
            index += 1

    def render_json_list(self) -> None:
        if self.json_list is None:
            return
        self.json_list.delete(0, END)
        for path in self.json_files:
            self.json_list.insert(END, self.app._json_list_display(path))

    def add_json(self) -> None:
        files = filedialog.askopenfilenames(
            title=self._tr("pixel_dialog_add_json"),
            filetypes=[("Handmade JSON", "*.json"), ("All files", "*.*")],
        )
        if not files:
            return
        for raw in files:
            path = Path(raw)
            if path.suffix.lower() != ".json" or not path.exists():
                continue
            if path not in self.json_files:
                self.json_files.append(path)
        self.render_json_list()
        if self.json_files:
            self.json_list.selection_set(len(self.json_files) - 1)
            self._on_json_list_select()

    def remove_selected_json(self) -> None:
        if self.json_list is None:
            return
        selection = list(self.json_list.curselection())
        if not selection:
            return
        for index in reversed(selection):
            path = self.json_files[index]
            self._grid_for_path.pop(path, None)
            del self.json_files[index]
        self.render_json_list()
        if self.json_files:
            self.json_list.selection_set(0)
            self._on_json_list_select()
        else:
            self._json_preview_path = None
            self._preview_art_path = None
            self.set_json_preview(None)
            self.set_preview_art(None)
            self._refresh_stats_panel(None)

    def send_to_handmade_import(self) -> None:
        if self.json_list is None:
            return
        selection = list(self.json_list.curselection())
        paths = [self.json_files[index] for index in selection] if selection else list(self.json_files)
        if not paths:
            self.app.log_line(self._tr("pixel_log_no_json_to_send"))
            return
        added = self.app.add_pixel_import_paths(paths, navigate=True)
        if added:
            self.app.log_line(self._tr("pixel_log_added_handmade").format(count=added))
        else:
            self.app.log_line(self._tr("pixel_log_json_already_handmade"))

    def open_output_folder(self) -> None:
        PIXEL_ART_WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
        os.startfile(PIXEL_ART_WORKSPACE_ROOT)  # type: ignore[attr-defined]

    def _on_json_list_select(self, _event=None) -> None:
        if self.json_list is None:
            return
        selection = list(self.json_list.curselection())
        if not selection:
            return
        path = self.json_files[selection[0]]
        self.set_json_preview(path)
        self.set_preview_art(path)
        self._refresh_stats_panel(path)

    def _schedule_source_preview_refresh(self) -> None:
        if self.source_preview_label is None or self.closed:
            return
        if self._source_preview_job is not None:
            try:
                self.root.after_cancel(self._source_preview_job)
            except Exception:
                pass
        self._source_preview_job = self.root.after(180, self._refresh_source_preview)

    def _refresh_source_preview(self) -> None:
        self._source_preview_job = None
        raw = self.source_path.get().strip()
        path = Path(raw) if raw else None
        self.set_source_preview(path)

    def set_source_preview(self, path: Path | None) -> None:
        if self.source_preview_label is None:
            return
        self._source_preview_path = Path(path) if path else None
        label = self.source_preview_label
        preview_bg, preview_fg = self._preview_colors()
        if path is None or not path.exists():
            label.config(image="", text=self._tr("preview_hint"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        render_source_image, _render_geometry_json = self._preview_renderers()
        data = render_source_image(path, self._preview_bounds(label, min_height=PREVIEW_MIN_HEIGHT))
        if not data:
            label.config(image="", text=self._tr("preview_unavailable"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        image = PhotoImage(data=data)
        label.config(image=image, text="", bg=preview_bg)
        label.image = image

    def _json_preview_data(self, path: Path, label: Label, *, min_height: int) -> bytes | None:
        grid = self._grid_for_path.get(path)
        if grid is not None:
            data = render_color_grid_preview(grid, self._preview_bounds(label, min_height=min_height))
            if data:
                return data
        _render_source_image, render_geometry_json = self._preview_renderers()
        return render_geometry_json(path, self._preview_bounds(label, min_height=min_height))

    def set_json_preview(self, path: Path | None) -> None:
        if self.json_preview_label is None:
            return
        self._json_preview_path = Path(path) if path else None
        label = self.json_preview_label
        preview_bg, preview_fg = self._preview_colors()
        if path is None or not path.exists():
            label.config(image="", text=self._tr("preview_hint"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        path = Path(path)
        data = self._json_preview_data(path, label, min_height=JSON_PREVIEW_MIN_HEIGHT)
        if not data:
            label.config(image="", text=self._tr("preview_unavailable"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        image = PhotoImage(data=data)
        label.config(image=image, text="", bg=preview_bg)
        label.image = image

    def set_preview_art(self, path: Path | None) -> None:
        if self.preview_art_label is None:
            return
        self._preview_art_path = Path(path) if path else None
        label = self.preview_art_label
        preview_bg, preview_fg = self._preview_colors()
        if path is None or not path.exists():
            label.config(image="", text=self._tr("preview_hint"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        path = Path(path)
        data = self._json_preview_data(path, label, min_height=PREVIEW_MIN_HEIGHT)
        if not data:
            label.config(image="", text=self._tr("preview_unavailable"), bg=preview_bg, fg=preview_fg)
            label.image = None
            return
        image = PhotoImage(data=data)
        label.config(image=image, text="", bg=preview_bg)
        label.image = image

    def _schedule_json_preview_refresh(self) -> None:
        if self.json_preview_label is None or self.closed:
            return
        if self._json_preview_job is not None:
            try:
                self.root.after_cancel(self._json_preview_job)
            except Exception:
                pass
        self._json_preview_job = self.root.after(180, self._refresh_json_preview)

    def _refresh_json_preview(self) -> None:
        self._json_preview_job = None
        self.set_json_preview(self._json_preview_path)

    def _schedule_preview_art_refresh(self) -> None:
        if self.preview_art_label is None or self.closed:
            return
        if self._preview_art_job is not None:
            try:
                self.root.after_cancel(self._preview_art_job)
            except Exception:
                pass
        self._preview_art_job = self.root.after(180, self._refresh_preview_art)

    def _refresh_preview_art(self) -> None:
        self._preview_art_job = None
        self.set_preview_art(self._preview_art_path)

    def _stats_for_path(self, path: Path | None) -> dict | None:
        if path is None or not path.exists():
            return None
        grid = self._grid_for_path.get(path)
        merge_mode = self.merge_mode.get()
        try:
            if grid is not None:
                return analyze_pixel_art(grid=grid, merge_mode=merge_mode)
            payload = json.loads(path.read_text(encoding="utf-8"))
            return analyze_pixel_art(payload=payload, merge_mode=merge_mode)
        except Exception:
            return None

    def _format_stats_text(self, stats: dict | None) -> str:
        if stats is None:
            return self._tr("pixel_stats_none")
        lines = [
            self._tr("pixel_stats_filled").format(count=stats.get("filled_pixels", 0)),
            self._tr("pixel_stats_layers").format(
                count=stats.get("merged_layers", 0),
                budget=stats.get("layer_budget", layer_budget_message(int(stats.get("merged_layers", 0)))),
            ),
        ]
        canvas_size = stats.get("canvas_size")
        if canvas_size:
            width, height = canvas_size
            lines.append(self._tr("pixel_stats_canvas").format(width=width, height=height))
        color_counts = stats.get("color_counts") or {}
        lines.append(self._tr("pixel_stats_colors").format(count=len(color_counts)))
        for rgb, count in sorted(color_counts.items(), key=lambda item: (-item[1], item[0])):
            hex_color = f"{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            lines.append(self._tr("pixel_stats_color_entry").format(hex=hex_color, count=count))
        return "\n".join(lines)

    def _refresh_stats_panel(self, path: Path | None = None) -> None:
        if self.stats_text is None:
            return
        if path is None:
            if self.json_list is not None:
                selection = list(self.json_list.curselection())
                if selection:
                    path = self.json_files[selection[0]]
        stats = self._stats_for_path(path)
        self.stats_text.config(text=self._format_stats_text(stats))

    def _cell_size(self) -> int:
        try:
            size = int(self.cell_display_size.get().strip() or "12")
        except ValueError:
            size = 12
        return max(6, min(48, size))

    def _render_editor(self) -> None:
        if self.editor_canvas is None:
            return
        cell = self._cell_size()
        width_px = self.grid.width * cell
        height_px = self.grid.height * cell
        canvas = self.editor_canvas
        canvas.delete("all")
        canvas.config(scrollregion=(0, 0, width_px, height_px))
        checker = self._color("COLOR_PANEL_ALT")
        bg = self._color("COLOR_PREVIEW_BG")
        for y in range(self.grid.height):
            for x in range(self.grid.width):
                x0 = x * cell
                y0 = y * cell
                if (x + y) % 2 == 0:
                    canvas.create_rectangle(x0, y0, x0 + cell, y0 + cell, fill=checker, outline="")
                else:
                    canvas.create_rectangle(x0, y0, x0 + cell, y0 + cell, fill=bg, outline="")
                color = self.grid.get(x, y)
                if color is not None and color[3] > 0:
                    hex_color = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                    inset = max(0, cell // 8)
                    canvas.create_rectangle(
                        x0 + inset,
                        y0 + inset,
                        x0 + cell - inset,
                        y0 + cell - inset,
                        fill=hex_color,
                        outline="",
                    )

    def _canvas_to_grid(self, event) -> tuple[int, int] | None:
        cell = self._cell_size()
        x = int(event.x // cell)
        y = int(event.y // cell)
        if x < 0 or y < 0 or x >= self.grid.width or y >= self.grid.height:
            return None
        return x, y

    def _push_undo(self) -> None:
        self._undo_stack.append((self.grid.width, self.grid.height, self.grid.cells))
        self._redo_stack.clear()
        if len(self._undo_stack) > 48:
            self._undo_stack.pop(0)

    def _apply_tool(self, x: int, y: int) -> None:
        if self.active_tool == "eraser":
            self.grid = self.grid.set(x, y, None)
            return
        if self.active_tool == "fill":
            self._flood_fill(x, y)
            return
        self.grid = self.grid.set(x, y, self._active_color())

    def _flood_fill(self, x: int, y: int) -> None:
        target = self.grid.get(x, y)
        fill = self._active_color()
        if target == fill:
            return
        stack = [(x, y)]
        seen = set()
        while stack:
            cx, cy = stack.pop()
            if (cx, cy) in seen:
                continue
            seen.add((cx, cy))
            if self.grid.get(cx, cy) != target:
                continue
            self.grid = self.grid.set(cx, cy, fill)
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if 0 <= nx < self.grid.width and 0 <= ny < self.grid.height:
                    stack.append((nx, ny))

    def _on_editor_press(self, event) -> None:
        coords = self._canvas_to_grid(event)
        if coords is None:
            return
        self._push_undo()
        self._drag_paint = True
        self._apply_tool(*coords)
        self._render_editor()
        self._refresh_layer_estimate()

    def _on_editor_drag(self, event) -> None:
        if not self._drag_paint or self.active_tool == "fill":
            return
        coords = self._canvas_to_grid(event)
        if coords is None:
            return
        self._apply_tool(*coords)
        self._render_editor()
        self._refresh_layer_estimate()

    def _on_editor_release(self, _event) -> None:
        self._drag_paint = False
