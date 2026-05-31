import numpy as np

from preprocess.alpha import bgra_has_semi_transparent_alpha, composite_bgra_on_bgr, defringe_alpha_bgra


def test_bgra_has_semi_transparent_alpha_detects_fringe():
    bgra = np.zeros((4, 4, 4), dtype=np.uint8)
    bgra[..., 3] = 255
    bgra[1, 1, 3] = 128
    assert bgra_has_semi_transparent_alpha(bgra)


def test_defringe_removes_premultiplied_halo():
    bgra = np.zeros((6, 6, 4), dtype=np.uint8)
    bgra[2:4, 2:4, :3] = 200
    bgra[2:4, 2:4, 3] = 255
    bgra[1, 2, :3] = 40
    bgra[1, 2, 3] = 64
    bgra[4, 3, :3] = 30
    bgra[4, 3, 3] = 48
    cleaned = defringe_alpha_bgra(bgra)
    assert not bgra_has_semi_transparent_alpha(cleaned)
    assert cleaned[1, 2, 3] == 0
    assert cleaned[2, 2, 3] == 255


def test_composite_bgra_on_bgr_matches_opaque_pixels():
    bgra = np.zeros((2, 2, 4), dtype=np.uint8)
    bgra[0, 0, :3] = (10, 20, 30)
    bgra[0, 0, 3] = 255
    out = composite_bgra_on_bgr(bgra, (0, 0, 0))
    assert tuple(out[0, 0]) == (10, 20, 30)
