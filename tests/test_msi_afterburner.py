from __future__ import annotations

import ctypes
import struct

from msi_afterburner import (
    MAHM_SIGNATURE,
    SRC_CPU_TEMPERATURE,
    SRC_GPU_CORE_CLOCK,
    SRC_GPU_TEMPERATURE,
    SRC_GPU_USAGE,
    _decode_ascii,
    _is_finite,
    _is_load_pct,
    _looks_like_cpu_clock,
    _looks_like_cpu_temp,
    _looks_like_gpu_temp,
    _parse_entries,
    _pick_max,
    _select_gpu_index,
)
import msi_afterburner as module


def _make_entry(entry_size: int, *, data: float, src_id: int, dw_gpu: int = 0, name: str = "") -> bytearray:
    entry = bytearray(entry_size)
    if name:
        entry[0 : len(name)] = name.encode("ascii")
    struct.pack_into("<f", entry, 1300, data)
    struct.pack_into("<I", entry, 1316, dw_gpu)
    struct.pack_into("<I", entry, 1320, src_id)
    return entry


def test_select_gpu_index_prefers_active_gpu():
    assert _select_gpu_index({0: 5.0, 1: 40.0}, {0: 600.0, 1: 210.0}, {0: 35.0, 1: 36.0}) == 1


def test_select_gpu_index_prefers_highest_clocked_gpu_when_idle():
    assert _select_gpu_index({0: 0.0, 1: 0.0}, {0: 600.0, 1: 210.0}, {0: 35.0, 1: 35.0}) == 1


def test_parse_entries_reads_gpu_and_cpu_temps():
    entry_size = 1324
    header_size = 32
    entries = [
        _make_entry(entry_size, data=72.0, src_id=SRC_GPU_TEMPERATURE, dw_gpu=1),
        _make_entry(entry_size, data=54.0, src_id=SRC_CPU_TEMPERATURE),
        _make_entry(entry_size, data=32.0, src_id=SRC_GPU_USAGE, dw_gpu=1),
        _make_entry(entry_size, data=210.0, src_id=SRC_GPU_CORE_CLOCK, dw_gpu=1),
        _make_entry(entry_size, data=600.0, src_id=SRC_GPU_CORE_CLOCK, dw_gpu=0),
    ]

    blob = bytearray(header_size + entry_size * len(entries))
    struct.pack_into("<6I", blob, 0, MAHM_SIGNATURE, 0, header_size, len(entries), entry_size, 1234)
    offset = header_size
    for entry in entries:
        blob[offset : offset + entry_size] = entry
        offset += entry_size

    original = module._read_bytes
    module._read_bytes = lambda view, offset, size: view[offset : offset + size]
    try:
        reading = _parse_entries(bytes(blob), header_size, len(entries), entry_size, 1234)
    finally:
        module._read_bytes = original

    assert reading.gpu_temp_c == 72.0
    assert reading.cpu_temp_c == 54.0
    assert reading.gpu_load_pct == 32.0
    assert reading.gpu_clock_mhz == 210.0


def test_view_address_adds_offset():
    view = ctypes.c_void_p(0x1000)
    assert module._view_address(view, 32) == 0x1020


def test_read_bytes_from_c_void_p_view():
    payload = b"MAHM" + b"\x00" * 28
    address = (ctypes.c_char * len(payload)).from_buffer_copy(payload)
    view = ctypes.cast(address, ctypes.c_void_p)
    assert module._read_bytes(view, 0, 4) == b"MAHM"


def test_name_helpers():
    assert _looks_like_gpu_temp("gpu temperature", "c")
    assert _looks_like_cpu_temp("cpu temperature", "c")
    assert _looks_like_cpu_clock("cpu clock")
    assert _pick_max([10.0, 20.0]) == 20.0
    assert _decode_ascii(b"GPU\x00rest", 0, 8) == "GPU"
    assert not _is_finite(float("nan"))
    assert _is_load_pct(50.0)
    assert not _is_load_pct(2556.0)
