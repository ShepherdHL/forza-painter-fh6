"""Top-level hub tab bar with optional far-right tab (Dev Tools)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from tkinter import BOTH, LEFT, RIGHT, X, Button, Frame

if TYPE_CHECKING:
    from ui.theme_manager import ThemeManager

Align = Literal["left", "right"]


class HubBar:
    """Notebook-style hub switcher; ``align='right'`` tabs pin to the window's right edge."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self._entries: list[tuple[Frame, str, Align]] = []
        self._buttons: dict[Frame, Button] = {}
        self._active: Frame | None = None
        self._bar: Frame | None = None
        self._left: Frame | None = None
        self._right: Frame | None = None
        self._content: Frame | None = None

    def attach_content(self, parent: Frame) -> Frame:
        """Create the hub content host; packed below the tab bar in ``build()``."""
        self._content = Frame(parent)
        return self._content

    def register(self, hub_frame: Frame, label_key: str, *, align: Align = "left") -> None:
        self._entries.append((hub_frame, label_key, align))

    def _tokens(self):
        return self.app.themes.tokens

    def build(self, parent: Frame) -> None:
        from app import tr

        tokens = self._tokens()
        ui_font = getattr(self.app, "_ui_font", "Segoe UI")
        self._bar = Frame(parent, bg=tokens.chrome_bg)
        self._bar._theme_surface = "chrome"  # type: ignore[attr-defined]
        self._bar.pack(fill=X, pady=(0, 4))
        self._left = Frame(self._bar, bg=tokens.chrome_bg)
        self._left._theme_surface = "chrome"  # type: ignore[attr-defined]
        self._left.pack(side=LEFT, fill=X, expand=True)
        self._right = Frame(self._bar, bg=tokens.chrome_bg)
        self._right._theme_surface = "chrome"  # type: ignore[attr-defined]
        self._right.pack(side=RIGHT)

        lang = self.app.lang
        for hub_frame, key, align in self._entries:
            row = self._right if align == "right" else self._left
            btn = Button(
                row,
                text=tr(lang, key),
                relief="flat",
                bd=0,
                padx=22,
                pady=10,
                font=(ui_font, 10, "bold"),
                highlightthickness=0,
                command=lambda frame=hub_frame: self.select(frame),
            )
            btn._theme_managed = True  # type: ignore[attr-defined]
            btn.pack(side=LEFT if align == "left" else RIGHT)
            self._buttons[hub_frame] = btn
            self.app.translated.append((btn, key, "text"))
            if self._content is not None:
                hub_frame.place(in_=self._content, x=0, y=0, relwidth=1, relheight=1)

        if self._content is not None:
            self._content.pack(fill=BOTH, expand=True)

        if hasattr(self.app, "themes"):
            self.app.themes.register(self.apply_theme)

        if self._entries:
            self.select(self._entries[0][0])
        else:
            self.apply_theme(self.app.themes)

    def select(self, hub_frame: Frame) -> None:
        if hub_frame not in self._buttons:
            return
        self._active = hub_frame
        hub_frame.lift()
        self.apply_theme(self.app.themes)
        if hasattr(self.app, "_on_main_tab_changed"):
            self.app._on_main_tab_changed()

    def is_active(self, hub_frame: Frame) -> bool:
        return self._active is hub_frame

    def active_index(self) -> int:
        for index, (frame, _key, _align) in enumerate(self._entries):
            if frame is self._active:
                return index
        return 0

    def apply_theme(self, manager: ThemeManager) -> None:
        tokens = manager.tokens
        for bar in (self._bar, self._left, self._right):
            if bar is not None:
                bar.config(bg=tokens.chrome_bg)

        for frame, button in self._buttons.items():
            if frame is self._active:
                button.config(
                    bg=tokens.tab_selected_bg,
                    fg=tokens.tab_selected_fg,
                    activebackground=tokens.tab_selected_bg,
                    activeforeground=tokens.tab_selected_fg,
                    highlightbackground=tokens.border,
                    highlightcolor=tokens.tab_selected_bg,
                )
            else:
                button.config(
                    bg=tokens.tab_idle_bg,
                    fg=tokens.tab_idle_fg,
                    activebackground=tokens.button_active,
                    activeforeground=tokens.tab_idle_fg,
                    highlightbackground=tokens.border,
                    highlightcolor=tokens.border,
                )

    def refresh_styles(self) -> None:
        """Backward-compatible alias for language changes and legacy callers."""
        self.apply_theme(self.app.themes)
