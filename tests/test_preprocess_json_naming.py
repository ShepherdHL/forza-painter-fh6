from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from preprocess.filters import (
    PREPROCESS_BILATERAL,
    PREPROCESS_LUMA,
    PREPROCESS_NONE,
    filter_json_slug,
    preprocess_mode_for_path,
    preprocess_mode_from_json_slug,
)
from generator_backend import _json_checkpoint_group_stem, best_geometry_jsons


def test_filter_json_slug_short_codes():
    assert filter_json_slug(PREPROCESS_NONE) == "og"
    assert filter_json_slug(PREPROCESS_LUMA) == "lu"
    assert filter_json_slug(PREPROCESS_BILATERAL) == "bi"


def test_preprocess_mode_for_path_canonical_json_name():
    path = Path("bigwalk_og_1800.json")
    assert preprocess_mode_for_path(path) == PREPROCESS_NONE


def test_preprocess_mode_for_path_legacy_dot_layers():
    path = Path("original.1800.json")
    assert preprocess_mode_for_path(path) is None


def test_preprocess_mode_from_json_slug_round_trip():
    assert preprocess_mode_from_json_slug("lu") == PREPROCESS_LUMA


def test_json_checkpoint_group_stem_strips_layer_suffix():
    assert _json_checkpoint_group_stem("bigwalk_og_1800") == "bigwalk_og"
    assert _json_checkpoint_group_stem("original.1800") == "original"


def test_best_geometry_jsons_groups_canonical_names(tmp_path: Path):
    low = tmp_path / "art_og_500.json"
    high = tmp_path / "art_og_1800.json"
    payload = (
        '[{"type":1,"data":[0,0,10,10],"color":[0,0,0,0]},'
        '{"type":16,"data":[5,5,2,2,0],"color":[255,255,255,255]}]'
    )
    low.write_text(payload, encoding="utf-8")
    time.sleep(0.02)
    high.write_text(payload, encoding="utf-8")
    best = best_geometry_jsons([low, high])
    assert len(best) == 1
    assert best[0] == high
