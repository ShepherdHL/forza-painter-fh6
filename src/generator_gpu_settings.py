"""Persist GPU selection for resource monitor and generation routing."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from app_paths import ROOT

AUTO_GPU_ID = "auto"
AUTO_BACKEND_ID = "auto"
GENERATOR_BACKENDS: tuple[str, ...] = ("opencl", "vulkan")


@dataclass(frozen=True)
class GeneratorGpuSettings:
    gpu_selection_id: str = AUTO_GPU_ID
    generator_backend: str = AUTO_BACKEND_ID

    def listing_backend(self) -> str:
        if self.generator_backend in GENERATOR_BACKENDS:
            return self.generator_backend
        return "opencl"

    def with_gpu_selection(self, selection_id: str) -> "GeneratorGpuSettings":
        return replace(self, gpu_selection_id=selection_id)

    def with_generator_backend(self, backend: str) -> "GeneratorGpuSettings":
        normalized = normalize_generator_backend(backend)
        return replace(self, generator_backend=normalized)


def normalize_generator_backend(value: str | None) -> str:
    backend = str(value or AUTO_BACKEND_ID).strip().lower() or AUTO_BACKEND_ID
    if backend == AUTO_BACKEND_ID:
        return AUTO_BACKEND_ID
    if backend in GENERATOR_BACKENDS:
        return backend
    return AUTO_BACKEND_ID


def settings_path(root: Path | None = None) -> Path:
    return (root or ROOT) / "runtime" / "settings" / "generator_gpu.json"


def load_generator_gpu_settings(root: Path | None = None) -> GeneratorGpuSettings:
    path = settings_path(root)
    if not path.is_file():
        return GeneratorGpuSettings()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return GeneratorGpuSettings()
    if not isinstance(payload, dict):
        return GeneratorGpuSettings()
    selection = str(payload.get("gpu_selection_id", AUTO_GPU_ID)).strip() or AUTO_GPU_ID
    backend = normalize_generator_backend(payload.get("generator_backend", AUTO_BACKEND_ID))
    return GeneratorGpuSettings(gpu_selection_id=selection, generator_backend=backend)


def save_generator_gpu_settings(settings: GeneratorGpuSettings, root: Path | None = None) -> None:
    path = settings_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gpu_selection_id": settings.gpu_selection_id,
        "generator_backend": settings.generator_backend,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
