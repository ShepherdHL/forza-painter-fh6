from __future__ import annotations

import math

import cv2
import numpy as np


def estimate_layers_from_bgra(bgra: np.ndarray, *, max_dim: int = 400) -> int:
    """Fast heuristic — approximate shape count, not exact Geometrize output."""
    if bgra is None or bgra.size == 0:
        return 0

    height, width = bgra.shape[:2]
    scale = min(1.0, float(max_dim) / float(max(height, width)))
    if scale < 1.0:
        bgra = cv2.resize(
            bgra,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    if bgra.ndim == 2:
        bgr = cv2.cvtColor(bgra, cv2.COLOR_GRAY2BGR)
        alpha = np.full(bgra.shape[:2], 255, dtype=np.uint8)
    elif bgra.shape[2] == 4:
        bgr = np.clip(bgra[..., :3], 0, 255).astype(np.uint8)
        alpha = np.clip(bgra[..., 3], 0, 255).astype(np.uint8)
    else:
        bgr = np.clip(bgra[..., :3], 0, 255).astype(np.uint8)
        alpha = np.full(bgr.shape[:2], 255, dtype=np.uint8)

    mask = alpha > 16
    if not np.any(mask):
        mask = np.ones(bgr.shape[:2], dtype=bool)

    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    lightness = lab[:, :, 0]
    a_chan = lab[:, :, 1]
    b_chan = lab[:, :, 2]

    code = (lightness // 12).astype(np.int32) << 12
    code += (a_chan // 24).astype(np.int32) << 6
    code += (b_chan // 24).astype(np.int32)
    masked_codes = code[mask]
    color_bins = int(len(np.unique(masked_codes))) if masked_codes.size else 1

    l_cc = (lightness // 18).astype(np.uint8)
    _, _labels, stats, _ = cv2.connectedComponentsWithStats(l_cc, connectivity=8)
    min_area = max(12, int(mask.sum()) // 800)
    regions = sum(
        1 for index in range(1, len(stats)) if stats[index, cv2.CC_STAT_AREA] >= min_area
    )

    blur = cv2.GaussianBlur(lightness, (0, 0), 1.2)
    edges = cv2.Canny(blur, 45, 120)
    edges[~mask] = 0
    _, _edge_labels, edge_stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
    edge_min = max(8, int(mask.sum()) // 1200)
    edge_regions = sum(
        1 for index in range(1, len(edge_stats)) if edge_stats[index, cv2.CC_STAT_AREA] >= edge_min
    )

    raw = int(color_bins * 1.35 + regions * 0.55 + edge_regions * 0.45)
    pixels = int(mask.sum())
    scale_factor = max(0.45, min(2.2, math.sqrt(pixels / (400 * 400)) if pixels > 0 else 1.0))
    return max(80, min(int(raw * scale_factor), 6000))
