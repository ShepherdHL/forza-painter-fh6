from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

from app_paths import ROOT
from utils import PreprocessError

PREVIEW_EXPORT_ROOT = ROOT / "imgs" / "filter-previews"
LUMA_BANDS_ROOT = PREVIEW_EXPORT_ROOT


def read_bgra(image_path: Path) -> np.ndarray:
    bgra = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if bgra is None:
        raise PreprocessError(f"failed to read image: {image_path}")
    if bgra.ndim == 2:
        bgra = cv2.cvtColor(bgra, cv2.COLOR_GRAY2BGRA)
    elif bgra.ndim == 3 and bgra.shape[2] == 3:
        bgra = cv2.cvtColor(bgra, cv2.COLOR_BGR2BGRA)
    elif bgra.ndim != 3 or bgra.shape[2] != 4:
        raise PreprocessError(f"unsupported image shape: {bgra.shape}")
    return bgra


def atomic_cv2_write(output_path: Path, image: np.ndarray) -> None:
    tmp_path = output_path.with_name(f"{output_path.stem}.tmp{output_path.suffix}")
    if not cv2.imwrite(str(tmp_path), image):
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise PreprocessError(f"failed to write preprocessed image: {output_path}")
    try:
        os.replace(str(tmp_path), str(output_path))
    except OSError as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise PreprocessError(f"failed to finalize preprocessed image: {output_path}") from exc
