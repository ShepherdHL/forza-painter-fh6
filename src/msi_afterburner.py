"""
Read CPU/GPU sensor data from MSI Afterburner shared memory (MAHMSharedMemory).

Requires MSI Afterburner to be installed and running. No bundled drivers or DLLs.
"""

from __future__ import annotations

import ctypes
import os
import struct
from ctypes import wintypes
from dataclasses import dataclass
from typing import Iterable

MAHM_SIGNATURE = 0x4D41484D
MAHM_NAMES = ("MAHMSharedMemory", "Local\\MAHMSharedMemory")
MAX_PATH = 260

# MAHM monitoring source ids (see MSI Afterburner SDK MAHMSharedMemory.h).
SRC_GPU_TEMPERATURE = 0x00
SRC_GPU_CORE_CLOCK = 0x20
SRC_GPU_SHADER_CLOCK = 0x21
SRC_GPU_MEMORY_CLOCK = 0x22
SRC_GPU_USAGE = 0x30
SRC_CPU_TEMPERATURE = 0x80
SRC_CPU_USAGE = 0x90
SRC_CPU_CLOCK = 0xA0

FILE_MAP_READ = 0x0004
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

_kernel32: ctypes.WinDLL | None = None


@dataclass(frozen=True)
class MahmReading:
    cpu_load_pct: float | None = None
    cpu_clock_mhz: float | None = None
    cpu_temp_c: float | None = None
    gpu_load_pct: float | None = None
    gpu_clock_mhz: float | None = None
    gpu_temp_c: float | None = None
    timestamp: int | None = None


