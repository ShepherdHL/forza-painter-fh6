from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from gpu_adapters import GpuAdapter, normalize_gpu_selection
from generator_gpu_settings import AUTO_GPU_ID, GeneratorGpuSettings
from windows_gpu_preference import GPU_PREF_HIGH_PERFORMANCE, GPU_PREF_POWER_SAVING, apply_generator_gpu_preference


class _FakeKey:
    def __init__(self):
        self.values: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def DeleteValue(self, _key, name):
        self.values.pop(name, None)


def _set_value_ex(key, name, _reserved, _type, value):
    key.values[name] = value


def _fake_winreg(fake_key):
    return SimpleNamespace(
        HKEY_CURRENT_USER=1,
        KEY_SET_VALUE=2,
        REG_SZ=3,
        OpenKey=lambda *_args, **_kwargs: fake_key,
        CreateKey=lambda *_args, **_kwargs: fake_key,
        DeleteValue=lambda key, name: key.DeleteValue(key, name),
        SetValueEx=_set_value_ex,
    )


def test_normalize_gpu_selection_resets_missing_id():
    settings = GeneratorGpuSettings(gpu_selection_id="wmi:missing")
    adapters = [GpuAdapter(id="wmi:1", label="GPU", afterburner_index=0)]
    normalized, missing = normalize_gpu_selection(settings, adapters)
    assert missing
    assert normalized.gpu_selection_id == AUTO_GPU_ID


def test_normalize_gpu_selection_keeps_valid_id():
    settings = GeneratorGpuSettings(gpu_selection_id="wmi:1")
    adapters = [GpuAdapter(id="wmi:1", label="GPU", afterburner_index=0)]
    normalized, missing = normalize_gpu_selection(settings, adapters)
    assert not missing
    assert normalized.gpu_selection_id == "wmi:1"


def test_apply_generator_gpu_preference_sets_discrete(monkeypatch, tmp_path):
    fake_key = _FakeKey()
    exe = tmp_path / "forza-painter-geometrize-go.exe"
    exe.write_bytes(b"x")
    adapter = GpuAdapter(id="wmi:1", label="NVIDIA GeForce RTX 4070", is_integrated=False)

    monkeypatch.setitem(sys.modules, "winreg", _fake_winreg(fake_key))
    monkeypatch.setattr("windows_gpu_preference.os.name", "nt")

    assert apply_generator_gpu_preference(exe, adapter, auto=False)
    assert fake_key.values[str(exe.resolve())] == f"GpuPreference={GPU_PREF_HIGH_PERFORMANCE};"


def test_apply_generator_gpu_preference_sets_integrated(monkeypatch, tmp_path):
    fake_key = _FakeKey()
    exe = tmp_path / "forza-painter-geometrize-go.exe"
    exe.write_bytes(b"x")
    adapter = GpuAdapter(id="wmi:1", label="AMD Radeon Graphics", is_integrated=True)

    monkeypatch.setitem(sys.modules, "winreg", _fake_winreg(fake_key))
    monkeypatch.setattr("windows_gpu_preference.os.name", "nt")

    assert apply_generator_gpu_preference(exe, adapter, auto=False)
    assert fake_key.values[str(exe.resolve())] == f"GpuPreference={GPU_PREF_POWER_SAVING};"
