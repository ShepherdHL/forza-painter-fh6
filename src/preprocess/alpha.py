from __future__ import annotations

import cv2
import numpy as np


def bgra_has_semi_transparent_alpha(bgra: np.ndarray) -> bool:
    if bgra.ndim != 3 or bgra.shape[2] != 4:
        return False
    alpha = bgra[..., 3]
    return bool(np.any((alpha > 0) & (alpha < 255)))


def composite_bgra_on_bgr(bgra: np.ndarray, bg_bgr: tuple[int, int, int]) -> np.ndarray:
    """Alpha-composite BGRA onto a solid BGR background for display."""
    if bgra.ndim == 2:
        gray = np.clip(bgra, 0, 255).astype(np.uint8)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    if bgra.shape[2] == 3:
        return np.clip(bgra, 0, 255).astype(np.uint8)
    if bgra.shape[2] != 4:
        raise ValueError(f"unsupported channel count: {bgra.shape[2]}")

    bgr = bgra[..., :3].astype(np.float32)
    alpha = bgra[..., 3].astype(np.float32) / 255.0
    bg = np.array(bg_bgr, dtype=np.float32)
    out = bgr * alpha[..., None] + bg * (1.0 - alpha[..., None])
    return np.clip(out, 0, 255).astype(np.uint8)


def defringe_alpha_bgra(bgra: np.ndarray, *, alpha_threshold: int = 16) -> np.ndarray:
    """Remove premultiplied cutout fringe; keep hard edges on black."""
    if bgra.ndim == 2:
        gray = np.clip(bgra, 0, 255).astype(np.uint8)
        bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return np.dstack([bgr, np.full(gray.shape, 255, dtype=np.uint8)])
    if bgra.ndim != 3:
        raise ValueError(f"expected a 2D or 3D image array, got shape {bgra.shape}")

    if bgra.shape[2] == 3:
        bgr = np.clip(bgra, 0, 255).astype(np.uint8)
        return np.dstack([bgr, np.full(bgr.shape[:2], 255, dtype=np.uint8)])
    if bgra.shape[2] != 4:
        raise ValueError(f"unsupported channel count: {bgra.shape[2]}")

    if not bgra_has_semi_transparent_alpha(bgra):
        return np.clip(bgra, 0, 255).astype(np.uint8)

    bgr = bgra[..., :3].astype(np.float32)
    alpha = bgra[..., 3].astype(np.float32)
    alpha_norm = np.clip(alpha / 255.0, 0.0, 1.0)
    inv = np.where(alpha_norm > 1e-3, 1.0 / np.maximum(alpha_norm, 1e-3), 0.0)
    bgr = np.clip(bgr * inv[..., None], 0, 255)

    mask = alpha > float(alpha_threshold)
    alpha_out = np.where(mask, 255, 0).astype(np.uint8)
    alpha_f = alpha_out.astype(np.float32) / 255.0
    bgr_out = np.clip(bgr * alpha_f[..., None], 0, 255).astype(np.uint8)
    return np.dstack([bgr_out, alpha_out]).astype(np.uint8)
