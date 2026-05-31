from __future__ import annotations

import json
import subprocess

from gpu_adapters import (
    GpuAdapter,
    _attach_afterburner_indices,
    _label_match_score,
    _make_adapter,
    _parse_wmi_json,
    is_likely_integrated_graphics,
    list_wmi_gpu_adapters,
    normalize_gpu_selection,
    resolve_afterburner_index,
    wmi_adapter_id,
)
from generator_gpu_settings import (
    AUTO_GPU_ID,
    GeneratorGpuSettings,
    load_generator_gpu_settings,
    save_generator_gpu_settings,
)


def test_generator_gpu_settings_round_trip(tmp_path):
    save_generator_gpu_settings(
        GeneratorGpuSettings(gpu_selection_id="wmi:abc123", generator_backend="vulkan"),
        tmp_path,
    )
    loaded = load_generator_gpu_settings(tmp_path)
    assert loaded.gpu_selection_id == "wmi:abc123"
    assert loaded.generator_backend == "vulkan"


def test_normalize_generator_backend_rejects_unknown():
    from generator_gpu_settings import normalize_generator_backend

    assert normalize_generator_backend("cuda") == "auto"


def test_wmi_adapter_id_is_stable():
    pnp = "PCI\\VEN_10DE&DEV_2786&SUBSYS_..."
    assert wmi_adapter_id(pnp) == wmi_adapter_id(pnp)
    assert wmi_adapter_id(pnp).startswith("wmi:")


def test_parse_wmi_json_single_object():
    payload = json.dumps({"Name": "NVIDIA GeForce RTX 4070", "PNPDeviceID": "PCI\\VEN_10DE"})
    items = _parse_wmi_json(payload)
    assert len(items) == 1
    assert items[0]["Name"] == "NVIDIA GeForce RTX 4070"


def test_list_wmi_gpu_adapters_parses_powershell_json():
    payload = json.dumps(
        [
            {"Name": "Intel UHD Graphics 770", "PNPDeviceID": "PCI\\VEN_8086&A"},
            {"Name": "NVIDIA GeForce RTX 4070", "PNPDeviceID": "PCI\\VEN_10DE&B"},
        ]
    )

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=payload, stderr="")

    adapters = list_wmi_gpu_adapters(runner=fake_run)
    assert len(adapters) == 2
    assert adapters[0].vendor_hint == "intel"
    assert adapters[1].vendor_hint == "nvidia"


def test_attach_afterburner_indices_matches_by_name():
    wmi = [
        GpuAdapter(id="wmi:1", label="Intel UHD Graphics 770", vendor_hint="intel"),
        GpuAdapter(id="wmi:2", label="NVIDIA GeForce RTX 4070", vendor_hint="nvidia"),
    ]
    mahm = {0: "Intel UHD Graphics", 1: "NVIDIA GeForce RTX 4070"}
    attached = _attach_afterburner_indices(wmi, mahm)
    assert attached[0].afterburner_index == 0
    assert attached[1].afterburner_index == 1


def test_resolve_afterburner_index_auto_returns_none():
    settings = GeneratorGpuSettings(gpu_selection_id=AUTO_GPU_ID)
    adapters = [GpuAdapter(id="wmi:1", label="GPU", afterburner_index=1)]
    assert resolve_afterburner_index(settings, adapters) is None


def test_resolve_afterburner_index_returns_matching_index():
    settings = GeneratorGpuSettings(gpu_selection_id="wmi:2")
    adapters = [
        GpuAdapter(id="wmi:1", label="Intel", afterburner_index=0),
        GpuAdapter(id="wmi:2", label="NVIDIA", afterburner_index=1),
    ]
    assert resolve_afterburner_index(settings, adapters) == 1


def test_label_match_score_prefers_shared_tokens():
    assert _label_match_score("nvidia geforce rtx 4070", "geforce rtx 4070") > 0


def test_is_likely_integrated_amd_radeon_graphics():
    assert is_likely_integrated_graphics("AMD Radeon Graphics")
    assert is_likely_integrated_graphics("AMD Radeon(TM) Graphics")


def test_is_likely_integrated_intel_uhd():
    assert is_likely_integrated_graphics("Intel(R) UHD Graphics 770")


def test_is_likely_integrated_rejects_discrete():
    assert not is_likely_integrated_graphics("NVIDIA GeForce RTX 4070")
    assert not is_likely_integrated_graphics("AMD Radeon RX 7900 XTX")
    assert not is_likely_integrated_graphics("Intel Arc A770")


def test_make_adapter_sets_integrated_flag():
    adapter = _make_adapter(adapter_id="wmi:1", label="AMD Radeon Graphics")
    assert adapter.is_integrated


def test_adapter_display_label_marks_integrated():
    from gpu_adapters import adapter_display_label

    adapter = _make_adapter(adapter_id="wmi:1", label="AMD Radeon Graphics")
    assert adapter_display_label(adapter, integrated_tag="integrated") == "AMD Radeon Graphics (integrated)"


def test_normalize_gpu_selection_auto_unchanged():
    settings = GeneratorGpuSettings(gpu_selection_id=AUTO_GPU_ID)
    normalized, missing = normalize_gpu_selection(settings, [])
    assert not missing
    assert normalized.gpu_selection_id == AUTO_GPU_ID


def test_list_wmi_marks_integrated_intel():
    payload = json.dumps([{"Name": "AMD Radeon Graphics", "PNPDeviceID": "PCI\\VEN_1002&A"}])

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=payload, stderr="")

    adapters = list_wmi_gpu_adapters(runner=fake_run)
    assert len(adapters) == 1
    assert adapters[0].is_integrated
