"""Enumerate Windows GPU adapters for monitor selection."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Callable

from generator_gpu_settings import AUTO_GPU_ID, GeneratorGpuSettings

_WMI_SKIP_NAMES = (
    "microsoft basic render driver",
    "microsoft remote display adapter",
    "microsoft hyper-v virtual",
)


@dataclass(frozen=True)
class GpuAdapter:
    id: str
    label: str
    afterburner_index: int | None = None
    vendor_hint: str = "unknown"
    is_integrated: bool = False


_DISCRETE_NAME_PATTERNS: tuple[str, ...] = (
    r"\bgeforce\b",
    r"\bquadro\b",
    r"\brtx\b",
    r"\bgtx\b",
    r"\btitan\b",
    r"\bradeon rx\b",
    r"\brx\s*\d",
    r"\bradeon pro\b",
    r"\bfirepro\b",
    r"\barc a\d",
    r"\bintel arc\b",
    r"\bworkstation\b",
)


def is_likely_integrated_graphics(name: str) -> bool:
    """Return True when the adapter name looks like CPU/iGPU graphics, not a discrete card."""
    lowered = _normalize_wmi_name(name).lower()
    if not lowered:
        return False
    if any(re.search(pattern, lowered) for pattern in _DISCRETE_NAME_PATTERNS):
        return False
    if "intel" in lowered and any(
        fragment in lowered for fragment in ("uhd", "iris", "hd graphics", "graphics")
    ):
        return True
    if re.search(r"\bradeon\s*(?:\(tm\)\s*)?graphics\b", lowered):
        return True
    if "vega" in lowered and "rx" not in lowered:
        return True
    return False


def _make_adapter(
    *,
    adapter_id: str,
    label: str,
    afterburner_index: int | None = None,
    vendor_hint: str | None = None,
) -> GpuAdapter:
    name = _normalize_wmi_name(label)
    return GpuAdapter(
        id=adapter_id,
        label=name,
        afterburner_index=afterburner_index,
        vendor_hint=vendor_hint or _vendor_hint(name),
        is_integrated=is_likely_integrated_graphics(name),
    )


def wmi_adapter_id(pnp_device_id: str) -> str:
    digest = hashlib.sha256(pnp_device_id.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"wmi:{digest}"


def _vendor_hint(name: str) -> str:
    lowered = name.lower()
    if "nvidia" in lowered or "geforce" in lowered or "quadro" in lowered or "rtx" in lowered:
        return "nvidia"
    if "amd" in lowered or "radeon" in lowered:
        return "amd"
    if "intel" in lowered:
        return "intel"
    return "unknown"


def _normalize_wmi_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip())


def _should_skip_wmi_name(name: str) -> bool:
    lowered = name.lower()
    return not lowered or any(fragment in lowered for fragment in _WMI_SKIP_NAMES)


def _parse_wmi_json(payload: str) -> list[dict]:
    text = str(payload or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def list_wmi_gpu_adapters(
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> list[GpuAdapter]:
    if os.name != "nt":
        return []
    run = runner or subprocess.run
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        result = run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    "Get-CimInstance Win32_VideoController "
                    "| Where-Object { $_.Name } "
                    "| Select-Object Name, PNPDeviceID, AdapterRAM "
                    "| ConvertTo-Json -Compress"
                ),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            creationflags=flags,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []

    adapters: list[GpuAdapter] = []
    seen: set[str] = set()
    for item in _parse_wmi_json(result.stdout):
        name = _normalize_wmi_name(item.get("Name", ""))
        pnp = str(item.get("PNPDeviceID", "")).strip()
        if _should_skip_wmi_name(name) or not pnp:
            continue
        adapter_id = wmi_adapter_id(pnp)
        if adapter_id in seen:
            continue
        seen.add(adapter_id)
        adapters.append(
            _make_adapter(
                adapter_id=adapter_id,
                label=name,
            )
        )
    return adapters


def _attach_afterburner_indices(
    adapters: list[GpuAdapter],
    mahm_labels: dict[int, str],
) -> list[GpuAdapter]:
    if not adapters or not mahm_labels:
        return adapters

    remaining = dict(mahm_labels)
    attached: list[GpuAdapter] = []

    for adapter in adapters:
        match_index = _match_afterburner_index(adapter.label, remaining)
        attached.append(
            _make_adapter(
                adapter_id=adapter.id,
                label=adapter.label,
                afterburner_index=match_index,
                vendor_hint=adapter.vendor_hint,
            )
        )
        if match_index is not None:
            remaining.pop(match_index, None)

    for index in sorted(remaining):
        label = remaining[index]
        attached.append(
            _make_adapter(
                adapter_id=f"mahm:{index}",
                label=label,
                afterburner_index=index,
            )
        )
    return attached


def _match_afterburner_index(label: str, mahm_labels: dict[int, str]) -> int | None:
    target = label.lower()
    best_index: int | None = None
    best_score = 0
    for index, mahm_label in mahm_labels.items():
        score = _label_match_score(target, mahm_label.lower())
        if score > best_score:
            best_score = score
            best_index = index
    return best_index if best_score > 0 else None


def label_match_score(left_label: str, right_label: str) -> int:
    return _label_match_score(left_label, right_label)


def _label_match_score(wmi_label: str, mahm_label: str) -> int:
    if not wmi_label or not mahm_label:
        return 0
    if wmi_label in mahm_label or mahm_label in wmi_label:
        return 100 + min(len(wmi_label), len(mahm_label))
    wmi_tokens = {token for token in re.split(r"[^a-z0-9]+", wmi_label) if len(token) >= 3}
    mahm_tokens = {token for token in re.split(r"[^a-z0-9]+", mahm_label) if len(token) >= 3}
    overlap = len(wmi_tokens & mahm_tokens)
    if overlap:
        return 10 * overlap
    return 0


def list_gpu_adapters(
    *,
    mahm_labels: dict[int, str] | None = None,
    wmi_runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> list[GpuAdapter]:
    if mahm_labels is None:
        from msi_afterburner import list_mahm_gpu_labels

        mahm_labels = list_mahm_gpu_labels()
    wmi_adapters = list_wmi_gpu_adapters(runner=wmi_runner)
    if wmi_adapters:
        return _attach_afterburner_indices(wmi_adapters, mahm_labels)
    return [
        _make_adapter(
            adapter_id=f"mahm:{index}",
            label=label,
            afterburner_index=index,
        )
        for index, label in sorted(mahm_labels.items())
    ]


def resolve_afterburner_index(
    settings: GeneratorGpuSettings,
    adapters: list[GpuAdapter],
) -> int | None:
    if settings.gpu_selection_id == AUTO_GPU_ID:
        return None
    for adapter in adapters:
        if adapter.id == settings.gpu_selection_id:
            return adapter.afterburner_index
    return None


def adapter_for_id(adapters: list[GpuAdapter], selection_id: str) -> GpuAdapter | None:
    if selection_id == AUTO_GPU_ID:
        return None
    for adapter in adapters:
        if adapter.id == selection_id:
            return adapter
    return None


def normalize_gpu_selection(
    settings: GeneratorGpuSettings,
    adapters: list[GpuAdapter],
) -> tuple[GeneratorGpuSettings, bool]:
    """Return updated settings and whether the saved GPU id was missing."""
    if settings.gpu_selection_id == AUTO_GPU_ID:
        return settings, False
    if adapter_for_id(adapters, settings.gpu_selection_id) is not None:
        return settings, False
    return GeneratorGpuSettings(gpu_selection_id=AUTO_GPU_ID), True


def adapter_display_label(adapter: GpuAdapter, *, integrated_tag: str = "") -> str:
    if adapter.is_integrated and integrated_tag:
        return f"{adapter.label} ({integrated_tag})"
    return adapter.label


def adapter_label_for_id(adapters: list[GpuAdapter], selection_id: str) -> str | None:
    if selection_id == AUTO_GPU_ID:
        return None
    for adapter in adapters:
        if adapter.id == selection_id:
            return adapter.label
    return None
