"""
Windows resource monitor backed by MSI Afterburner shared memory with psutil fallbacks.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import psutil

from app_paths import ROOT
from msi_afterburner import read_mahm_reading

Component = Literal["cpu", "gpu"]
AlertLevel = Literal["warning", "critical"]
HeatState = Literal["normal", "warning", "critical"]

TEMP_WARNING_C = 80.0
TEMP_CRITICAL_C = 90.0

DEFAULT_THRESHOLDS: dict[Component, dict[AlertLevel, float]] = {
    "cpu": {"warning": TEMP_WARNING_C, "critical": TEMP_CRITICAL_C},
    "gpu": {"warning": TEMP_WARNING_C, "critical": TEMP_CRITICAL_C},
}

DEFAULT_POLL_SECONDS = 2.0
DEFAULT_ALERT_COOLDOWN_SECONDS = 300.0

AFTERBURNER_URL = "https://www.msi.com/Landing/afterburner"


@dataclass(frozen=True)
class ResourceSnapshot:
    cpu_load_pct: float | None
    cpu_clock_mhz: float | None
    cpu_temp_c: float | None
    gpu_load_pct: float | None
    gpu_clock_mhz: float | None
    gpu_temp_c: float | None
    backend: str
    message: str | None = None


@dataclass(frozen=True)
class ResourceAlert:
    component: Component
    level: AlertLevel
    temp_c: float
    threshold_c: float


@dataclass(frozen=True)
class ResourceMonitorSettings:
    enabled: bool = True
    poll_seconds: float = DEFAULT_POLL_SECONDS
    alert_cooldown_seconds: float = DEFAULT_ALERT_COOLDOWN_SECONDS


def settings_path(root: Path | None = None) -> Path:
    return (root or ROOT) / "runtime" / "settings" / "resource_monitor.json"


def load_settings(root: Path | None = None) -> ResourceMonitorSettings:
    path = settings_path(root)
    if not path.is_file():
        return ResourceMonitorSettings()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return ResourceMonitorSettings()
    if not isinstance(payload, dict):
        return ResourceMonitorSettings()
    return ResourceMonitorSettings(
        enabled=bool(payload.get("enabled", True)),
        poll_seconds=max(1.0, float(payload.get("poll_seconds", DEFAULT_POLL_SECONDS))),
        alert_cooldown_seconds=max(
            30.0,
            float(payload.get("alert_cooldown_seconds", DEFAULT_ALERT_COOLDOWN_SECONDS)),
        ),
    )


def save_settings(settings: ResourceMonitorSettings, root: Path | None = None) -> None:
    path = settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "enabled": settings.enabled,
        "poll_seconds": settings.poll_seconds,
        "alert_cooldown_seconds": settings.alert_cooldown_seconds,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def evaluate_heat_state(snapshot: ResourceSnapshot) -> HeatState:
    temps = [snapshot.cpu_temp_c, snapshot.gpu_temp_c]
    measured = [temp for temp in temps if temp is not None]
    if not measured:
        return "normal"
    peak = max(measured)
    if peak >= TEMP_CRITICAL_C:
        return "critical"
    if peak >= TEMP_WARNING_C:
        return "warning"
    return "normal"


def temp_color_role(temp_c: float | None) -> str:
    if temp_c is None:
        return "muted"
    if temp_c >= TEMP_CRITICAL_C:
        return "error"
    if temp_c >= TEMP_WARNING_C:
        return "warn"
    return "success"


def temp_status_message_key(temp_c: float | None) -> str | None:
    role = temp_color_role(temp_c)
    if temp_c is None:
        return None
    if role == "error":
        return "resource_temp_critical"
    if role == "warn":
        return "resource_temp_warning"
    return "resource_temp_nominal"


def evaluate_alerts(snapshot: ResourceSnapshot) -> list[ResourceAlert]:
    alerts: list[ResourceAlert] = []
    for component, temp in (
        ("cpu", snapshot.cpu_temp_c),
        ("gpu", snapshot.gpu_temp_c),
    ):
        if temp is None:
            continue
        thresholds = DEFAULT_THRESHOLDS[component]
        if temp >= thresholds["critical"]:
            alerts.append(
                ResourceAlert(
                    component=component,
                    level="critical",
                    temp_c=temp,
                    threshold_c=thresholds["critical"],
                )
            )
        elif temp >= thresholds["warning"]:
            alerts.append(
                ResourceAlert(
                    component=component,
                    level="warning",
                    temp_c=temp,
                    threshold_c=thresholds["warning"],
                )
            )
    return alerts


def format_load(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.0f}%"


def format_clock_mhz(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1000.0:
        return f"{value / 1000.0:.1f} GHz"
    return f"{value:.0f} MHz"


def format_temp_c(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.0f}°C"


class ResourceMonitorBackend:
    def __init__(self) -> None:
        self._cpu_load_initialized = False

    def poll(self) -> ResourceSnapshot:
        if os.name != "nt":
            return unavailable_snapshot("Windows only")

        try:
            reading = read_mahm_reading()
        except OSError:
            reading = None
        if reading is None:
            return unavailable_snapshot("afterburner")

        cpu_load = reading.cpu_load_pct if reading.cpu_load_pct is not None else self._read_cpu_load()
        cpu_clock = reading.cpu_clock_mhz if reading.cpu_clock_mhz is not None else self._read_cpu_clock()
        gpu_load = reading.gpu_load_pct
        gpu_clock = reading.gpu_clock_mhz
        cpu_temp = reading.cpu_temp_c
        gpu_temp = reading.gpu_temp_c

        backend = "afterburner"
        if any(value is None for value in (cpu_load, cpu_clock, cpu_temp, gpu_load, gpu_clock, gpu_temp)):
            backend = "partial"
        return ResourceSnapshot(
            cpu_load_pct=cpu_load,
            cpu_clock_mhz=cpu_clock,
            cpu_temp_c=cpu_temp,
            gpu_load_pct=gpu_load,
            gpu_clock_mhz=gpu_clock,
            gpu_temp_c=gpu_temp,
            backend=backend,
            message=None,
        )

    def _read_cpu_load(self) -> float | None:
        if not self._cpu_load_initialized:
            psutil.cpu_percent(interval=None)
            self._cpu_load_initialized = True
            return None
        return float(psutil.cpu_percent(interval=None))

    def _read_cpu_clock(self) -> float | None:
        try:
            freq = psutil.cpu_freq()
        except Exception:
            return None
        if freq is None or freq.current is None:
            return None
        return float(freq.current)


def unavailable_snapshot(message: str | None = None) -> ResourceSnapshot:
    return ResourceSnapshot(
        None, None, None, None, None, None, "unavailable", message
    )
