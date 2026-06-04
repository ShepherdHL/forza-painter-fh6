"""Raster preview for legacy Geometrize JSON — alpha compositing, FH6 ellipse calibration."""

from __future__ import annotations

import json
import math
from geometry_json import (
    ELLIPSE,
    ROTATED_ELLIPSE,
    ROTATED_RECTANGLE,
    ShapeType,
    load_normalized_geometry,
)
from utils import load_pillow

PREVIEW_JSON_SUPERSAMPLE = 2
CHECKER_DARK = (38, 38, 38)
CHECKER_LIGHT = (58, 58, 58)


def compensated_ellipse_size(width: float, height: float) -> tuple[float, float]:
    """Shrink large / high-aspect ellipses so preview matches FH6 footprint better."""
    w = float(width)
    h = float(height)
    major = max(w, h)
    minor = min(w, h)
    aspect = major / minor if minor > 1e-6 else 1.0
    shrink = 1.0
    if major >= 300:
        shrink *= 0.985
    elif major >= 220:
        shrink *= 0.99
    if aspect >= 6.0:
        shrink *= 0.96
    elif aspect >= 3.5:
        shrink *= 0.97
    elif aspect >= 2.0:
        shrink *= 0.98
    return w * shrink, h * shrink


def _preview_scale(image_w: int, image_h: int, max_size) -> float:
    if max_size is None:
        from app_config import PREVIEW_MAX

        max_w = max_h = PREVIEW_MAX
    elif isinstance(max_size, (tuple, list)):
        if len(max_size) >= 2:
            max_w, max_h = int(max_size[0]), int(max_size[1])
        elif len(max_size) == 1:
            max_w = max_h = int(max_size[0])
        else:
            from app_config import PREVIEW_MAX

            max_w = max_h = PREVIEW_MAX
    else:
        max_w = max_h = int(max_size)
    max_w = max(1, max_w)
    max_h = max(1, max_h)
    if image_w <= 0 or image_h <= 0:
        return 1.0
    return min(max_w / image_w, max_h / image_h, 1.0)


