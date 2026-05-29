# Discord: A-Dawg#0001 (AE)
# Supports: Forza Horizon 5 / Forza Horizon 6 profile probing
# License: MIT

import ctypes
import struct
import sys
from ctypes import wintypes

import win32process

from security_policy import MAX_MEMORY_READ_BYTES, is_user_address


ERROR_PARTIAL_COPY = 0x012B
ERROR_ACCESS_DENIED = 5
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_ALL_ACCESS = 0x1F0FFF
PROCESS_ACCESS_READ = PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
PROCESS_ACCESS_READ_LIMITED = PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ
PROCESS_ACCESS_WRITE = PROCESS_ACCESS_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION

TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

SIZE_T = ctypes.c_size_t
PSIZE_T = ctypes.POINTER(SIZE_T)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class ProcessMemoryError(OSError):
    """Raised when a process memory operation fails or returns insufficient data."""


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("th32ModuleID", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("GlblcntUsage", wintypes.DWORD),
        ("ProccntUsage", wintypes.DWORD),
        ("modBaseAddr", ctypes.c_size_t),
        ("modBaseSize", wintypes.DWORD),
        ("hModule", wintypes.HMODULE),
        ("szModule", wintypes.WCHAR * 256),
        ("szExePath", wintypes.WCHAR * 260),
    ]


def _check_zero(result, func, args):
    if not result:
        raise ctypes.WinError(ctypes.get_last_error())
    return args


kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)

kernel32.ReadProcessMemory.errcheck = _check_zero
kernel32.ReadProcessMemory.argtypes = (
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    SIZE_T,
    PSIZE_T,
)

kernel32.WriteProcessMemory.errcheck = _check_zero
kernel32.WriteProcessMemory.argtypes = (
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    SIZE_T,
    PSIZE_T,
)

kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Module32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W))
kernel32.Module32FirstW.restype = wintypes.BOOL

_handles: dict[tuple[int, bool], int] = {}

READ_ACCESS_CANDIDATES = (
    PROCESS_ACCESS_READ,
    PROCESS_ACCESS_READ_LIMITED,
    PROCESS_ALL_ACCESS,
)
WRITE_ACCESS_CANDIDATES = (
    PROCESS_ACCESS_WRITE,
    PROCESS_ALL_ACCESS,
)


def is_64bit():
    return struct.calcsize("P") == 8


def _open_process_raw(pid: int, access: int) -> int:
    handle = kernel32.OpenProcess(access, False, int(pid))
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    return handle


def _open_handle(pid: int, write: bool) -> int:
    key = (int(pid), bool(write))
    cached = _handles.get(key)
    if cached:
        return cached

    candidates = WRITE_ACCESS_CANDIDATES if write else READ_ACCESS_CANDIDATES
    last_exc = None
    for access in candidates:
        try:
            handle = _open_process_raw(pid, access)
            _handles[key] = handle
            return handle
        except OSError as exc:
            last_exc = exc
            continue

    raise ProcessMemoryError(
        "Unable to open Forza process {} for {}. Close other memory tools, keep FH6 in "
        "Vinyl Group Editor, then run this app as administrator.".format(
            pid, "writing" if write else "reading"
        )
    ) from last_exc


def open_process_handle(pid: int, write: bool = False) -> int:
    """Shared process handle for VirtualQueryEx and memory I/O."""
    return _open_handle(pid, write=write)


def release_process(pid: int | None = None) -> None:
    if pid is None:
        keys = list(_handles.keys())
    else:
        keys = [item for item in _handles if item[0] == int(pid)]
    for key in keys:
        try:
            kernel32.CloseHandle(_handles.pop(key))
        except OSError:
            pass


def _base_address_from_snapshot(pid: int) -> int:
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, int(pid))
    if snapshot == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32W)
        if not kernel32.Module32FirstW(snapshot, ctypes.byref(entry)):
            raise ctypes.WinError(ctypes.get_last_error())
        base = int(entry.modBaseAddr)
        if base <= 0:
            raise ProcessMemoryError("Module snapshot returned an invalid base address")
        return base
    finally:
        kernel32.CloseHandle(snapshot)


def get_base_address(pid):
    pid = int(pid)
    try:
        return _base_address_from_snapshot(pid)
    except OSError as snapshot_exc:
        if getattr(snapshot_exc, "winerror", None) != ERROR_ACCESS_DENIED:
            raise ProcessMemoryError(
                "Unable to query module base for process {}: {}".format(pid, snapshot_exc)
            ) from snapshot_exc
    try:
        handle = _open_handle(pid, write=False)
        modules = win32process.EnumProcessModules(handle)
        return modules[0]
    except OSError as exc:
        raise ProcessMemoryError(
            "Unable to query module base for process {}. Run the app as administrator.".format(pid)
        ) from exc


