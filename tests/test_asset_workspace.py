from __future__ import annotations

from pathlib import Path

import pytest

from asset_workspace import (
    WORKSPACE_SIGNATURE_NAME,
    clear_workspace_tier1,
    clear_workspace_tier2,
    folder_size_bytes,
    format_bytes,
    image_workspace,
    image_workspace_id,
    text_vinyl_workspace,
    workspace_display_name,
    workspace_signature_path,
    write_manifest,
)
from version import APP_LINE_VERSION, GENERATOR_AUTHOR, REPOSITORY_URL
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


def test_workspace_signature_skipped_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    monkeypatch.setattr(
        "ui.workspace_signature_option.should_write_workspace_signature",
        lambda: False,
    )
    source = tmp_path / "art.png"
    source.write_bytes(b"x")
    paths = image_workspace(source).ensure()
    assert not workspace_signature_path(paths).is_file()


def test_workspace_signature_written_on_ensure(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ui.workspace_signature_option.should_write_workspace_signature",
        lambda: True,
    )
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    source = tmp_path / "art.png"
    source.write_bytes(b"x")
    paths = image_workspace(source).ensure()
    signature = workspace_signature_path(paths)
    assert signature.name == WORKSPACE_SIGNATURE_NAME
    assert signature.suffix.lower() == ".txt"
    assert signature.is_file()
    text = signature.read_text(encoding="utf-8")
    assert f"Generator Author: {GENERATOR_AUTHOR}" in text
    assert f"Repo Link: {REPOSITORY_URL}" in text
    assert f"Program Version: {APP_LINE_VERSION}" in text
    assert f"Workspace ID: {paths.workspace_id}" in text
    assert "Workspace Kind: image" in text
    assert "Written:" in text


