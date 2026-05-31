from __future__ import annotations

from generator_capabilities import GeneratorCapabilities, parse_generator_probe_output
from generator_devices import GeneratorDevice, match_adapter_to_device, parse_list_devices_output
from gpu_adapters import GpuAdapter, _make_adapter


def test_parse_generator_probe_output_detects_backend_only_canary():
    text = """
Version: v1.2-Canary-20260525
flag provided but not defined: -list-devices
Usage of forza-painter-geometrize-go.exe:
  -backend string
        GPU backend: opencl (default) or vulkan (default "opencl")
"""
    caps = parse_generator_probe_output(text)
    assert caps.version == "v1.2-Canary-20260525"
    assert caps.supports_backend
    assert not caps.supports_list_devices
    assert not caps.supports_gpu_id
    assert not caps.supports_direct_gpu_binding


def test_parse_generator_probe_output_detects_direct_binding_flags():
    text = """
Version: canary-27010101
  -backend string
  -list-devices
  -gpu-id int
"""
    caps = parse_generator_probe_output(text)
    assert caps.supports_backend
    assert caps.supports_list_devices
    assert caps.supports_gpu_id
    assert caps.supports_direct_gpu_binding


def test_parse_list_devices_json():
    payload = """
    {
      "backend": "opencl",
      "devices": [
        {"index": 0, "name": "AMD Radeon Graphics", "type": "integrated"},
        {"index": 1, "name": "NVIDIA GeForce RTX 4070", "type": "discrete"}
      ]
    }
    """
    devices = parse_list_devices_output(payload, backend="opencl")
    assert len(devices) == 2
    assert devices[0].is_integrated
    assert not devices[1].is_integrated


def test_parse_list_devices_indexed_lines():
    payload = "0: NVIDIA GeForce RTX 4070\n1: AMD Radeon Graphics\n"
    devices = parse_list_devices_output(payload, backend="opencl")
    assert [device.index for device in devices] == [0, 1]


def test_match_adapter_to_device_prefers_name_overlap():
    adapter = _make_adapter(adapter_id="wmi:1", label="NVIDIA GeForce RTX 4070")
    devices = [
        GeneratorDevice(index=0, name="AMD Radeon Graphics", is_integrated=True),
        GeneratorDevice(index=1, name="NVIDIA GeForce RTX 4070", is_integrated=False),
    ]
    matched = match_adapter_to_device(adapter, devices)
    assert matched is not None
    assert matched.index == 1


def test_list_generator_devices_parses_json_stdout(tmp_path):
    from types import SimpleNamespace

    from generator_capabilities import GeneratorCapabilities
    from generator_devices import list_generator_devices

    exe = tmp_path / "gen.exe"
    exe.write_bytes(b"x")
    payload = '{"backend":"opencl","devices":[{"index":0,"name":"GPU A"}]}'

    def _runner(cmd, **_kwargs):
        assert "-list-devices" in cmd
        return SimpleNamespace(returncode=0, stdout=payload, stderr="")

    caps = GeneratorCapabilities(supports_list_devices=True)
    devices = list_generator_devices(
        exe_path=exe,
        backend="opencl",
        capabilities=caps,
        runner=_runner,
    )
    assert len(devices) == 1
    assert devices[0].name == "GPU A"
