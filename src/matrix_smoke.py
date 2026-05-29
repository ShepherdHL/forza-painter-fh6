"""
Headless smoke probe for Defender matrix builds.

Invoked via: forza-painter-fh6.exe --matrix-smoke
Writes runtime/logs/matrix-smoke.json with startup and environment evidence.
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def _is_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def _meipass_dirs() -> list[str]:
    found: list[str] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        found.append(str(meipass))
    temp_root = Path(tempfile.gettempdir())
    try:
        for entry in temp_root.glob("_MEI*"):
            if entry.is_dir():
                found.append(str(entry))
    except OSError:
        pass
    return found


def run_matrix_smoke() -> int:
    from app_paths import ROOT, RESOURCE_ROOT

    started = time.perf_counter()
    report: dict = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "variant_id": None,
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "argv": sys.argv,
        "elevated": _is_admin(),
        "root": str(ROOT),
        "resource_root": str(RESOURCE_ROOT),
        "meipass": getattr(sys, "_MEIPASS", None),
        "meipass_dirs_seen": _meipass_dirs(),
        "env_flags": {
            key: os.environ.get(key)
            for key in (
                "FORZA_PAINTER_DEFENDER_AUDIT",
                "FORZA_PAINTER_DISABLE_ELEVATION",
                "FORZA_PAINTER_DISABLE_GENERATOR",
                "FORZA_PAINTER_DISABLE_NETWORKING",
                "FORZA_PAINTER_DISABLE_MEMORY_SCAN",
            )
            if os.environ.get(key)
        },
        "build_profile": None,
        "defender_audit_log": None,
        "errors": [],
    }

    try:
        from build_profile import get_build_profile

        report["build_profile"] = get_build_profile().to_dict()
        report["variant_id"] = get_build_profile().variant_id
    except Exception as exc:
        report["errors"].append(f"build_profile: {exc}")

    try:
        from defender_audit import audit_enabled, log_event, log_startup, CATEGORY_STARTUP

        if audit_enabled():
            log_startup(sys.argv)
            log_event(CATEGORY_STARTUP, "matrix-smoke begin")
    except Exception as exc:
        report["errors"].append(f"defender_audit: {exc}")

    try:
        from build_profile import generator_disabled, memory_scan_disabled, networking_disabled

        report["gates"] = {
            "generator_disabled": generator_disabled(),
            "networking_disabled": networking_disabled(),
            "memory_scan_disabled": memory_scan_disabled(),
        }
    except Exception as exc:
        report["errors"].append(f"gates: {exc}")

    try:
        import psutil

        report["process_count"] = len(list(psutil.process_iter(["pid"])))
    except Exception as exc:
        report["errors"].append(f"psutil: {exc}")

    report["elapsed_ms"] = int((time.perf_counter() - started) * 1000)

    out_dir = ROOT / "runtime" / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "matrix-smoke.json"
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    report["defender_audit_log"] = str(out_dir / "defender-audit.log")
    report["output"] = str(out_path)

    try:
        from defender_audit import log_event, CATEGORY_STARTUP

        log_event(CATEGORY_STARTUP, "matrix-smoke complete", output=str(out_path))
    except Exception:
        pass

    return 0
