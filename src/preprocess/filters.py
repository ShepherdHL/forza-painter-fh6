from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from preprocess.common import PREVIEW_EXPORT_ROOT, atomic_cv2_write, read_bgra
from preprocess.complexity import estimate_layers_from_bgra
from preprocess.luma import apply_luma_bands_bgra
from utils import PreprocessError

PREPROCESS_NONE = "none"
PREPROCESS_LUMA = "luma_band"
PREPROCESS_BILATERAL = "bilateral"
PREPROCESS_POSTERIZE = "posterize"
PREPROCESS_CLAHE = "clahe"
PREPROCESS_SMOOTH = "smooth"
PREPROCESS_CEL_SOFT = "cel_soft"
PREPROCESS_CEL_HEAVY = "cel_heavy"
PREPROCESS_CEL_SHADE = "cel_shade"  # legacy alias -> cel_soft

PREPROCESS_MODE_IDS: tuple[str, ...] = (
    PREPROCESS_NONE,
    PREPROCESS_LUMA,
    PREPROCESS_BILATERAL,
    PREPROCESS_POSTERIZE,
    PREPROCESS_CLAHE,
    PREPROCESS_SMOOTH,
    PREPROCESS_CEL_SOFT,
    PREPROCESS_CEL_HEAVY,
)


@dataclass(frozen=True)
class PreprocessFilterSpec:
    mode_id: str
    label_key: str
    hint_key: str
    json_tag_key: str


PREPROCESS_FILTERS: tuple[PreprocessFilterSpec, ...] = (
    PreprocessFilterSpec(PREPROCESS_NONE, "filter_none", "filter_none_hint", "json_tag_plain"),
    PreprocessFilterSpec(PREPROCESS_LUMA, "filter_luma", "filter_luma_hint", "json_tag_luma"),
    PreprocessFilterSpec(
        PREPROCESS_BILATERAL, "filter_bilateral", "filter_bilateral_hint", "json_tag_bilateral"
    ),
    PreprocessFilterSpec(
        PREPROCESS_POSTERIZE, "filter_posterize", "filter_posterize_hint", "json_tag_posterize"
    ),
    PreprocessFilterSpec(PREPROCESS_CLAHE, "filter_clahe", "filter_clahe_hint", "json_tag_clahe"),
    PreprocessFilterSpec(PREPROCESS_SMOOTH, "filter_smooth", "filter_smooth_hint", "json_tag_smooth"),
    PreprocessFilterSpec(PREPROCESS_CEL_SOFT, "filter_cel_soft", "filter_cel_soft_hint", "json_tag_cel_soft"),
    PreprocessFilterSpec(
        PREPROCESS_CEL_HEAVY, "filter_cel_heavy", "filter_cel_heavy_hint", "json_tag_cel_heavy"
    ),
)


def filter_spec(mode_id: str) -> PreprocessFilterSpec | None:
    for spec in PREPROCESS_FILTERS:
        if spec.mode_id == mode_id:
            return spec
    return None


def normalize_preprocess_mode(mode: str | None) -> str:
    value = str(mode or PREPROCESS_NONE).strip().lower()
    if value == PREPROCESS_CEL_SHADE:
        return PREPROCESS_CEL_SOFT
    if value in PREPROCESS_MODE_IDS:
        return value
    if value in ("", "off", "false", "0"):
        return PREPROCESS_NONE
    return value


def is_preprocess_mode(mode: str | None) -> bool:
    return normalize_preprocess_mode(mode) != PREPROCESS_NONE


def is_preprocess_variant_path(path: str | Path) -> bool:
    stem = Path(path).stem.lower()
    for mode_id in PREPROCESS_MODE_IDS:
        if mode_id == PREPROCESS_NONE:
            continue
        if f".{mode_id}" in stem:
            return True
    return ".luma-bands" in stem or ".luma_band" in stem


def preprocess_mode_for_path(path: str | Path) -> str | None:
    stem = Path(path).stem.lower()
    for mode_id in PREPROCESS_MODE_IDS:
        if mode_id != PREPROCESS_NONE and f".{mode_id}" in stem:
            return mode_id
    if ".luma-bands" in stem or ".luma_band" in stem:
        return PREPROCESS_LUMA
    return None


def preprocessed_image_path(image_path: str | Path, mode: str) -> Path:
    image_path = Path(image_path)
    mode = normalize_preprocess_mode(mode)
    if mode == PREPROCESS_NONE:
        return image_path
    return image_path.with_name(f"{image_path.stem}.{mode}{image_path.suffix}")


