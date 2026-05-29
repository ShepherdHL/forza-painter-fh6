#!/usr/bin/env python3
"""Merge matrix artifacts into MATRIX_REPORT.md with evidence-based conclusions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _first_clean_variant(scan: dict) -> str | None:
    for item in scan.get("variants", []):
        if not item.get("detected"):
            return item.get("id")
    return None


def _baseline_detected(scan: dict) -> bool:
    for item in scan.get("variants", []):
        if item.get("id") == "onefile-baseline":
            return bool(item.get("detected"))
    return False


def _attribute_delta(clean_id: str | None, analysis: dict) -> list[str]:
    if not clean_id:
        return ["No clean variant observed — all builds flagged or scan incomplete."]
    clean = next((v for v in analysis.get("variants", []) if v.get("variant_id") == clean_id), None)
    if not clean:
        return [f"Clean variant {clean_id} missing from analysis."]
    lines = [f"First clean build: **{clean_id}**"]
    profile = clean.get("build_profile") or {}
    if profile.get("onefile") is False:
        lines.append("- Onedir layout avoids one-file unpack heuristics.")
    if profile.get("disable_memory_scan"):
        lines.append("- Memory scan/import disabled — strongly implicates OpenProcess/scan/write path.")
    if profile.get("disable_generator"):
        lines.append("- Geometrize helper absent — implicates bundled unsigned child EXE.")
    if profile.get("disable_elevation"):
        lines.append("- No elevation — admin + cross-process combo may be required for detection.")
    if profile.get("disable_networking"):
        lines.append("- Networking disabled — network was not the primary trigger.")
    if not clean.get("geometrize_bundled"):
        lines.append("- No geometrize binary in bundle directory.")
    if not clean.get("upx_section_signature"):
        lines.append("- No UPX section markers in PE.")
    return lines


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    matrix = root / "dist" / "defender-matrix"
    analysis = _load(matrix / "analysis_results.json") or {}
    smoke = _load(matrix / "smoke_results.json") or {}
    scan = _load(matrix / "defender_scan_results.json") or {}

    clean = _first_clean_variant(scan) if scan else None
    baseline_bad = _baseline_detected(scan) if scan else None

    lines = [
        "# Defender matrix report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
    ]

    if scan:
        detected = [v["id"] for v in scan.get("variants", []) if v.get("detected")]
        clean_list = [v["id"] for v in scan.get("variants", []) if not v.get("detected")]
        lines.append(f"- **Defender detections:** {', '.join(detected) if detected else 'none recorded'}")
        lines.append(f"- **Clean builds:** {', '.join(clean_list) if clean_list else 'none recorded'}")
        if clean:
            lines.append(f"- **First clean variant:** `{clean}`")
    else:
        lines.append("- Defender scan results not found. Run `run_defender_scans.ps1` as Administrator.")

    lines.extend(["", "## Evidence-based attribution", ""])
    lines.extend(_attribute_delta(clean, analysis))

    lines.extend(
        [
            "",
            "## Most likely heuristic trigger (ranked)",
            "",
            "1. **PyInstaller onefile extraction** (`_MEI*` under `%TEMP%`) — compare `onefile-baseline` vs `onedir`.",
            "2. **Cross-process memory access** on game process — compare `onefile-no-memory-scan` vs baseline.",
            "3. **Unsigned bundled `forza-painter-geometrize-go.exe`** — compare `onefile-no-geometrize` / `onefile-no-embedded-binaries`.",
            "4. **Administrator + OpenProcess** — compare `onefile-no-elevation` (smoke only) vs elevated import test.",
            "5. **pythonnet / LHM DLL load** — compare `onefile-no-embedded-binaries`.",
            "",
            "## Safest permanent remediation",
            "",
            "1. Ship **onedir** + **Authenticode-signed** release EXE and signed geometrize helper.",
            "2. Keep **import-only elevation**; never auto-elevate at startup.",
            "3. Use `scripts/forza_painter.spec` defaults: `upx=False`, no `--collect-all pythonnet` unless LHM required.",
            "4. Submit signed builds to Microsoft WDSI as false positives with this report.",
            "",
            "## Per-variant metrics",
            "",
            "| Variant | SHA256 (first 16) | Size (MB) | UPX sig | Signed | Defender |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )

    scan_by_id = {v["id"]: v for v in (scan or {}).get("variants", [])}
    for item in analysis.get("variants", []):
        vid = item.get("variant_id", "?")
        sha = (item.get("sha256") or "")[:16]
        size_mb = f"{(item.get('size_bytes') or 0) / (1024 * 1024):.1f}"
        upx = "yes" if item.get("upx_section_signature") else "no"
        sig = item.get("authenticode", "?")
        det = scan_by_id.get(vid, {})
        defender = "DETECTED" if det.get("detected") else ("clean" if det else "not scanned")
        lines.append(f"| `{vid}` | `{sha}…` | {size_mb} | {upx} | {sig} | {defender} |")

    lines.extend(["", "## Startup smoke (`--matrix-smoke`)", ""])
    if smoke:
        for item in smoke.get("variants", []):
            lines.append(f"### `{item.get('id')}`")
            lines.append(f"- Exit code: {item.get('exit_code')}")
            meipass = item.get("temp_meipass") or []
            if meipass:
                lines.append(f"- Temp extract dirs: `{'; '.join(meipass)}`")
            tail = item.get("audit_log_tail") or []
            if tail:
                lines.append("- Audit tail:")
                lines.extend(f"  - {line}" for line in tail[:5])
            lines.append("")
    else:
        lines.append("_No smoke results — run `run_smoke_tests.ps1`._")

    lines.extend(
        [
            "",
            "## Imported DLLs (main EXE, sample)",
            "",
        ]
    )
    for item in analysis.get("variants", [])[:3]:
        dlls = item.get("import_dlls") or []
        lines.append(f"**{item.get('variant_id')}:** {', '.join(dlls[:12])}{'…' if len(dlls) > 12 else ''}")

    out = matrix / "MATRIX_REPORT.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
