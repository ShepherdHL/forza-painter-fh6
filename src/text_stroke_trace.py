"""
Fit text masks with rotated rectangle strokes (few layers, smoother Latin/CJK edges).

Each stroke becomes one FH6 square vinyl layer with independent width, length, and rotation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set, Tuple

from fh6_shape_catalog import get_square_type_code
from pixel_art_geometry import POSITION_SCALE, SIZE_SCALE
from text_geometry import TEXT_TYPECODE_SCORE

ColorRGBA = Tuple[int, int, int, int]
Point = Tuple[int, int]

STROKE_COORDINATE_MODEL = "forza_painter_text_stroke_v1"

# Prefer cardinal/diagonal angles before fine steps (cleaner Latin diagonals).
_PRIORITY_ANGLES = (0.0, 90.0, 45.0, 135.0)


@dataclass(frozen=True)
class StrokeRect:
    """Axis-aligned bar in a rotated frame, stored as center + size + degrees."""

    cx: float
    cy: float
    length: float
    width: float
    rotation_deg: float

    def corners(self) -> List[Tuple[float, float]]:
        hw = self.length / 2.0
        hh = self.width / 2.0
        rad = math.radians(self.rotation_deg)
        cos_t = math.cos(rad)
        sin_t = math.sin(rad)
        points: List[Tuple[float, float]] = []
        for du, dv in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)):
            px = self.cx + du * cos_t - dv * sin_t
            py = self.cy + du * sin_t + dv * cos_t
            points.append((px, py))
        return points

    def covers_pixel(self, x: int, y: int, *, pad: float = 0.35) -> bool:
        rad = math.radians(self.rotation_deg)
        cos_t = math.cos(rad)
        sin_t = math.sin(rad)
        dx = float(x) - self.cx
        dy = float(y) - self.cy
        along = dx * cos_t + dy * sin_t
        perp = -dx * sin_t + dy * cos_t
        half_l = self.length / 2.0 + pad
        half_w = self.width / 2.0 + pad
        return abs(along) <= half_l and abs(perp) <= half_w


def _prepare_mask(mask):
    """Hard-threshold and lightly close gaps from anti-aliased glyph renders."""
    from PIL import Image, ImageFilter

    binary = mask.point(lambda value: 255 if value >= 128 else 0)
    # Close 1px gaps without visibly bloating strokes.
    closed = binary.filter(ImageFilter.MaxFilter(3))
    closed = closed.filter(ImageFilter.MinFilter(3))
    return closed


def _mask_pixels(mask, *, threshold: int = 128) -> Set[Point]:
    width, height = mask.size
    pixels = mask.load()
    out: Set[Point] = set()
    for y in range(height):
        for x in range(width):
            if pixels[x, y] >= threshold:
                out.add((x, y))
    return out


def _connected_components(pixels: Set[Point]) -> List[Set[Point]]:
    remaining = set(pixels)
    components: List[Set[Point]] = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        component: Set[Point] = {seed}
        while stack:
            x, y = stack.pop()
            for nx, ny in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
                (x - 1, y - 1),
                (x + 1, y - 1),
                (x - 1, y + 1),
                (x + 1, y + 1),
            ):
                if (nx, ny) in remaining:
                    remaining.remove((nx, ny))
                    component.add((nx, ny))
                    stack.append((nx, ny))
        components.append(component)
    return components


def _column_has_pixel(pixels: Set[Point], x: int) -> bool:
    return any(px == x for px, _py in pixels)


def _split_component_by_vertical_gaps(
    pixels: Set[Point],
    *,
    min_gap_columns: int = 2,
) -> List[Set[Point]]:
    """Split a word-wide blob into per-letter groups using empty vertical gaps."""
    if len(pixels) < 24:
        return [pixels]
    xs = [p[0] for p in pixels]
    min_x, max_x = min(xs), max(xs)
    if max_x - min_x < 12:
        return [pixels]

    segments: List[tuple[int, int]] = []
    seg_start = min_x
    gap = 0
    for x in range(min_x, max_x + 1):
        if _column_has_pixel(pixels, x):
            if gap >= min_gap_columns and seg_start < x - gap:
                segments.append((seg_start, x - gap))
                seg_start = x
            gap = 0
        else:
            gap += 1
    segments.append((seg_start, max_x + 1))

    if len(segments) <= 1:
        return [pixels]

    groups: List[Set[Point]] = []
    for left, right in segments:
        group = {(px, py) for px, py in pixels if left <= px < right}
        if group:
            groups.append(group)
    return groups if groups else [pixels]


def _text_stroke_components(pixels: Set[Point]) -> List[Set[Point]]:
    out: List[Set[Point]] = []
    for component in _connected_components(pixels):
        out.extend(_split_component_by_vertical_gaps(component))
    return out


def _ink_thickness_from_scans(pixels: Set[Point]) -> float:
    """Estimate stem width from row/column spans (works for L, E, T — not bbox min side)."""
    rows: dict[int, List[int]] = {}
    cols: dict[int, List[int]] = {}
    for x, y in pixels:
        rows.setdefault(y, []).append(x)
        cols.setdefault(x, []).append(y)
    row_spans = [max(xs) - min(xs) + 1 for xs in rows.values() if xs]
    col_spans = [max(ys) - min(ys) + 1 for ys in cols.values() if ys]
    samples = sorted(row_spans + col_spans)
    if not samples:
        return 4.0
    # Lower quartile ignores long crossbars / tall stems in the other axis.
    index = max(0, len(samples) // 4)
    return float(samples[index])


def _estimate_stroke_width(pixels: Set[Point]) -> float:
    if not pixels:
        return 4.0
    xs = [p[0] for p in pixels]
    ys = [p[1] for p in pixels]
    w = max(xs) - min(xs) + 1
    h = max(ys) - min(ys) + 1
    bbox_thin = float(min(w, h))
    ink_thin = _ink_thickness_from_scans(pixels)
    thin = min(bbox_thin, ink_thin * 1.15)
    thick = float(max(w, h))
    if thin <= 2:
        return max(2.0, thin)
    if thick / max(1.0, thin) > 6.0:
        return max(2.0, thin * 0.45)
    return max(2.0, min(thin * 0.36, ink_thin * 0.9))


def _bar_max_width(pixels: Set[Point], stroke_w: float) -> float:
    """Wide enough to score runs on real glyphs; still capped near ink thickness."""
    ink = _ink_thickness_from_scans(pixels)
    return max(stroke_w * 1.2, ink * 0.88)


def _stroke_angles(angle_step: int) -> List[float]:
    step = max(5, min(30, int(angle_step)))
    angles: List[float] = []
    seen: set[float] = set()
    for value in list(_PRIORITY_ANGLES) + [float(deg) for deg in range(0, 180, step)]:
        key = round(value, 3)
        if key in seen:
            continue
        seen.add(key)
        angles.append(value)
    return angles


def _angle_diff(a: float, b: float) -> float:
    delta = abs((a - b) % 180.0)
    return min(delta, 180.0 - delta)


def _stroke_rect_from_uv_bounds(
    u_min: float,
    u_max: float,
    v_min: float,
    v_max: float,
    rotation_deg: float,
) -> StrokeRect:
    rad = math.radians(rotation_deg)
    cos_t = math.cos(rad)
    sin_t = math.sin(rad)
    u_mid = (u_min + u_max) / 2.0
    v_mid = (v_min + v_max) / 2.0
    cx = u_mid * cos_t - v_mid * sin_t
    cy = u_mid * sin_t + v_mid * cos_t
    length = max(1.0, u_max - u_min)
    width = max(1.0, v_max - v_min)
    return StrokeRect(cx=cx, cy=cy, length=length, width=width, rotation_deg=rotation_deg)


def _bar_run_coverage(covered: Set[Point], run_pixels: Sequence[Tuple[float, float, int, int]]) -> float:
    """Fraction of run pixels captured by the bar (not rectangle area efficiency)."""
    if not run_pixels:
        return 0.0
    return len(covered) / len(run_pixels)


def _split_run_along_key(
    run_pixels: Sequence[Tuple[float, float, int, int]],
    *,
    key_index: int,
    max_span: float,
) -> List[List[Tuple[float, float, int, int]]]:
    if len(run_pixels) <= 1:
        return [list(run_pixels)]
    ordered = sorted(run_pixels, key=lambda row: row[key_index])
    span_limit = max(2.0, float(max_span))
    chunks: List[List[Tuple[float, float, int, int]]] = [[ordered[0]]]
    for row in ordered[1:]:
        if row[key_index] - chunks[-1][-1][key_index] > span_limit:
            chunks.append([row])
        else:
            chunks[-1].append(row)
    return [chunk for chunk in chunks if chunk]


def _split_run_along_perp(
    run_pixels: Sequence[Tuple[float, float, int, int]],
    *,
    max_span: float,
) -> List[List[Tuple[float, float, int, int]]]:
    """Break one long UV run into stroke-aligned chunks (e.g. crossbar vs stem on 'A')."""
    if len(run_pixels) <= 1:
        return [list(run_pixels)]
    ordered = sorted(run_pixels, key=lambda row: (row[1], row[0]))
    span_limit = max(2.0, float(max_span))
    chunks: List[List[Tuple[float, float, int, int]]] = [[ordered[0]]]
    for row in ordered[1:]:
        if row[1] - chunks[-1][-1][1] > span_limit:
            chunks.append([row])
        else:
            chunks[-1].append(row)
    return [chunk for chunk in chunks if chunk]


def _split_run_for_bar(
    run_pixels: Sequence[Tuple[float, float, int, int]],
    *,
    max_bar_width: float,
) -> List[List[Tuple[float, float, int, int]]]:
    span = max_bar_width * 1.75
    chunks = _split_run_along_perp(run_pixels, max_span=span)
    if len(chunks) == 1 and len(chunks[0]) > max_bar_width * 28:
        alt = _split_run_along_key(chunks[0], key_index=0, max_span=span)
        if len(alt) > 1:
            chunks = alt
    return chunks


def _mask_image_from_pixels(pixels: Set[Point]):
    from PIL import Image

    xs = [p[0] for p in pixels]
    ys = [p[1] for p in pixels]
    min_x, min_y = min(xs), min(ys)
    width = max(xs) - min_x + 1
    height = max(ys) - min_y + 1
    image = Image.new("L", (width, height), 0)
    load = image.load()
    for x, y in pixels:
        load[x - min_x, y - min_y] = 255
    return image, min_x, min_y


def _fallback_strokes_from_rectangles(pixels: Set[Point], stroke_w: float) -> List[StrokeRect]:
    """Axis-aligned rectangle trace when UV bar runs cannot start (e.g. 'A', 'K')."""
    from text_geometry import decompose_mask_to_rectangles

    if not pixels:
        return []
    image, offset_x, offset_y = _mask_image_from_pixels(pixels)
    rects = decompose_mask_to_rectangles(image, cell_size=1)
    cap_w = max(2.0, stroke_w * 1.05)
    strokes: List[StrokeRect] = []
    for x0, y0, width, height in rects:
        rw = max(1, int(width))
        rh = max(1, int(height))
        cx = offset_x + x0 + rw / 2.0
        cy = offset_y + y0 + rh / 2.0
        if rw >= rh:
            length, bar_w, rotation = float(rw), min(float(rh), cap_w), 0.0
        else:
            length, bar_w, rotation = float(rh), min(float(rw), cap_w), 90.0
        if length < 2.0:
            continue
        strokes.append(
            StrokeRect(cx=cx, cy=cy, length=length, width=max(1.0, bar_w), rotation_deg=rotation)
        )
    return strokes


def _clamp_bar_thickness(
    run_pixels: Sequence[Tuple[float, float, int, int]],
    rotation_deg: float,
    *,
    max_width: float,
) -> tuple[StrokeRect, Set[Point]]:
    u_vals = [row[0] for row in run_pixels]
    v_vals = [row[1] for row in run_pixels]
    u_min = min(u_vals)
    u_max = max(u_vals)
    v_mid = sorted(v_vals)[len(v_vals) // 2]
    half_w = max(0.5, min(max_width / 2.0, (max(v_vals) - min(v_vals)) / 2.0))
    v_min = v_mid - half_w
    v_max = v_mid + half_w
    covered: Set[Point] = set()
    for _u, v, x, y in run_pixels:
        if v_min <= v <= v_max:
            covered.add((x, y))
    rect = _stroke_rect_from_uv_bounds(u_min, u_max, v_min, v_max, rotation_deg)
    return rect, covered


def _find_best_bar_at_angle(
    pixels: Set[Point],
    rotation_deg: float,
    *,
    bin_size: float,
    min_pixels: int,
    max_bar_width: float,
    min_run_coverage: float = 0.62,
    already_covered: Set[Point] | None = None,
) -> tuple[StrokeRect | None, Set[Point]]:
    if len(pixels) < min_pixels:
        return None, set()

    rad = math.radians(rotation_deg)
    cos_t = math.cos(rad)
    sin_t = math.sin(rad)
    uv: List[Tuple[float, float, int, int]] = []
    for x, y in pixels:
        u = float(x) * cos_t + float(y) * sin_t
        v = -float(x) * sin_t + float(y) * cos_t
        uv.append((u, v, x, y))

    u_vals = [row[0] for row in uv]
    u_min_all = min(u_vals)
    bin_w = max(1.0, bin_size)
    bins: dict[int, List[Tuple[float, float, int, int]]] = {}
    for row in uv:
        key = int(math.floor((row[0] - u_min_all) / bin_w))
        bins.setdefault(key, []).append(row)

    ordered_keys = sorted(bins.keys())
    runs: List[List[int]] = []
    current = [ordered_keys[0]]
    for key in ordered_keys[1:]:
        if key == current[-1] + 1:
            current.append(key)
        else:
            runs.append(current)
            current = [key]
    runs.append(current)

    best_rect: StrokeRect | None = None
    best_covered: Set[Point] = set()
    best_score = 0.0
    covered_prior = already_covered or set()

    for run in runs:
        run_pixels: List[Tuple[float, float, int, int]] = []
        for key in run:
            run_pixels.extend(bins[key])
        if len(run_pixels) < min_pixels:
            continue
        for chunk in _split_run_for_bar(run_pixels, max_bar_width=max_bar_width):
            if len(chunk) < min_pixels:
                continue
            rect, covered = _clamp_bar_thickness(
                chunk,
                rotation_deg,
                max_width=max_bar_width,
            )
            if len(covered) < min_pixels:
                continue
            coverage = _bar_run_coverage(covered, chunk)
            large_chunk = len(chunk) > max_bar_width * 28
            if coverage < min_run_coverage:
                if not (large_chunk and len(covered) >= min_pixels and coverage >= 0.2):
                    continue
            overlap = len(covered & covered_prior)
            fresh = len(covered) - overlap
            if fresh < min_pixels:
                continue
            max_len = max(1.0, max_bar_width * 18.0)
            if rect.length > max_len:
                continue
            elongation = rect.length / max(1.0, rect.width)
            score = (
                float(fresh)
                * min(1.0, coverage / min_run_coverage)
                * min(2.0, 0.75 + elongation ** 0.3)
            )
            if score > best_score:
                best_score = score
                best_covered = covered
                best_rect = rect

    return best_rect, best_covered


def _project_to_uv(points: Iterable[Tuple[float, float]], rotation_deg: float) -> List[Tuple[float, float]]:
    rad = math.radians(rotation_deg)
    cos_t = math.cos(rad)
    sin_t = math.sin(rad)
    out: List[Tuple[float, float]] = []
    for x, y in points:
        u = x * cos_t + y * sin_t
        v = -x * sin_t + y * cos_t
        out.append((u, v))
    return out


def _merge_group(group: Sequence[StrokeRect]) -> StrokeRect:
    if len(group) == 1:
        return group[0]
    rotation = group[0].rotation_deg
    corners: List[Tuple[float, float]] = []
    for stroke in group:
        corners.extend(stroke.corners())
    uv = _project_to_uv(corners, rotation)
    u_vals = [row[0] for row in uv]
    v_vals = [row[1] for row in uv]
    return _stroke_rect_from_uv_bounds(
        min(u_vals),
        max(u_vals),
        min(v_vals),
        max(v_vals),
        rotation,
    )


def _strokes_can_merge(a: StrokeRect, b: StrokeRect, stroke_w: float) -> bool:
    if _angle_diff(a.rotation_deg, b.rotation_deg) > 8.0:
        return False
    rotation = (a.rotation_deg + b.rotation_deg) / 2.0
    au = _project_to_uv([(a.cx, a.cy)], rotation)[0][0]
    bu = _project_to_uv([(b.cx, b.cy)], rotation)[0][0]
    av = _project_to_uv([(a.cx, a.cy)], rotation)[0][1]
    bv = _project_to_uv([(b.cx, b.cy)], rotation)[0][1]
    gap_u = abs(au - bu) - (a.length + b.length) / 2.0
    gap_v = abs(av - bv)
    if gap_u > stroke_w * 0.5 or gap_v > stroke_w * 0.85:
        return False
    merged = _merge_group([a, b])
    if merged.length > stroke_w * 22 or merged.width > stroke_w * 2.2:
        return False
    return True


def _merge_strokes(strokes: List[StrokeRect], stroke_w: float) -> List[StrokeRect]:
    """Pairwise merge only — avoids chaining an entire letter into one slab."""
    if len(strokes) <= 1:
        return strokes
    merged: List[StrokeRect] = []
    used = [False] * len(strokes)
    for i, stroke in enumerate(strokes):
        if used[i]:
            continue
        partner: StrokeRect | None = None
        for j in range(i + 1, len(strokes)):
            if used[j]:
                continue
            if _strokes_can_merge(stroke, strokes[j], stroke_w):
                partner = strokes[j]
                used[j] = True
                break
        if partner is not None:
            merged.append(_merge_group([stroke, partner]))
        else:
            merged.append(stroke)
        used[i] = True
    return merged


def _uncovered_pixels(pixels: Set[Point], strokes: Sequence[StrokeRect]) -> Set[Point]:
    return {
        point
        for point in pixels
        if not any(stroke.covers_pixel(point[0], point[1], pad=0.0) for stroke in strokes)
    }


def _pixels_covered_by(strokes: Sequence[StrokeRect], pixels: Set[Point]) -> Set[Point]:
    covered: Set[Point] = set()
    for stroke in strokes:
        for x, y in pixels:
            if stroke.covers_pixel(x, y, pad=0.0):
                covered.add((x, y))
    return covered


def _greedy_pass(
    pixels: Set[Point],
    *,
    angle_step: int,
    min_bar_pixels: int,
    max_strokes: int,
    stroke_w: float,
    global_covered: Set[Point] | None = None,
    min_run_coverage: float = 0.62,
) -> List[StrokeRect]:
    if not pixels:
        return []
    bin_size = max(1.0, min(stroke_w * 0.65, 2.5))
    min_pixels = max(4, min(min_bar_pixels, max(4, len(pixels) // 16)))
    remaining = set(pixels)
    strokes: List[StrokeRect] = []
    angles = _stroke_angles(angle_step)
    max_bar_width = _bar_max_width(pixels, stroke_w)
    covered_prior = set(global_covered or ())

    while remaining and len(strokes) < max_strokes:
        best_rect: StrokeRect | None = None
        best_covered: Set[Point] = set()
        best_fresh = 0
        for angle in angles:
            rect, covered = _find_best_bar_at_angle(
                remaining,
                angle,
                bin_size=bin_size,
                min_pixels=min_pixels,
                max_bar_width=max_bar_width,
                already_covered=covered_prior,
                min_run_coverage=min_run_coverage,
            )
            if rect is None:
                continue
            fresh = len(covered - covered_prior)
            if fresh > best_fresh:
                best_rect = rect
                best_covered = covered
                best_fresh = fresh

        if best_rect is None or best_fresh < min_pixels:
            break

        strokes.append(best_rect)
        remaining -= best_covered
        covered_prior |= best_covered

    return strokes


def _greedy_strokes_for_component(
    pixels: Set[Point],
    *,
    mask,
    angle_step: int = 15,
    min_bar_pixels: int = 10,
    max_strokes: int = 80,
) -> List[StrokeRect]:
    del mask  # reserved for future mask-aware gap fill
    if not pixels:
        return []
    stroke_w = _estimate_stroke_width(pixels)
    ink_span = _ink_thickness_from_scans(pixels)
    per_glyph_budget = max(6, min(max_strokes, int(ink_span * 2.2) + 10))

    strokes = _greedy_pass(
        pixels,
        angle_step=angle_step,
        min_bar_pixels=min_bar_pixels,
        max_strokes=per_glyph_budget,
        stroke_w=stroke_w,
    )
    global_covered = _pixels_covered_by(strokes, pixels)

    uncovered = _uncovered_pixels(pixels, strokes)
    if uncovered and len(strokes) < per_glyph_budget:
        refine = _greedy_pass(
            uncovered,
            angle_step=max(6, angle_step // 2),
            min_bar_pixels=max(3, min_bar_pixels // 2),
            max_strokes=max(8, per_glyph_budget - len(strokes)),
            stroke_w=stroke_w,
            global_covered=global_covered,
        )
        strokes.extend(refine)
        global_covered |= _pixels_covered_by(refine, pixels)

    uncovered = _uncovered_pixels(pixels, strokes)
    if uncovered and len(strokes) < per_glyph_budget:
        tail = _greedy_pass(
            uncovered,
            angle_step=6,
            min_bar_pixels=3,
            max_strokes=max(6, per_glyph_budget - len(strokes)),
            stroke_w=stroke_w,
            global_covered=global_covered,
            min_run_coverage=0.52,
        )
        strokes.extend(tail)
        global_covered |= _pixels_covered_by(tail, pixels)

    uncovered = _uncovered_pixels(pixels, strokes)
    if uncovered and len(strokes) < per_glyph_budget + 6:
        cleanup = _greedy_pass(
            uncovered,
            angle_step=5,
            min_bar_pixels=2,
            max_strokes=10,
            stroke_w=stroke_w,
            global_covered=global_covered,
            min_run_coverage=0.48,
        )
        strokes.extend(cleanup)

    uncovered = _uncovered_pixels(pixels, strokes)
    gap_limit = max(4, min_bar_pixels, int(len(pixels) * 0.08))
    if not strokes or len(uncovered) > gap_limit:
        fallback = _fallback_strokes_from_rectangles(uncovered if strokes else pixels, stroke_w)
        if fallback:
            strokes.extend(fallback)

    return _merge_strokes(strokes, stroke_w)


def fit_stroke_rectangles_from_mask(
    mask,
    *,
    angle_step: int = 15,
    min_bar_pixels: int = 10,
    max_strokes_per_component: int = 80,
) -> List[StrokeRect]:
    prepared = _prepare_mask(mask)
    pixels = _mask_pixels(prepared)
    if not pixels:
        return []
    strokes: List[StrokeRect] = []
    for component in _text_stroke_components(pixels):
        strokes.extend(
            _greedy_strokes_for_component(
                component,
                mask=prepared,
                angle_step=angle_step,
                min_bar_pixels=min_bar_pixels,
                max_strokes=max_strokes_per_component,
            )
        )
    return strokes


def stroke_rect_to_typecode_shape(rect: StrokeRect, color: ColorRGBA) -> dict:
    length = max(1.0, float(rect.length))
    width = max(1.0, float(rect.width))
    cx = float(rect.cx) * POSITION_SCALE
    cy = float(rect.cy) * POSITION_SCALE
    sx = length * SIZE_SCALE
    sy = width * SIZE_SCALE
    rotation = float(rect.rotation_deg) % 180.0
    return {
        "type": get_square_type_code(),
        "data": [cx, cy, sx, sy, rotation, 0.0, 0],
        "color": [int(color[0]), int(color[1]), int(color[2]), int(color[3])],
        "score": TEXT_TYPECODE_SCORE,
    }


def build_stroke_typecode_shapes(
    mask,
    color: ColorRGBA,
    *,
    angle_step: int = 15,
    min_bar_pixels: int = 10,
) -> List[dict]:
    rects = fit_stroke_rectangles_from_mask(
        mask,
        angle_step=angle_step,
        min_bar_pixels=min_bar_pixels,
    )
    if not rects:
        return []
    return [stroke_rect_to_typecode_shape(rect, color) for rect in rects]


def count_stroke_layers_from_mask(
    mask,
    *,
    angle_step: int = 15,
    min_bar_pixels: int = 10,
) -> int:
    return len(
        fit_stroke_rectangles_from_mask(
            mask,
            angle_step=angle_step,
            min_bar_pixels=min_bar_pixels,
        )
    )


def resolve_stroke_params_for_layer_budget(
    mask,
    *,
    max_layers: int,
    angle_steps: Sequence[int] = (15, 22, 30),
    min_bar_candidates: Sequence[int] = (6, 8, 10, 14, 18, 24, 32, 48, 64, 96),
) -> tuple[int, int, int]:
    """Return (angle_step, min_bar_pixels, layer_count) under max_layers when possible."""
    budget = max(1, int(max_layers))
    last = (15, 10, 0)
    for angle_step in angle_steps:
        for min_bar in min_bar_candidates:
            count = count_stroke_layers_from_mask(
                mask,
                angle_step=angle_step,
                min_bar_pixels=min_bar,
            )
            last = (angle_step, min_bar, count)
            if count <= budget:
                return last
    return last
