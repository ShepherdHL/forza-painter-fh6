from __future__ import annotations

import re

import cv2
import numpy as np
from pathlib import Path

from asset_workspace import variant_image_path
from preprocess.common import LUMA_BANDS_ROOT, atomic_cv2_write, read_bgra
from utils import PreprocessError


def apply_luma_bands_bgra(bgra: np.ndarray) -> np.ndarray:
    """Edge-aware luma banding for flat anime/logo regions while preserving soft gradients."""
    if bgra.ndim == 2:
        bgr = cv2.cvtColor(bgra, cv2.COLOR_GRAY2BGR)
        alpha = np.full(bgra.shape[:2], 255, dtype=np.uint8)
    elif bgra.ndim != 3:
        raise PreprocessError(f"expected a 2D or 3D image array, got shape {bgra.shape}")
    elif bgra.shape[2] == 4:
        bgr = np.clip(bgra[..., :3], 0, 255).astype(np.uint8)
        alpha = np.clip(bgra[..., 3], 0, 255).astype(np.uint8)
    elif bgra.shape[2] == 3:
        bgr = np.clip(bgra, 0, 255).astype(np.uint8)
        alpha = np.full(bgr.shape[:2], 255, dtype=np.uint8)
    else:
        raise PreprocessError(f"unsupported channel count: {bgra.shape[2]}")

    # cv2.imread returns BGR; use BGR2LAB (not RGB2LAB).
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l = lab[..., 0].astype(np.float32)
    levels = 64.0
    step = 256.0 / levels
    lq = np.floor(l / step) * step + step * 0.5

    blur = cv2.GaussianBlur(l, (0, 0), 1.1)
    gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1, ksize=3)
    edge = np.sqrt(gx * gx + gy * gy)
    edge = np.clip((edge - 3.0) / 18.0, 0.0, 1.0)
    band_weight = 0.16 + edge * 0.34
    l_out = lq * band_weight + l * (1.0 - band_weight)
    l_out = (l_out - 128.0) * 1.005 + 128.0
    lab[..., 0] = np.clip(l_out, 0, 255).astype(np.uint8)
    bgr_out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    if alpha is not None and alpha.ndim == 2:
        return np.dstack([bgr_out, alpha]).astype(np.uint8)
    return bgr_out.astype(np.uint8)


def apply_luma_bands_rgba(rgba: np.ndarray) -> np.ndarray:
    """Backward-compatible alias; input channels are treated as BGR(A) from OpenCV."""
    return apply_luma_bands_bgra(rgba)


def build_luma_bands_file(source: Path, output_dir: Path | None = None) -> Path:
    source = Path(source)
    if output_dir is None:
        output_path = variant_image_path(source, "luma_band")
    else:
        output_dir = Path(output_dir)
        bgra = read_bgra(source)
        processed = apply_luma_bands_bgra(bgra)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", source.stem).strip("._") or "image"
        candidate = output_dir / f"{safe_stem}.luma-bands.png"
        index = 2
        while candidate.exists():
            candidate = output_dir / f"{safe_stem}.luma-bands-v{index}.png"
            index += 1
        atomic_cv2_write(candidate, processed)
        return candidate
    bgra = read_bgra(source)
    processed = apply_luma_bands_bgra(bgra)
    atomic_cv2_write(output_path, processed)
    return output_path


def luma_band(image_path: str | Path) -> Path:
    image_path = Path(image_path)
    output_path = variant_image_path(image_path, "luma_band")
    bgra = read_bgra(image_path)
    processed = apply_luma_bands_bgra(bgra)
    atomic_cv2_write(output_path, processed)
    return output_path
