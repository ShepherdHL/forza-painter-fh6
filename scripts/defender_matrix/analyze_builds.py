#!/usr/bin/env python3
"""
Analyze Defender matrix builds: SHA256, size, PE imports, UPX heuristics, smoke output.
Writes dist/defender-matrix/analysis_results.json and MATRIX_ANALYSIS.md
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_cstring(data: bytes, offset: int) -> str:
    end = data.find(b"\x00", offset)
    if end < 0:
        end = len(data)
    return data[offset:end].decode("ascii", errors="replace")


def pe_import_dlls(path: Path) -> list[str]:
    """Minimal PE import table parser (no pefile dependency)."""
    try:
        data = path.read_bytes()
    except OSError as exc:
        return [f"<read-error: {exc}>"]

    if len(data) < 0x40 or data[:2] != b"MZ":
        return ["<invalid-pe>"]

    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if e_lfanew + 0x18 > len(data) or data[e_lfanew : e_lfanew + 4] != b"PE\0\0":
        return ["<invalid-pe-header>"]

    machine = struct.unpack_from("<H", data, e_lfanew + 4)[0]
    optional_offset = e_lfanew + 24
    magic = struct.unpack_from("<H", data, optional_offset)[0]
    is_pe32_plus = magic == 0x20B
    if is_pe32_plus:
        import_rva = struct.unpack_from("<I", data, optional_offset + 120)[0]
        import_size = struct.unpack_from("<I", data, optional_offset + 124)[0]
    else:
        import_rva = struct.unpack_from("<I", data, optional_offset + 104)[0]
        import_size = struct.unpack_from("<I", data, optional_offset + 108)[0]

    if not import_rva:
        return []

    num_sections = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    size_optional = struct.unpack_from("<H", data, e_lfanew + 20)[0]
    section_offset = optional_offset + size_optional
    sections = []
    for index in range(num_sections):
        off = section_offset + index * 40
        name = data[off : off + 8].rstrip(b"\x00").decode("ascii", errors="replace")
        virtual_size, virtual_addr, raw_size, raw_ptr = struct.unpack_from("<IIII", data, off + 8)
        sections.append((name, virtual_addr, virtual_size, raw_ptr, raw_size))

    def rva_to_offset(rva: int) -> int | None:
        for _name, virt, _vsize, raw, _rsize in sections:
            if virt <= rva < virt + max(_vsize, 1):
                return raw + (rva - virt)
        return None

    imp_off = rva_to_offset(import_rva)
    if imp_off is None:
        return []

    dlls: list[str] = []
    idx = 0
    while True:
        entry_off = imp_off + idx * 20
        if entry_off + 20 > len(data):
            break
        orig_first_thunk, _time, _fwd, name_rva, _first_thunk = struct.unpack_from("<IIIII", data, entry_off)
        if orig_first_thunk == 0 and name_rva == 0:
            break
        name_off = rva_to_offset(name_rva)
        if name_off is not None:
            dlls.append(_read_cstring(data, name_off))
        idx += 1
        if idx > 512:
            break
    _ = import_size
    return sorted(set(dll for dll in dlls if dll))


def pe_has_upx_signature(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    upper = data.upper()
    return b"UPX0" in upper or b"UPX1" in upper or b"UPX!" in upper


def authenticode_status(path: Path) -> str:
    if sys.platform != "win32":
        return "n/a"
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-AuthenticodeSignature -LiteralPath '{path}').Status.ToString()",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return (result.stdout or result.stderr or "unknown").strip() or "unknown"
    except Exception as exc:
        return f"error:{exc}"


def analyze_variant(variant_dir: Path, manifest_entry: dict[str, Any]) -> dict[str, Any]:
    exe = Path(manifest_entry.get("exe_path", ""))
    if not exe.is_file():
        exe = variant_dir / "forza-painter-fh6.exe"
    if not exe.is_file():
        nested = variant_dir / "forza-painter-fh6" / "forza-painter-fh6.exe"
        if nested.is_file():
            exe = nested

    profile_path = variant_dir / "build_profile.json"
    profile = {}
    if profile_path.is_file():
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            profile = {}

    record: dict[str, Any] = {
        "variant_id": manifest_entry.get("id", variant_dir.name),
        "label": manifest_entry.get("label", ""),
        "exe_path": str(exe),
        "exe_exists": exe.is_file(),
        "build_profile": profile,
    }
    if not exe.is_file():
        record["error"] = "executable missing"
        return record

    record["sha256"] = sha256_file(exe)
    record["size_bytes"] = exe.stat().st_size
    record["authenticode"] = authenticode_status(exe)
    record["import_dlls"] = pe_import_dlls(exe)
    record["upx_section_signature"] = pe_has_upx_signature(exe)

    # Embedded geometrize in bundle (onedir: check adjacent bin)
    bin_candidates = [
        variant_dir / "bin" / "forza-painter-geometrize-go.exe",
        exe.parent / "bin" / "forza-painter-geometrize-go.exe",
    ]
    record["geometrize_bundled"] = any(p.is_file() for p in bin_candidates)

    return record


def load_smoke(exe: Path) -> dict[str, Any] | None:
    # Smoke writes next to EXE ROOT (parent for onedir folder)
    roots = [exe.parent, exe.parent.parent]
    for root in roots:
        smoke = root / "runtime" / "logs" / "matrix-smoke.json"
        if smoke.is_file():
            try:
                return json.loads(smoke.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {"error": "invalid smoke json", "path": str(smoke)}
    return None


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    matrix_root = root / "dist" / "defender-matrix"
    manifest_path = matrix_root / "build_manifest.json"
    if not manifest_path.is_file():
        print(f"Missing manifest: {manifest_path}", file=sys.stderr)
        print("Run scripts/build_defender_matrix.ps1 first.", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    results: list[dict[str, Any]] = []
    for entry in manifest.get("variants", []):
        variant_id = entry["id"]
        variant_dir = matrix_root / variant_id
        record = analyze_variant(variant_dir, entry)
        results.append(record)

    out_json = matrix_root / "analysis_results.json"
    payload = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "variants": results,
    }
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
