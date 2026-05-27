"""
Windows hardware resource monitor backed by LibreHardwareMonitor with psutil fallbacks.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Literal

import psutil

from app_paths import RESOURCE_ROOT, ROOT

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


def lhm_dll_dir() -> Path:
    bundled = RESOURCE_ROOT / "librehardwaremonitor"
    if (bundled / "LibreHardwareMonitorLib.dll").is_file():
        return bundled
    return RESOURCE_ROOT / "bin" / "librehardwaremonitor"


def _is_windows_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


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
        self._handle = None
        self._hardware_module = None
        self._gpu_name = ""
        self._init_error: str | None = None
        self._logged_init_error = False
        self._cpu_load_initialized = False

    def poll(self) -> ResourceSnapshot:
        if os.name != "nt":
            return ResourceSnapshot(
                None, None, None, None, None, None, "unavailable", "Windows only"
            )
        if not self._ensure_initialized():
            return ResourceSnapshot(
                None, None, None, None, None, None, "unavailable", self._init_error
            )

        cpu_load = self._read_cpu_load()
        cpu_clock = self._read_cpu_clock()
        cpu_temp = self._read_cpu_temp()
        gpu_load, gpu_clock, gpu_temp = self._read_gpu_stats()

        backend = "lhm"
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
            message=self._init_error,
        )

    def _ensure_initialized(self) -> bool:
        if self._handle is not None:
            return True
        if self._init_error is not None:
            return False

        dll_dir = lhm_dll_dir()
        lhm_dll = dll_dir / "LibreHardwareMonitorLib.dll"
        hid_dll = dll_dir / "HidSharp.dll"
        if not lhm_dll.is_file() or not hid_dll.is_file():
            self._init_error = "LibreHardwareMonitor DLLs missing"
            return False
        if not _is_windows_admin():
            self._init_error = "Administrator privileges required"
            return False

        try:
            import clr  # pythonnet

            clr.AddReference(str(lhm_dll))
            clr.AddReference(str(hid_dll))
            from LibreHardwareMonitor import Hardware  # type: ignore

            self._hardware_module = Hardware
            handle = Hardware.Computer()
            handle.IsCpuEnabled = True
            handle.IsGpuEnabled = True
            handle.IsMemoryEnabled = False
            handle.IsMotherboardEnabled = False
            handle.IsControllerEnabled = False
            handle.IsNetworkEnabled = False
            handle.IsStorageEnabled = False
            handle.IsPsuEnabled = False
            handle.Open()
            self._handle = handle
            self._gpu_name = self._detect_gpu_name()
            return True
        except Exception as exc:
            self._init_error = str(exc)
            return False

    def _detect_gpu_name(self) -> str:
        hardware = self._hardware_module
        gpus = []
        for item in self._handle.Hardware:
            if item.HardwareType in (
                hardware.HardwareType.GpuNvidia,
                hardware.HardwareType.GpuAmd,
                hardware.HardwareType.GpuIntel,
            ):
                gpus.append(item)
        if not gpus:
            return ""
        if len(gpus) == 1:
            return str(gpus[0].Name)

        for item in gpus:
            if item.HardwareType == hardware.HardwareType.GpuNvidia:
                return str(item.Name)
        for item in gpus:
            if item.HardwareType == hardware.HardwareType.GpuAmd:
                item.Update()
                for sensor in item.Sensors:
                    if (
                        sensor.SensorType == hardware.SensorType.Load
                        and str(sensor.Name).startswith("GPU Core")
                        and sensor.Value is not None
                    ):
                        return str(item.Name)
        return str(gpus[0].Name)

    def _get_hardware(self, hwtype, name: str | None = None):
        hardware = self._hardware_module
        for item in self._handle.Hardware:
            if item.HardwareType == hwtype and (name is None or str(item.Name) == name):
                item.Update()
                return item
        return None

    def _get_gpu(self):
        hardware = self._hardware_module
        for hwtype in (
            hardware.HardwareType.GpuNvidia,
            hardware.HardwareType.GpuAmd,
            hardware.HardwareType.GpuIntel,
        ):
            gpu = self._get_hardware(hwtype, self._gpu_name or None)
            if gpu is not None:
                return gpu
        return None

    def _read_cpu_load(self) -> float | None:
        hardware = self._hardware_module
        cpu = self._get_hardware(hardware.HardwareType.Cpu)
        if cpu is not None:
            for sensor in cpu.Sensors:
                if (
                    sensor.SensorType == hardware.SensorType.Load
                    and str(sensor.Name).startswith("CPU Total")
                    and sensor.Value is not None
                ):
                    return float(sensor.Value)
        if not self._cpu_load_initialized:
            psutil.cpu_percent(interval=None)
            self._cpu_load_initialized = True
            return None
        return float(psutil.cpu_percent(interval=None))

    def _read_cpu_clock(self) -> float | None:
        hardware = self._hardware_module
        cpu = self._get_hardware(hardware.HardwareType.Cpu)
        if cpu is None:
            return None
        frequencies = []
        for sensor in cpu.Sensors:
            name = str(sensor.Name)
            if (
                sensor.SensorType == hardware.SensorType.Clock
                and "Core #" in name
                and "Effective" not in name
                and sensor.Value is not None
            ):
                frequencies.append(float(sensor.Value))
        if frequencies:
            return mean(frequencies)
        return None

    def _read_cpu_temp(self) -> float | None:
        hardware = self._hardware_module
        cpu = self._get_hardware(hardware.HardwareType.Cpu)
        if cpu is None:
            return None
        preferred_prefixes = ("Core Average", "Core Max", "CPU Package", "Core")
        for prefix in preferred_prefixes:
            for sensor in cpu.Sensors:
                if (
                    sensor.SensorType == hardware.SensorType.Temperature
                    and str(sensor.Name).startswith(prefix)
                    and sensor.Value is not None
                ):
                    return float(sensor.Value)
        return None

    def _read_gpu_stats(self) -> tuple[float | None, float | None, float | None]:
        hardware = self._hardware_module
        gpu = self._get_gpu()
        if gpu is None:
            return None, None, None

        load = None
        clock = None
        temp = None
        for sensor in gpu.Sensors:
            name = str(sensor.Name)
            if (
                sensor.SensorType == hardware.SensorType.Load
                and name.startswith("GPU Core")
                and sensor.Value is not None
            ):
                load = float(sensor.Value)
            elif (
                sensor.SensorType == hardware.SensorType.Load
                and name.startswith("D3D 3D")
                and load is None
                and sensor.Value is not None
            ):
                load = float(sensor.Value)
            elif (
                sensor.SensorType == hardware.SensorType.Clock
                and "Core" in name
                and "Effective" not in name
                and sensor.Value is not None
            ):
                clock = float(sensor.Value)
            elif (
                sensor.SensorType == hardware.SensorType.Temperature
                and name.startswith("GPU Core")
                and sensor.Value is not None
            ):
                temp = float(sensor.Value)
        return load, clock, temp

    def consume_init_error_for_log(self) -> str | None:
        if self._logged_init_error or not self._init_error:
            return None
        self._logged_init_error = True
        return self._init_error


def unavailable_snapshot(message: str | None = None) -> ResourceSnapshot:
    return ResourceSnapshot(
        None, None, None, None, None, None, "unavailable", message
    )
