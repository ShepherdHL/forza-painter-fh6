from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from generator_backend import all_geometry_jsons_in_folder, discover_import_json_dirs


def test_all_geometry_jsons_lists_every_variant(tmp_path, monkeypatch):
    monkeypatch.setattr("generator_backend.IMAGE_WORKSPACE_ROOT", tmp_path / "workspace")
    json_dir = tmp_path / "workspace" / "kiara__abc123" / "json"
    json_dir.mkdir(parents=True)
    for layers in (500, 1000, 1500, 2000, 2500, 3000):
        (json_dir / f"kiara_og_{layers}.json").write_text("[]", encoding="utf-8")

    paths = all_geometry_jsons_in_folder(json_dir)
    assert len(paths) == 6
    assert [p.stem for p in paths] == [
        "kiara_og_500",
        "kiara_og_1000",
        "kiara_og_1500",
        "kiara_og_2000",
        "kiara_og_2500",
        "kiara_og_3000",
    ]


def test_discover_import_json_dirs_one_row_per_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr("generator_backend.ROOT", tmp_path)
    monkeypatch.setattr("generator_backend.IMAGE_WORKSPACE_ROOT", tmp_path / "workspace")
    ws = tmp_path / "workspace" / "kiara__abc123"
    json_dir = ws / "json"
    json_dir.mkdir(parents=True)
    (json_dir / "finals").mkdir()
    (json_dir / "kiara_og_3000.json").write_text("[]", encoding="utf-8")
    (json_dir / "finals" / "kiara_og_3000.json").write_text("[]", encoding="utf-8")

    dirs = discover_import_json_dirs(tmp_path)
    assert len(dirs) == 1
    assert dirs[0] == json_dir
