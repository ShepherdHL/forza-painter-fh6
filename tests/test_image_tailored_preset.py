from __future__ import annotations

from image_tailored_preset import (
    build_tailored_values,
    compute_save_at,
    compute_stop_at,
    snap_layers_up,
)
from preset_preview import projected_layer_count


def test_snap_layers_up():
    assert snap_layers_up(167) == 200
    assert snap_layers_up(180) == 200
    assert snap_layers_up(100) == 100


def test_compute_stop_at_from_estimate():
    assert compute_stop_at(167) == 250
    assert compute_stop_at(80) == 100
    assert compute_stop_at(2000) == 2500


def test_compute_save_at_includes_cap():
    assert compute_save_at(250, 50) == "50,100,150,200,250"


def test_build_tailored_values_uses_estimate():
    values = build_tailored_values(
        complexity_estimate=400,
        width=1920,
        height=1080,
        preprocess_mode="none",
        base_values={
            "saveEvery": "50",
            "mutatedSamples": "5000",
            "posterizeLevels": "20",
        },
    )
    assert int(values["stopAt"]) == 500
    assert values["preprocessMode"] == "none"
    assert int(values["randomSamples"]) >= 45_000


def test_projected_vs_tailored_cap():
    raw = 167
    stop_at = int(build_tailored_values(
        complexity_estimate=raw,
        width=800,
        height=600,
        preprocess_mode="none",
        base_values={"saveEvery": "50"},
    )["stopAt"])
    assert projected_layer_count(raw, stop_at) == raw
    assert projected_layer_count(raw, 1800) == raw
