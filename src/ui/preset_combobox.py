"""Quality-preset dropdown with per-row text colors (ttk.Combobox cannot do this)."""

from __future__ import annotations

from dataclasses import dataclass
from tkinter import END, Frame, Label, Listbox, Toplevel
from tkinter import StringVar
from typing import Callable

from preset_preview import preset_index_from_path, preset_label_color
from ui_themes import DEFAULT_THEME_ID, palette_to_color_globals, resolve_palette


@dataclass(frozen=True)
class PresetComboItem:
    label: str
    fg: str | None = None


class PresetCombobox(Frame):
    """Read-only preset picker: combobox-style field + list popup."""

    def __init__(
        self,
        parent,
        textvariable: StringVar,
        *,
        on_select: Callable | None = None,
        font=("Segoe UI", 10),
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._textvariable = textvariable
        self._on_select = on_select
        self._font = font
        self._items: list[PresetComboItem] = []
        self._popup: Toplevel | None = None
        self._listbox: Listbox | None = None
        defaults = palette_to_color_globals(resolve_palette(DEFAULT_THEME_ID))
        self._panel_bg = defaults["COLOR_PANEL"]
        self._input_bg = defaults["COLOR_INPUT"]
        self._border_color = defaults["COLOR_BORDER"]
        self._muted_fg = defaults["COLOR_MUTED"]
        self._default_fg = defaults["COLOR_TEXT"]
        self._select_bg = defaults["COLOR_ACCENT_DARK"]
        self._select_fg = defaults["COLOR_SELECT_FG"]

        self._shell = Frame(
            self,
            highlightthickness=1,
            highlightbackground=self._border_color,
            highlightcolor=self._border_color,
            bg=self._input_bg,
        )
        self._shell.pack(fill="both", expand=True)

        self._field = Frame(self._shell, bg=self._input_bg)
        self._field.pack(fill="both", expand=True)

        self._display = Label(
            self._field,
            anchor="w",
            font=self._font,
            padx=8,
            pady=5,
            bg=self._input_bg,
            fg=self._default_fg,
        )
        self._display._preset_colored = True
        self._display.pack(side="left", fill="both", expand=True)

        self._separator = Frame(self._field, width=1, bg=self._border_color)
        self._separator.pack(side="right", fill="y", padx=0, pady=2)

        self._chevron_host = Frame(self._field, width=34, bg=self._input_bg)
        self._chevron_host.pack(side="right", fill="y")
        self._chevron_host.pack_propagate(False)

        self._chevron = Label(
            self._chevron_host,
            text="▾",
            font=(self._font[0], int(self._font[1]) + 2 if len(self._font) > 1 else 12, "bold"),
            bg=self._input_bg,
            fg=self._muted_fg,
            cursor="hand2",
        )
        self._chevron.pack(fill="both", expand=True)

        self._textvariable.trace_add("write", self._sync_display)
        for widget in (self._shell, self._field, self._display, self._chevron_host, self._chevron):
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", self._on_click)

    def _on_click(self, event) -> None:
        if event.widget is self._separator:
            return
        self._toggle_popup()

    def set_items(self, items: list[PresetComboItem]) -> None:
        self._items = list(items)
        self._sync_display()

    def set_profiles(self, profiles) -> None:
        items: list[PresetComboItem] = []
        for profile in profiles:
            path = profile.get("path") if hasattr(profile, "get") else profile["path"]
            preset_index = None
            if path is not None:
                preset_index = preset_index_from_path(path)
            label = profile.get("label") if hasattr(profile, "get") else profile["label"]
            items.append(PresetComboItem(label=str(label), fg=preset_label_color(preset_index)))
        self.set_items(items)

    def apply_theme(
        self,
        *,
        panel_bg: str,
        input_bg: str,
        text_fg: str,
        select_bg: str,
        select_fg: str,
        border_fg: str | None = None,
        muted_fg: str | None = None,
    ) -> None:
        self._panel_bg = panel_bg
        self._input_bg = input_bg
        self._default_fg = text_fg
        self._select_bg = select_bg
        self._select_fg = select_fg
        if border_fg is not None:
            self._border_color = border_fg
        if muted_fg is not None:
            self._muted_fg = muted_fg
        self.configure(bg=panel_bg)
        border = self._border_color
        for frame in (self._shell, self._field, self._chevron_host):
            frame.configure(bg=input_bg, highlightbackground=border, highlightcolor=border)
        self._shell.configure(highlightthickness=1)
        self._separator.configure(bg=border)
        self._display.configure(bg=input_bg)
        self._chevron.configure(bg=input_bg, fg=self._muted_fg)
        if self._listbox is not None and self._listbox.winfo_exists():
            self._listbox.configure(
                bg=input_bg,
                selectbackground=select_bg,
                selectforeground=select_fg,
            )
        self._sync_display()

    def _current_fg(self) -> str:
        label = self._textvariable.get()
        for item in self._items:
            if item.label == label and item.fg:
                return item.fg
        return self._default_fg

    def _sync_display(self, *_args) -> None:
        label = self._textvariable.get()
        self._display.configure(text=label or " ", fg=self._current_fg())

    def _toggle_popup(self) -> None:
        if self._popup is not None and self._popup.winfo_exists():
            self._close_popup()
            return
        self._open_popup()

    def _open_popup(self) -> None:
        if not self._items:
            return
        self._popup = Toplevel(self)
        self._popup.wm_overrideredirect(True)
        self._popup.configure(bg=self._border_color)
        width = max(self.winfo_width(), 320)
        height = min(max(len(self._items), 1) * 22 + 4, 280)
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self._popup.geometry(f"{width}x{height}+{x}+{y}")

        self._listbox = Listbox(
            self._popup,
            activestyle="none",
            exportselection=False,
            font=self._font,
            bg=self._input_bg,
            fg=self._default_fg,
            selectbackground=self._select_bg,
            selectforeground=self._select_fg,
            highlightthickness=1,
            highlightbackground=self._border_color,
            relief="flat",
            borderwidth=0,
        )
        self._listbox.pack(fill="both", expand=True, padx=1, pady=1)
        current = self._textvariable.get()
        select_index = 0
        for index, item in enumerate(self._items):
            self._listbox.insert(END, item.label)
            if item.fg:
                self._listbox.itemconfig(index, fg=item.fg)
            if item.label == current:
                select_index = index
        self._listbox.selection_set(select_index)
        self._listbox.activate(select_index)
        self._listbox.see(select_index)
        self._listbox.bind("<<ListboxSelect>>", self._on_list_pick)
        self._listbox.bind("<Escape>", lambda _e: self._close_popup())
        self._popup.bind("<FocusOut>", self._on_popup_focus_out)
        self._listbox.focus_set()

    def _on_popup_focus_out(self, _event=None) -> None:
        self.after_idle(self._close_popup_if_focus_left)

    def _close_popup_if_focus_left(self) -> None:
        if self._popup is None or not self._popup.winfo_exists():
            return
        focus = self._popup.focus_displayof()
        if focus is None:
            self._close_popup()
            return
        try:
            widget = self._popup.nametowidget(str(focus))
            if widget is self._listbox or widget.master is self._popup:
                return
        except Exception:
            pass
        self._close_popup()

    def _on_list_pick(self, _event=None) -> None:
        if self._listbox is None:
            return
        selection = self._listbox.curselection()
        if not selection:
            return
        index = int(selection[0])
        if index < 0 or index >= len(self._items):
            return
        self._textvariable.set(self._items[index].label)
        self._close_popup()
        if self._on_select is not None:
            self._on_select()

    def _close_popup(self) -> None:
        if self._popup is not None:
            try:
                self._popup.destroy()
            except Exception:
                pass
        self._popup = None
        self._listbox = None
