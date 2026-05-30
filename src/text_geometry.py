"""
Build Forza-compatible geometry JSON from Unicode text or raster text images.

Traces glyph masks into importable primitives (rectangles, squares, ellipses, etc.)
so CJK scripts such as katakana can be used when in-game text does not support them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Sequence, Tuple

from geometry_json import RECTANGLE, ROTATED_ELLIPSE, normalize_geometry_payload
from security_policy import MAX_GEOMETRY_SHAPES, MAX_IMAGE_DIMENSION
from mandarin_chars import is_cjk_char, is_hangul_char
from text_fonts import find_cjk_font, find_font_for_text, format_missing_chars, validate_text_coverage

ColorRGBA = Tuple[int, int, int, int]
Rect = Tuple[int, int, int, int]  # x0, y0, width, height in pixels

SHAPE_MODE_RECTANGLES = "rectangles"
SHAPE_MODE_SQUARES = "squares"
SHAPE_MODE_ELLIPSES = "ellipses"
SHAPE_MODE_CIRCLES = "circles"
SHAPE_MODE_TRIANGLES = "triangles"
SHAPE_MODE_MIXED = "mixed"

TEXT_SHAPE_MODES = (
    SHAPE_MODE_RECTANGLES,
    SHAPE_MODE_SQUARES,
    SHAPE_MODE_ELLIPSES,
    SHAPE_MODE_CIRCLES,
    SHAPE_MODE_TRIANGLES,
    SHAPE_MODE_MIXED,
)

_SHAPE_MODE_ALIASES = {
    "rect": SHAPE_MODE_RECTANGLES,
    "rectangle": SHAPE_MODE_RECTANGLES,
    "rectangles": SHAPE_MODE_RECTANGLES,
    "square": SHAPE_MODE_SQUARES,
    "squares": SHAPE_MODE_SQUARES,
    "ellipse": SHAPE_MODE_ELLIPSES,
    "ellipses": SHAPE_MODE_ELLIPSES,
    "ellipsis": SHAPE_MODE_ELLIPSES,
    "circle": SHAPE_MODE_CIRCLES,
    "circles": SHAPE_MODE_CIRCLES,
    "triangle": SHAPE_MODE_TRIANGLES,
    "triangles": SHAPE_MODE_TRIANGLES,
    "diamond": SHAPE_MODE_TRIANGLES,
    "diamonds": SHAPE_MODE_TRIANGLES,
    "mixed": SHAPE_MODE_MIXED,
    "auto": SHAPE_MODE_MIXED,
}


def normalize_text_shape_mode(value: str | None) -> str:
    if not value:
        return SHAPE_MODE_RECTANGLES
    key = str(value).strip().lower().replace("-", "_")
    return _SHAPE_MODE_ALIASES.get(key, SHAPE_MODE_RECTANGLES)


def text_shape_mode_choices() -> List[str]:
    return list(TEXT_SHAPE_MODES)


def template_hint_for_shape_mode(shape_mode: str) -> str:
    mode = normalize_text_shape_mode(shape_mode)
    if mode in (SHAPE_MODE_ELLIPSES, SHAPE_MODE_CIRCLES, SHAPE_MODE_TRIANGLES, SHAPE_MODE_MIXED):
        return "Use an ungrouped sphere template in FH6 (ellipse / sphere layers)."
    return "Use an ungrouped rectangle template in FH6 when possible (fewer layers)."


def _load_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("Pillow is required for text vinyl generation. Install requirements.txt.") from exc
    return Image, ImageDraw, ImageFont


def render_text_mask(
    text: str,
    font_path: Path | None = None,
    font_size: int = 120,
    padding: int = 24,
    bold: bool = False,
):
    if not text or not text.strip():
        raise ValueError("Text is empty")
    Image, ImageDraw, ImageFont = _load_pillow()
    font_path = Path(font_path) if font_path else find_cjk_font()
    if bold and font_path.suffix.lower() == ".ttc":
        font = None
        for index in (1, 0):
            try:
                font = ImageFont.truetype(str(font_path), font_size, index=index)
                break
            except OSError:
                continue
        if font is None:
            font = ImageFont.truetype(str(font_path), font_size)
    else:
        try:
            font = ImageFont.truetype(str(font_path), font_size)
        except OSError:
            raise FileNotFoundError(f"Cannot load font: {font_path}") from None

    probe = Image.new("L", (4, 4), 0)
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), text, font=font)
    width = max(4, bbox[2] - bbox[0] + padding * 2)
    height = max(4, bbox[3] - bbox[1] + padding * 2)
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ValueError(f"Rendered text exceeds {MAX_IMAGE_DIMENSION}px; reduce font size")

    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    origin = (padding - bbox[0], padding - bbox[1])
    draw.text(origin, text, fill=255, font=font)
    return image


def load_text_image_mask(path: Path, invert: bool = False, threshold: int = 128):
    Image, _, _ = _load_pillow()
    path = Path(path)
    image = Image.open(path).convert("L")
    if invert:
        image = Image.eval(image, lambda value: 255 - value)
    width, height = image.size
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise ValueError(f"Image exceeds {MAX_IMAGE_DIMENSION}px; crop or downscale first")
    pixels = list(image.getdata())
    binary = Image.new("L", image.size, 0)
    binary.putdata([255 if value >= threshold else 0 for value in pixels])
    return binary


def decompose_mask_to_rectangles(mask, cell_size: int = 4) -> List[Rect]:
    """Merge grid cells into larger axis-aligned rectangles."""
    cell_size = max(2, min(16, int(cell_size)))
    width, height = mask.size
    pixels = mask.load()
    threshold = 128
    cols = (width + cell_size - 1) // cell_size
    rows = (height + cell_size - 1) // cell_size
    grid = [[False] * cols for _ in range(rows)]

    for row in range(rows):
        y0 = row * cell_size
        y1 = min(height, y0 + cell_size)
        for col in range(cols):
            x0 = col * cell_size
            x1 = min(width, x0 + cell_size)
            filled = 0
            total = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    total += 1
                    if pixels[x, y] >= threshold:
                        filled += 1
            grid[row][col] = filled > total * 0.45

    visited = [[False] * cols for _ in range(rows)]
    rectangles: List[Rect] = []
    for row in range(rows):
        col = 0
        while col < cols:
            if not grid[row][col] or visited[row][col]:
                col += 1
                continue
            span = 1
            while col + span < cols and grid[row][col + span] and not visited[row][col + span]:
                span += 1
            height_span = 1
            can_grow = True
            while row + height_span < rows and can_grow:
                for dx in range(span):
                    if not grid[row + height_span][col + dx] or visited[row + height_span][col + dx]:
                        can_grow = False
                        break
                if can_grow:
                    height_span += 1
            for dy in range(height_span):
                for dx in range(span):
                    visited[row + dy][col + dx] = True
            x0 = col * cell_size
            y0 = row * cell_size
            rectangles.append(
                (
                    x0,
                    y0,
                    min(width - x0, span * cell_size),
                    min(height - y0, height_span * cell_size),
                )
            )
            col += span
    return rectangles


def _rect_to_primitive_shapes(
    x0: int,
    y0: int,
    width: int,
    height: int,
    color: ColorRGBA,
    shape_mode: str,
) -> List[dict]:
    if width <= 0 or height <= 0:
        return []
    mode = normalize_text_shape_mode(shape_mode)
    cx = int(x0 + width / 2)
    cy = int(y0 + height / 2)
    w = int(width)
    h = int(height)

    if mode == SHAPE_MODE_SQUARES:
        side = max(w, h)
        return [
            {
                "type": RECTANGLE,
                "data": [cx, cy, side, side],
                "color": list(color),
                "score": 0,
            }
        ]

    if mode == SHAPE_MODE_ELLIPSES:
        return [
            {
                "type": ROTATED_ELLIPSE,
                "data": [cx, cy, max(1, w), max(1, h), 0],
                "color": list(color),
                "score": 0,
            }
        ]

    if mode == SHAPE_MODE_CIRCLES:
        diameter = max(1, min(w, h))
        return [
            {
                "type": ROTATED_ELLIPSE,
                "data": [cx, cy, diameter, diameter, 0],
                "color": list(color),
                "score": 0,
            }
        ]

    if mode == SHAPE_MODE_TRIANGLES:
        # FH6 import only supports rectangles and rotated ellipses; diamond ellipses
        # give a sharper, triangle-like look for katakana strokes.
        diameter = max(1, min(w, h))
        if w > h * 1.35:
            rot = 0
            axes = [max(1, w), max(1, h // 2 or 1)]
        elif h > w * 1.35:
            rot = 90
            axes = [max(1, w // 2 or 1), max(1, h)]
        else:
            rot = 45
            axes = [diameter, diameter]
        return [
            {
                "type": ROTATED_ELLIPSE,
                "data": [cx, cy, axes[0], axes[1], rot],
                "color": list(color),
                "score": 0,
            }
        ]

    if mode == SHAPE_MODE_MIXED:
        aspect = max(w, h) / max(1, min(w, h))
        if aspect >= 2.2:
            return [
                {
                    "type": RECTANGLE,
                    "data": [cx, cy, w, h],
                    "color": list(color),
                    "score": 0,
                }
            ]
        diameter = max(1, min(w, h))
        return [
            {
                "type": ROTATED_ELLIPSE,
                "data": [cx, cy, diameter, diameter, 45 if w != h else 0],
                "color": list(color),
                "score": 0,
            }
        ]

    return [
        {
            "type": RECTANGLE,
            "data": [cx, cy, w, h],
            "color": list(color),
            "score": 0,
        }
    ]


def rectangles_to_shapes(
    rectangles: Sequence[Rect],
    image_width: int,
    image_height: int,
    color: ColorRGBA,
    shape_mode: str = SHAPE_MODE_RECTANGLES,
) -> List[dict]:
    shapes = []
    for x0, y0, width, height in rectangles:
        shapes.extend(_rect_to_primitive_shapes(x0, y0, width, height, color, shape_mode))
    if len(shapes) > MAX_GEOMETRY_SHAPES:
        raise ValueError(
            f"Text trace produced {len(shapes)} shapes (limit {MAX_GEOMETRY_SHAPES}). "
            "Increase cell size, choose a simpler shape mode, or reduce font size / resolution."
        )
    background = {
        "type": RECTANGLE,
        "data": [0, 0, int(image_width), int(image_height)],
        "color": [0, 0, 0, 0],
        "score": 0,
    }
    return [background] + shapes


def build_geometry_from_mask(
    mask,
    color: ColorRGBA,
    cell_size: int = 4,
    shape_mode: str = SHAPE_MODE_RECTANGLES,
) -> dict:
    rectangles = decompose_mask_to_rectangles(mask, cell_size=cell_size)
    if not rectangles:
        raise ValueError("No text pixels detected in image mask")
    width, height = mask.size
    payload = {
        "shapes": rectangles_to_shapes(
            rectangles,
            width,
            height,
            color,
            shape_mode=shape_mode,
        )
    }
    return normalize_geometry_payload(payload)


def build_geometry_from_text(
    text: str,
    color: ColorRGBA = (255, 255, 255, 255),
    font_path: Path | None = None,
    font_size: int = 120,
    cell_size: int = 4,
    bold: bool = False,
    strict_glyph_check: bool = True,
    shape_mode: str = SHAPE_MODE_RECTANGLES,
) -> dict:
    resolved_font = Path(font_path) if font_path else find_font_for_text(text)
    if strict_glyph_check:
        ok, missing = validate_text_coverage(text, resolved_font)
        if not ok:
            hint = (
                " For Korean, choose a [KR] font such as Malgun Gothic."
                if any(is_hangul_char(char) for char in text)
                else " Choose a text font that supports every character in your input."
            )
            raise ValueError(
                f"Font {resolved_font.name} is missing {len(missing)} character(s): "
                f"{format_missing_chars(missing)}. Choose another font or install a fuller CJK face.{hint}"
            )
    mask = render_text_mask(text, font_path=resolved_font, font_size=font_size, bold=bold)
    return build_geometry_from_mask(mask, color=color, cell_size=cell_size, shape_mode=shape_mode)


def build_geometry_from_text_image(
    image_path: Path,
    color: ColorRGBA | None = None,
    cell_size: int = 3,
    invert: bool = False,
    threshold: int = 128,
    sample_text_color: bool = True,
    shape_mode: str = SHAPE_MODE_RECTANGLES,
) -> dict:
    mask = load_text_image_mask(image_path, invert=invert, threshold=threshold)
    if color is None and sample_text_color:
        color = _sample_ink_color(image_path, mask, threshold, invert)
    if color is None:
        color = (255, 255, 255, 255)
    return build_geometry_from_mask(mask, color=color, cell_size=cell_size, shape_mode=shape_mode)


def _sample_ink_color(image_path: Path, mask, threshold: int, invert: bool) -> ColorRGBA:
    Image, _, _ = _load_pillow()
    source = Image.open(image_path).convert("RGBA")
    if invert:
        from PIL import ImageOps

        source = ImageOps.invert(source.convert("RGB")).convert("RGBA")
    mask_pixels = mask.load()
    totals = [0, 0, 0]
    count = 0
    width, height = source.size
    for y in range(min(height, mask.size[1])):
        for x in range(min(width, mask.size[0])):
            if mask_pixels[x, y] < threshold:
                continue
            r, g, b, a = source.getpixel((x, y))
            if a < 16:
                continue
            totals[0] += r
            totals[1] += g
            totals[2] += b
            count += 1
    if not count:
        return (255, 255, 255, 255)
    return (
        int(totals[0] / count),
        int(totals[1] / count),
        int(totals[2] / count),
        255,
    )


def write_geometry_json(path: Path, payload: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def contains_cjk(text: str) -> bool:
    return any(is_cjk_char(char) for char in text)


def estimate_layer_count(payload: dict) -> int:
    return max(0, len(payload.get("shapes", [])) - 1)
