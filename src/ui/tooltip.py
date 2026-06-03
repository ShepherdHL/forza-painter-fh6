"""Lightweight hover tooltips for Tk widgets."""

from __future__ import annotations

from tkinter import Toplevel


class ToolTip:
    def __init__(self, widget, text: str, *, delay_ms: int = 500) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tipwindow: Toplevel | None = None
        self._after_id: str | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def set_text(self, text: str) -> None:
        self.text = text
        if self.tipwindow is not None:
            label = getattr(self, "_label", None)
            if label is not None:
                label.config(text=text)

    def _schedule(self, _event=None) -> None:
        self._hide()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _show(self) -> None:
        self._after_id = None
        if not self.text.strip():
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        except Exception:
            return
        self.tipwindow = Toplevel(self.widget)
        self.tipwindow.wm_overrideredirect(True)
        self.tipwindow.wm_geometry(f"+{x}+{y}")
        from tkinter import Label

        self._label = Label(
            self.tipwindow,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9),
            wraplength=360,
        )
        self._label.pack(ipadx=6, ipady=4)

    def _hide(self, _event=None) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        if self.tipwindow is not None:
            try:
                self.tipwindow.destroy()
            except Exception:
                pass
            self.tipwindow = None