def _make_checkerboard(height: int, width: int, tile: int) -> "object":
    import numpy as np

    tile = max(1, int(tile))
    y = np.arange(height, dtype=np.int32)
    x = np.arange(width, dtype=np.int32)
    checker = ((x // tile) + (y[:, None] // tile)) % 2 == 0
    board = np.where(checker[..., None], CHECKER_LIGHT, CHECKER_DARK).astype(np.uint8)
    return board


def _composite_over(
    canvas_rgb: "object",
    canvas_a: "object",
    mask: "object",
    color_rgb: tuple[int, int, int],
    color_alpha: int,
) -> None:
    import numpy as np

    if color_alpha <= 0 or mask.size == 0:
        return
    layer_a = (mask.astype(np.float32) / 255.0) * (float(color_alpha) / 255.0)
    if not np.any(layer_a > 1e-6):
        return
    src = np.array(color_rgb, dtype=np.float32)
    da = canvas_a.astype(np.float32) / 255.0
    out_a = layer_a + da * (1.0 - layer_a)
    for channel in range(3):
        canvas_rgb[:, :, channel] = (
            src[channel] * layer_a + canvas_rgb[:, :, channel] * da * (1.0 - layer_a)
        )
    canvas_a[:] = np.clip(out_a * 255.0, 0, 255).astype(np.uint8)


def _rasterize_ellipse_mask(
    height: int,
    width: int,
    cx: float,
    cy: float,
    ellipse_w: float,
    ellipse_h: float,
    rot_deg: float,
    *,
    compensate: bool = True,
) -> tuple[slice, slice, "object"]:
    import numpy as np

    if compensate:
        ellipse_w, ellipse_h = compensated_ellipse_size(ellipse_w, ellipse_h)
    rx = max(float(ellipse_h), 1.0)
    ry = max(float(ellipse_w), 1.0)
    theta = (-90.0 + float(rot_deg)) * (math.pi / 180.0)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    inv_rx2 = 1.0 / (rx * rx)
    inv_ry2 = 1.0 / (ry * ry)
    extent_x = math.sqrt(rx * rx * cos_t * cos_t + ry * ry * sin_t * sin_t)
    extent_y = math.sqrt(rx * rx * sin_t * sin_t + ry * ry * cos_t * cos_t)
    x_min = max(0, int(math.floor(cx - extent_x - 1)))
    x_max = min(width - 1, int(math.ceil(cx + extent_x + 1)))
    y_min = max(0, int(math.floor(cy - extent_y - 1)))
    y_max = min(height - 1, int(math.ceil(cy + extent_y + 1)))
    if x_min > x_max or y_min > y_max:
        empty = np.zeros((0, 0), dtype=np.uint8)
        return slice(0, 0), slice(0, 0), empty
    yy = np.arange(y_min, y_max + 1, dtype=np.float64) + 0.5
    xx = np.arange(x_min, x_max + 1, dtype=np.float64) + 0.5
    grid_y, grid_x = np.meshgrid(yy, xx, indexing="ij")
    dy = grid_y - cy
    dx = grid_x - cx
    xr = dx * cos_t + dy * sin_t
    yr = -dx * sin_t + dy * cos_t
    inside = (xr * xr * inv_rx2 + yr * yr * inv_ry2) <= 1.0
    mask = (inside * 255).astype(np.uint8)
    return slice(y_min, y_max + 1), slice(x_min, x_max + 1), mask


def _point_in_polygon(px: float, py: float, polygon: list[tuple[float, float]]) -> bool:
    inside = False
    count = len(polygon)
    if count < 3:
        return False
    j = count - 1
    for i in range(count):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i
    return inside


def _rasterize_polygon_mask(
    height: int,
    width: int,
    points: list[tuple[float, float]],
) -> tuple[slice, slice, "object"]:
    import numpy as np

    if len(points) < 3:
        empty = np.zeros((0, 0), dtype=np.uint8)
        return slice(0, 0), slice(0, 0), empty
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_min = max(0, int(math.floor(min(xs))))
    x_max = min(width - 1, int(math.ceil(max(xs))))
    y_min = max(0, int(math.floor(min(ys))))
    y_max = min(height - 1, int(math.ceil(max(ys))))
    if x_min > x_max or y_min > y_max:
        empty = np.zeros((0, 0), dtype=np.uint8)
        return slice(0, 0), slice(0, 0), empty

    from utils import load_cv2

    loaded = load_cv2()
    if loaded:
        cv2, _np = loaded
        contour = np.array(points, dtype=np.float32).reshape(-1, 1, 2)
        mask_full = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask_full, [np.round(contour).astype(np.int32)], 255)
        region = mask_full[y_min : y_max + 1, x_min : x_max + 1]
        return slice(y_min, y_max + 1), slice(x_min, x_max + 1), region

    mask = np.zeros((y_max - y_min + 1, x_max - x_min + 1), dtype=np.uint8)
    for yy in range(y_min, y_max + 1):
        py = float(yy) + 0.5
        row = yy - y_min
        for xx in range(x_min, x_max + 1):
            px = float(xx) + 0.5
            if _point_in_polygon(px, py, points):
                mask[row, xx - x_min] = 255
    return slice(y_min, y_max + 1), slice(x_min, x_max + 1), mask


def _rasterize_ring_mask(
    height: int,
    width: int,
    cx: float,
    cy: float,
    ellipse_w: float,
    ellipse_h: float,
    rot_deg: float,
    *,
    inner_scale: float = 0.72,
    compensate: bool = True,
) -> tuple[slice, slice, "object"]:
    import numpy as np

    if compensate:
        ellipse_w, ellipse_h = compensated_ellipse_size(ellipse_w, ellipse_h)
    rx_outer = max(float(ellipse_h), 1.0)
    ry_outer = max(float(ellipse_w), 1.0)
    rx_inner = rx_outer * inner_scale
    ry_inner = ry_outer * inner_scale
    theta = (-90.0 + float(rot_deg)) * (math.pi / 180.0)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    inv_rx2_o = 1.0 / (rx_outer * rx_outer)
    inv_ry2_o = 1.0 / (ry_outer * ry_outer)
    inv_rx2_i = 1.0 / (rx_inner * rx_inner)
    inv_ry2_i = 1.0 / (ry_inner * ry_inner)
    extent_x = math.sqrt(
        rx_outer * rx_outer * cos_t * cos_t + ry_outer * ry_outer * sin_t * sin_t
    )
    extent_y = math.sqrt(
        rx_outer * rx_outer * sin_t * sin_t + ry_outer * ry_outer * cos_t * cos_t
    )
    x_min = max(0, int(math.floor(cx - extent_x - 1)))
    x_max = min(width - 1, int(math.ceil(cx + extent_x + 1)))
    y_min = max(0, int(math.floor(cy - extent_y - 1)))
    y_max = min(height - 1, int(math.ceil(cy + extent_y + 1)))
    if x_min > x_max or y_min > y_max:
        empty = np.zeros((0, 0), dtype=np.uint8)
        return slice(0, 0), slice(0, 0), empty
    yy = np.arange(y_min, y_max + 1, dtype=np.float64) + 0.5
    xx = np.arange(x_min, x_max + 1, dtype=np.float64) + 0.5
    grid_y, grid_x = np.meshgrid(yy, xx, indexing="ij")
    dy = grid_y - cy
    dx = grid_x - cx
    xr = dx * cos_t + dy * sin_t
    yr = -dx * sin_t + dy * cos_t
    outer = xr * xr * inv_rx2_o + yr * yr * inv_ry2_o <= 1.0
    inner = xr * xr * inv_rx2_i + yr * yr * inv_ry2_i <= 1.0
    mask = ((outer & ~inner) * 255).astype(np.uint8)
    return slice(y_min, y_max + 1), slice(x_min, x_max + 1), mask


def _rotated_rect_corners(
    cx: float,
    cy: float,
    rect_w: float,
    rect_h: float,
    rot_deg: float,
) -> list[tuple[float, float]]:
    hw = max(float(rect_w), 1.0) / 2.0
    hh = max(float(rect_h), 1.0) / 2.0
    theta = float(rot_deg) * (math.pi / 180.0)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    points = []
    for dx, dy in corners:
        px = cx + dx * cos_t - dy * sin_t
        py = cy + dx * sin_t + dy * cos_t
        points.append((px, py))
    return points


def _rasterize_rotated_rect_mask(
    height: int,
    width: int,
    cx: float,
    cy: float,
    rect_w: float,
    rect_h: float,
    rot_deg: float,
) -> tuple[slice, slice, "object"]:
    return _rasterize_polygon_mask(
        height,
        width,
        _rotated_rect_corners(cx, cy, rect_w, rect_h, rot_deg),
    )


def _rasterize_rect_mask(
    height: int,
    width: int,
    cx: float,
    cy: float,
    rect_w: float,
    rect_h: float,
) -> tuple[slice, slice, "object"]:
    import numpy as np

    x0 = int(math.floor(cx - rect_w / 2.0))
    x1 = int(math.ceil(cx + rect_w / 2.0))
    y0 = int(math.floor(cy - rect_h / 2.0))
    y1 = int(math.ceil(cy + rect_h / 2.0))
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(width, x1)
    y1 = min(height, y1)
    if x0 >= x1 or y0 >= y1:
        empty = np.zeros((0, 0), dtype=np.uint8)
        return slice(0, 0), slice(0, 0), empty
    region = np.full((y1 - y0, x1 - x0), 255, dtype=np.uint8)
    return slice(y0, y1), slice(x0, x1), region


def render_legacy_geometry_rgba(
    shapes: list,
    image_w: int,
    image_h: int,
    render_scale: float,
) -> tuple["object", "object"] | None:
    """Return (rgb uint8 HxWx3, alpha uint8 HxW) at render_scale."""
    try:
        import numpy as np
    except ImportError:
        return None

    rw = max(1, int(round(image_w * render_scale)))
    rh = max(1, int(round(image_h * render_scale)))
    canvas_rgb = np.zeros((rh, rw, 3), dtype=np.float32)
    canvas_a = np.zeros((rh, rw), dtype=np.uint8)

    bg = shapes[0]
    bg_r, bg_g, bg_b, bg_a = [int(v) for v in bg.get("color", [0, 0, 0, 0])[:4]]
    if len(bg.get("color", [])) == 3:
        bg_a = 255
    if bg_a > 0:
        canvas_rgb[:, :, 0] = bg_r
        canvas_rgb[:, :, 1] = bg_g
        canvas_rgb[:, :, 2] = bg_b
        canvas_a[:, :] = bg_a

    for shape in shapes[1:]:
        color = [int(v) for v in shape.get("color", [])]
        if len(color) == 3:
            color.append(255)
        if len(color) < 4 or color[3] <= 0:
            continue
        r, g, b, a = color[0], color[1], color[2], color[3]
        shape_type = int(shape.get("type", 0))
        data = shape.get("data", [])
        mask = None
        ys = xs = slice(0, 0)
        if shape_type == int(ShapeType.RECTANGLE) and len(data) >= 4:
            x, y, w, h = [float(v) for v in data[:4]]
            cx = x * render_scale
            cy = y * render_scale
            ys, xs, mask = _rasterize_rect_mask(
                rh, rw, cx, cy, w * render_scale, h * render_scale
            )
        elif shape_type == int(ROTATED_RECTANGLE) and len(data) >= 5:
            x, y, w, h, rot_deg = [float(v) for v in data[:5]]
            cx = x * render_scale
            cy = y * render_scale
            ys, xs, mask = _rasterize_rotated_rect_mask(
                rh, rw, cx, cy, w * render_scale, h * render_scale, rot_deg
            )
        elif shape_type == int(ELLIPSE) and len(data) >= 4:
            x, y, w, h = [float(v) for v in data[:4]]
            rot_deg = float(data[4]) if len(data) >= 5 else 0.0
            cx = x * render_scale
            cy = y * render_scale
            ys, xs, mask = _rasterize_ellipse_mask(
                rh,
                rw,
                cx,
                cy,
                w * render_scale,
                h * render_scale,
                rot_deg,
                compensate=True,
            )
        elif shape_type == int(ROTATED_ELLIPSE) and len(data) >= 5:
            x, y, w, h, rot_deg = [float(v) for v in data[:5]]
            cx = x * render_scale
            cy = y * render_scale
            ys, xs, mask = _rasterize_ellipse_mask(
                rh,
                rw,
                cx,
                cy,
                w * render_scale,
                h * render_scale,
                rot_deg,
                compensate=True,
            )
        else:
            continue
        if mask is None or mask.size == 0:
            continue
        _composite_over(
            canvas_rgb[ys, xs, :],
            canvas_a[ys, xs],
            mask,
            (r, g, b),
            a,
        )

    rgb = np.clip(canvas_rgb, 0, 255).astype(np.uint8)
    return rgb, canvas_a


def flatten_rgba_on_checkerboard(
    rgb: "object",
    alpha: "object",
    *,
    tile: int = 32,
) -> "object":
    import numpy as np

    h, w = alpha.shape[:2]
    checker = _make_checkerboard(h, w, max(8, tile))
    a = alpha.astype(np.float32) / 255.0
    out = (
        rgb.astype(np.float32) * a[:, :, None]
        + checker.astype(np.float32) * (1.0 - a[:, :, None])
    )
    return np.clip(out, 0, 255).astype(np.uint8)


def render_legacy_geometry_preview(path, max_size=None):
    """Render normalized legacy JSON to a PIL RGB image, or None if unavailable."""
    loaded = load_pillow()
    if not loaded:
        return None
    Image, _ImageDraw = loaded
    try:
        data = load_normalized_geometry(path)
        shapes = data["shapes"]
        image_w, image_h = [int(v) for v in shapes[0]["data"][2:]]
        display_scale = _preview_scale(image_w, image_h, max_size)
        render_scale = display_scale * PREVIEW_JSON_SUPERSAMPLE
        rendered = render_legacy_geometry_rgba(shapes, image_w, image_h, render_scale)
        if rendered is None:
            return None
        rgb, alpha = rendered
        tile = max(8, int(round(32 * render_scale)))
        flat = flatten_rgba_on_checkerboard(rgb, alpha, tile=tile)
        if PREVIEW_JSON_SUPERSAMPLE > 1:
            preview_w = max(1, int(round(image_w * display_scale)))
            preview_h = max(1, int(round(image_h * display_scale)))
            image = Image.fromarray(flat, mode="RGB")
            image = image.resize((preview_w, preview_h), Image.Resampling.LANCZOS)
            return image
        return Image.fromarray(flat, mode="RGB")
    except Exception:
        return None


SCALED_TRACE_COORDINATE_MODELS = frozenset(
    {
        "endarz_pixel_grid_v1",
        "forza_painter_text_trace_v1",
        "forza_painter_text_stroke_v1",
    }
)

FORZA_FONT_COORDINATE_MODEL = "forza_painter_forza_font_v1"


def _forza_font_shape_pixels(item: dict) -> tuple[float, float, float, float, float]:
    """Decode Forza in-game font type-code entries to layout pixel center and size."""
    from pixel_art_geometry import POSITION_SCALE, SIZE_SCALE
    from text_forza_fonts import FORZA_GLYPH_SCALE

    cx = float(item["x"])
    cy = float(item["y"])
    sx = float(item["sx"])
    sy = float(item["sy"])
    rot = float(item.get("rotation", 0.0))
    glyph_scale = SIZE_SCALE * FORZA_GLYPH_SCALE
    px = cx / POSITION_SCALE
    py = cy / POSITION_SCALE
    width = max(1.0, sx / glyph_scale)
    height = max(1.0, sy / glyph_scale)
    return px, py, width, height, rot


def _typecode_bounds(
    shapes: list,
    *,
    coordinate_model: str | None = None,
) -> tuple[float, float, float, float]:
    model = str(coordinate_model or "").lower()
    if model == FORZA_FONT_COORDINATE_MODEL:
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for item in shapes:
            px, py, pw, ph, _rot = _forza_font_shape_pixels(item)
            min_x = min(min_x, px - pw / 2.0)
            max_x = max(max_x, px + pw / 2.0)
            min_y = min(min_y, py - ph / 2.0)
            max_y = max(max_y, py + ph / 2.0)
        if min_x == float("inf"):
            return 0.0, 0.0, 1.0, 1.0
        return min_x, min_y, max_x, max_y
    if model in SCALED_TRACE_COORDINATE_MODELS:
        return _scaled_trace_bounds(shapes)
    xs = [float(item["x"]) for item in shapes]
    ys = [float(item["y"]) for item in shapes]
    half_x = [max(1.0, float(item["sx"])) / 2.0 for item in shapes]
    half_y = [max(1.0, float(item["sy"])) / 2.0 for item in shapes]
    min_x = min(x - hx for x, hx in zip(xs, half_x))
    max_x = max(x + hx for x, hx in zip(xs, half_x))
    min_y = min(y - hy for y, hy in zip(ys, half_y))
    max_y = max(y + hy for y, hy in zip(ys, half_y))
    return min_x, min_y, max_x, max_y


def _typecode_uses_scaled_trace_coordinates(path) -> bool:
    from pathlib import Path

    try:
        from preview.geometry_preview_cache import read_json_cached

        payload = read_json_cached(path)
    except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    model = str(payload.get("coordinate_model", "")).lower()
    if model == FORZA_FONT_COORDINATE_MODEL:
        return False
    return model in SCALED_TRACE_COORDINATE_MODELS


def _scaled_trace_shape_pixels(item: dict) -> tuple[float, float, float, float, float]:
    """Decode text-vinyl / pixel-art type-code entries to pixel-space center and size."""
    from pixel_art_geometry import POSITION_SCALE, SIZE_SCALE

    cx = float(item["x"])
    cy = float(item["y"])
    sx = float(item["sx"])
    sy = float(item["sy"])
    rot = float(item.get("rotation", 0.0))
    width = max(1.0, sx / SIZE_SCALE)
    height = max(1.0, sy / SIZE_SCALE)
    px = cx / POSITION_SCALE
    py = cy / POSITION_SCALE
    return px, py, width, height, rot


def _scaled_trace_bounds(shapes: list) -> tuple[float, float, float, float]:
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for item in shapes:
        px, py, pw, ph, _rot = _scaled_trace_shape_pixels(item)
        min_x = min(min_x, px - pw / 2.0)
        max_x = max(max_x, px + pw / 2.0)
        min_y = min(min_y, py - ph / 2.0)
        max_y = max(max_y, py + ph / 2.0)
    if min_x == float("inf"):
        return 0.0, 0.0, 1.0, 1.0
    return min_x, min_y, max_x, max_y


def _composite_shape_on_canvas(
    canvas_rgb: "object",
    canvas_a: "object",
    mask: "object",
    y_slice: slice,
    x_slice: slice,
    color_rgb: tuple[int, int, int],
    color_alpha: int,
) -> None:
    if mask is None or mask.size == 0 or color_alpha <= 0:
        return
    _composite_over(
        canvas_rgb[y_slice, x_slice, :],
        canvas_a[y_slice, x_slice],
        mask,
        color_rgb,
        color_alpha,
    )


def render_typecode_geometry_rgba(
    shapes: list,
    canvas_w: int,
    canvas_h: int,
    *,
    min_x: float,
    min_y: float,
    pad: float,
    render_scale: float,
    scaled_trace: bool,
    coordinate_model: str | None = None,
) -> tuple["object", "object"] | None:
    """Rasterize FH6 type-code shapes onto a fixed canvas with alpha compositing."""
    try:
        import numpy as np
    except ImportError:
        return None

    from fh6_shape_catalog import preview_style_for_type_code

    rw = max(1, int(round(canvas_w * render_scale)))
    rh = max(1, int(round(canvas_h * render_scale)))
    canvas_rgb = np.zeros((rh, rw, 3), dtype=np.float32)
    canvas_a = np.zeros((rh, rw), dtype=np.uint8)

    for item in shapes:
        color_vals = [int(v) for v in item.get("color", (255, 255, 255, 255))]
        if len(color_vals) == 3:
            color_vals.append(255)
        if len(color_vals) < 4 or color_vals[3] <= 0:
            continue
        r, g, b, a = color_vals[0], color_vals[1], color_vals[2], color_vals[3]
        code = int(item.get("type_code", 0))
        rot = float(item.get("rotation", 0.0))
        if coordinate_model == FORZA_FONT_COORDINATE_MODEL:
            px, py, pw, ph, rot = _forza_font_shape_pixels(item)
            cx = (px - min_x + pad) * render_scale
            cy = (py - min_y + pad) * render_scale
            sx_screen = pw * render_scale
            sy_screen = ph * render_scale
        elif scaled_trace:
            px, py, pw, ph, rot = _scaled_trace_shape_pixels(item)
            cx = (px - min_x + pad) * render_scale
            cy = (py - min_y + pad) * render_scale
            sx_screen = pw * render_scale
            sy_screen = ph * render_scale
        else:
            sx_screen = max(1.0, float(item["sx"])) * render_scale
            sy_screen = max(1.0, float(item["sy"])) * render_scale
            cx = (float(item["x"]) - min_x + pad) * render_scale
            cy = (float(item["y"]) - min_y + pad) * render_scale
        style = preview_style_for_type_code(code)
        mask = None
        ys = xs = slice(0, 0)

        if style in ("circle", "ellipse"):
            ys, xs, mask = _rasterize_ellipse_mask(
                rh, rw, cx, cy, sx_screen, sy_screen, rot, compensate=True
            )
        elif style == "square":
            use_layout_rect = scaled_trace or coordinate_model == FORZA_FONT_COORDINATE_MODEL
            if use_layout_rect and abs(rot) < 1e-6:
                ys, xs, mask = _rasterize_rect_mask(
                    rh, rw, cx, cy, sx_screen, sy_screen
                )
            else:
                side = min(sx_screen, sy_screen)
                if abs(rot) < 1e-6:
                    ys, xs, mask = _rasterize_rect_mask(rh, rw, cx, cy, side, side)
                else:
                    ys, xs, mask = _rasterize_rotated_rect_mask(
                        rh, rw, cx, cy, side, side, rot
                    )
        elif style == "triangle":
            pts = [
                (cx, cy - sy_screen / 2.0),
                (cx + sx_screen / 2.0, cy + sy_screen / 2.0),
                (cx - sx_screen / 2.0, cy + sy_screen / 2.0),
            ]
            theta = rot * (math.pi / 180.0)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            rotated = []
            for px, py in pts:
                dx = px - cx
                dy = py - cy
                rotated.append((cx + dx * cos_t - dy * sin_t, cy + dx * sin_t + dy * cos_t))
            ys, xs, mask = _rasterize_polygon_mask(rh, rw, rotated)
        elif style == "ring":
            ys, xs, mask = _rasterize_ring_mask(
                rh, rw, cx, cy, sx_screen, sy_screen, rot, compensate=True
            )
        else:
            ys, xs, mask = _rasterize_rotated_rect_mask(
                rh, rw, cx, cy, sx_screen, sy_screen, rot
            )

        _composite_shape_on_canvas(canvas_rgb, canvas_a, mask, ys, xs, (r, g, b), a)

    rgb = np.clip(canvas_rgb, 0, 255).astype(np.uint8)
    return rgb, canvas_a


def render_typecode_geometry_preview(path, max_size=None, *, skipped_badge: bool = True):
    """Render type-code JSON with alpha compositing; returns PIL Image or None."""
    from fh6_typecode_json import load_typecode_shapes

    loaded = load_pillow()
    if not loaded:
        return None
    Image, ImageDraw = loaded
    try:
        shapes, skipped = load_typecode_shapes(path, allow_unknown_low_byte=True)
        if not shapes:
            return None
        scaled_trace = _typecode_uses_scaled_trace_coordinates(path)
        coordinate_model = None
        try:
            from preview.geometry_preview_cache import read_json_cached

            payload = read_json_cached(path)
            if isinstance(payload, dict):
                coordinate_model = str(payload.get("coordinate_model", "")).lower() or None
        except (OSError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
            coordinate_model = None
        if scaled_trace or coordinate_model == FORZA_FONT_COORDINATE_MODEL:
            trace_min_x, trace_min_y, trace_max_x, trace_max_y = _typecode_bounds(
                shapes,
                coordinate_model=coordinate_model,
            )
            min_x = trace_min_x
            min_y = trace_min_y
            max_x = trace_max_x
            max_y = trace_max_y
        else:
            xs = [float(item["x"]) for item in shapes]
            ys = [float(item["y"]) for item in shapes]
            half_x = [max(1.0, float(item["sx"])) / 2.0 for item in shapes]
            half_y = [max(1.0, float(item["sy"])) / 2.0 for item in shapes]
            min_x = min(x - hx for x, hx in zip(xs, half_x))
            max_x = max(x + hx for x, hx in zip(xs, half_x))
            min_y = min(y - hy for y, hy in zip(ys, half_y))
            max_y = max(y + hy for y, hy in zip(ys, half_y))
        pad = 18.0
        width = max(1, int(round((max_x - min_x) + pad * 2.0)))
        height = max(1, int(round((max_y - min_y) + pad * 2.0)))
        display_scale = _preview_scale(width, height, max_size)
        render_scale = display_scale * PREVIEW_JSON_SUPERSAMPLE
        rendered = render_typecode_geometry_rgba(
            shapes,
            width,
            height,
            min_x=min_x,
            min_y=min_y,
            pad=pad,
            render_scale=render_scale,
            scaled_trace=scaled_trace,
            coordinate_model=coordinate_model,
        )
        if rendered is None:
            return None
        rgb, alpha = rendered
        tile = max(8, int(round(24 * render_scale)))
        flat = flatten_rgba_on_checkerboard(rgb, alpha, tile=tile)
        if PREVIEW_JSON_SUPERSAMPLE > 1:
            preview_w = max(1, int(round(width * display_scale)))
            preview_h = max(1, int(round(height * display_scale)))
            image = Image.fromarray(flat, mode="RGB")
            image = image.resize((preview_w, preview_h), Image.Resampling.LANCZOS)
        else:
            image = Image.fromarray(flat, mode="RGB")
        if skipped_badge and skipped:
            draw = ImageDraw.Draw(image)
            badge = f"skipped: {len(skipped)}"
            draw.rectangle((6, 6, 6 + 8 * len(badge), 24), fill=(20, 20, 20))
            draw.text((10, 9), badge, fill=(220, 120, 120))
        return image
    except Exception:
        return None


def draw_preview_ellipse_pillow(
    image,
    x,
    y,
    w,
    h,
    rot_deg,
    color,
    scale,
    *,
    compensate: bool = True,
    alpha: int = 255,
) -> None:
    """Draw ellipse into a PIL RGB image using the FH6-aligned axis convention."""
    if alpha <= 0:
        return
    width, height = image.size
    if compensate:
        w, h = compensated_ellipse_size(w, h)
    cx = float(x) * scale
    cy = float(y) * scale
    rx = max(float(h) * scale, 1.0)
    ry = max(float(w) * scale, 1.0)
    theta = (-90.0 + float(rot_deg)) * (math.pi / 180.0)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    inv_rx2 = 1.0 / (rx * rx)
    inv_ry2 = 1.0 / (ry * ry)
    extent_x = math.sqrt(rx * rx * cos_t * cos_t + ry * ry * sin_t * sin_t)
    extent_y = math.sqrt(rx * rx * sin_t * sin_t + ry * ry * cos_t * cos_t)
    x_min = max(0, int(math.floor(cx - extent_x - 1)))
    x_max = min(width - 1, int(math.ceil(cx + extent_x + 1)))
    y_min = max(0, int(math.floor(cy - extent_y - 1)))
    y_max = min(height - 1, int(math.ceil(cy + extent_y + 1)))
    if x_min > x_max or y_min > y_max:
        return
    pixels = image.load()
    r, g, b = color
    a_frac = float(alpha) / 255.0
    for yy in range(y_min, y_max + 1):
        dy = (float(yy) + 0.5) - cy
        for xx in range(x_min, x_max + 1):
            dx = (float(xx) + 0.5) - cx
            xr = dx * cos_t + dy * sin_t
            yr = -dx * sin_t + dy * cos_t
            if xr * xr * inv_rx2 + yr * yr * inv_ry2 <= 1.0:
                if a_frac >= 0.999:
                    pixels[xx, yy] = (r, g, b)
                else:
                    pr, pg, pb = pixels[xx, yy]
                    pixels[xx, yy] = (
                        int(r * a_frac + pr * (1.0 - a_frac)),
                        int(g * a_frac + pg * (1.0 - a_frac)),
                        int(b * a_frac + pb * (1.0 - a_frac)),
                    )
