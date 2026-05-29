"""
Compact header telemetry strip (CPU/GPU) with responsive layout modes.

Rendering and layout live here; sampling stays in ``resource_monitor``.
"""

from __future__ import annotations

from typing import Any, Callable, Literal

from tkinter import BOTH, LEFT, RIGHT, X, Frame, Label

from resource_monitor import (
    HeatState,
    ResourceSnapshot,
    format_clock_mhz,
    format_load,
    format_temp_c,
    temp_color_role,
    temp_status_message_key,
)
from ui_chrome import DonutGauge

LayoutMode = Literal["full", "compact", "minimal"]

# Width thresholds for the telemetry host (not the whole window).
_FULL_MIN = 480
_COMPACT_MIN = 300


class HeaderTelemetryPanel:
    """Persistent header CPU/GPU telemetry with adaptive density."""

    def __init__(self, app: Any, parent: Frame) -> None:
        self.app = app
        self._layout: LayoutMode | None = None
        self._snapshot: ResourceSnapshot | None = None
        self._heat_state: HeatState = "normal"
        self._unavailable_message: str | None = None

        import app as app_module

        self._colors = app_module
        bg = app_module.COLOR_BG

        self.host = Frame(parent, bg=bg)
        self.host._chrome_bg_locked = True  # type: ignore[attr-defined]
        self.host.pack(side=LEFT, fill=X, expand=True, padx=(16, 12))

        shell = Frame(
            self.host,
            bg=app_module.COLOR_PANEL,
            highlightbackground=app_module.COLOR_BORDER,
            highlightthickness=1,
        )
        shell.pack(fill=X, anchor="center")
        self._shell = shell

        self._heat_stripe = Frame(shell, height=3, bg=app_module.COLOR_PANEL)
        self._heat_stripe.pack(fill=X)

        body = Frame(shell, bg=app_module.COLOR_PANEL)
        body.pack(fill=X, padx=10, pady=(6, 8))
        self._body = body

        self._full_row = Frame(body, bg=app_module.COLOR_PANEL)
        self._compact_row = Frame(body, bg=app_module.COLOR_PANEL)
        self._minimal_row = Frame(body, bg=app_module.COLOR_PANEL)

        self._donuts: list[DonutGauge] = []
        self._metric_values: dict[str, list[dict[str, Label]]] = {}
        self._metric_status: dict[str, list[Label]] = {}
        self._minimal_labels: dict[str, Label] = {}

        self._build_full(self._full_row)
        self._build_compact(self._compact_row)
        self._build_minimal(self._minimal_row)

        self._status = Label(
            body,
            text="",
            anchor="w",
            justify="left",
            bg=app_module.COLOR_PANEL,
            fg=app_module.COLOR_MUTED,
            font=app._ui_font(8),
        )
        self._status._theme_role = "muted"  # type: ignore[attr-defined]
        self._heat_banner = Label(
            body,
            text="",
            anchor="w",
            bg=app_module.COLOR_PANEL,
            fg=app_module.COLOR_WARN,
            font=app._ui_font(8, bold=True),
        )

        self.host.bind("<Configure>", self._on_configure, add="+")
        self._bind_status_wraplength()
        self._apply_layout_mode("full")

    def _bind_status_wraplength(self) -> None:
        def _resize(_event=None) -> None:
            try:
                width = max(160, self.host.winfo_width() - 24)
                self._status.config(wraplength=width)
            except Exception:
                pass

        self.host.bind("<Configure>", _resize, add="+")
        _resize()

    def _tr(self, key: str) -> str:
        from app import tr

        return tr(self.app.lang, key)

    def _theme_fg(self, role: str) -> str:
        return self.app._theme_fg(role)

    def _register_translation(self, widget: Label, key: str, *, upper: bool = False) -> None:
        option = "text_upper" if upper else "text"
        self.app.translated.append((widget, key, option))

    def _build_full(self, parent: Frame) -> None:
        row = Frame(parent, bg=self._colors.COLOR_PANEL)
        row.pack(fill=X)
        for column, key in enumerate(("resource_cpu", "resource_gpu")):
            cell = self._build_metric_cell(row, key, donut_size=52, ring_width=7, show_clock=True, show_status=True)
            cell.grid(row=0, column=column, sticky="nsew", padx=(0, 14 if column == 0 else 0))
            row.columnconfigure(column, weight=1)

    def _build_compact(self, parent: Frame) -> None:
        row = Frame(parent, bg=self._colors.COLOR_PANEL)
        row.pack(fill=X)
        for column, key in enumerate(("resource_cpu", "resource_gpu")):
            cell = self._build_metric_cell(row, key, donut_size=40, ring_width=6, show_clock=False, show_status=False)
            cell.grid(row=0, column=column, sticky="nsew", padx=(0, 10 if column == 0 else 0))
            row.columnconfigure(column, weight=1)

    def _build_minimal(self, parent: Frame) -> None:
        row = Frame(parent, bg=self._colors.COLOR_PANEL)
        row.pack(fill=X)
        for index, key in enumerate(("resource_cpu", "resource_gpu")):
            if index:
                sep = Label(row, text="  |  ", bg=self._colors.COLOR_PANEL, fg=self._colors.COLOR_MUTED, font=self.app._ui_font(8))
                sep._theme_role = "muted"  # type: ignore[attr-defined]
                sep.pack(side=LEFT)
            label = Label(row, text="—", bg=self._colors.COLOR_PANEL, fg=self._colors.COLOR_TEXT, font=self.app._ui_font(8))
            label.pack(side=LEFT)
            self._minimal_labels[key] = label

    def _build_metric_cell(
        self,
        parent: Frame,
        metric_key: str,
        *,
        donut_size: int,
        ring_width: int,
        show_clock: bool,
        show_status: bool,
    ) -> Frame:
        cell = Frame(parent, bg=self._colors.COLOR_PANEL)
        fill = self._colors.COLOR_SUCCESS if metric_key == "resource_cpu" else self._colors.COLOR_ACCENT
        donut = DonutGauge(
            cell,
            size=donut_size,
            track_color=self._colors.COLOR_BORDER,
            fill_color=fill,
            bg_color=self._colors.COLOR_PANEL,
            text_color=self._colors.COLOR_TEXT,
            muted_color=self._colors.COLOR_MUTED,
            ring_width=ring_width,
        )
        donut._donut_role = "cpu" if metric_key == "resource_cpu" else "gpu"  # type: ignore[attr-defined]
        donut.pack(side=LEFT, padx=(0, 8))
        self._donuts.append(donut)

        text_col = Frame(cell, bg=self._colors.COLOR_PANEL)
        text_col.pack(side=LEFT, fill=X, expand=True)
        heading = Label(
            text_col,
            text=self._tr(metric_key).upper(),
            anchor="w",
            bg=self._colors.COLOR_PANEL,
            fg=self._colors.COLOR_TEXT,
            font=self.app._ui_font(9, bold=True),
        )
        heading.pack(fill=X)
        self._register_translation(heading, metric_key, upper=True)

        value_row = Frame(text_col, bg=self._colors.COLOR_PANEL)
        value_row.pack(anchor="w", fill=X, pady=(2, 0))
        parts: dict[str, Label] = {}
        part_keys = ("load", "clock", "temp") if show_clock else ("load", "temp")
        for index, part_key in enumerate(part_keys):
            if index:
                sep = Label(value_row, text=" · ", bg=self._colors.COLOR_PANEL, fg=self._colors.COLOR_MUTED, font=self.app._ui_font(8))
                sep._theme_role = "muted"  # type: ignore[attr-defined]
                sep.pack(side=LEFT)
            label = Label(value_row, text="—", bg=self._colors.COLOR_PANEL, fg=self._colors.COLOR_MUTED, font=self.app._ui_font(8))
            label._theme_role = "muted"  # type: ignore[attr-defined]
            label._resource_part = part_key  # type: ignore[attr-defined]
            label.pack(side=LEFT)
            parts[part_key] = label
        self._metric_values.setdefault(metric_key, []).append(parts)

        if show_status:
            status = Label(cell, text="", anchor="w", bg=self._colors.COLOR_PANEL, fg=self._colors.COLOR_SUCCESS, font=self.app._ui_font(8))
            status.pack(anchor="w", pady=(2, 0))
            self._metric_status.setdefault(metric_key, []).append(status)

        return cell

    def _on_configure(self, _event=None) -> None:
        try:
            width = self.host.winfo_width()
        except Exception:
            return
        if width < 1:
            return
        if width >= _FULL_MIN:
            mode: LayoutMode = "full"
        elif width >= _COMPACT_MIN:
            mode = "compact"
        else:
            mode = "minimal"
        if mode != self._layout:
            self._apply_layout_mode(mode)

    def _apply_layout_mode(self, mode: LayoutMode) -> None:
        self._layout = mode
        for row, active in (
            (self._full_row, mode == "full"),
            (self._compact_row, mode == "compact"),
            (self._minimal_row, mode == "minimal"),
        ):
            if active:
                row.pack(fill=X)
            else:
                row.pack_forget()
        if self._snapshot is not None:
            self.apply_snapshot(self._snapshot)
        self._render_heat_chrome()

    def _apply_temp_label(self, label: Label, temp: float | None) -> None:
        role = temp_color_role(temp)
        label.config(text=format_temp_c(temp))
        label._theme_role = role  # type: ignore[attr-defined]
        label.config(fg=self._theme_fg(role))

    def _apply_temp_status(self, label: Label, temp: float | None) -> None:
        key = temp_status_message_key(temp)
        if key is None:
            label.config(text="", fg=self._theme_fg("muted"))
            label._theme_role = "muted"  # type: ignore[attr-defined]
            return
        role = temp_color_role(temp)
        label.config(text=self._tr(key), fg=self._theme_fg(role))
        label._theme_role = role  # type: ignore[attr-defined]

    def apply_snapshot(self, snapshot: ResourceSnapshot) -> None:
        self._snapshot = snapshot
        if snapshot.backend == "unavailable":
            if snapshot.message == "afterburner":
                message = self._tr("resource_afterburner_recommend")
            else:
                message = self._tr("resource_unavailable")
                if snapshot.message:
                    message = f"{message}: {snapshot.message}"
            self._set_unavailable(message)
            return

        self._unavailable_message = None
        self._status.pack_forget()

        component_map = {
            "resource_cpu": (snapshot.cpu_load_pct, snapshot.cpu_clock_mhz, snapshot.cpu_temp_c),
            "resource_gpu": (snapshot.gpu_load_pct, snapshot.gpu_clock_mhz, snapshot.gpu_temp_c),
        }
        for key, (load, clock, temp) in component_map.items():
            for donut in self._donuts:
                if getattr(donut, "_donut_role", None) == ("cpu" if key == "resource_cpu" else "gpu"):
                    donut.set_value(load)
            for parts in self._metric_values.get(key, []):
                if "load" in parts:
                    parts["load"].config(text=format_load(load), fg=self._theme_fg("muted"))
                if "clock" in parts:
                    parts["clock"].config(text=format_clock_mhz(clock), fg=self._theme_fg("muted"))
                if "temp" in parts:
                    self._apply_temp_label(parts["temp"], temp)
            for status in self._metric_status.get(key, []):
                self._apply_temp_status(status, temp)
            minimal = self._minimal_labels.get(key)
            if minimal is not None:
                minimal.config(
                    text=self._minimal_line(key, load, clock, temp),
                    fg=self._theme_fg(temp_color_role(temp) if temp is not None else "text"),
                )
                minimal._theme_role = temp_color_role(temp) if temp is not None else "text"  # type: ignore[attr-defined]

    def _minimal_line(self, key: str, load, clock, temp) -> str:
        prefix = self._tr(key).upper()
        load_text = format_load(load)
        temp_text = format_temp_c(temp)
        return f"{prefix} {load_text}  {temp_text}"

    def _set_unavailable(self, message: str) -> None:
        self._unavailable_message = message
        for key in ("resource_cpu", "resource_gpu"):
            role = "cpu" if key == "resource_cpu" else "gpu"
            for donut in self._donuts:
                if getattr(donut, "_donut_role", None) == role:
                    donut.set_value(None)
            for parts in self._metric_values.get(key, []):
                for label in parts.values():
                    label.config(text="—", fg=self._theme_fg("muted"))
            for status in self._metric_status.get(key, []):
                status.config(text="")
            minimal = self._minimal_labels.get(key)
            if minimal is not None:
                minimal.config(text=f"{self._tr(key).upper()} —", fg=self._theme_fg("muted"))
        self._status.config(text=message)
        self._status.pack(fill=X, pady=(4, 0))
        self.set_heat_state("normal", banner_text="")

    def set_heat_state(self, heat_state: HeatState, *, banner_text: str) -> None:
        self._heat_state = heat_state
        self._heat_banner_text = banner_text
        self._render_heat_chrome()

    def _render_heat_chrome(self) -> None:
        if self._unavailable_message:
            self._heat_stripe.config(bg=self._colors.COLOR_PANEL)
            self._heat_banner.pack_forget()
            return

        if self._heat_state == "critical":
            self._heat_stripe.config(bg=self._colors.COLOR_ERROR)
            self._heat_banner.config(text=getattr(self, "_heat_banner_text", ""), fg=self._colors.COLOR_ERROR)
            self._heat_banner.pack(fill=X, pady=(4, 0))
        elif self._heat_state == "warning":
            self._heat_stripe.config(bg=self._colors.COLOR_WARN)
            self._heat_banner.config(text=getattr(self, "_heat_banner_text", ""), fg=self._colors.COLOR_WARN)
            self._heat_banner.pack(fill=X, pady=(4, 0))
        else:
            self._heat_stripe.config(bg=self._colors.COLOR_PANEL)
            self._heat_banner.pack_forget()

    def apply_theme_recursive(self, apply_fn: Callable[[Any], None]) -> None:
        for widget in (
            self.host,
            self._shell,
            self._body,
            self._full_row,
            self._compact_row,
            self._minimal_row,
            self._status,
            self._heat_banner,
        ):
            apply_fn(widget)
        for donut in self._donuts:
            apply_fn(donut)
        for part_groups in self._metric_values.values():
            for parts in part_groups:
                for label in parts.values():
                    apply_fn(label)
        for status_group in self._metric_status.values():
            for label in status_group:
                apply_fn(label)
        for label in self._minimal_labels.values():
            apply_fn(label)
