"""Generator command-line GPU options (backend / device index)."""

from __future__ import annotations

from dataclasses import dataclass

from generator_capabilities import GeneratorCapabilities
from generator_gpu_settings import AUTO_BACKEND_ID


@dataclass(frozen=True)
class GeneratorLaunchOptions:
    backend: str = AUTO_BACKEND_ID
    gpu_device_index: int | None = None
    capabilities: GeneratorCapabilities | None = None

    def resolved_backend_flag(self) -> str | None:
        caps = self.capabilities
        if caps is None or not caps.supports_backend:
            return None
        if self.backend not in {"opencl", "vulkan"}:
            return None
        return self.backend

    def resolved_gpu_id(self) -> int | None:
        caps = self.capabilities
        if caps is None or not caps.supports_gpu_id:
            return None
        if self.gpu_device_index is None:
            return None
        return self.gpu_device_index

    def gpu_id_argv(self) -> list[str]:
        gpu_id = self.resolved_gpu_id()
        if gpu_id is None:
            return []
        flag = "gpu-id"
        if self.capabilities is not None and self.capabilities.gpu_id_flag:
            flag = self.capabilities.gpu_id_flag
        return [f"-{flag}", str(gpu_id)]

    @property
    def uses_direct_gpu_binding(self) -> bool:
        return self.resolved_gpu_id() is not None


def append_launch_options(cmd: list[str], launch_options: GeneratorLaunchOptions | None) -> list[str]:
    if launch_options is None:
        return cmd
    backend = launch_options.resolved_backend_flag()
    if backend:
        cmd.extend(["-backend", backend])
    cmd.extend(launch_options.gpu_id_argv())
    return cmd
