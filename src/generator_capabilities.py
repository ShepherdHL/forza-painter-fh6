"""Probe bundled generator executable capabilities (flags vary by upstream canary)."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app_paths import RESOURCE_ROOT

DEFAULT_GENERATOR_EXE = RESOURCE_ROOT / "bin" / "forza-painter-geometrize-go.exe"

_VERSION_RE = re.compile(r"^Version:\s*(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class GeneratorCapabilities:
    version: str | None = None
    supports_backend: bool = False
    supports_list_devices: bool = False
    supports_gpu_id: bool = False
    gpu_id_flag: str = "gpu-id"

    @property
    def supports_direct_gpu_binding(self) -> bool:
        return self.supports_list_devices and self.supports_gpu_id


def _usage_declares_flag(payload: str, flag: str) -> bool:
    return bool(re.search(rf"^\s+-{re.escape(flag)}\b", payload, re.MULTILINE))


def parse_generator_probe_output(text: str) -> GeneratorCapabilities:
    """Parse usage / probe output from the generator executable."""
    payload = str(text or "")
    version_match = _VERSION_RE.search(payload)
    version = version_match.group(1).strip() if version_match else None
    supports_gpu_id = _usage_declares_flag(payload, "gpu-id")
    gpu_id_flag = "gpu-id"
    if not supports_gpu_id and _usage_declares_flag(payload, "device-id"):
        supports_gpu_id = True
        gpu_id_flag = "device-id"
    elif not supports_gpu_id and _usage_declares_flag(payload, "device"):
        supports_gpu_id = True
        gpu_id_flag = "device"
    return GeneratorCapabilities(
        version=version,
        supports_backend=_usage_declares_flag(payload, "backend"),
        supports_list_devices=_usage_declares_flag(payload, "list-devices"),
        supports_gpu_id=supports_gpu_id,
        gpu_id_flag=gpu_id_flag,
    )


def probe_generator_capabilities(
    exe_path: str | Path | None = None,
    *,
    runner=subprocess.run,
) -> GeneratorCapabilities:
    """Detect which optional GPU flags the bundled generator supports."""
    path = Path(exe_path or DEFAULT_GENERATOR_EXE)
    if not path.is_file():
        return GeneratorCapabilities()
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        result = runner(
            [str(path), "-list-devices"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            creationflags=flags,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return GeneratorCapabilities()
    return parse_generator_probe_output(f"{result.stdout}\n{result.stderr}")
