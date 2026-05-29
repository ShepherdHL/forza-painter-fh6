#!/usr/bin/env python3
"""Write src/_build_profile.json for a matrix variant before PyInstaller runs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--variant-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--src-root", type=Path, required=True)
    args = parser.parse_args()

    catalog = json.loads(args.variants.read_text(encoding="utf-8"))
    variants = {item["id"]: item for item in catalog.get("variants", [])}
    if args.variant_id not in variants:
        print(f"Unknown variant: {args.variant_id}", file=sys.stderr)
        print("Known:", ", ".join(sorted(variants)), file=sys.stderr)
        return 2

    item = variants[args.variant_id]
    runtime_profile = {
        "variant_id": item["id"],
        "label": item.get("label", item["id"]),
        "onefile": bool(item.get("onefile", True)),
        "disable_elevation": bool(item.get("disable_elevation", False)),
        "disable_generator": bool(item.get("disable_generator", False)),
        "disable_networking": bool(item.get("disable_networking", False)),
        "disable_memory_scan": bool(item.get("disable_memory_scan", False)),
    }
    out = args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    # args.out may already contain full variant JSON for PyInstaller; preserve it.
    if out.is_file():
        try:
            full = json.loads(out.read_text(encoding="utf-8"))
            if isinstance(full, dict) and "embed_bin" in full:
                full.update(runtime_profile)
                out.write_text(json.dumps(full, indent=2) + "\n", encoding="utf-8")
            else:
                out.write_text(json.dumps(runtime_profile, indent=2) + "\n", encoding="utf-8")
        except json.JSONDecodeError:
            out.write_text(json.dumps(runtime_profile, indent=2) + "\n", encoding="utf-8")
    else:
        out.write_text(json.dumps(item, indent=2) + "\n", encoding="utf-8")

    src_copy = args.src_root / "_build_profile.json"
    src_copy.write_text(json.dumps(runtime_profile, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out} and {src_copy}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
