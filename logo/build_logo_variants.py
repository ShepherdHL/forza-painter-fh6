#!/usr/bin/env python3
"""Build every logo file from fp-monogram-master.png (uniform output)."""

from __future__ import annotations

from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont
except ImportError as exc:
    raise SystemExit("Install Pillow: pip install Pillow") from exc

ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "fp-monogram-master.png"
PNG_DIR = ROOT / "png"

ORANGE = (255, 106, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    Path(r"C:\Windows\Fonts\arialbi.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _trim_alpha(img: Image.Image) -> Image.Image:
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if not bbox:
        return img
    return img.crop(bbox)


def _fit(master: Image.Image, max_w: int, max_h: int) -> Image.Image:
    w, h = master.size
    scale = min(max_w / w, max_h / h)
    size = (max(1, int(w * scale)), max(1, int(h * scale)))
    return master.resize(size, Image.Resampling.LANCZOS)


def _paste_center(base: Image.Image, mark: Image.Image, cx: int, cy: int) -> None:
    x = cx - mark.width // 2
    y = cy - mark.height // 2
    base.paste(mark, (x, y), mark)


def _rounded_square_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def load_master() -> Image.Image:
    if not MASTER.is_file():
        raise SystemExit(f"Missing master: {MASTER}")
    return _trim_alpha(Image.open(MASTER).convert("RGBA"))


def build_icon(master: Image.Image, size: int = 1024) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (*BLACK, 255))
    mark = _fit(master, int(size * 0.82), int(size * 0.82))
    _paste_center(canvas, mark, size // 2, size // 2)
    return canvas


def build_app_icon(master: Image.Image, size: int = 1024) -> Image.Image:
    icon = build_icon(master, size)
    mask = _rounded_square_mask(size, radius=int(size * 0.22))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(icon, (0, 0), mask)
    return out


def build_vertical_lockup(master: Image.Image) -> Image.Image:
    w, h = 1024, 1280
    canvas = Image.new("RGBA", (w, h), (*BLACK, 255))
    mark = _fit(master, int(w * 0.74), int(h * 0.40))
    _paste_center(canvas, mark, w // 2, int(h * 0.30))

    draw = ImageDraw.Draw(canvas)
    forza = _font(108)
    painter = _font(52)
    forza_text = "FORZA"
    painter_text = "PAINTER"
    fb = draw.textbbox((0, 0), forza_text, font=forza)
    pb = draw.textbbox((0, 0), painter_text, font=painter)
    draw.text(((w - (fb[2] - fb[0])) // 2, 760), forza_text, fill=WHITE, font=forza)
    draw.text(((w - (pb[2] - pb[0])) // 2, 860), painter_text, fill=ORANGE, font=painter)
    return canvas


def build_horizontal_lockup(master: Image.Image) -> Image.Image:
    w, h = 1600, 600
    canvas = Image.new("RGBA", (w, h), (*BLACK, 255))
    mark = _fit(master, int(w * 0.36), int(h * 0.74))
    _paste_center(canvas, mark, int(w * 0.22), h // 2)

    draw = ImageDraw.Draw(canvas)
    forza = _font(96)
    painter = _font(46)
    x = int(w * 0.44)
    draw.text((x, 180), "FORZA", fill=WHITE, font=forza)
    draw.text((x, 300), "PAINTER", fill=ORANGE, font=painter)
    return canvas


def export_sizes(icon: Image.Image) -> None:
    def _tight_crop_non_black(img: Image.Image) -> Image.Image:
        rgb = img.convert("RGB")
        black_bg = Image.new("RGB", rgb.size, (0, 0, 0))
        diff = ImageChops.difference(rgb, black_bg)
        bbox = diff.getbbox()
        if not bbox:
            return img
        return img.crop(bbox)

    def _small_icon_variant(base_icon: Image.Image, size: int) -> Image.Image:
        # Tighten mark footprint so details remain legible at tiny sizes.
        cropped = _tight_crop_non_black(base_icon)
        canvas = Image.new("RGBA", (size, size), (*BLACK, 255))
        target = int(size * (0.94 if size == 16 else 0.96))
        mark = _fit(cropped, target, target)
        _paste_center(canvas, mark, size // 2, size // 2)
        if size == 16:
            # Nudge the tiny mark up by 1px for crisper Windows taskbar alignment.
            shifted = Image.new("RGBA", canvas.size, (*BLACK, 255))
            shifted.paste(canvas, (0, -1), canvas)
            canvas = shifted
            # Slightly thicken strokes at 16px so stems don't disappear on taskbars.
            alpha = canvas.split()[-1]
            alpha = alpha.filter(ImageFilter.MaxFilter(3))
            rgb = canvas.convert("RGB")
            thick = Image.new("RGBA", canvas.size, (*BLACK, 255))
            thick.paste(rgb, (0, 0))
            thick.putalpha(alpha)
            canvas = thick
        # Mild sharpening/contrast boost improves taskbar readability.
        sharpened = canvas.filter(
            ImageFilter.UnsharpMask(radius=0.8 if size == 16 else 0.6, percent=180, threshold=1)
        )
        contrasted = ImageEnhance.Contrast(sharpened).enhance(1.18 if size == 16 else 1.12)
        return contrasted

    PNG_DIR.mkdir(exist_ok=True)
    for size in (16, 32, 48, 64, 128, 256, 512, 1024):
        if size in (16, 32):
            out = _small_icon_variant(icon, size)
        else:
            out = icon.resize((size, size), Image.Resampling.LANCZOS)
        out.save(PNG_DIR / f"icon-{size}.png")
    frames = []
    for size in (256, 128, 64, 48, 32, 16):
        if size in (16, 32):
            frames.append(_small_icon_variant(icon, size))
        else:
            frames.append(icon.resize((size, size), Image.Resampling.LANCZOS))
    frames[0].save(
        ROOT / "forza-painter.ico",
        format="ICO",
        sizes=[(f.width, f.height) for f in frames],
        append_images=frames[1:],
    )


def main() -> None:
    master = load_master()
    icon = build_icon(master)
    app_icon = build_app_icon(master)
    vertical = build_vertical_lockup(master)
    horizontal = build_horizontal_lockup(master)

    icon.save(ROOT / "forza-painter-icon-1024.png")
    app_icon.save(ROOT / "forza-painter-app-icon-1024.png")
    vertical.save(ROOT / "forza-painter-lockup-vertical.png")
    horizontal.save(ROOT / "forza-painter-lockup-horizontal.png")
    export_sizes(icon)
    print("Built uniform logo set from", MASTER.name)


if __name__ == "__main__":
    main()
