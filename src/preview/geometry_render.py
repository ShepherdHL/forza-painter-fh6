"""Geometry JSON → PIL image / PNG bytes (no Tk dependencies)."""

from __future__ import annotations

import io
from pathlib import Path

from preview.fh6_raster_preview import render_legacy_geometry_preview, render_typecode_geometry_preview


def preview_size_tuple(max_size=None):
    from app_config import PREVIEW_MAX

    if max_size is None:
        return PREVIEW_MAX, PREVIEW_MAX
    if isinstance(max_size, (tuple, list)):
        if len(max_size) >= 2:
            width, height = max_size[0], max_size[1]
        elif len(max_size) == 1:
            width = height = max_size[0]
        else:
            width = height = PREVIEW_MAX
    else:
        width = height = max_size
    try:
        width = int(width)
        height = int(height)
    except (TypeError, ValueError):
        width = height = PREVIEW_MAX
    return max(1, width), max(1, height)


def render_geometry_preview_image(path, max_size=None):
    """Return a PIL RGB image for legacy or type-code geometry JSON."""
    path = Path(path)
    from fh6_typecode_json import is_typecode_geometry_json

    if is_typecode_geometry_json(path):
        return render_typecode_geometry_preview(path, max_size)
    return render_legacy_geometry_preview(path, max_size)


def pil_image_to_png_bytes(image, max_size=None) -> bytes | None:
    from utils import load_pillow

    loaded = load_pillow()
    if not loaded or image is None:
        return None
    Image, _ImageDraw = loaded
    image = image.convert("RGB")
    image.thumbnail(preview_size_tuple(max_size), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_geometry_preview_png(path, max_size=None) -> bytes | None:
    image = render_geometry_preview_image(path, max_size)
    return pil_image_to_png_bytes(image, max_size)
