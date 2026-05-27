"""
CLI: generate Forza geometry JSON from typed CJK text or a text image.

Examples:
  python text_to_json.py --text "ソニック" --output sonic.json
  python text_to_json.py --image katakana.png --output traced.json --cell-size 3
  python text_to_json.py --image sign.png --ocr --output sign.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from text_geometry import (
    build_geometry_from_text,
    build_geometry_from_text_image,
    contains_cjk,
    estimate_layer_count,
    normalize_text_shape_mode,
    template_hint_for_shape_mode,
    text_shape_mode_choices,
    write_geometry_json,
)
from text_fonts import discover_cjk_fonts, find_cjk_font, format_missing_chars, resolve_font_path, validate_text_coverage
from text_ocr import ocr_available, read_combined_text, try_easyocr_lines


def parse_color(value: str):
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) == 3:
        parts.append(255)
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Color must be R,G,B or R,G,B,A")
    return tuple(parts[:4])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate geometry JSON from CJK / Katakana text.")
    parser.add_argument("--text", help="Unicode text to render (Katakana, Hiragana, Kanji, etc.).")
    parser.add_argument("--image", help="PNG/JPG with text artwork to trace into rectangles.")
    parser.add_argument("--output", required=True, help="Output .json path.")
    parser.add_argument("--font", help="Path to .ttf/.ttc/.otf font, or a discovered font label.")
    parser.add_argument("--list-fonts", action="store_true", help="List discovered CJK fonts and exit.")
    parser.add_argument("--font-size", type=int, default=120, help="Font size for --text mode.")
    parser.add_argument("--cell-size", type=int, default=4, help="Trace grid size (larger = fewer layers).")
    parser.add_argument(
        "--shape-mode",
        choices=text_shape_mode_choices(),
        default="rectangles",
        help=(
            "Primitive used to fill traced cells: rectangles, squares, ellipses, circles, "
            "triangles (diamond ellipses), or mixed."
        ),
    )
    parser.add_argument("--color", type=parse_color, default="255,255,255,255", help="Shape color R,G,B,A.")
    parser.add_argument("--invert", action="store_true", help="Invert --image before tracing (light text on dark).")
    parser.add_argument("--threshold", type=int, default=128, help="Binarization threshold for --image.")
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Run OCR on --image and print detected text (also writes traced geometry from image).",
    )
    parser.add_argument("--ocr-only", action="store_true", help="Only print OCR text, do not write JSON.")
    args = parser.parse_args(argv)

    if args.list_fonts:
        fonts = discover_cjk_fonts()
        if not fonts:
            print("No CJK fonts discovered.")
            return 1
        for font in fonts:
            print(f"{font.label}\n  {font.path}")
        return 0

    if not args.text and not args.image:
        parser.error("Provide --text or --image")
    if args.text and args.image:
        parser.error("Use either --text or --image, not both")

    font_path = resolve_font_path(args.font) if args.font else None
    output = Path(args.output)
    shape_mode = normalize_text_shape_mode(args.shape_mode)
    print("Shape mode:", shape_mode)
    print(template_hint_for_shape_mode(shape_mode))

    if args.image:
        image_path = Path(args.image)
        if args.ocr or args.ocr_only:
            detected = ""
            easy_lines = try_easyocr_lines(image_path)
            if easy_lines is not None:
                detected = "".join(line.text for line in easy_lines)
                print("EasyOCR:", detected or "(empty)")
            elif ocr_available():
                detected = read_combined_text(image_path)
                print("Tesseract:", detected or "(empty)")
            else:
                print(
                    "OCR not available. Install requirements-text-ocr.txt and Tesseract with Japanese.",
                    file=sys.stderr,
                )
            if args.ocr_only:
                return 0 if detected else 1
        payload = build_geometry_from_text_image(
            image_path,
            color=args.color,
            cell_size=args.cell_size,
            invert=args.invert,
            threshold=args.threshold,
            shape_mode=shape_mode,
        )
    else:
        if contains_cjk(args.text):
            print(f"CJK text detected; shape mode: {shape_mode}.")
        resolved = font_path or find_cjk_font()
        print("Font:", resolved)
        ok, missing = validate_text_coverage(args.text, resolved)
        if not ok:
            print(
                f"Warning: font is missing {len(missing)} glyph(s): {format_missing_chars(missing)}",
                file=sys.stderr,
            )
        payload = build_geometry_from_text(
            args.text,
            color=args.color,
            font_path=font_path,
            font_size=args.font_size,
            cell_size=args.cell_size,
            shape_mode=shape_mode,
        )

    write_geometry_json(output, payload)
    layers = estimate_layer_count(payload)
    print(f"Wrote {output} ({layers} drawable shapes, mode={shape_mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
