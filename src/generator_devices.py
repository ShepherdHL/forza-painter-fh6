"""Enumerate OpenCL/Vulkan devices from the bundled generator when supported."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from generator_capabilities import DEFAULT_GENERATOR_EXE, GeneratorCapabilities
from gpu_adapters import GpuAdapter, is_likely_integrated_graphics, label_match_score

_INDEXED_LINE_RE = re.compile(r"^\s*(\d+)\s*[:\.)-]\s*(.+?)\s*$")


@dataclass(frozen=True)
class GeneratorDevice:
    index: int
    name: str
    vendor: str = ""
    backend: str = "opencl"
    is_integrated: bool = False


def parse_list_devices_output(text: str, *, backend: str = "opencl") -> list[GeneratorDevice]:
    """Parse `-list-devices` stdout (JSON array/object or indexed text lines)."""
    payload = str(text or "").strip()
    if not payload:
        return []

    json_devices = _parse_list_devices_json(payload, backend=backend)
    if json_devices:
        return json_devices
    return _parse_list_devices_lines(payload, backend=backend)


def _parse_list_devices_json(payload: str, *, backend: str) -> list[GeneratorDevice]:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        return []

    items: list[object]
    resolved_backend = backend
    if isinstance(parsed, dict):
        resolved_backend = str(parsed.get("backend", backend) or backend)
        raw_items = parsed.get("devices", parsed.get("Devices", []))
        items = raw_items if isinstance(raw_items, list) else []
    elif isinstance(parsed, list):
        items = parsed
    else:
        return []

    devices: list[GeneratorDevice] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", item.get("label", ""))).strip()
        if not name:
            continue
        try:
            index = int(item.get("index", item.get("id", len(devices))))
        except (TypeError, ValueError):
            index = len(devices)
        vendor = str(item.get("vendor", item.get("vendor_name", ""))).strip()
        device_backend = str(item.get("backend", resolved_backend) or resolved_backend)
        device_type = str(item.get("type", item.get("kind", ""))).strip().lower()
        integrated = item.get("integrated")
        if integrated is None:
            integrated = device_type in {"integrated", "igpu", "cpu"}
        else:
            integrated = bool(integrated)
        if not integrated:
            integrated = is_likely_integrated_graphics(name)
        devices.append(
            GeneratorDevice(
                index=index,
                name=name,
                vendor=vendor,
                backend=device_backend,
                is_integrated=integrated,
            )
        )
    return sorted(devices, key=lambda device: device.index)


def _parse_list_devices_lines(payload: str, *, backend: str) -> list[GeneratorDevice]:
    devices: list[GeneratorDevice] = []
    for line in payload.splitlines():
        match = _INDEXED_LINE_RE.match(line.strip())
        if not match:
            continue
        index = int(match.group(1))
        name = match.group(2).strip()
        if not name:
            continue
        devices.append(
            GeneratorDevice(
                index=index,
                name=name,
                backend=backend,
                is_integrated=is_likely_integrated_graphics(name),
            )
        )
    return devices


def list_generator_devices(
    *,
    exe_path: str | Path | None = None,
    backend: str = "opencl",
    capabilities: GeneratorCapabilities | None = None,
    runner=subprocess.run,
) -> list[GeneratorDevice]:
    path = Path(exe_path or DEFAULT_GENERATOR_EXE)
    caps = capabilities
    if caps is None:
        from generator_capabilities import probe_generator_capabilities

        caps = probe_generator_capabilities(path, runner=runner)
    if not caps.supports_list_devices:
        return []

    cmd = [str(path), "-list-devices"]
    if backend in {"opencl", "vulkan"}:
        cmd.extend(["-backend", backend])

    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        result = runner(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=12,
            creationflags=flags,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    return parse_list_devices_output(result.stdout or result.stderr, backend=backend)


def match_adapter_to_device(
    adapter: GpuAdapter,
    devices: list[GeneratorDevice],
    *,
    backend: str | None = None,
) -> GeneratorDevice | None:
    if not adapter or not devices:
        return None
    candidates = devices
    if backend in {"opencl", "vulkan"}:
        scoped = [device for device in devices if device.backend == backend]
        if scoped:
            candidates = scoped
    target = adapter.label.lower()
    best_device: GeneratorDevice | None = None
    best_score = 0
    for device in candidates:
        score = label_match_score(target, device.name.lower())
        if score > best_score:
            best_score = score
            best_device = device
    return best_device if best_score > 0 else None
