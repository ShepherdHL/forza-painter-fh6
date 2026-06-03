#!/usr/bin/env python3
"""Benchmark geometry JSON parse, shape count, and preview rasterization.

Run from repo root::

    python benchmarks/geometry_preview_benchmark.py

Optional JSON fixture path and repeat count::

    python benchmarks/geometry_preview_benchmark.py path/to/design.json 5
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _make_fixture(tmp: Path, shape_count: int) -> Path:
    shapes = []
    cols = max(1, int(shape_count**0.5))
    for index in range(shape_count):
        x = (index % cols) * 14 + 20
        y = (index // cols) * 14 + 20
        shapes.append(
            {
                "type": 0x100001,
                "data": [x * 1.28, y * 1.28, 12.8, 12.8, 0.0, 0.0, 0],
                "color": [40 + (index * 3) % 200, 80, 120, 255],
            }
        )
    payload = {
        "format": "forza_painter_text_trace_v1",
        "coordinate_model": "forza_painter_text_trace_v1",
        "shapes": shapes,
    }
    path = tmp / f"bench_{shape_count}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _timed(label: str, repeats: int, fn) -> float:
    started = time.perf_counter()
    for _ in range(repeats):
        fn()
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    per_call = elapsed_ms / max(1, repeats)
    print(f"{label:32} {per_call:8.2f} ms/call  ({repeats} repeats, {elapsed_ms:.1f} ms total)")
    return per_call


def run_benchmark(json_path: Path, repeats: int = 3) -> dict[str, float]:
    from preview.geometry_preview_cache import (
        clear_geometry_preview_caches,
        drawable_shape_count_cached,
        read_json_cached,
        render_geometry_preview_png,
    )

    bounds = (520, 520)
    results: dict[str, float] = {}

    clear_geometry_preview_caches()
    results["parse_cold"] = _timed(
        "parse (cold cache)",
        repeats,
        lambda: read_json_cached(json_path),
    )
    results["parse_warm"] = _timed(
        "parse (warm cache)",
        repeats,
        lambda: read_json_cached(json_path),
    )

    clear_geometry_preview_caches()
    results["count_cold"] = _timed(
        "shape count (cold)",
        repeats,
        lambda: drawable_shape_count_cached(json_path),
    )
    results["count_warm"] = _timed(
        "shape count (warm)",
        repeats,
        lambda: drawable_shape_count_cached(json_path),
    )

    clear_geometry_preview_caches()
    results["preview_cold"] = _timed(
        "preview PNG (cold)",
        1,
        lambda: render_geometry_preview_png(json_path, bounds),
    )
    results["preview_warm"] = _timed(
        "preview PNG (warm)",
        repeats,
        lambda: render_geometry_preview_png(json_path, bounds),
    )

    clear_geometry_preview_caches()
    results["count_scan_x3"] = _timed(
        "shape count scan x3",
        repeats,
        lambda: [drawable_shape_count_cached(json_path) for _ in range(3)],
    )

    shape_total = drawable_shape_count_cached(json_path)
    print(f"{'shapes in fixture':32} {shape_total:8d}")
    return results


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    repeats = 3
    if argv and argv[-1].isdigit():
        repeats = max(1, int(argv.pop()))
    if argv:
        json_path = Path(argv[0])
        if not json_path.is_file():
            print(f"Fixture not found: {json_path}", file=sys.stderr)
            return 1
    else:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            json_path = _make_fixture(Path(tmp), shape_count=200)
            print(f"Using synthetic fixture ({json_path.name})")
            run_benchmark(json_path, repeats=repeats)
        return 0

    print(f"Using fixture: {json_path}")
    run_benchmark(json_path, repeats=repeats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