def _audit_memory_read(pid, address, size):
    try:
        from defender_audit import CATEGORY_MEMORY_READ, log_memory

        log_memory(
            CATEGORY_MEMORY_READ,
            "ReadProcessMemory",
            target_pid=pid,
            address=address,
            size=size,
        )
    except Exception:
        pass


def _audit_memory_write(pid, address, nbytes):
    try:
        from defender_audit import CATEGORY_MEMORY_WRITE, log_memory

        log_memory(
            CATEGORY_MEMORY_WRITE,
            "WriteProcessMemory",
            target_pid=pid,
            address=address,
            size=nbytes,
        )
    except Exception:
        pass


def read_process_memory(pid, address, size, *, strict=False, allow_partial=True, audit=True):
    try:
        from build_profile import memory_scan_disabled

        if memory_scan_disabled():
            if strict:
                raise ProcessMemoryError("Memory read disabled for this build profile")
            return b""
    except ProcessMemoryError:
        raise
    except Exception:
        pass
    if size <= 0:
        return b""
    if size > MAX_MEMORY_READ_BYTES:
        raise ProcessMemoryError(
            f"Refusing to read {size} bytes (limit {MAX_MEMORY_READ_BYTES})"
        )
    if not is_user_address(address):
        if strict:
            raise ProcessMemoryError(f"Refusing to read invalid address 0x{int(address):x}")
        return b""

    if audit:
        _audit_memory_read(pid, address, size)
    handle = _open_handle(pid, write=False)
    buf = (ctypes.c_char * size)()
    nread = SIZE_T()
    try:
        kernel32.ReadProcessMemory(
            handle, int(address), buf, size, ctypes.byref(nread)
        )
    except OSError as exc:
        winerror = getattr(exc, "winerror", None)
        if allow_partial and winerror == ERROR_PARTIAL_COPY and nread.value:
            data = bytes(buf[: nread.value])
            if strict and len(data) != size:
                raise ProcessMemoryError(
                    f"Partial read at 0x{int(address):x}: got {len(data)} of {size} bytes"
                ) from exc
            return data
        if strict:
            raise ProcessMemoryError(
                f"Read failed at 0x{int(address):x} ({size} bytes): {exc}"
            ) from exc
        return b""

    data = bytes(buf[: nread.value])
    if strict and len(data) != size:
        raise ProcessMemoryError(
            f"Incomplete read at 0x{int(address):x}: got {len(data)} of {size} bytes"
        )
    return data


def write_process_memory(pid, address, buf):
    if not buf:
        return
    try:
        from build_profile import memory_scan_disabled

        if memory_scan_disabled():
            raise ProcessMemoryError("Memory write disabled for this build profile")
    except ProcessMemoryError:
        raise
    except Exception:
        pass
    if not is_user_address(address):
        raise ProcessMemoryError(f"Refusing to write invalid address 0x{int(address):x}")
    _audit_memory_write(pid, address, len(buf))
    handle = _open_handle(pid, write=True)
    nwritten = SIZE_T()
    try:
        kernel32.WriteProcessMemory(
            handle,
            int(address),
            buf,
            len(buf),
            ctypes.byref(nwritten),
        )
    except OSError as exc:
        raise ProcessMemoryError(
            f"Write failed at 0x{int(address):x} ({len(buf)} bytes): {exc}"
        ) from exc
    if nwritten.value != len(buf):
        raise ProcessMemoryError(
            f"Incomplete write at 0x{int(address):x}: wrote {nwritten.value} of {len(buf)} bytes"
        )


def scan_block(pid, start_address, block_size, scan_for):
    try:
        from build_profile import memory_scan_disabled

        if memory_scan_disabled():
            return -1
    except Exception:
        pass
    try:
        from defender_audit import CATEGORY_MEMORY_SCAN, log_memory

        log_memory(
            CATEGORY_MEMORY_SCAN,
            "signature scan",
            target_pid=pid,
            address=start_address,
            size=block_size,
            pattern_len=len(scan_for),
        )
    except Exception:
        pass
    memory = read_process_memory(
        pid,
        start_address,
        block_size,
        strict=False,
        allow_partial=True,
        audit=False,
    )
    return memory.find(scan_for)


def dereference_pointer(pid, pointer_address):
    address_bytes = read_process_memory(pid, pointer_address, 8, strict=True)
    return int.from_bytes(address_bytes, byteorder=sys.byteorder)


def read_int(pid, int_address):
    int_bytes = read_process_memory(pid, int_address, 4, strict=True)
    return int.from_bytes(int_bytes, byteorder=sys.byteorder)


def read_long(pid, int_address):
    long_bytes = read_process_memory(pid, int_address, 8, strict=True)
    return int.from_bytes(long_bytes, byteorder=sys.byteorder)