def test_tier_cleanup_preserves_signature(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    source = tmp_path / "art.png"
    source.write_bytes(b"x")
    paths = image_workspace(source).ensure()
    signature = workspace_signature_path(paths)
    assert signature.is_file()
    (paths.cache / "scratch.tmp").write_text("temp", encoding="utf-8")
    clear_workspace_tier1(paths)
    clear_workspace_tier2(paths)
    assert signature.is_file()


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
    (paths.variants / "art.luma_band.png").write_bytes(b"variant")
    (paths.json_finals / "final.json").write_text("{}", encoding="utf-8")

    clear_workspace_tier1(paths)
    clear_workspace_tier2(paths)

    assert not paths.cache.exists() or not any(paths.cache.iterdir())
    assert not paths.preview_generation.exists()
    assert not (paths.preview_filters / "luma_band.png").exists()
    assert not (paths.variants / "art.luma_band.png").exists()
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


def test_workspace_display_name_uses_manifest_label(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    source = tmp_path / "Kiara_pr-img.png"
    source.write_bytes(b"png")
    paths = image_workspace(source).ensure()
    workspace_source = paths.source / "original.png"
    workspace_source.write_bytes(b"png")
    write_manifest(paths, {"label": "Kiara_pr-img.png", "source_original": str(source)})
    assert workspace_display_name(workspace_source) == "Kiara_pr-img.png"


def test_variant_image_path_uses_stem_and_mode(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    from asset_workspace import variant_image_path

    source = tmp_path / "Kiara_pr-img.png"
    source.write_bytes(b"png")
    paths = image_workspace(source).ensure()
    workspace_source = paths.source / "original.png"
    workspace_source.write_bytes(b"png")
    write_manifest(paths, {"label": "Kiara_pr-img.png", "source_original": str(source)})
    path = variant_image_path(workspace_source, "bilateral")
    assert path.name == "Kiara_pr-img.bilateral.png"
    assert path.parent.name == "variants"


def test_workspace_json_stem_falls_back_to_workspace_id_when_manifest_is_internal(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    from asset_workspace import ensure_image_workspace_source, workspace_display_name, workspace_json_stem

    external = tmp_path / "kiara_bluefield_nobg.png"
    external.write_bytes(b"png")
    paths = image_workspace(external).ensure()
    workspace_source = paths.source / "original.png"
    workspace_source.write_bytes(b"png")
    write_manifest(
        paths,
        {
            "label": "original.png",
            "source_original": str(workspace_source.resolve()),
        },
    )
    assert workspace_json_stem(workspace_source) == "kiara_bluefield_nobg"
    assert workspace_display_name(workspace_source) == "kiara_bluefield_nobg.png"

    repaired = ensure_image_workspace_source(workspace_source, copy_external=False)
    assert repaired == workspace_source
    manifest = paths.manifest.read_text(encoding="utf-8")
    assert "kiara_bluefield_nobg.png" in manifest


def test_ensure_image_workspace_source_does_not_clobber_external_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    from asset_workspace import ensure_image_workspace_source, read_manifest

    external = tmp_path / "kiara_bluefield_nobg.png"
    external.write_bytes(b"png")
    paths = image_workspace(external).ensure()
    dest = paths.source / "original.png"
    dest.write_bytes(b"png")
    write_manifest(
        paths,
        {"label": "kiara_bluefield_nobg.png", "source_original": str(external.resolve())},
    )
    ensure_image_workspace_source(dest, copy_external=False)
    manifest = read_manifest(paths)
    assert manifest is not None
    assert Path(manifest["source_original"]).name == "kiara_bluefield_nobg.png"


def test_generated_run_folder_label_uses_workspace_id(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    from asset_workspace import generated_run_folder_label

    ws = tmp_path / "runtime" / "workspace" / "kiara_bluefield_nobg__ca0663de"
    json_dir = ws / "json"
    json_dir.mkdir(parents=True)
    (json_dir / "kiara_bluefield_nobg_og_3000.json").write_text("[]", encoding="utf-8")
    assert generated_run_folder_label(json_dir) == "kiara_bluefield_nobg"


def test_workspace_json_stem_prefers_source_original(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    from asset_workspace import workspace_json_stem

    source = tmp_path / "bigwalk.png"
    source.write_bytes(b"png")
    paths = image_workspace(source).ensure()
    workspace_source = paths.source / "original.png"
    workspace_source.write_bytes(b"png")
    write_manifest(paths, {"label": "original.png", "source_original": str(source)})
    assert workspace_json_stem(workspace_source) == "bigwalk"


def test_generator_json_output_base_includes_stem_and_slug(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    from asset_workspace import generator_json_output_base

    source = tmp_path / "bigwalk.png"
    source.write_bytes(b"png")
    paths = image_workspace(source).ensure()
    workspace_source = paths.source / "original.png"
    workspace_source.write_bytes(b"png")
    write_manifest(paths, {"label": "original.png", "source_original": str(source)})
    assert generator_json_output_base(workspace_source, "none").name == "bigwalk_og"
    assert generator_json_output_base(workspace_source, "luma_band").name == "bigwalk_lu"


def test_canonicalize_generator_json_outputs_renames_dot_checkpoints(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    from asset_workspace import canonicalize_generator_json_outputs

    json_dir = tmp_path / "json"
    json_dir.mkdir()
    payload = (
        '[{"type":1,"data":[0,0,10,10],"color":[0,0,0,0]},'
        '{"type":16,"data":[5,5,2,2,0],"color":[255,255,255,255]}]'
    )
    (json_dir / "bigwalk_og.1200.json").write_text(payload, encoding="utf-8")
    (json_dir / "bigwalk_og.json").write_text(payload, encoding="utf-8")

    renamed = canonicalize_generator_json_outputs(json_dir, "bigwalk", "og")
    assert (json_dir / "bigwalk_og_1200.json").is_file()
    assert (json_dir / "bigwalk_og_1.json").is_file()
    assert not (json_dir / "bigwalk_og.1200.json").exists()
    assert not (json_dir / "bigwalk_og.json").exists()
    assert len(renamed) == 2


def test_legacy_variant_image_path_layout(tmp_path, monkeypatch):
    monkeypatch.setattr("asset_workspace.ROOT", tmp_path)
    monkeypatch.setattr("asset_workspace.IMAGE_WORKSPACE_ROOT", tmp_path / "runtime" / "workspace")
    from asset_workspace import legacy_variant_image_path

    source = tmp_path / "logo.png"
    source.write_bytes(b"png")
    paths = image_workspace(source).ensure()
    workspace_source = paths.source / "original.png"
    workspace_source.write_bytes(b"png")
    write_manifest(paths, {"label": "logo.png", "source_original": str(source)})
    assert legacy_variant_image_path(workspace_source, "bilateral").name == "bilateral.png"
