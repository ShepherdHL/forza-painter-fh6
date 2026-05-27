"""
Lightweight HUD-style chrome for tkinter (donut gauges, badges, separators).
Inspired by the UI featured in Syndicate (2012).
"""

from __future__ import annotations

import tkinter as tk


class DonutGauge(tk.Canvas):
    """Ring-style load indicator."""

    def __init__(
        self,
        master,
        *,
        size: int = 84,
        track_color: str,
        fill_color: str,
        bg_color: str,
        text_color: str,
        muted_color: str,
        ring_width: int = 10,
        **kwargs,
    ) -> None:
        kw = dict(
            width=size,
            height=size,
            bg=bg_color,
            highlightthickness=0,
            bd=0,
        )
        kw.update(kwargs)
        super().__init__(master, **kw)
        self._size = size
        self._track = track_color
        self._fill = fill_color
        self._bg_color = bg_color
        self._text_color = text_color
        self._muted = muted_color
        self._ring_width = ring_width
        self._text_id = self.create_text(
            size // 2,
            size // 2,
            text="—",
            fill=muted_color,
            font=("Segoe UI Semibold", 11),
        )

    def set_scheme(
        self,
        *,
        track_color: str,
        fill_color: str,
        bg_color: str,
        text_color: str,
        muted_color: str,
    ) -> None:
        self._track = track_color
        self._fill = fill_color
        self._bg_color = bg_color
        self.configure(bg=bg_color)
        self._text_color = text_color
        self._muted = muted_color

    def set_value(self, pct: float | None) -> None:
        self.delete("ring")
        pad = max(10, self._size // 7)
        x0, y0 = pad, pad
        x1 = self._size - pad
        y1 = self._size - pad
        w = self._ring_width
        self.create_arc(
            x0,
            y0,
            x1,
            y1,
            start=90.0,
            extent=-359.999,
            style=tk.ARC,
            outline=self._track,
            width=w,
            tags="ring",
        )
        try:
            p = float(pct)
            p = max(0.0, min(100.0, p))
            extent = -(p / 100.0) * 359.999
            self.create_arc(
                x0,
                y0,
                x1,
                y1,
                start=90.0,
                extent=extent,
                style=tk.ARC,
                outline=self._fill,
                width=w,
                tags="ring",
            )
            self.itemconfigure(self._text_id, text=f"{p:.0f}%", fill=self._text_color)
        except (TypeError, ValueError):
            self.itemconfigure(self._text_id, text="—", fill=self._muted)


def hud_badge(parent: tk.Widget, text: str, *, bg: str, fg: str, border: str, font: tuple[str, ...]) -> tk.Frame:
    """Minimal corporate-style wordmark tile (top-right header accents)."""
    outer = tk.Frame(parent, bg=bg, highlightbackground=border, highlightthickness=1, bd=0)
    inner = tk.Frame(outer, bg=bg)
    inner.pack(padx=10, pady=4)
    tk.Label(inner, text=text.upper(), bg=bg, fg=fg, font=font).pack()
    return outer


def header_rule(parent: tk.Widget, *, height: int, bg: str, line: str) -> tk.Canvas:
    """Single-pixel divider under the header cluster."""
    c = tk.Canvas(parent, height=height, bg=bg, highlightthickness=0, bd=0)
    c._chrome_bg = bg  # type: ignore[attr-defined] — read by app theme walker
    c.pack(fill=tk.X)

    def _draw(_event=None) -> None:
        c.delete("rule")
        w = max(1, c.winfo_width())
        c.create_line(0, height // 2, w, height // 2, fill=line, width=1, tags="rule")

    c.bind("<Configure>", _draw, add="+")
    return c