def _kernel32_api() -> ctypes.WinDLL | None:
    global _kernel32
    if os.name != "nt":
        return None
    if _kernel32 is None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenFileMappingW.restype = wintypes.HANDLE
        kernel32.OpenFileMappingW.argtypes = (
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        kernel32.MapViewOfFile.restype = wintypes.LPVOID
        kernel32.MapViewOfFile.argtypes = (
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_size_t,
        )
        kernel32.UnmapViewOfFile.restype = wintypes.BOOL
        kernel32.UnmapViewOfFile.argtypes = (wintypes.LPVOID,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        _kernel32 = kernel32
    return _kernel32


def afterburner_available() -> bool:
    return read_mahm_reading() is not None


def read_gpu_temp_c() -> float | None:
    reading = read_mahm_reading()
    if reading is None:
        return None
    return reading.gpu_temp_c


def read_mahm_reading() -> MahmReading | None:
    kernel32 = _kernel32_api()
    if kernel32 is None:
        return None

    for name in MAHM_NAMES:
        handle = kernel32.OpenFileMappingW(FILE_MAP_READ, False, name)
        if not handle or handle == INVALID_HANDLE_VALUE:
            continue
        view = None
        try:
            view = kernel32.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 0)
            if not view:
                continue
            header = _read_bytes(view, 0, 32)
            if len(header) < 32:
                continue
            signature, _version, header_size, num_entries, entry_size, timestamp = struct.unpack_from(
                "<6I", header, 0
            )
            if signature != MAHM_SIGNATURE or entry_size < 1324:
                continue
            return _parse_entries(view, header_size, num_entries, entry_size, timestamp)
        except OSError:
            continue
        finally:
            if view:
                kernel32.UnmapViewOfFile(view)
            kernel32.CloseHandle(handle)
    return None


def _view_address(view: int | ctypes.c_void_p, offset: int) -> int:
    base = ctypes.cast(view, ctypes.c_void_p).value
    if base is None:
        raise OSError("invalid mapped view address")
    return int(base) + int(offset)


def _read_bytes(view: int | ctypes.c_void_p, offset: int, size: int) -> bytes:
    if size <= 0:
        return b""
    buffer = (ctypes.c_char * size)()
    ctypes.memmove(buffer, _view_address(view, offset), size)
    return bytes(buffer)


def _parse_entries(
    view: int | ctypes.c_void_p,
    header_size: int,
    num_entries: int,
    entry_size: int,
    timestamp: int,
) -> MahmReading:
    gpu_temps: dict[int, float] = {}
    gpu_loads: dict[int, float] = {}
    gpu_clocks: dict[int, float] = {}
    cpu_temps: list[float] = []
    cpu_loads: list[float] = []
    cpu_clocks: list[float] = []
    cpu_clock_aggregate: float | None = None
    cpu_load_aggregate: float | None = None

    for index in range(int(num_entries)):
        base = int(header_size) + index * int(entry_size)
        entry = _read_bytes(view, base, int(entry_size))
        if len(entry) < 1324:
            continue
        data = struct.unpack_from("<f", entry, 1300)[0]
        dw_gpu = struct.unpack_from("<I", entry, 1316)[0]
        src_id = struct.unpack_from("<I", entry, 1320)[0]
        src_name = _decode_ascii(entry, 0, MAX_PATH).lower()
        units = _decode_ascii(entry, MAX_PATH, MAX_PATH).lower()

        if not _is_finite(data):
            continue

        if src_id == SRC_GPU_TEMPERATURE or _looks_like_gpu_temp(src_name, units):
            gpu_temps[int(dw_gpu)] = float(data)
        elif src_id == SRC_GPU_USAGE and _is_load_pct(data):
            gpu_loads[int(dw_gpu)] = float(data)
        elif src_id == SRC_GPU_CORE_CLOCK:
            gpu_clocks[int(dw_gpu)] = float(data)
        elif src_id == SRC_CPU_TEMPERATURE or _looks_like_cpu_temp(src_name, units):
            cpu_temps.append(float(data))
        elif src_id == SRC_CPU_USAGE and src_name == "cpu usage":
            cpu_load_aggregate = float(data)
        elif src_id == SRC_CPU_USAGE and _is_load_pct(data):
            cpu_loads.append(float(data))
        elif src_id == SRC_CPU_CLOCK and src_name == "cpu clock":
            cpu_clock_aggregate = float(data)
        elif src_id == SRC_CPU_CLOCK or _looks_like_cpu_clock(src_name):
            cpu_clocks.append(float(data))

    gpu_index = _select_gpu_index(gpu_loads, gpu_clocks, gpu_temps)

    return MahmReading(
        cpu_load_pct=cpu_load_aggregate if cpu_load_aggregate is not None else _pick_max(cpu_loads),
        cpu_clock_mhz=cpu_clock_aggregate if cpu_clock_aggregate is not None else _pick_max(cpu_clocks),
        cpu_temp_c=_pick_max(cpu_temps),
        gpu_load_pct=gpu_loads.get(gpu_index),
        gpu_clock_mhz=gpu_clocks.get(gpu_index),
        gpu_temp_c=gpu_temps.get(gpu_index),
        timestamp=int(timestamp),
    )


def _select_gpu_index(
    loads: dict[int, float],
    clocks: dict[int, float],
    temps: dict[int, float],
) -> int:
    candidates = set(loads) | set(clocks) | set(temps)
    if not candidates:
        return 0
    active = [gpu for gpu in candidates if loads.get(gpu, 0.0) > 1.0]
    if active:
        return max(active, key=lambda gpu: loads.get(gpu, 0.0))
    # Idle dual-GPU: index 0 is often iGPU; prefer the highest-index GPU with a clock reading.
    clocked = [gpu for gpu in candidates if gpu in clocks]
    if clocked:
        return max(clocked)
    return max(candidates)


def _decode_ascii(entry: bytes, offset: int, length: int) -> str:
    chunk = entry[offset : offset + length]
    return chunk.split(b"\0", 1)[0].decode("ascii", errors="ignore").strip()


def _is_finite(value: float) -> bool:
    return value == value and abs(value) != float("inf")


def _is_load_pct(value: float) -> bool:
    return 0.0 <= value <= 100.0


def _pick_max(values: Iterable[float]) -> float | None:
    items = list(values)
    if not items:
        return None
    return max(items)


def _looks_like_gpu_temp(name: str, units: str) -> bool:
    return "gpu" in name and "temp" in name and ("c" in units or "°" in units)


def _looks_like_cpu_temp(name: str, units: str) -> bool:
    return "cpu" in name and "temp" in name and ("c" in units or "°" in units)


def _looks_like_cpu_clock(name: str) -> bool:
    return "cpu" in name and "clock" in name
