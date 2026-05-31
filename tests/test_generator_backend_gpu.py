from __future__ import annotations

from generator_capabilities import GeneratorCapabilities
from generator_launch_options import GeneratorLaunchOptions, append_launch_options


def test_append_launch_options_adds_backend_flag():
    caps = GeneratorCapabilities(supports_backend=True)
    options = GeneratorLaunchOptions(backend="vulkan", capabilities=caps)
    cmd = append_launch_options(["exe", "image.png"], options)
    assert "-backend" in cmd
    assert cmd[cmd.index("-backend") + 1] == "vulkan"


def test_append_launch_options_adds_gpu_id_when_supported():
    caps = GeneratorCapabilities(supports_gpu_id=True, gpu_id_flag="gpu-id")
    options = GeneratorLaunchOptions(gpu_device_index=2, capabilities=caps)
    cmd = append_launch_options(["exe", "image.png"], options)
    assert "-gpu-id" in cmd
    assert cmd[cmd.index("-gpu-id") + 1] == "2"


def test_append_launch_options_omits_flags_when_unsupported():
    caps = GeneratorCapabilities(supports_backend=False, supports_gpu_id=False)
    options = GeneratorLaunchOptions(backend="vulkan", gpu_device_index=1, capabilities=caps)
    cmd = append_launch_options(["exe", "image.png"], options)
    assert "-backend" not in cmd
    assert "-gpu-id" not in cmd


def test_launch_options_auto_backend_omits_flag():
    caps = GeneratorCapabilities(supports_backend=True)
    options = GeneratorLaunchOptions(backend="auto", capabilities=caps)
    assert options.resolved_backend_flag() is None
