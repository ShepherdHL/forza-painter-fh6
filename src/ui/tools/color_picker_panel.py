"""Standalone image color picker (file-based, isolated from the Generate JSON image list)."""

from __future__ import annotations

import io
from pathlib import Path

from tkinter import BOTH, HORIZONTAL, LEFT, X, Button, Canvas, Entry, Frame, Label, StringVar, filedialog, ttk

from forza_colors import describe_color, hex_to_rgb
from ui.tools.panel_base import ToolPanel, build_tool_hint
from utils import load_pillow


class ColorPickerToolPanel(ToolPanel):
    panel_id = "color_picker"
    tab_key = "tools_panel_color_picker"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.image_path = StringVar()
        self.pixel_size = StringVar(value="1")
        self.hex_var = StringVar(value="#808080")
        self.rgb_r_var = StringVar(value="128")
        self.rgb_g_var = StringVar(value="128")
        self.rgb_b_var = StringVar(value="128")
        self.hsl_h_var = StringVar()
        self.hsl_s_var = StringVar()
        self.hsl_l_var = StringVar()
        self.hsb_h_var = StringVar()
        self.hsb_s_var = StringVar()
        self.hsb_b_var = StringVar()
        self.forza_h_var = StringVar()
        self.forza_s_var = StringVar()
        self.forza_b_var = StringVar()
        self._saved_history: list[str] = []
        self._pil_image = None
        self._photo = None
        self._canvas_scale = 1.0
        self._canvas_offset = (0, 0)
        self._canvas_size = (1, 1)
        self._canvas: Canvas | None = None
        self._swatch: Label | None = None
        self._history_frame: Frame | None = None
    def build(self, parent: Frame) -> None:
        app = self.app
        paned = app._create_paned(parent, orient=HORIZONTAL, layout_key="tools_color_horizontal", padx=10, pady=10)
        left = Frame(paned)
        right = Frame(paned)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        build_tool_hint(left, app, "tools_color_picker_hint")

        path_row = Frame(left)
        path_row.pack(fill=X, pady=(0, 6))
        Entry(path_row, textvariable=self.image_path).pack(side=LEFT, fill=X, expand=True)
        app._button(path_row, "tools_color_browse", self._browse_image).pack(side=LEFT, padx=8)

        size_row = Frame(left)
        size_row.pack(fill=X, pady=(0, 6))
        app._label(size_row, "colors_pixel_size").pack(side=LEFT)
        Entry(size_row, textvariable=self.pixel_size, width=6).pack(side=LEFT, padx=8)

        canvas_host = Frame(left)
        canvas_host.pack(fill=BOTH, expand=True)
        self._canvas = Canvas(
            canvas_host,
            bg=self._color("COLOR_PANEL"),
            highlightthickness=1,
            highlightbackground=self._color("COLOR_BORDER"),
            cursor="crosshair",
        )
        self._canvas.pack(fill=BOTH, expand=True)
        self._canvas.bind("<Button-1>", self._on_click)
        self._canvas.bind("<Motion>", self._on_hover)
        self._canvas.bind("<Configure>", self._redraw)
        self._canvas.bind("<Shift-MouseWheel>", self._on_wheel)
        self._canvas.bind("<Enter>", lambda _e: self._canvas.focus_set())

        app._label(left, "colors_click_hint", anchor="w", theme_role="muted").pack(fill=X, pady=(6, 0))

        swatch_row = Frame(right)
        swatch_row.pack(fill=X, pady=(0, 10))
        self._swatch = Label(swatch_row, text="", width=10, height=2, bg="#808080", relief="solid", bd=1)
        self._swatch.pack(side=LEFT, padx=(0, 12))
        actions = Frame(swatch_row)
        actions.pack(side=LEFT, fill=X, expand=True)
        app._button(actions, "colors_copy_hex", lambda: self._copy(self.hex_var.get())).pack(fill=X, pady=2)
        app._button(actions, "colors_copy_forza", self._copy_forza).pack(fill=X, pady=2)
        app._button(actions, "colors_open_bang", self._open_bang).pack(fill=X, pady=2)

        values = ttk.LabelFrame(right, text=self._tr("colors_values"))
        app.translated.append((values, "colors_values", "text"))
        values.pack(fill=X)
        grid = Frame(values)
        grid.pack(fill=X, padx=10, pady=8)
        self._value_row(grid, 0, "colors_hex", self.hex_var)
        self._value_row(grid, 1, "colors_rgb", self.rgb_r_var, extra=(self.rgb_g_var, self.rgb_b_var))
        self._value_row(grid, 2, "colors_hsl", self.hsl_h_var, extra=(self.hsl_s_var, self.hsl_l_var))
        self._value_row(grid, 3, "colors_hsb", self.hsb_h_var, extra=(self.hsb_s_var, self.hsb_b_var))
        self._value_row(grid, 4, "colors_forza", self.forza_h_var, extra=(self.forza_s_var, self.forza_b_var))

        self._apply_formats(describe_color(128, 128, 128))
        saved_row = Frame(right)
        saved_row.pack(fill=X, pady=(8, 0))
        app._label(saved_row, "colors_saved_history", anchor="w", theme_role="muted").pack(fill=X)
        self._history_frame = Frame(saved_row)
        self._history_frame.pack(fill=X, pady=(4, 0))

        self.image_path.trace_add("write", lambda *_args: self._refresh_image())

    def on_tab_activated(self) -> None:
        if self._canvas is not None:
            self._redraw()

    def _value_row(self, parent, row, label_key, primary_var, extra=()):
        self.app._label(parent, label_key, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        Entry(parent, textvariable=primary_var, width=14, state="readonly").grid(row=row, column=1, sticky="w", pady=4)
        column = 2
        for var in extra:
            Entry(parent, textvariable=var, width=8, state="readonly").grid(row=row, column=column, sticky="w", padx=(6, 0), pady=4)
            column += 1

    def _browse_image(self) -> None:
        path = filedialog.askopenfilename(
            title=self._tr("tools_color_browse"),
            filetypes=[
                (self._tr("tools_color_file_filter"), "*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.gif;*.tif;*.tiff"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.image_path.set(path)

    def _open_bang(self) -> None:
        import webbrowser

        webbrowser.open("https://dxbang.github.io/forza-colors/")

    def _copy(self, value: str) -> None:
        self.app._copy_to_clipboard(value.strip())

    def _copy_forza(self) -> None:
        text = f"{self.forza_h_var.get()}, {self.forza_s_var.get()}, {self.forza_b_var.get()}"
        self.app._copy_to_clipboard(text)

    def _apply_formats(self, formats) -> None:
        self.hex_var.set(formats.hex)
        self.rgb_r_var.set(str(formats.rgb.r))
        self.rgb_g_var.set(str(formats.rgb.g))
        self.rgb_b_var.set(str(formats.rgb.b))
        self.hsl_h_var.set(f"{formats.hsl_h:.2f}")
        self.hsl_s_var.set(f"{formats.hsl_s:.2f}")
        self.hsl_l_var.set(f"{formats.hsl_l:.2f}")
        self.hsb_h_var.set(f"{formats.hsb_h:.2f}")
        self.hsb_s_var.set(f"{formats.hsb_s:.2f}")
        self.hsb_b_var.set(f"{formats.hsb_b:.2f}")
        self.forza_h_var.set(f"{formats.forza_h:.2f}")
        self.forza_s_var.set(f"{formats.forza_s:.2f}")
        self.forza_b_var.set(f"{formats.forza_b:.2f}")
        if self._swatch is not None:
            try:
                self._swatch.config(bg=formats.hex)
            except Exception:
                pass

    def _pixel_size(self) -> int:
        try:
            size = int(str(self.pixel_size.get()).strip())
        except ValueError:
            size = 1
        return max(1, min(64, size))

    def _on_wheel(self, event) -> None:
        delta = 1 if event.delta > 0 else -1
        self.pixel_size.set(str(self._pixel_size() + delta))

    def _load_pil(self, path: Path):
        loaded = load_pillow()
        if not loaded:
            return None
        Image, _ImageDraw = loaded
        try:
            with Image.open(path) as image:
                return image.convert("RGB")
        except Exception:
            return None

    def _refresh_image(self) -> None:
        if self._canvas is None:
            return
        self._pil_image = None
        self._photo = None
        raw = str(self.image_path.get()).strip()
        if not raw:
            self._redraw()
            return
        path = Path(raw)
        if path.is_file():
            self._pil_image = self._load_pil(path)
        self._redraw()

    def _resample(self):
        loaded = load_pillow()
        if not loaded:
            return None
        Image, _ImageDraw = loaded
        if hasattr(Image, "Resampling"):
            return Image.Resampling.LANCZOS
        return Image.LANCZOS

    def _redraw(self, _event=None) -> None:
        if self._canvas is None:
            return
        canvas = self._canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        self._canvas_size = (width, height)
        if self._pil_image is None:
            canvas.create_text(
                width // 2,
                height // 2,
                text=self._tr("tools_color_no_image"),
                fill=self._color("COLOR_MUTED"),
                font=("Segoe UI", 11),
            )
            return
        resample = self._resample()
        image = self._pil_image.copy()
        if resample is not None:
            image.thumbnail((width, height), resample)
        disp_w, disp_h = image.size
        offset_x = (width - disp_w) // 2
        offset_y = (height - disp_h) // 2
        self._canvas_offset = (offset_x, offset_y)
        self._canvas_scale = self._pil_image.width / max(1, disp_w)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        from tkinter import PhotoImage

        self._photo = PhotoImage(data=buffer.getvalue())
        canvas.create_image(offset_x, offset_y, anchor="nw", image=self._photo)

    def _canvas_to_image_xy(self, canvas_x: int, canvas_y: int):
        offset_x, offset_y = self._canvas_offset
        if self._pil_image is None:
            return None
        local_x = canvas_x - offset_x
        local_y = canvas_y - offset_y
        if self._photo is None:
            return None
        resample = self._resample()
        disp = self._pil_image.copy()
        if resample is not None:
            disp.thumbnail(self._canvas_size, resample)
        if local_x < 0 or local_y < 0 or local_x >= disp.width or local_y >= disp.height:
            return None
        img_x = int(local_x * self._canvas_scale)
        img_y = int(local_y * self._canvas_scale)
        img_x = max(0, min(self._pil_image.width - 1, img_x))
        img_y = max(0, min(self._pil_image.height - 1, img_y))
        return img_x, img_y

    def _sample(self, canvas_x: int, canvas_y: int):
        coords = self._canvas_to_image_xy(canvas_x, canvas_y)
        if coords is None or self._pil_image is None:
            return None
        img_x, img_y = coords
        size = self._pixel_size()
        half = size // 2
        left = max(0, img_x - half)
        top = max(0, img_y - half)
        right = min(self._pil_image.width, left + size)
        bottom = min(self._pil_image.height, top + size)
        region = self._pil_image.crop((left, top, right, bottom))
        pixels = list(region.getdata())
        if not pixels:
            return None
        total_r = total_g = total_b = 0
        for r, g, b in pixels:
            total_r += r
            total_g += g
            total_b += b
        count = len(pixels)
        return describe_color(total_r // count, total_g // count, total_b // count)

    def _on_hover(self, event) -> None:
        formats = self._sample(event.x, event.y)
        if formats and self._swatch is not None:
            try:
                self._swatch.config(bg=formats.hex)
            except Exception:
                pass

    def _on_click(self, event) -> None:
        formats = self._sample(event.x, event.y)
        if not formats:
            return
        self._apply_formats(formats)
        hex_value = formats.hex.lower()
        if hex_value in self._saved_history:
            self._saved_history.remove(hex_value)
        self._saved_history.insert(0, hex_value)
        self._saved_history = self._saved_history[:16]
        self._render_history()
        self.app.log_line(self._tr("colors_saved", hex=hex_value))

    def on_theme_changed(self) -> None:
        if self._canvas is not None:
            self._canvas.configure(
                bg=self._color("COLOR_PANEL"),
                highlightbackground=self._color("COLOR_BORDER"),
            )
        self._redraw()
        self._render_history()

    def _render_history(self) -> None:
        if self._history_frame is None:
            return
        for child in self._history_frame.winfo_children():
            child.destroy()
        for hex_value in self._saved_history:
            try:
                btn = Button(
                    self._history_frame,
                    text="",
                    width=3,
                    height=1,
                    bg=hex_value,
                    activebackground=hex_value,
                    relief="solid",
                    bd=1,
                    highlightthickness=1,
                    highlightbackground=self._color("COLOR_BORDER"),
                    command=lambda value=hex_value: self._recall(value),
                )
                btn.pack(side=LEFT, padx=(0, 4))
            except Exception:
                pass

    def _recall(self, hex_value: str) -> None:
        rgb = hex_to_rgb(hex_value)
        if rgb is None:
            return
        self._apply_formats(describe_color(rgb.r, rgb.g, rgb.b))
