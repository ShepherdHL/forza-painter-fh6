"""
Centralized runtime theme engine for tkinter / ttk widgets.

All visible styling should derive from :class:`ThemeTokens` on the active
:class:`ThemeManager`. Module-level ``COLOR_*`` globals on ``app`` are kept in
sync for legacy call sites during incremental migration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from tkinter import TclError, ttk
from tkinter import (
    Button,
    Canvas,
    Checkbutton,
    Entry,
    Frame,
    Label,
    Listbox,
    Text,
    Tk,
)

from ui.preset_combobox import PresetCombobox
from ui_chrome import DonutGauge
from ui_themes import (
    Palette,
    load_saved_theme_id,
    normalize_theme_id,
    palette_to_color_globals,
    resolve_palette,
    save_theme_id,
)

ForegroundRole = Literal[
    "text",
    "muted",
    "hint",
    "info",
    "warn",
    "accent",
    "success",
    "error",
]

ThemeHook = Callable[["ThemeManager"], None]


@dataclass(frozen=True)
class ThemeTokens:
    """Semantic styling tokens derived from the active palette."""

    # Surfaces
    bg: str
    panel: str
    panel_alt: str
    input: str
    preview_bg: str

    # Text
    text: str
    muted: str
    hint: str
    info: str
    preview_fg: str

    # Accent / feedback
    accent: str
    accent_dark: str
    warn: str
    success: str
    error: str
    select_fg: str

    # Borders / chrome
    border: str
    frame_light: str
    frame_dark: str
    sash: str

    # Buttons
    button: str
    button_active: str
    button_active_fg: str
    button_fg: str

    # Derived semantic aliases
    chrome_bg: str
    tab_selected_bg: str
    tab_selected_fg: str
    tab_idle_bg: str
    tab_idle_fg: str
    focus_ring: str
    disabled_bg: str
    canvas_bg: str
    separator: str

    # Dialogs
    dialog_bg: str
    dialog_surface: str
    dialog_input: str
    dialog_text: str
    dialog_muted: str

    # Dropdown / list
    dropdown_bg: str
    dropdown_input: str
    dropdown_select_bg: str
    dropdown_select_fg: str

    # Scrollbar
    scrollbar_thumb: str
    scrollbar_trough: str

    # Interactive / state-driven (derived from palette)
    selection_border: str
    selection_border_secondary: str
    idle_border: str
    validation_border: str
    indicator_attention: str
    indicator_alert: str
    text_select_bg: str
    text_select_fg: str
    scrollbar_active: str

    # HUD / layered surfaces (CryNet tactical overlays; sensible defaults for all themes)
    surface_hud: str
    overlay_glass: str
    border_illuminated: str
    accent_holographic: str
    text_technical: str
    interactive_glow: str


def tokens_from_palette(palette: Palette, theme_id: str | None = None) -> ThemeTokens:
    from ui_themes import normalize_theme_id

    tid = normalize_theme_id(theme_id)
    is_crynet = tid == "crynet"
    is_unatco = tid == "unatco"
    frame_light = palette.frame_light or palette.border
    frame_dark = palette.frame_dark or palette.panel_alt
    sash = palette.sash or palette.button
    button_active_fg = palette.button_active_fg or palette.text
    button_fg = palette.button_fg or palette.text
    interactive_glow = palette.info if palette.info != palette.text else palette.accent

    tab_idle_bg = palette.panel_alt
    tab_selected_bg = palette.accent_dark
    tab_selected_fg = palette.select_fg
    dropdown_select_bg = palette.accent_dark
    dropdown_select_fg = palette.select_fg
    text_select_bg = palette.accent_dark
    text_select_fg = palette.select_fg
    separator = palette.border
    selection_border = palette.accent
    selection_border_secondary = palette.warn
    idle_border = palette.border
    focus_ring = palette.accent
    indicator_attention = palette.accent
    indicator_alert = palette.warn
    scrollbar_active = palette.accent
    accent_holographic = palette.accent

    if is_crynet:
        tab_idle_bg = palette.bg
        tab_selected_fg = palette.accent
        dropdown_select_fg = palette.accent
        text_select_fg = palette.accent
        separator = frame_light
        selection_border_secondary = frame_light
        idle_border = frame_light
        indicator_alert = palette.error
        scrollbar_active = interactive_glow
    elif is_unatco:
        tab_idle_bg = palette.panel
        tab_selected_bg = palette.accent_dark
        tab_selected_fg = palette.text
        dropdown_select_bg = palette.panel_alt
        dropdown_select_fg = palette.text
        text_select_bg = palette.panel_alt
        text_select_fg = palette.text
        separator = frame_light
        selection_border = frame_light
        selection_border_secondary = palette.border
        idle_border = palette.border
        focus_ring = palette.info
        indicator_attention = palette.success
        indicator_alert = palette.error
        scrollbar_active = frame_light
        accent_holographic = palette.info

    return ThemeTokens(
        bg=palette.bg,
        panel=palette.panel,
        panel_alt=palette.panel_alt,
        input=palette.input,
        preview_bg=palette.preview_bg,
        text=palette.text,
        muted=palette.muted,
        hint=palette.hint,
        info=palette.info,
        preview_fg=palette.preview_fg,
        accent=palette.accent,
        accent_dark=palette.accent_dark,
        warn=palette.warn,
        success=palette.success,
        error=palette.error,
        select_fg=palette.select_fg,
        border=palette.border,
        frame_light=frame_light,
        frame_dark=frame_dark,
        sash=sash,
        button=palette.button,
        button_active=palette.button_active,
        button_active_fg=button_active_fg,
        button_fg=button_fg,
        chrome_bg=palette.bg,
        tab_selected_bg=tab_selected_bg,
        tab_selected_fg=tab_selected_fg,
        tab_idle_bg=tab_idle_bg,
        tab_idle_fg=palette.muted,
        focus_ring=focus_ring,
        disabled_bg=palette.panel_alt,
        canvas_bg=palette.panel,
        separator=separator,
        dialog_bg=palette.bg,
        dialog_surface=palette.panel,
        dialog_input=palette.input,
        dialog_text=palette.text,
        dialog_muted=palette.muted,
        dropdown_bg=palette.panel,
        dropdown_input=palette.input,
        dropdown_select_bg=dropdown_select_bg,
        dropdown_select_fg=dropdown_select_fg,
        scrollbar_thumb=palette.panel_alt,
        scrollbar_trough=palette.bg,
        selection_border=selection_border,
        selection_border_secondary=selection_border_secondary,
        idle_border=idle_border,
        validation_border=palette.warn,
        indicator_attention=indicator_attention,
        indicator_alert=indicator_alert,
        text_select_bg=text_select_bg,
        text_select_fg=text_select_fg,
        scrollbar_active=scrollbar_active,
        surface_hud=palette.panel_alt,
        overlay_glass=palette.panel,
        border_illuminated=frame_light,
        accent_holographic=accent_holographic,
        text_technical=palette.text,
        interactive_glow=interactive_glow,
    )


class ThemeManager:
    """Owns the active palette/tokens and applies them across the widget tree."""

    def __init__(self, root: Tk, persist_root: Path, *, app: Any | None = None) -> None:
        self.root = root
        self.persist_root = persist_root
        self.app = app
        self.theme_id = normalize_theme_id(load_saved_theme_id(persist_root))
        self.palette = resolve_palette(self.theme_id)
        self.tokens = tokens_from_palette(self.palette, self.theme_id)
        self._hooks: list[ThemeHook] = []

    def register(self, hook: ThemeHook) -> None:
        if hook not in self._hooks:
            self._hooks.append(hook)

    def fg(self, role: ForegroundRole | str) -> str:
        mapping = {
            "text": self.tokens.text,
            "muted": self.tokens.muted,
            "hint": self.tokens.hint,
            "info": self.tokens.info,
            "warn": self.tokens.warn,
            "accent": self.tokens.accent,
            "success": self.tokens.success,
            "error": self.tokens.error,
        }
        return mapping.get(str(role), self.tokens.text)

    def sync_legacy_globals(self) -> None:
        import sys

        app_module = sys.modules.get("app")
        if app_module is None:
            return
        for name, value in palette_to_color_globals(self.palette).items():
            setattr(app_module, name, value)

    def apply(self, theme_id: str | None = None) -> None:
        self.theme_id = normalize_theme_id(theme_id or self.theme_id)
        self.palette = resolve_palette(self.theme_id)
        self.tokens = tokens_from_palette(self.palette, self.theme_id)
        save_theme_id(self.persist_root, self.theme_id)
        self.sync_legacy_globals()

        try:
            self.root.configure(bg=self.tokens.bg)
        except TclError:
            pass

        self.configure_ttk()
        self.apply_widget(self.root)

        app = self.app
        if app is not None:
            self._refresh_header_chrome(app)
            if hasattr(app, "_paint_tab_strip"):
                app._paint_tab_strip()

        for hook in self._hooks:
            try:
                hook(self)
            except Exception:
                pass

        from ui.theme_states import refresh_app_interactive_ui, refresh_ttk_widgets

        refresh_ttk_widgets(self.root, self)
        if app is not None:
            refresh_app_interactive_ui(app, self)

        try:
            self.root.update_idletasks()
        except TclError:
            pass

    def configure_ttk(self) -> None:
        app = self.app
        lang = getattr(app, "lang", "en") if app is not None else "en"
        from i18n import ui_font_name

        ui_font = ui_font_name(lang)
        t = self.tokens
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        try:
            style.configure(".", background=t.bg, foreground=t.text, fieldbackground=t.input)
            style.configure("TFrame", background=t.bg)
            style.configure("TNotebook", background=t.bg, borderwidth=0)
            style.configure("Primary.TNotebook", background=t.bg, borderwidth=0, tabmargins=(0, 0, 0, 0))
            style.configure(
                "Primary.TNotebook.Tab",
                padding=(22, 10),
                font=(ui_font, 10, "bold"),
                background=t.tab_idle_bg,
                foreground=t.text_technical,
                borderwidth=0,
            )
            style.map(
                "Primary.TNotebook.Tab",
                background=[
                    ("selected", t.tab_selected_bg),
                    ("active", t.tab_selected_bg),
                    ("!selected", t.tab_idle_bg),
                ],
                foreground=[
                    ("selected", t.tab_selected_fg),
                    ("active", t.tab_selected_fg),
                    ("!selected", t.tab_idle_fg),
                ],
            )
            style.configure(
                "Script.TNotebook",
                background=t.bg,
                borderwidth=0,
                tabmargins=(0, 0, 0, 0),
            )
            style.configure(
                "Script.TNotebook.Tab",
                padding=(14, 8),
                font=(ui_font, 9, "bold"),
                background=t.tab_idle_bg,
                foreground=t.text_technical,
                borderwidth=0,
            )
            style.map(
                "Script.TNotebook.Tab",
                background=[
                    ("selected", t.tab_selected_bg),
                    ("active", t.tab_selected_bg),
                    ("!selected", t.tab_idle_bg),
                ],
                foreground=[
                    ("selected", t.tab_selected_fg),
                    ("active", t.tab_selected_fg),
                    ("!selected", t.tab_idle_fg),
                ],
            )
            style.configure(
                "TLabelframe",
                background=t.panel,
                foreground=t.text,
                bordercolor=t.border,
                lightcolor=t.frame_light,
                darkcolor=t.frame_dark,
                relief="solid",
            )
            style.configure(
                "TLabelframe.Label",
                background=t.panel,
                foreground=t.text,
                font=(ui_font, 10, "bold"),
            )
            style.configure(
                "TCombobox",
                fieldbackground=t.input,
                background=t.panel_alt,
                foreground=t.text_technical,
                arrowcolor=t.muted,
                bordercolor=t.border_illuminated,
                lightcolor=t.border_illuminated,
                darkcolor=t.border,
            )
            style.map(
                "TCombobox",
                fieldbackground=[("readonly", t.input), ("focus", t.input)],
                foreground=[("readonly", t.text_technical)],
                selectbackground=[("readonly", t.dropdown_select_bg)],
                selectforeground=[("readonly", t.dropdown_select_fg)],
                bordercolor=[("focus", t.focus_ring)],
            )
            style.configure(
                "TScrollbar",
                background=t.scrollbar_thumb,
                troughcolor=t.scrollbar_trough,
                bordercolor=t.border_illuminated,
                arrowcolor=t.muted,
            )
            style.map(
                "TScrollbar",
                background=[("active", t.scrollbar_active), ("pressed", t.scrollbar_active)],
                arrowcolor=[("active", t.interactive_glow), ("pressed", t.interactive_glow)],
            )
            style.configure(
                "TButton",
                background=t.button,
                foreground=t.button_fg,
                bordercolor=t.border_illuminated,
                lightcolor=t.frame_light,
                darkcolor=t.frame_dark,
            )
            style.map(
                "TButton",
                background=[("active", t.button_active), ("pressed", t.button_active), ("disabled", t.panel_alt)],
                foreground=[("disabled", t.muted)],
            )
            style.configure("TPanedwindow", background=t.border)
        except Exception:
            pass

        try:
            style.configure("Sash", sashthickness=5, gripcount=0, background=t.sash)
            style.map("Sash", background=[("active", t.interactive_glow)])
        except Exception:
            pass

    def apply_widget(self, widget: Any) -> None:
        app = self.app
        t = self.tokens
        try:
            if isinstance(widget, PresetCombobox):
                widget.apply_theme(
                    panel_bg=t.dropdown_bg,
                    input_bg=t.dropdown_input,
                    text_fg=t.text,
                    select_bg=t.dropdown_select_bg,
                    select_fg=t.dropdown_select_fg,
                    border_fg=t.border,
                    muted_fg=t.muted,
                )
            elif isinstance(widget, Frame):
                bg = self._frame_bg(widget)
                opts: dict[str, Any] = {"bg": bg}
                selection = getattr(widget, "_theme_selection", None)
                try:
                    thickness = int(widget.cget("highlightthickness") or 0)
                except TclError:
                    thickness = 0
                if selection == "selected":
                    opts["highlightbackground"] = t.selection_border
                    opts["highlightthickness"] = 3
                elif selection == "idle" or thickness > 0:
                    opts["highlightbackground"] = t.idle_border
                    if selection == "idle":
                        opts["highlightthickness"] = 1
                widget.configure(**opts)
            elif isinstance(widget, Label):
                if app is not None and widget in self._preview_labels(app):
                    widget.configure(bg=t.preview_bg, fg=t.preview_fg)
                elif app is not None and widget is getattr(app, "update_indicator", None):
                    status = getattr(widget, "_theme_indicator_status", "default")
                    fg = t.indicator_attention if status == "available" else (
                        t.indicator_alert if status == "failed" else t.muted
                    )
                    widget.configure(bg=t.panel, fg=fg)
                elif getattr(widget, "_preset_colored", False):
                    widget.configure(bg=self._parent_bg(widget))
                else:
                    emphasis = getattr(widget, "_theme_emphasis", None)
                    if emphasis in ("accent", "warn", "muted", "text", "hint", "info", "success", "error"):
                        fg = self.fg(emphasis)
                    else:
                        fg = self._label_fg(widget)
                    label_opts: dict[str, Any] = {
                        "bg": self._parent_bg(widget),
                        "fg": fg,
                    }
                    selection = getattr(widget, "_theme_selection", None)
                    if selection == "selected":
                        label_opts["highlightbackground"] = (
                            t.selection_border_secondary
                            if getattr(widget, "_theme_selection_secondary", False)
                            else t.selection_border
                        )
                        label_opts["highlightthickness"] = (
                            2 if getattr(widget, "_theme_selection_secondary", False) else 3
                        )
                    elif selection == "none":
                        label_opts["highlightthickness"] = 0
                    widget.configure(**label_opts)
            elif isinstance(widget, Button):
                if getattr(widget, "_theme_managed", False):
                    pass
                else:
                    widget.configure(
                        bg=t.button,
                        fg=t.button_fg,
                        disabledforeground=t.muted,
                        activebackground=t.button_active,
                        activeforeground=t.button_active_fg,
                        relief="flat",
                        bd=0,
                        highlightbackground=t.border,
                        highlightcolor=t.focus_ring,
                    )
            elif isinstance(widget, Checkbutton):
                parent_bg = self._parent_bg(widget)
                widget.configure(
                    bg=parent_bg,
                    fg=t.text,
                    disabledforeground=t.muted,
                    activebackground=parent_bg,
                    activeforeground=t.text,
                    selectcolor=t.input,
                    relief="flat",
                    highlightbackground=t.border,
                    highlightcolor=t.focus_ring,
                )
            elif isinstance(widget, Entry):
                invalid = getattr(widget, "_theme_invalid", False)
                widget.configure(
                    bg=t.input,
                    fg=t.text,
                    insertbackground=t.text,
                    disabledbackground=t.disabled_bg,
                    disabledforeground=t.muted,
                    readonlybackground=t.input,
                    relief="flat",
                    highlightthickness=1,
                    highlightbackground=t.validation_border if invalid else t.idle_border,
                    highlightcolor=t.focus_ring,
                )
                if app is not None:
                    from app import UI_INPUT_FONT

                    widget.configure(font=UI_INPUT_FONT)
            elif isinstance(widget, Listbox):
                from app import UI_INPUT_FONT

                widget.configure(
                    bg=t.input,
                    fg=t.text,
                    selectbackground=t.text_select_bg,
                    selectforeground=t.text_select_fg,
                    highlightthickness=1,
                    highlightbackground=t.border,
                    relief="flat",
                    font=UI_INPUT_FONT,
                )
            elif isinstance(widget, Text):
                from app import UI_INPUT_FONT, UI_LOG_FONT

                log = getattr(app, "log", None) if app is not None else None
                log_font = UI_LOG_FONT if widget is log else UI_INPUT_FONT
                widget.configure(
                    bg=t.input,
                    fg=t.text,
                    insertbackground=t.text,
                    selectbackground=t.text_select_bg,
                    selectforeground=t.text_select_fg,
                    highlightthickness=1,
                    highlightbackground=t.border,
                    relief="flat",
                    font=log_font,
                )
            elif isinstance(widget, DonutGauge):
                fill = (
                    t.success
                    if getattr(widget, "_donut_role", None) == "cpu"
                    else t.accent_holographic
                )
                widget.set_scheme(
                    track_color=t.border_illuminated,
                    fill_color=fill,
                    bg_color=t.bg if widget.master is self.root else self._parent_bg(widget),
                    text_color=t.text_technical,
                    muted_color=t.muted,
                )
            elif isinstance(widget, Canvas):
                chrome_bg = getattr(widget, "_chrome_bg", None)
                if chrome_bg is not None:
                    widget._chrome_bg = t.chrome_bg  # type: ignore[attr-defined]
                    widget.configure(bg=t.chrome_bg, highlightthickness=0)
                    if widget is getattr(app, "_tab_strip_canvas", None) if app is not None else None:
                        if hasattr(app, "_paint_tab_strip"):
                            app._paint_tab_strip()
                    elif hasattr(widget, "_chrome_line"):
                        widget._chrome_line = t.separator  # type: ignore[attr-defined]
                        widget.event_generate("<Configure>")
                else:
                    widget.configure(bg=t.canvas_bg, highlightthickness=0)
        except (TclError, Exception):
            pass

        for child in widget.winfo_children():
            self.apply_widget(child)

    def _frame_bg(self, widget: Frame) -> str:
        t = self.tokens
        surface = getattr(widget, "_theme_surface", None)
        if surface == "chrome":
            return t.chrome_bg
        if surface == "hud":
            return t.surface_hud
        if surface == "glass":
            return t.overlay_glass
        if surface == "panel":
            return t.panel
        if surface == "panel_alt":
            return t.panel_alt
        if surface == "bg":
            return t.bg
        if getattr(widget, "_chrome_bg_locked", False):
            return t.chrome_bg
        if widget.master is self.root:
            try:
                if int(widget.cget("highlightthickness") or 0) > 0:
                    return t.panel
            except TclError:
                pass
            return t.bg
        return t.panel

    def _parent_bg(self, widget: Any) -> str:
        try:
            return widget.master.cget("bg")
        except Exception:
            return self.tokens.panel

    def _label_fg(self, widget: Label) -> str:
        role = getattr(widget, "_theme_role", None)
        if role:
            return self.fg(role)
        return self.tokens.text

    @staticmethod
    def _preview_labels(app: Any) -> tuple:
        return (
            getattr(app, "generate_source_before_preview", None),
            getattr(app, "generate_source_after_preview", None),
            getattr(app, "generate_result_without_preview", None),
            getattr(app, "generate_result_with_preview", None),
            getattr(app, "import_preview_label", None),
        )

    @staticmethod
    def _update_indicator_fg(app: Any) -> str:
        status = getattr(app, "update_state", {}).get("status")
        t = app.themes.tokens if hasattr(app, "themes") else tokens_from_palette(resolve_palette())
        if status == "available":
            return t.accent
        if status == "failed":
            return t.warn
        return t.warn

    @staticmethod
    def _refresh_header_chrome(app: Any) -> None:
        rule = getattr(app, "_header_rule_canvas", None)
        if rule is None:
            return
        t = app.themes.tokens
        rule._chrome_bg = t.chrome_bg  # type: ignore[attr-defined]
        rule._chrome_line = t.separator  # type: ignore[attr-defined]
        try:
            rule.configure(bg=t.chrome_bg)
            rule.event_generate("<Configure>")
        except Exception:
            pass
