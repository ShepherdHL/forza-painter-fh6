"""Cached JSON reads and geometry preview PNG bytes (mtime-keyed LRU)."""

from __future__ import annotations

import json
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, TypeVar

from security_policy import MAX_GEOMETRY_JSON_BYTES, validate_geometry_path

_JSON_CACHE_MAX = 64
_RENDER_CACHE_MAX = 48
_COUNT_CACHE_MAX = 128

_JSON_CACHE: OrderedDict[tuple[str, int], Any] = OrderedDict()
_RENDER_CACHE: OrderedDict[tuple[str, int, int, int], bytes] = OrderedDict()
_COUNT_CACHE: OrderedDict[tuple[str, int], int] = OrderedDict()
_CACHE_LOCK = threading.Lock()

T = TypeVar("T")


def _normalize_bounds(max_size) -> tuple[int, int]:
    from app_config import PREVIEW_MAX

    if max_size is None:
        return PREVIEW_MAX, PREVIEW_MAX
    if isinstance(max_size, (tuple, list)):
        if len(max_size) >= 2:
            width, height = int(max_size[0]), int(max_size[1])
        elif len(max_size) == 1:
            width = height = int(max_size[0])
        else:
            width = height = PREVIEW_MAX
    else:
        width = height = int(max_size)
    return max(1, width), max(1, height)


def file_cache_identity(path: Path) -> tuple[str, int] | None:
    path = Path(path)
    try:
        stat = path.stat()
    except OSError:
        return None
    try:
        resolved = str(path.resolve())
    except OSError:
        resolved = str(path)
    return resolved, int(stat.st_mtime_ns)


def read_json_cached(path: Path) -> Any:
    """Read and parse geometry JSON with validation; reuse payload when mtime unchanged."""
    path = Path(path)
    identity = file_cache_identity(path)
    if identity is None:
        raise OSError(f"Cannot read geometry JSON: {path}")
    with _CACHE_LOCK:
        cached = _JSON_CACHE.get(identity)
        if cached is not None:
            _JSON_CACHE.move_to_end(identity)
            return cached
    validate_geometry_path(path)
    raw = path.read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) > MAX_GEOMETRY_JSON_BYTES:
        raise ValueError("Geometry file exceeds size limit")
    payload = json.loads(raw)
    with _CACHE_LOCK:
        _JSON_CACHE[identity] = payload
        _JSON_CACHE.move_to_end(identity)
        while len(_JSON_CACHE) > _JSON_CACHE_MAX:
            _JSON_CACHE.popitem(last=False)
    return payload


def get_cached_geometry_preview_png(path: Path, max_size=None) -> bytes | None:
    """Return cached PNG bytes for a geometry preview, or None if not cached / file missing."""
    path = Path(path)
    identity = file_cache_identity(path)
    if identity is None:
        return None
    bounds = _normalize_bounds(max_size)
    key = (identity[0], identity[1], bounds[0], bounds[1])
    with _CACHE_LOCK:
        cached = _RENDER_CACHE.get(key)
        if cached is not None:
            _RENDER_CACHE.move_to_end(key)
            return cached
    return None


def render_geometry_preview_png(path: Path, max_size=None) -> bytes | None:
    """Rasterize geometry JSON to PNG bytes; results are cached by path, mtime, and bounds."""
    path = Path(path)
    if not path.is_file():
        return None
    identity = file_cache_identity(path)
    if identity is None:
        return None
    bounds = _normalize_bounds(max_size)
    key = (identity[0], identity[1], bounds[0], bounds[1])
    with _CACHE_LOCK:
        cached = _RENDER_CACHE.get(key)
        if cached is not None:
            _RENDER_CACHE.move_to_end(key)
            return cached

    from preview.geometry_render import build_geometry_preview_png

    png = build_geometry_preview_png(path, max_size)
    if png is None:
        return None
    with _CACHE_LOCK:
        _RENDER_CACHE[key] = png
        _RENDER_CACHE.move_to_end(key)
        while len(_RENDER_CACHE) > _RENDER_CACHE_MAX:
            _RENDER_CACHE.popitem(last=False)
    return png


def clear_geometry_preview_caches() -> None:
    """Reset caches (tests)."""
    with _CACHE_LOCK:
        _JSON_CACHE.clear()
        _RENDER_CACHE.clear()
        _COUNT_CACHE.clear()


def cached_drawable_shape_count(path: Path) -> int | None:
    """Return cached drawable shape count when mtime matches, else None."""
    path = Path(path)
    identity = file_cache_identity(path)
    if identity is None:
        return None
    with _CACHE_LOCK:
        if identity in _COUNT_CACHE:
            _COUNT_CACHE.move_to_end(identity)
            return _COUNT_CACHE[identity]
    return None


def store_drawable_shape_count(path: Path, count: int) -> None:
    path = Path(path)
    identity = file_cache_identity(path)
    if identity is None:
        return
    with _CACHE_LOCK:
        _COUNT_CACHE[identity] = int(count)
        _COUNT_CACHE.move_to_end(identity)
        while len(_COUNT_CACHE) > _COUNT_CACHE_MAX:
            _COUNT_CACHE.popitem(last=False)


def drawable_shape_count_cached(path: Path) -> int:
    """Count drawable shapes, reusing JSON parse cache and memoizing the count."""
    path = Path(path)
    cached = cached_drawable_shape_count(path)
    if cached is not None:
        return cached
    from geometry_json import drawable_shape_count

    count = drawable_shape_count(path)
    store_drawable_shape_count(path, count)
    return count


def with_json_payload(path: Path, fn: Callable[[Any], T], *, default: T) -> T:
    """Run ``fn(payload)`` using a cached JSON document when possible."""
    try:
        payload = read_json_cached(path)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return default
    return fn(payload)
