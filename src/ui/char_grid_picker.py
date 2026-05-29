"""Paginated character grid picker for Text vinyl (Google Docs–style)."""

from __future__ import annotations

from typing import Any, Callable

from tkinter import BOTH, LEFT, RIGHT, X, Button, Entry, Frame, Label, StringVar, ttk

from i18n import ui_font_name
from text_char_libraries import GRID_COLUMNS, PAGE_SIZE, filter_library, library_total, paginate_chars


class CharGridPicker:
    """Searchable, paginated grid of insertable characters."""

    def __init__(
        self,
        parent,
        app: Any,
        library_id: str,
        *,
        on_insert: Callable[[str], None],
        label_key: str,
        framed: bool = True,
    ) -> None:
        self.app = app
        self.library_id = library_id
        self.on_insert = on_insert
        self.label_key = label_key
        self._framed = bool(framed)
        self._page = 0
        self._filtered: list[str] = []
        self.search_var = StringVar()
        if self._framed:
            self.frame = ttk.LabelFrame(parent, text=self._tr(label_key))
        else:
            self.frame = Frame(parent)
        self._status_label: Label | None = None
        self._grid_frame: Frame | None = None
        self._grid_buttons: list[Button] = []
        self._build()

    def _tr(self, key: str) -> str:
        from app import tr

        return tr(self.app.lang, key)

    def _color(self, name: str) -> str:
        import app as app_module

        return getattr(app_module, name)

    def _build(self) -> None:
        app = self.app
        if self._framed:
            app.translated.append((self.frame, self.label_key, "text"))

        top = Frame(self.frame)
        top.pack(fill=X, padx=10, pady=(8, 4))
        app._label(top, "text_char_search").pack(side=LEFT)
        search = Entry(top, textvariable=self.search_var, width=18)
        search.pack(side=LEFT, padx=8)
        search.bind("<KeyRelease>", lambda _e: self._on_search_changed())

        self._status_label = app._label(top, "text_char_page_status", theme_role="muted")
        self._status_label.pack(side=RIGHT)

        self._grid_frame = Frame(self.frame)
        self._grid_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 4))

        nav = Frame(self.frame)
        nav.pack(fill=X, padx=10, pady=(0, 8))
        app._button(nav, "text_char_page_prev", self._prev_page).pack(side=LEFT)
        app._button(nav, "text_char_page_next", self._next_page).pack(side=LEFT, padx=8)
        app._button(nav, "text_char_insert", self._insert_focused).pack(side=RIGHT)

        self.search_var.trace_add("write", lambda *_args: self._on_search_changed())
        self.refresh()

    def _on_search_changed(self) -> None:
        self._page = 0
        self.refresh()

    def _prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            self.refresh()

    def _next_page(self) -> None:
        self._page += 1
        self.refresh()

    def _insert_focused(self) -> None:
        for button in self._grid_buttons:
            try:
                if button.focus_get() == button:
                    self.on_insert(button.cget("text"))
                    return
            except Exception:
                pass
        if self._filtered:
            page_chars, _, _ = paginate_chars(self._filtered, self._page)
            if page_chars:
                self.on_insert(page_chars[0])

    def refresh(self) -> None:
        query = self.search_var.get().strip()
        self._filtered = filter_library(self.library_id, query)
        page_chars, self._page, total_pages = paginate_chars(self._filtered, self._page)
        self._render_grid(page_chars)
        if self._status_label is not None:
            total = library_total(self.library_id)
            shown = len(self._filtered)
            self._status_label.config(
                text=self._tr("text_char_page_status").format(
                    page=self._page + 1,
                    pages=total_pages,
                    shown=shown,
                    total=total,
                )
            )

    def _render_grid(self, chars: list[str]) -> None:
        if self._grid_frame is None:
            return
        for button in self._grid_buttons:
            button.destroy()
        self._grid_buttons.clear()

        ui_font = ui_font_name(self.app.lang)
        columns = GRID_COLUMNS
        for index, char in enumerate(chars):
            row = index // columns
            col = index % columns
            btn = Button(
                self._grid_frame,
                text=char,
                width=2,
                font=(ui_font, 11),
                relief="flat",
                bd=1,
                highlightthickness=1,
                highlightbackground=self._color("COLOR_BORDER"),
                bg=self._color("COLOR_PANEL_ALT"),
                fg=self._color("COLOR_TEXT"),
                activebackground=self._color("COLOR_BUTTON_ACTIVE"),
                activeforeground=self._color("COLOR_BUTTON_ACTIVE_FG"),
                command=lambda c=char: self.on_insert(c),
            )
            btn.grid(row=row, column=col, padx=1, pady=1, sticky="nsew")
            btn.bind("<Double-Button-1>", lambda _e, c=char: self.on_insert(c))
            self._grid_buttons.append(btn)

        for col in range(columns):
            self._grid_frame.columnconfigure(col, weight=1)

    def on_language_changed(self) -> None:
        if self._framed:
            try:
                self.frame.config(text=self._tr(self.label_key))
            except Exception:
                pass
        self.refresh()

    def on_theme_changed(self) -> None:
        self.refresh()