def preprocessed_image_exists(image_path: str | Path, mode: str) -> bool:
    path = preprocessed_image_path(image_path, mode)
    try:
        return path.is_file()
    except OSError:
        return False


def apply_preprocess_bgra(bgra: np.ndarray, mode: str) -> np.ndarray:
    mode = normalize_preprocess_mode(mode)
    if mode == PREPROCESS_NONE:
        return bgra
    if mode == PREPROCESS_LUMA:
        return apply_luma_bands_bgra(bgra)

    if bgra.ndim == 2:
        bgr = cv2.cvtColor(bgra, cv2.COLOR_GRAY2BGR)
        alpha = None
    elif bgra.shape[2] == 4:
        bgr = np.clip(bgra[..., :3], 0, 255).astype(np.uint8)
        alpha = np.clip(bgra[..., 3], 0, 255).astype(np.uint8)
    else:
        bgr = np.clip(bgra[..., :3], 0, 255).astype(np.uint8)
        alpha = None

    if mode == PREPROCESS_BILATERAL:
        out = cv2.bilateralFilter(bgr, d=9, sigmaColor=72, sigmaSpace=72)
    elif mode == PREPROCESS_POSTERIZE:
        levels = 10
        step = 256 // max(4, levels)
        out = ((bgr.astype(np.int32) // step) * step + step // 2).clip(0, 255).astype(np.uint8)
    elif mode == PREPROCESS_CLAHE:
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        out = cv2.cvtColor(cv2.merge([clahe.apply(l), a, b]), cv2.COLOR_LAB2BGR)
    elif mode == PREPROCESS_SMOOTH:
        out = cv2.GaussianBlur(bgr, (0, 0), 1.15)
    elif mode in (PREPROCESS_CEL_SOFT, PREPROCESS_CEL_HEAVY):
        base = cv2.bilateralFilter(bgr, d=9, sigmaColor=72, sigmaSpace=72)
        if mode == PREPROCESS_CEL_SOFT:
            levels, block_size, c_bias = 8, 9, 3
            blend = 0.72
        else:
            levels, block_size, c_bias = 6, 7, 5
            blend = 0.92
        step = 256 // max(4, levels)
        flat = ((base.astype(np.int32) // step) * step + step // 2).clip(0, 255).astype(np.uint8)
        gray = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
        edges = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            block_size,
            c_bias,
        )
        edges = cv2.GaussianBlur(edges, (3, 3), 0.0)
        edge_mask = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0
        inked = (flat.astype(np.float32) * edge_mask).clip(0, 255)
        out = cv2.addWeighted(inked.astype(np.uint8), blend, flat, 1.0 - blend, 0.0)
    else:
        raise PreprocessError(f"unsupported preprocess mode: {mode}")

    if alpha is not None:
        return np.dstack([out, alpha]).astype(np.uint8)
    return out.astype(np.uint8)


def preprocess_image_file(image_path: str | Path, mode: str) -> Path:
    image_path = Path(image_path)
    mode = normalize_preprocess_mode(mode)
    if mode == PREPROCESS_NONE:
        return image_path

    output_path = preprocessed_image_path(image_path, mode)
    try:
        if output_path.exists() and output_path.stat().st_mtime >= image_path.stat().st_mtime:
            return output_path
    except OSError:
        pass

    processed = apply_preprocess_bgra(read_bgra(image_path), mode)
    atomic_cv2_write(output_path, processed)
    return output_path


def preview_cache_path(source: Path, mode: str) -> Path:
    source = Path(source)
    PREVIEW_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    safe_stem = source.stem.replace(" ", "_")[:80] or "image"
    return PREVIEW_EXPORT_ROOT / f"{safe_stem}.{normalize_preprocess_mode(mode)}.png"


def build_preview_payload(source: Path, *, max_dim: int = 760) -> dict[str, dict]:
    source = Path(source)
    bgra = read_bgra(source)
    height, width = bgra.shape[:2]
    scale = min(1.0, float(max_dim) / float(max(height, width)))
    if scale < 1.0:
        bgra = cv2.resize(
            bgra,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    payload: dict[str, dict] = {}
    for mode_id in PREPROCESS_MODE_IDS:
        processed = apply_preprocess_bgra(bgra, mode_id)
        cache_path = preview_cache_path(source, mode_id)
        atomic_cv2_write(cache_path, processed)
        payload[mode_id] = {
            "path": cache_path,
            "estimate": estimate_layers_from_bgra(processed),
        }
    return payload
