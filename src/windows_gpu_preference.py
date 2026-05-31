"""Windows per-exe GPU preference for the bundled generator (Phase 2 routing)."""

from __future__ import annotations

import os
from pathlib import Path

from gpu_adapters import GpuAdapter

GPU_PREF_POWER_SAVING = 1
GPU_PREF_HIGH_PERFORMANCE = 2
_USER_GPU_PREFS_KEY = r"Software\Microsoft\DirectX\UserGpuPreferences"


def apply_generator_gpu_preference(
    exe_path: str | Path,
    adapter: GpuAdapter | None,
    *,
    auto: bool,
) -> bool:
    """Set or clear DirectX UserGpuPreferences for the generator executable."""
    if os.name != "nt":
        return False
    exe_path = Path(exe_path)
    try:
        exe_key = str(exe_path.resolve())
    except OSError:
        exe_key = str(exe_path)

    import winreg

    if auto or adapter is None:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _USER_GPU_PREFS_KEY, 0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, exe_key)
                except FileNotFoundError:
                    pass
        except FileNotFoundError:
            pass
        except OSError:
            return False
        return True

    preference = GPU_PREF_POWER_SAVING if adapter.is_integrated else GPU_PREF_HIGH_PERFORMANCE
    value = f"GpuPreference={preference};"
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _USER_GPU_PREFS_KEY) as key:
            winreg.SetValueEx(key, exe_key, 0, winreg.REG_SZ, value)
    except OSError:
        return False
    return True
