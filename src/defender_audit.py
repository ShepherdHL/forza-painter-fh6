"""
Structured behavior logging to isolate Windows Defender / AV heuristic triggers.

Enable with environment variable FORZA_PAINTER_DEFENDER_AUDIT=1 (or true/yes/on).
Logs append to runtime/logs/defender-audit.log under the app ROOT (see app_paths).
"""

from __future__ import annotations

import os
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

_LOCK = threading.Lock()
_LOG_PATH: Path | None = None
_ENABLED: bool | None = None

# Categories map to common AV / Defender heuristic families.
CATEGORY_ELEVATION = "ELEVATION"
CATEGORY_PROCESS_SPAWN = "PROCESS_SPAWN"
CATEGORY_PROCESS_ENUM = "PROCESS_ENUM"
CATEGORY_MEMORY_READ = "MEMORY_READ"
CATEGORY_MEMORY_WRITE = "MEMORY_WRITE"
CATEGORY_MEMORY_SCAN = "MEMORY_SCAN"
CATEGORY_MEMORY_QUERY = "MEMORY_QUERY"
CATEGORY_DLL_LOAD = "DLL_LOAD"
CATEGORY_NETWORK = "NETWORK"
CATEGORY_REGISTRY_READ = "REGISTRY_READ"
CATEGORY_FILE_IO = "FILE_IO"
CATEGORY_HELPER = "HELPER"
CATEGORY_STARTUP = "STARTUP"


def audit_enabled() -> bool:
    global _ENABLED
    if _ENABLED is not None:
        return _ENABLED
    value = os.environ.get("FORZA_PAINTER_DEFENDER_AUDIT", "").strip().lower()
    _ENABLED = value in ("1", "true", "yes", "on")
    return _ENABLED


def _resolve_log_path() -> Path:
    global _LOG_PATH
    if _LOG_PATH is not None:
        return _LOG_PATH
    try:
        from app_paths import ROOT

        path = ROOT / "runtime" / "logs" / "defender-audit.log"
    except Exception:
        path = Path.cwd() / "runtime" / "logs" / "defender-audit.log"
    _LOG_PATH = path
    return path


def log_path() -> Path:
    return _resolve_log_path()


def _format_context(context: Mapping[str, Any]) -> str:
    if not context:
        return ""
    parts = []
    for key, value in context.items():
        if value is None:
            continue
        parts.append(f"{key}={value}")
    return (" " + " ".join(parts)) if parts else ""


def log_event(category: str, message: str, **context: Any) -> None:
    if not audit_enabled():
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    pid = os.getpid()
    frozen = bool(getattr(sys, "frozen", False))
    admin = context.pop("elevated", None)
    if admin is None and os.name == "nt":
        try:
            import ctypes

            admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except OSError:
            admin = "unknown"
    line = (
        f"{timestamp} pid={pid} frozen={int(frozen)} elevated={admin} "
        f"[{category}] {message}{_format_context(context)}"
    )
    path = _resolve_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with path.open("a", encoding="utf-8", errors="replace") as handle:
                handle.write(line + "\n")
    except OSError:
        pass


def log_startup(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv
    log_event(
        CATEGORY_STARTUP,
        "process start",
        executable=sys.executable,
        argv=" ".join(str(a) for a in args[:12]),
        helper=bool(len(args) >= 3 and args[1] == "--helper"),
    )


def log_elevation(action: str, **context: Any) -> None:
    log_event(CATEGORY_ELEVATION, action, **context)


def log_subprocess(cmd, *, purpose: str = "", **context: Any) -> None:
    try:
        from security_policy import redact_sensitive_log_text

        command = redact_sensitive_log_text(" ".join(str(x) for x in cmd))
    except Exception:
        command = "<redacted-unavailable>"
    log_event(
        CATEGORY_PROCESS_SPAWN,
        purpose or "subprocess",
        command=command,
        **context,
    )


def log_memory(
    category: str,
    operation: str,
    *,
    target_pid: int | None = None,
    address: int | None = None,
    size: int | None = None,
    **context: Any,
) -> None:
    ctx: dict[str, Any] = dict(context)
    if target_pid is not None:
        ctx["target_pid"] = target_pid
    if address is not None:
        ctx["address"] = f"0x{int(address):x}"
    if size is not None:
        ctx["size"] = size
    log_event(category, operation, **ctx)


def log_dll_load(path: str | Path, **context: Any) -> None:
    log_event(CATEGORY_DLL_LOAD, "clr.AddReference or native load", path=str(path), **context)


def log_network(url: str, purpose: str = "") -> None:
    log_event(CATEGORY_NETWORK, purpose or "https request", url=url)


def log_registry_read(key: str, **context: Any) -> None:
    log_event(CATEGORY_REGISTRY_READ, "registry read", key=key, **context)


def log_exception(category: str, message: str, exc: BaseException) -> None:
    log_event(category, message, error=type(exc).__name__, detail=str(exc)[:500])


def audit_call(category: str, operation: str):
    """Decorator for short, auditable call sites."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if audit_enabled():
                log_event(category, f"{operation} begin")
            try:
                return func(*args, **kwargs)
            except BaseException as exc:
                if audit_enabled():
                    log_exception(category, f"{operation} failed", exc)
                raise
            finally:
                if audit_enabled():
                    log_event(category, f"{operation} end")

        wrapper.__name__ = getattr(func, "__name__", "wrapped")
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
