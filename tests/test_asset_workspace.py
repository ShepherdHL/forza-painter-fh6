from __future__ import annotations

from pathlib import Path

import pytest

from asset_workspace import (
    clear_workspace_tier1,
    clear_workspace_tier2,
    folder_size_bytes,
    format_bytes,
    image_workspace,
    image_workspace_id,
    text_vinyl_workspace,
    write_manifest,
)
from file_management_settings import (
    PRESET_CUSTOM,
    PRESET_KEEP_ALL,
    PRESET_MINIMAL_DISK,
    PRESET_RECOMMENDED,
    FileManagementSettings,
    apply_preset,
    load_file_management_settings,
    save_file_management_settings,
)


def test_image_workspace_id_is_stable(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    source = tmp_path / "logo.png"
    source.write_bytes(b"png")
    first = image_workspace_id(source)
    second = image_workspace_id(source)
    assert first == second
    assert first.startswith("logo__")


def test_tier_cleanup_preserves_final_json(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    source = tmp_path / "art.png"
    source.write_bytes(b"x")
    paths = image_workspace(source).ensure()
    write_manifest(paths, {"label": "art.png", "source_original": str(source)})
    (paths.cache / "scratch.tmp").write_text("temp", encoding="utf-8")
    paths.preview_generation.parent.mkdir(parents=True, exist_ok=True)
    paths.preview_generation.write_bytes(b"preview")
    paths.preview_filters.mkdir(parents=True, exist_ok=True)
    (paths.preview_filters / "luma_band.png").write_bytes(b"filter")
    (paths.variants / "luma_band.png").write_bytes(b"variant")
    (paths.json_finals / "final.json").write_text("{}", encoding="utf-8")

    clear_workspace_tier1(paths)
    clear_workspace_tier2(paths)

    assert not paths.cache.exists() or not any(paths.cache.iterdir())
    assert not paths.preview_generation.exists()
    assert not (paths.preview_filters / "luma_band.png").exists()
    assert not (paths.variants / "luma_band.png").exists()
    assert (paths.json_finals / "final.json").is_file()


def test_filter_preview_path_uses_workspace(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    from asset_workspace import filter_preview_path

    source = tmp_path / "logo.png"
    source.write_bytes(b"x")
    path = filter_preview_path(source, "bilateral")
    assert "workspace" in str(path).replace("\\", "/")
    assert path.name == "bilateral.png"
    assert "filter-previews" not in str(path).replace("\\", "/")


def test_keep_filter_previews_default_off():
    from file_management_settings import FileManagementSettings, PRESET_RECOMMENDED

    settings = FileManagementSettings(preset=PRESET_RECOMMENDED)
    assert settings.effective_keep_filter_previews() is False


def test_format_bytes():
    assert format_bytes(512) == "512 B"
    assert format_bytes(2048) == "2.0 KB"


def test_folder_size_bytes(tmp_path):
    file_a = tmp_path / "a.bin"
    file_a.write_bytes(b"1234")
    assert folder_size_bytes(file_a) == 4
    assert folder_size_bytes(tmp_path) >= 4


def test_preset_defaults_for_beginners():
    settings = FileManagementSettings(preset=PRESET_RECOMMENDED)
    assert settings.effective_clear_ephemeral_on_exit() is True
    assert settings.effective_clear_session_cache_on_exit() is False
    assert settings.effective_copy_external_images() is True


def test_preset_keep_all(tmp_path, monkeypatch):
    monkeypatch.setattr("file_management_settings.ROOT", tmp_path)
    monkeypatch.setattr("file_management_settings.SETTINGS_PATH", tmp_path / "file_management.json")
    settings = apply_preset(PRESET_KEEP_ALL)
    assert settings.effective_clear_ephemeral_on_exit() is False
    assert settings.effective_clear_session_cache_on_exit() is False


def test_preset_minimal_disk(tmp_path, monkeypatch):
    monkeypatch.setattr("file_management_settings.ROOT", tmp_path)
    monkeypatch.setattr("file_management_settings.SETTINGS_PATH", tmp_path / "file_management.json")
    settings = apply_preset(PRESET_MINIMAL_DISK)
    assert settings.effective_clear_ephemeral_on_exit() is True
    assert settings.effective_clear_session_cache_on_exit() is True


def test_save_and_load_custom_settings(tmp_path, monkeypatch):
    monkeypatch.setattr("file_management_settings.ROOT", tmp_path)
    path = tmp_path / "runtime" / "settings" / "file_management.json"
    monkeypatch.setattr("file_management_settings.SETTINGS_PATH", path)
    settings = FileManagementSettings(
        preset=PRESET_CUSTOM,
        clear_ephemeral_on_exit=False,
        clear_session_cache_on_exit=True,
        copy_external_images=False,
        copy_trace_references=False,
    )
    save_file_management_settings(settings)
    loaded = load_file_management_settings()
    assert loaded.preset == PRESET_CUSTOM
    assert loaded.clear_session_cache_on_exit is True
    assert loaded.copy_external_images is False


def test_text_vinyl_workspace_paths(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.TEXT_VINYL_WORKSPACE_ROOT", tmp_path / "runtime" / "text-vinyl")
    paths = text_vinyl_workspace("typed", "hello").ensure()
    assert paths.json_finals == paths.root / "json"
    assert paths.kind == "text_vinyl"
