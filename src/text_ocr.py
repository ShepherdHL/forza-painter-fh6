"""
Optional OCR helpers for Japanese / Katakana text in reference images.

Install optional dependencies (see requirements-text-ocr.txt). The app works
without OCR when you type text or trace from an image directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class OcrLine:
    text: str
    confidence: float
    box: tuple  # (x0, y0, x1, y1)


def ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return True


def read_text_from_image(
    image_path: Path,
    languages: str = "jpn",
    psm: int = 7,
) -> List[OcrLine]:
    """
    Read text from an image using Tesseract.

    Requires:
      pip install pytesseract pillow
      Tesseract OCR installed with Japanese traineddata (jpn / jpn_vert).
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "OCR requires: pip install pytesseract pillow, plus Tesseract with Japanese data."
        ) from exc

    image_path = Path(image_path)
    image = Image.open(image_path)
    config = f"--psm {int(psm)} -l {languages}"
    data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
    lines: List[OcrLine] = []
    n = len(data.get("text", []))
    for index in range(n):
        text = (data["text"][index] or "").strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][index])
        except (TypeError, ValueError):
            conf = -1.0
        if conf >= 0 and conf < 40:
            continue
        x = int(data["left"][index])
        y = int(data["top"][index])
        w = int(data["width"][index])
        h = int(data["height"][index])
        lines.append(OcrLine(text=text, confidence=conf, box=(x, y, x + w, y + h)))
    return lines


def read_combined_text(image_path: Path, languages: str = "chi_sim+jpn") -> str:
    lines = read_text_from_image(image_path, languages=languages)
    if not lines:
        return ""
    return "".join(line.text for line in lines)


def try_easyocr_lines(image_path: Path) -> Optional[List[OcrLine]]:
    try:
        import easyocr
    except ImportError:
        return None
    reader = easyocr.Reader(["ch_sim", "ja", "en"], gpu=False)
    results = reader.readtext(str(image_path))
    lines = []
    for box, text, confidence in results:
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        lines.append(
            OcrLine(
                text=str(text).strip(),
                confidence=float(confidence),
                box=(int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))),
            )
        )
    return [line for line in lines if line.text]
