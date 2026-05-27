import argparse
import ctypes
import importlib
import io
import json
import math
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import traceback
import tempfile
import faulthandler
from collections import deque
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, BOTTOM, END, HORIZONTAL, LEFT, RIGHT, TOP, TclError, VERTICAL, X, Y, Button, Canvas, Checkbutton, Entry, Frame, Label, Listbox, PhotoImage, StringVar, Text, Tk, Toplevel, filedialog, messagebox, ttk

import psutil

from acknowledgements import get_acknowledgements
from app_paths import ROOT
from app_config import (
    APP_DIR,
    PROBE_DIR,
    SESSION_PATH,
    TYPECODE_EXPORT_DIR,
    TYPECODE_IMPORT_DIR,
    MEMORY_SNAPSHOT_LIMIT_MB,
    PREVIEW_MAX,
    GENERATE_COMPARE_SOURCE_MIN,
    GENERATE_COMPARE_RESULT_MIN,
    DETAILED_LOG_OUTPUT_LIMIT,
    DETAILED_LOG_MEMORY_LIMIT,
    FH6_AUTO_LOCATE_MAX_SECONDS,
    FH6_AUTO_LOCATE_TIMEOUT_SECONDS,
    UPDATE_CHANGELOG_URL,
    UPDATE_RELEASE_URL,
    UPDATE_CHECK_TIMEOUT_SECONDS,
)
from game_profiles import PROFILES
from geometry_json import RECTANGLE, ROTATED_ELLIPSE, load_normalized_geometry
from fh6_typecode_json import (
    is_typecode_geometry_json,
    load_typecode_shapes,
    typecode_shape_count,
    typecode_shape_summary,
)
from generator_backend import (
    GENERATOR_EXE,
    GENERATOR_JSON_SCAN_SECONDS,
    GENERATOR_POLL_SLEEP_SECONDS,
    GENERATOR_PREVIEW_SCAN_SECONDS,
    USER_SETTINGS_DIR,
    best_geometry_jsons,
    best_safe_final_json,
    build_generator_command,
    build_generator_env,
    checkpoints_for_image,
    discover_generated_run_folders,
    generated_jsons,
    json_candidates_for_run_folder,
    is_luma_variant_path,
    json_from_preprocess_pipeline,
    json_from_luma_pipeline,
    setting_preprocess_mode,
    setting_uses_luma_prep,
    generated_preview_files,
    generator_preview_path,
    geometry_shape_count,
    load_settings,
    preprocess_input_image,
    write_custom_settings,
    write_user_settings_preset,
)
from utils import load_cv2, load_pillow
from preprocess.common import PREVIEW_EXPORT_ROOT
from preprocess.filters import (
    PREPROCESS_FILTERS,
    PREPROCESS_MODE_IDS,
    PREPROCESS_NONE,
    build_preview_payload,
    filter_spec,
    normalize_preprocess_mode,
    preprocessed_image_exists,
    preprocessed_image_path,
    preprocess_mode_for_path,
)
from security_policy import (
    GITHUB_RELEASES_API,
    redact_sensitive_log_text,
    updates_enabled,
    validate_fetch_url,
    validate_fh6_session,
    parse_safe_hex_address,
)
from ui_layout import (
    DEFAULT_PANE_RATIOS,
    apply_pane_ratio,
    load_ui_layout,
    pane_ratio,
    save_ui_layout,
)
from ui.header_telemetry import HeaderTelemetryPanel
from ui.text_vinyl_workspace import TextVinylWorkspace
from ui.tools import ToolsWorkspace
from ui_chrome import DonutGauge, header_rule
from ui_themes import (
    DEFAULT_THEME_ID,
    THEME_IDS,
    load_saved_theme_id,
    normalize_theme_id,
    palette_to_color_globals,
    resolve_palette,
    save_theme_id,
)
from resource_monitor import (
    ResourceMonitorBackend,
    ResourceSnapshot,
    evaluate_heat_state,
    load_settings as load_resource_monitor_settings,
)
from i18n import LANGUAGES, eta_suffix, tr as tr_text, ui_font_name
from i18n_ja import merge_japanese_text
from i18n_ko_patch import merge_korean_patch
from i18n_text import apply_text_patches
from ui_language import language_display_name, resolve_initial_language_code, save_language_code
from version import APP_DISPLAY_NAME, __version__, app_title, app_version_string


def _startup_crash_report_paths() -> list[Path]:
    # Write somewhere the user can find even for one-file EXEs.
    # - beside the EXE (ROOT)
    # - inside runtime/logs (if creatable)
    # - %TEMP%
    paths: list[Path] = []
    try:
        paths.append(ROOT / "forza-painter-startup-crash.txt")
        paths.append(ROOT / "runtime" / "logs" / "forza-painter-startup-crash.txt")
    except Exception:
        pass
    try:
        paths.append(Path(tempfile.gettempdir()) / "forza-painter-startup-crash.txt")
    except Exception:
        pass
    # De-dup while preserving order
    unique: list[Path] = []
    seen: set[str] = set()
    for p in paths:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _write_startup_crash_report(exc: BaseException) -> Path | None:
    report = "\n".join(
        [
            f"{APP_DISPLAY_NAME} startup crash report",
            f"Version: {__version__}",
            f"Timestamp: {datetime.utcnow().isoformat()}Z",
            f"Frozen: {bool(getattr(sys, 'frozen', False))}",
            f"Executable: {getattr(sys, 'executable', '')}",
            f"Python: {sys.version}",
            "",
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        ]
    )
    for path in _startup_crash_report_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding="utf-8", errors="replace")
            return path
        except Exception:
            continue
    return None
def _install_color_globals(palette) -> None:
    import sys

    module = sys.modules[__name__]
    for name, value in palette_to_color_globals(palette).items():
        setattr(module, name, value)


_install_color_globals(resolve_palette(load_saved_theme_id(ROOT)))
UI_INPUT_FONT = ("Segoe UI", 10)
UI_LOG_FONT = ("Consolas", 10)


TEXT = {
    "en": {
        "title": app_title(),
        "subtitle": "Generate geometry JSON and import it into Forza Horizon vinyl editor.",
        "header_kicker": "FORZA PAINTER 1.6.X",
        "header_audit": "Experimental build",
        "language": "Language",
        "appearance": "Appearance",
        "layout_resize_hint": "Drag dividers to resize panels. Sizes are remembered.",
        "theme_label": "Themes",
        "theme_eurocorp": "Eurocorp",
        "theme_elite": "Elite",
        "theme_red_phosphorous": "Red Phosphorous",
        "theme_y2k": "Y2K",
        "theme_spirit_of_horizon": "The Spirit of Horizon",
        "process": "Game process",
        "refresh": "Refresh",
        "generate_tab": "Generate JSON",
        "text_tab": "Text vinyl",
        "text_tab_hint": "Choose a script tab, enter text, pick a font (use search to filter), then generate. Use the right panel to preview reference images and generated JSON.",
        "text_outputs": "Text vinyl JSON",
        "text_outputs_hint": "JSON created on this tab. Add files manually or send a selection to Import Final when ready.",
        "text_reference_preview": "Reference image preview",
        "text_json_preview": "Generated JSON preview",
        "text_add_json": "Add JSON",
        "text_remove_json": "Remove selected",
        "text_send_to_import": "Add to Import Final",
        "text_open_vinyl_folder": "Open text-vinyl folder",
        "text_script_universal": "Universal (Latin)",
        "text_script_japanese": "Japanese",
        "text_script_korean": "Korean",
        "text_script_chinese": "Chinese",
        "text_script_hint_universal": "Latin letters, numbers, and Western punctuation. Use a [LATIN] font such as Segoe UI or Arial.",
        "text_script_hint_japanese": "Hiragana, katakana, and kanji. Use a [JP] or [CJK] font such as Meiryo or Yu Gothic.",
        "text_script_hint_korean": "Hangul syllables. Use a [KR] font such as Malgun Gothic.",
        "text_script_hint_chinese": "Simplified or traditional hanzi. Use an [SC]/[TC] font; insert characters from the GB2312 library below.",
        "text_input": "Text (Unicode)",
        "text_font": "Font",
        "text_font_search": "Search fonts",
        "text_options": "Generation options",
        "text_font_browse": "Browse font file",
        "text_font_refresh": "Refresh fonts",
        "text_font_size": "Font size",
        "text_cell_size": "Trace cell size",
        "text_shape_mode": "Trace shape mode",
        "text_shape_mode_hint": "Rectangles/squares use rectangle layers; ellipses/circles/triangles/mixed use sphere layers in FH6.",
        "text_template_hint": "FH6 template: {hint}",
        "text_cell_hint": "Larger cell = fewer vinyl layers, less fine detail.",
        "text_color": "Color (R,G,B,A)",
        "text_coverage_ok": "All CJK characters are supported by the selected font.",
        "text_coverage_ok_korean": "Korean and other CJK characters are supported by the selected font.",
        "text_coverage_missing": "Missing {count} glyph(s) in selected font: {chars}",
        "text_coverage_missing_korean": "Korean needs a [KR] font (e.g. Malgun Gothic). Missing {count} glyph(s): {chars}",
        "text_coverage_suggest_kr": "Korean detected — select a [KR] font such as {font}.",
        "text_char_library": "Mandarin character library (GB2312 hanzi)",
        "text_char_search": "Search character",
        "text_char_insert": "Insert selected",
        "text_char_count": "{count} characters available",
        "text_reference_image": "Reference image",
        "text_browse_image": "Browse",
        "text_generate_typed": "Generate from text",
        "text_trace_image": "Trace from image",
        "text_invert": "Invert colors before trace",
        "text_generating": "Building text vinyl JSON...",
        "text_done": "Text JSON ready ({layers} layers): {path}",
        "text_failed": "Text vinyl generation failed",
        "text_log_scanning_fonts": "Scanning installed fonts for all script tabs...",
        "text_log_font_scan_failed": "Font scan failed: {error}",
        "text_log_fonts_loaded": "Loaded fonts — Latin/Universal: {latin}, Japanese: {japanese}, Korean: {korean}, Chinese: {chinese}.",
        "text_log_no_fonts": "No fonts found. Use Browse on each tab to pick a .ttf/.ttc/.otf file.",
        "text_log_enter_text": "Enter text to generate.",
        "text_log_choose_trace_image": "Choose a reference image to trace.",
        "text_log_no_json_to_send": "No text vinyl JSON to send to Import Final.",
        "text_log_json_already_import": "Selected JSON file(s) are already on the Import Final list.",
        "text_log_added_json_import": "Added {count} JSON file(s) to Import Final.",
        "text_dialog_select_font": "Select font file",
        "text_dialog_select_reference_image": "Select text reference image",
        "text_dialog_add_json": "Add text vinyl JSON",
        "text_template_hint_sphere": "Use an ungrouped sphere template in FH6 (ellipse / sphere layers).",
        "text_template_hint_rectangle": "Use an ungrouped rectangle template in FH6 when possible (fewer layers).",
        "import_final_tab": "Import Final JSON",
        "import_final_tab_hint": "Import finalized geometry JSON from this app (rectangles and rotated ellipses). Pick a generated run folder or add JSON files directly, then import into your ungrouped FH6 template.",
        "import_final_runs": "Generated runs",
        "import_final_refresh_runs": "Refresh runs",
        "import_final_run_files": "JSON in selected run",
        "import_final_use_best": "Use best safe final (highest layer count in run)",
        "import_final_pick_best": "Select best final",
        "import_final_import": "Import final JSON into FH6",
        "import_handmade_tab": "Import Handmade JSON",
        "handmade_tab": "Handmade JSON",
        "handmade_tab_hint": "Import user-made FH6 JSON that contains real FH6 shape type codes (not generated rectangles/ellipses). After import, save and reload the vinyl group in FH6 to refresh display.",
        "export_game_tab": "Export Game JSON",
        "export_game_tab_hint": "Export the open vinyl group from FH6 to a handmade/type-code JSON file. Use the same game connection and template layer count as import.",
        "export_game_json": "Export open FH6 group to JSON",
        "export_open_folder": "Open export folder",
        "handmade_choose_json": "Choose handmade JSON",
        "handmade_import": "Import handmade JSON into FH6",
        "handmade_export": "Export open FH6 group to JSON",
        "handmade_status_none": "Select a handmade JSON to inspect supported shapes.",
        "handmade_status_counts": "Shapes: total {total} · supported {supported} · unsupported {unsupported}",
        "preview_tab": "Image Preview",
        "preview_tab_hint": "Compare preprocessing filters and approximate layer cost before generating. Layer counts are estimates only — lower often means fewer shapes. Click a card to select the filter used on the Generate tab.",
        "preview_choose_image": "Choose image",
        "preview_use_generate_image": "Use selected Generate image",
        "preview_apply_generate": "Open Generate tab",
        "preview_open_folder": "Open preview cache",
        "preview_processing": "Building filter previews: {path}",
        "preview_failed": "Filter preview failed: {error}",
        "preview_output_folder": "Preview cache: {path}",
        "preview_estimate": "~{count} layers (est.)",
        "preview_estimate_unknown": "Estimate unavailable",
        "preview_select_filter": "Click a filter card to select it for generation.",
        "filter_none": "Original",
        "filter_none_hint": "Uses your image as-is with no preprocessing. Best baseline for photos, soft gradients, hair, and skin when you do not want extra simplification.",
        "filter_luma": "Luma Bands",
        "filter_luma_hint": "Applies edge-aware luminance banding to flatten similar tones into cleaner steps. Best for logos, decals, anime flat fills, and hard color blocks.",
        "filter_bilateral": "Bilateral Smooth",
        "filter_bilateral_hint": "Smooths noise and texture while keeping edges relatively sharp. Best for photos, portraits, skin, and hair.",
        "filter_posterize": "Posterize",
        "filter_posterize_hint": "Reduces the number of distinct color steps in the image. Best for stylized art, posters, and limited-palette designs.",
        "filter_clahe": "CLAHE Contrast",
        "filter_clahe_hint": "Boosts local contrast so dark or washed-out areas read more clearly. Best for underexposed, foggy, or low-contrast references.",
        "filter_smooth": "Mild Blur",
        "filter_smooth_hint": "Applies a light Gaussian blur to soften fine detail and compression artifacts. Best for noisy screenshots and busy JPEG sources. Seems silly, but you may like the results.",
        "filter_cel_soft": "Soft Cel Shading",
        "filter_cel_soft_hint": "Comic/cel style with gentler outlines and smoother fills. Good first pass for anime and stylized art.",
        "filter_cel_heavy": "Heavy Ink Cel Shading",
        "filter_cel_heavy_hint": "Stronger black ink lines and flatter shading for bold comic/Borderlands-like results. Can be harsh on photos.",
        "preprocess_filter": "Preprocess Filter",
        "preprocess_filter_hint": "Choose how the image is simplified before the GPU generator runs. Compare options on the Image Preview tab; lower estimates often mean fewer shapes.",
        "generate_source_original": "Original",
        "generate_source_filtered": "With filter",
        "generate_result_plain": "No filter",
        "generate_result_filtered": "With {filter}",
        "json_tag_bilateral": "[Bilateral]",
        "json_tag_posterize": "[Posterize]",
        "json_tag_clahe": "[CLAHE]",
        "json_tag_smooth": "[Smooth]",
        "json_tag_cel_soft": "[Cel Soft]",
        "json_tag_cel_heavy": "[Cel Ink]",
        "luma_before": "Before",
        "luma_after": "After Luma Band Pass",
        "luma_before_hint": "Choose an image to preview the source here.",
        "luma_after_hint": "The luma-banded result will appear here.",
        "luma_output_folder": "Output folder: {path}",
        "luma_processing": "Processing: {path}",
        "luma_saved": "Saved luma-band image: {path}",
        "luma_failed": "Luma Band Pass failed: {error}",
        "tools_tab": "Tools",
        "tools_tab_hint": "Creative utilities for your convenience. If you're a future developer, please place any future tools in under this series of tabs.",
        "tools_panel_color_picker": "Color Picker",
        "tools_panel_bg_remove": "Background Removal",
        "tools_panel_fh6": "FH6 Diagnostics",
        "tools_color_picker_hint": "Sample colors from any image file. Click the canvas to lock a color; Shift+mouse wheel changes sample size. Forza H/S/B matches Bang's converter.",
        "tools_color_browse": "Browse image",
        "tools_color_no_image": "Browse an image to sample colors.",
        "tools_color_file_filter": "Image files",
        "tools_bg_remove_hint": "Reputable tools for quick image editing. Online tools are fastest for one-off exports. Desktop apps give you significantly more control over vinyl prep.",
        "tools_bg_online_title": "Online (quick export)",
        "tools_bg_desktop_title": "Desktop (more control)",
        "tools_bg_iloveimg_title": "iloveimg — Background Remover",
        "tools_bg_iloveimg_desc": "Free browser workflow: upload, remove background, download PNG. Good for quick decals and logos.",
        "tools_bg_pixlr_title": "Pixlr — Background Remover",
        "tools_bg_pixlr_desc": "Browser editor with background removal and touch-up. Useful when you want light edits after cutout.",
        "tools_bg_gimp_title": "GIMP",
        "tools_bg_gimp_desc": "Free desktop editor. Use Select by Color / Fuzzy Select and layer masks for precise cutouts on complex art.",
        "tools_bg_mspaint_title": "Microsoft Paint (Windows 11)",
        "tools_bg_mspaint_desc": "Built-in Remove background (Image menu) for simple subjects. Fast for screenshots and flat art.",
        "tools_bg_inkscape_title": "Inkscape",
        "tools_bg_inkscape_desc": "Vector-friendly workflow: trace bitmap, edit paths, export clean PNG/SVG for vinyl references.",
        "tools_badge_online": "Online",
        "tools_badge_desktop": "Desktop",
        "tools_open_link": "Open in browser",
        "tools_open_website": "Open website",
        "tools_open_guide": "Open guide",
        "tools_open_paint": "Open Paint",
        "tools_fh6_hint": "Memory diagnostics and FH6 session tools. Requires Forza Horizon 6 running with a valid session. IF YOU DO NOT KNOW WHAT THIS DOES, DO NOT USE IT.",
        "tutorial_tab": "Tutorial",
        "acknowledgements_tab": "Acknowledgements",
        "colors_values": "Color values",
        "colors_pixel_size": "Sample size (px)",
        "colors_click_hint": "Click the image to pick a color.",
        "colors_hex": "Hex",
        "colors_rgb": "RGB",
        "colors_hsl": "HSL",
        "colors_hsb": "HSB",
        "colors_forza": "Forza H / S / B",
        "colors_copy_hex": "Copy hex",
        "colors_copy_forza": "Copy Forza H,S,B",
        "colors_open_bang": "Open Bang's converter",
        "colors_copied": "Copied to clipboard.",
        "colors_saved": "Saved color {hex}",
        "colors_saved_history": "Saved colors (click to recall)",
        "monitor_tab": "Resource Monitor",
        "monitor_why_title": "Why is this here?",
        "images": "Images",
        "add_images": "Add images",
        "remove_image": "Remove selected image",
        "quality": "Quality profile",
        "import_preset": "Import preset",
        "open_preset_folder": "Open preset folder",
        "custom_settings": "Use custom settings",
        "custom_layers": "Output layers",
        "custom_resolution": "Max resolution",
        "custom_random": "Random samples",
        "custom_mutated": "Mutated samples",
        "custom_save_at": "Save checkpoints",
        "preprocess_mode": "Preprocess mode",
        "luma_prep": "Luma Prep — cleaner flat regions, can soften tiny detail",
        "luma_prep_hint": "Best for logos, decals, and hard color bands. Leave off for soft gradients, hair, skin, and detailed character art.",
        "generate_compare_source": "Source prep",
        "generate_compare_result": "Generated result compare",
        "generate_without_luma": "Without Luma Prep",
        "generate_with_luma": "With Luma Prep",
        "generate_layers_count": "{count} layers",
        "generate_no_checkpoint": "No checkpoint yet",
        "luma_status_none": "Select an image to see whether Luma Prep applies and which JSON checkpoints exist.",
        "luma_status_next_on": "Next generate: {filter}.",
        "luma_status_next_off": "Next generate: original image (no filter).",
        "luma_status_file_ready": "Preprocessed file: ready ({name}).",
        "luma_status_file_missing": "Preprocessed file: not created yet (use Image Preview or Generate).",
        "luma_status_checkpoints": "Checkpoints — no filter: {plain} · with filter: {filtered}.",
        "luma_status_last_run_on": "Last completed run used {filter}.",
        "luma_status_last_run_off": "Last completed run used no filter.",
        "luma_status_last_run_unknown": "No completed generate run recorded yet for this image.",
        "luma_image_tag_ready": "luma file ready",
        "luma_image_tag_missing": "no luma file",
        "json_tag_luma": "[Luma]",
        "json_tag_plain": "[Plain]",
        "generate_log_pipeline_filter": "Generating with {filter} (input: {path})",
        "generate_log_pipeline_plain": "Generating with no filter (original image)",
        "generate_log_output_filter": "Generated JSON ({filter}): {path}",
        "generate_log_output_plain": "Generated JSON (no filter): {path}",
        "generate_select_image": "Select an image to compare prep and results.",
        "save_custom_preset": "Save as preset",
        "custom_panel_title": "Custom settings",
        "custom_panel_hint": "The selected preset fills these values. Enable custom settings if you want to edit them before generating.",
        "generate_step_image": "Step 1 - Choose Images",
        "generate_step_image_hint": "Add PNG/JPG/BMP images. Generated JSON is saved beside each source image.",
        "generate_step_image_credit": "If the image you are featuring was not made by you, credit the original artist wherever possible.",
        "preview_image_added_to_generate": "Added to Generate image list: {name}",
        "preview_image_already_on_generate": "Already on Generate image list: {name}",
        "generate_step_quality": "Step 2 - Choose Quality",
        "generate_step_quality_hint": "Fast profiles are quicker. Slow profiles use more GPU time and usually look cleaner.",
        "generate_step_run": "Step 3 - Generate",
        "generate_step_run_hint": "Click once and wait. Progress appears in Logs; generated JSON is added to the Import page automatically.",
        "scroll_hint": "Add image, choose a preset, then adjust custom settings if needed.",
        "start_generate": "Generate with current settings",
        "stop_generate": "Stop Current Generation",
        "open_output": "Open Output Folder",
        "preview": "Preview",
        "preview_hint": "Select an image or JSON to preview it here.",
        "preview_unavailable": "Preview is unavailable. Install optional preview dependencies, or continue without preview.",
        "logs": "Logs",
        "export_logs": "Export detailed log",
        "progress": "Progress",
        "json_files": "Geometry JSON files",
        "add_json": "Add JSON",
        "remove_json": "Remove selected JSON",
        "use_outputs": "Use generated JSON",
        "step_game": "Step 1 - Game",
        "step_game_hint": "Start FH6, open Vinyl Group Editor, load an ungrouped sphere template, then refresh the process list.",
        "step_template": "Step 2 - Template",
        "step_template_hint": "Enter the exact layer count shown by your current in-game template.",
        "step_json": "Step 3 - JSON",
        "step_json_hint": "Use the JSON generated by this app, or add a geometry JSON manually.",
        "step_import": "Step 4 - Import",
        "step_import_hint": "Click import once. The app will find the FH6 layer table safely, then write the design.",
        "advanced_options": "Advanced options",
        "show_advanced": "Show advanced",
        "hide_advanced": "Hide advanced",
        "import_preview": "Selected JSON preview",
        "game_profile": "Game profile",
        "pid": "PID",
        "layer_count": "Template layer count",
        "layer_count_required": "Template layer count is required. Enter the exact layer count shown in-game.",
        "layer_import_info": "Selected JSON: — | Enter in-game template layer count above",
        "easy_import": "Easy import",
        "easy_import_hint": "For FH6, leave addresses empty. The app will reuse a live session or auto-locate before import.",
        "manual_count": "Layer count address",
        "manual_table": "Layer table address",
        "auto_locate": "Auto-locate FH6",
        "import_json": "Import JSON",
        "handmade_section": "Handmade / universal JSON (FH6)",
        "handmade_section_hint": "For JSON with real FH6 shape type codes (not only generated rectangles/ellipses). Export reads the open vinyl group; import writes save-safe layer fields. Save and reload the vinyl group in FH6 after import.",
        "export_typecode_json": "Export open group to JSON",
        "typecode_trim_after_import": "Trim vinyl group to imported layer count after import",
        "typecode_allow_unknown": "Allow experimental shape codes (advanced)",
        "typecode_export_done": "Exported {count} layer(s) to {path}",
        "typecode_export_failed": "Export failed: {error}",
        "typecode_import_mode": "Using handmade/universal importer for {name}",
        "typecode_import_done": "Handmade import finished: {name}",
        "typecode_trim_done": "Trimmed vinyl group count to {count}",
        "typecode_trim_failed": "Trim failed: {error}",
        "typecode_missing_group": "Could not resolve FH6 group address for trim/export. Re-run auto-locate.",
        "diagnose": "Diagnose",
        "save_snapshot": "Save count snapshot",
        "compare_snapshot": "Compare snapshot",
        "snapshot_count": "Snapshot layer count",
        "current_count": "Current layer count",
        "inspect_table": "Inspect table",
        "table_address": "Candidate table",
        "admin_note": "This build requests administrator rights on startup for FH6 memory access.",
        "no_game": "No supported game process detected",
        "ready": "Ready",
        "running": "Running",
        "done": "Done",
        "failed": "Failed",
        "stopped": "Stopped",
        "no_generation_running": "No generation is running.",
        "stopping_generation": "Stopping current generation...",
        "generation_stopped": "Generation stopped.",
        "generator_recycled_layers": "Generator recycled fully covered layers after {max_layer}/{total}; continuing. This is normal and is not a full restart.",
        "existing_checkpoints_found": "Found existing checkpoint JSON for {image}: {count} file(s). Added the best one to Import.",
        "checkpoint_available_after_failure": "Saved checkpoint is available despite the failed/stopped run: {path}",
        "imported_presets": "Imported {count} preset file(s).",
        "saved_preset": "Saved preset: {path}",
        "no_image_selected": "No image is selected.",
        "no_json_selected": "No JSON is selected.",
        "cannot_resume_checkpoint": "Existing checkpoints can be reused/imported, but this GPU generator does not support true resume-from-checkpoint yet.",
        "locating": "Finding current FH6 template...",
        "locating_wait": "This can take up to 5 minutes. Keep FH6 in the Vinyl Group Editor, do not switch menus, and wait patiently.",
        "located": "FH6 template located and verified.",
        "importing": "Importing JSON into FH6...",
        "json_too_small": "Selected JSON has far fewer drawable layers than the usable template capacity. Import will look blurry; choose a higher-layer JSON.",
        "json_needs_more_template_layers": "FH needs 4 boundary layers for correct cover/apply behavior. Use a template with at least JSON drawable layers + 4.",
        "safe_stop": "Stopped before writing because no safe FH6 template was found.",
        "update_available_title": "Update available",
        "update_available_message": "A new version is available.\n\nCurrent: v{current}\nLatest: v{latest}",
        "update_open_page": "Open update page",
        "update_later": "Later",
        "update_check_failed_title": "Update check failed",
        "update_check_failed_message": "Could not check for updates. You can keep using the app.\n\n{error}",
        "update_current": "Already on the latest version.",
        "changelog": "Changelog",
        "runtime_folder": "Runtime/cache folder",
        "open_runtime_folder": "Open runtime folder",
        "runtime_location": "Runtime/cache files are stored beside the app: {runtime}. FH6 probe cache: {probe}.",
        "resource_monitor_title": "Resource monitor",
        "resource_cpu": "CPU",
        "resource_gpu": "GPU",
        "resource_temp_nominal": "Temperature nominal.",
        "resource_unavailable": "Unavailable",
        "resource_heat_warning_banner": "/// WARNING! Significant Heat Detected! ///",
        "resource_heat_critical_banner": "/// TEMPERATURE CRITICAL. STOP THE PROGRAM. ///",
        "resource_heat_log_warning": "/// WARNING! Significant Heat Detected! /// (peak {temp}°C)",
        "resource_heat_log_critical": "/// TEMPERATURE CRITICAL. STOP THE PROGRAM. /// (peak {temp}°C)",
        "resource_temp_returned_normal": "Resource monitor: temperatures returned to normal (peak {temp}°C).",
        "log_no_run_folder_selected": "No generated run folder selected.",
        "log_no_json_in_run": "No JSON found in {path}",
        "log_selected_best_final": "Selected best final: {name}",
        "log_no_quality_profile": "No quality profile selected.",
        "log_save_preset_failed": "Failed to save preset: {error}",
        "log_clipboard_failed": "Clipboard copy failed: {error}",
        "log_export_detailed_failed": "Failed to export detailed log: {error}",
        "log_export_detailed_done": "Detailed log exported: {path} ({chars} chars, limit {limit}).",
        "log_update_check_failed": "Update check failed: {error}",
        "log_update_available": "New version available: v{latest} (current v{current})",
        "dialog_choose_images": "Choose images",
        "dialog_import_preset": "Import generator preset",
        "log_import_preset_failed": "Failed to import preset {path}: {error}",
        "dialog_choose_geometry_json": "Choose geometry JSON",
        "log_added_generated_json": "Added {count} generated JSON file(s) to import list.",
        "log_process_stale": "Selected game process pid {pid} is no longer running; refreshing process list.",
        "log_no_game_process": "No live supported game process is selected. Start FH6, then click Refresh.",
        "log_generation_already_running": "Generation is already running. Wait for it to finish or use Stop current generation.",
        "log_no_images_selected": "No images selected.",
        "log_missing_generator": "Missing generator: {path}",
        "log_pid_layer_required": "PID and template layer count are required.",
        "log_no_json_files_selected": "No JSON files selected.",
        "log_pid_snapshot_required": "PID and snapshot layer count are required.",
        "log_pid_snapshot_current_required": "PID, snapshot layer count, and current layer count are required.",
        "log_pid_layer_table_required": "PID, layer count, and table address are required.",
        "update_no_changelog": "No changelog section was available.",
        "startup_failed": "The app failed to start.{details}\n\n{name}: {error}",
        "log_skipped_handmade_on_final": "Skipped handmade/type-code JSON on Final import tab: {name}",
        "log_skipped_non_handmade": "Skipped non-handmade JSON: {name}",
        "no_settings_profiles": "No settings profiles found.",
        "text_shape_rectangles": "Rectangles",
        "text_shape_squares": "Squares",
        "text_shape_ellipses": "Ellipses",
        "text_shape_circles": "Circles",
        "text_shape_triangles": "Triangles",
        "text_shape_mixed": "Mixed",
        "tutorial": """Beginner workflow

1. Download the one-file EXE from GitHub Releases and run it directly. Normal users do not need Python, .venv, or batch files.

2. Start Forza Horizon 6 and enter Create Vinyl Group / Vinyl Group Editor.

3. Load or create a template made of many simple sphere layers. 500 or more layers is recommended. Ungroup the template before importing.

4. In this app, open Generate JSON, add a PNG/JPG/BMP image, choose a quality profile, then click Start generating.

5. Open Import. Add the generated JSON or click Use generated JSON. Keep Game profile as Forza Horizon 6.

6. Enter the real template layer count currently loaded in-game. For FH6 you normally do not need to type memory addresses. Click Import JSON; the app will auto-locate the live FH6 layer table if needed.

7. If import fails with OpenProcess or permission errors, close the app and run the EXE as administrator. If the game was restarted, entered another menu, or reloaded the template, import again with the correct layer count.

Notes

- JSON generation uses the bundled GPU/OpenCL generator, so keep the graphics driver updated.
- Current FH6 addresses are valid only for the current game process and editor state.
- If the app cannot find a safe template, confirm the editor is open, the template is ungrouped, and the layer count is exact.
""",
    },
    "zh": {
        "title": app_title(),
        "subtitle": "生成 geometry JSON，并导入到 Forza Horizon 的 Vinyl Group 编辑器。",
        "header_kicker": "FORZA PAINTER 1.6.X",
        "header_audit": "实验版",
        "language": "语言",
        "appearance": "外观",
        "layout_resize_hint": "拖动分隔条可调整面板大小，设置会自动保存。",
        "theme_label": "主题",
        "theme_eurocorp": "Eurocorp",
        "theme_elite": "精英",
        "theme_red_phosphorous": "红磷",
        "theme_y2k": "Y2K",
        "theme_spirit_of_horizon": "地平线之魂",
        "process": "游戏进程",
        "refresh": "刷新",
        "generate_tab": "生成 JSON",
        "text_tab": "文字贴膜",
        "text_tab_hint": "选择文字体系标签页，输入文字并选择字体（可用搜索筛选），然后生成。右侧可预览参考图与生成的 JSON。",
        "text_outputs": "文字贴膜 JSON",
        "text_outputs_hint": "本标签页生成的 JSON。可手动添加文件，或选中后发送到「导入 Final JSON」。",
        "text_reference_preview": "参考图预览",
        "text_json_preview": "生成的 JSON 预览",
        "text_add_json": "添加 JSON",
        "text_remove_json": "移除选中",
        "text_send_to_import": "添加到 Import Final",
        "text_open_vinyl_folder": "打开 text-vinyl 文件夹",
        "text_script_universal": "通用（拉丁）",
        "text_script_japanese": "日文",
        "text_script_korean": "韩文",
        "text_script_chinese": "中文",
        "text_script_hint_universal": "拉丁字母与西方标点。请选用 [LATIN] 字体，如 Segoe UI、Arial。",
        "text_script_hint_japanese": "假名与汉字。请选用 [JP] 或 [CJK] 字体，如 Meiryo。",
        "text_script_hint_korean": "韩文音节。请选用 [KR] 字体，如 Malgun Gothic。",
        "text_script_hint_chinese": "简繁汉字。请选用 [SC]/[TC] 字体；可从下方 GB2312 字库插入。",
        "text_input": "文字（Unicode）",
        "text_font": "字体",
        "text_font_search": "搜索字体",
        "text_options": "生成选项",
        "text_font_browse": "浏览字体文件",
        "text_font_refresh": "刷新字体列表",
        "text_font_size": "字号",
        "text_cell_size": "栅格大小",
        "text_shape_mode": "描摹形状",
        "text_shape_mode_hint": "矩形/方块用矩形图层；椭圆/圆/三角/混合建议用球形模板。",
        "text_template_hint": "FH6 模板：{hint}",
        "text_cell_hint": "栅格越大，图层越少，细节越少。",
        "text_color": "颜色 (R,G,B,A)",
        "text_coverage_ok": "当前字体支持输入中的所有 CJK 字符。",
        "text_coverage_ok_korean": "当前字体支持输入中的韩文及其他 CJK 字符。",
        "text_coverage_missing": "当前字体缺少 {count} 个字形：{chars}",
        "text_coverage_missing_korean": "韩文请选用 [KR] 字体（如 Malgun Gothic）。缺少 {count} 个字形：{chars}",
        "text_coverage_suggest_kr": "检测到韩文 — 请选择 [KR] 字体，例如 {font}。",
        "text_char_library": "简体字库（GB2312）",
        "text_char_search": "搜索汉字",
        "text_char_insert": "插入选中字",
        "text_char_count": "可用 {count} 个字符",
        "text_reference_image": "参考图片",
        "text_browse_image": "浏览",
        "text_generate_typed": "从文字生成",
        "text_trace_image": "从图片描摹",
        "text_invert": "描摹前反色",
        "text_generating": "正在生成文字 JSON...",
        "text_done": "文字 JSON 已就绪（{layers} 层）：{path}",
        "text_failed": "文字贴膜生成失败",
        "text_log_scanning_fonts": "正在扫描各文字体系标签页的已安装字体…",
        "text_log_font_scan_failed": "字体扫描失败：{error}",
        "text_log_fonts_loaded": "已加载字体 — 拉丁/通用：{latin}，日文：{japanese}，韩文：{korean}，中文：{chinese}。",
        "text_log_no_fonts": "未找到字体。请在各标签页使用「浏览」选择 .ttf/.ttc/.otf 文件。",
        "text_log_enter_text": "请输入要生成的文字。",
        "text_log_choose_trace_image": "请选择要描摹的参考图片。",
        "text_log_no_json_to_send": "没有可发送到 Import Final 的文字贴膜 JSON。",
        "text_log_json_already_import": "所选 JSON 文件已在 Import Final 列表中。",
        "text_log_added_json_import": "已将 {count} 个 JSON 文件添加到 Import Final。",
        "text_dialog_select_font": "选择字体文件",
        "text_dialog_select_reference_image": "选择文字参考图片",
        "text_dialog_add_json": "添加文字贴膜 JSON",
        "text_template_hint_sphere": "FH6 请使用未分组的球形模板（椭圆 / sphere 图层）。",
        "text_template_hint_rectangle": "FH6 请尽量使用未分组的矩形模板（图层更少）。",
        "import_final_tab": "导入 Final JSON",
        "import_final_tab_hint": "导入本应用生成的最终几何 JSON（矩形与旋转椭圆）。选择生成运行文件夹或直接添加 JSON，然后导入到未分组的 FH6 模板。",
        "import_final_runs": "生成运行",
        "import_final_refresh_runs": "刷新运行列表",
        "import_final_run_files": "所选运行中的 JSON",
        "import_final_use_best": "使用最佳安全 final（运行内最高图层数）",
        "import_final_pick_best": "选择最佳 final",
        "import_final_import": "将 Final JSON 导入 FH6",
        "import_handmade_tab": "导入手工 JSON",
        "handmade_tab": "手工 JSON",
        "handmade_tab_hint": "导入包含真实 FH6 形状类型码的用户 JSON（非生成的矩形/椭圆）。导入后请在 FH6 中保存并重新加载贴膜组。",
        "export_game_tab": "导出游戏 JSON",
        "export_game_tab_hint": "将 FH6 中当前打开的贴膜组导出为手工/类型码 JSON。使用与导入相同的游戏连接和模板图层数。",
        "export_game_json": "将打开的 FH6 组导出为 JSON",
        "export_open_folder": "打开导出文件夹",
        "handmade_choose_json": "选择手工 JSON",
        "handmade_import": "将手工 JSON 导入 FH6",
        "handmade_export": "导出当前 FH6 组为 JSON",
        "handmade_status_none": "选择手工 JSON 后可查看支持的形状数量。",
        "handmade_status_counts": "形状：总计 {total} · 支持 {supported} · 不支持 {unsupported}",
        "preview_tab": "图像预览",
        "preview_tab_hint": "生成前对比预处理滤镜与预估层数。层数为估算值，越低通常形状越少。点击卡片后在「生成」页使用。",
        "preview_choose_image": "选择图片",
        "preview_use_generate_image": "使用「生成」页所选图片",
        "preview_apply_generate": "打开「生成」页",
        "preview_open_folder": "打开预览缓存",
        "preview_processing": "正在生成滤镜预览：{path}",
        "preview_failed": "滤镜预览失败：{error}",
        "preview_output_folder": "预览缓存：{path}",
        "preview_estimate": "约 {count} 层（预估）",
        "preview_estimate_unknown": "无法预估",
        "preview_select_filter": "点击滤镜卡片以用于生成。",
        "filter_none": "原图",
        "filter_none_hint": "不预处理，直接使用原图。适合照片、柔和渐变、头发和皮肤等不希望额外简化的素材。",
        "filter_luma": "亮度分带",
        "filter_luma_hint": "边缘感知的亮度分带，将相近色调压成更干净的阶梯。适合 Logo、贴花、动漫平涂和硬色块。",
        "filter_bilateral": "双边平滑",
        "filter_bilateral_hint": "在保留边缘的同时平滑噪点与纹理。适合照片、人像、皮肤和头发。",
        "filter_posterize": "色调分离",
        "filter_posterize_hint": "减少图像中的独立色阶数量。适合风格化插画、海报和有限色板设计。",
        "filter_clahe": "CLAHE 对比度",
        "filter_clahe_hint": "增强局部对比度，让偏暗或平淡的区域更清晰。适合曝光不足、雾面或低对比度参考图。",
        "filter_smooth": "轻度模糊",
        "filter_smooth_hint": "轻微高斯模糊，柔化细节与 JPEG 压缩痕迹。适合噪点多的截图和杂乱 JPEG 素材。",
        "filter_cel_soft": "柔和赛璐璐",
        "filter_cel_soft_hint": "漫画/赛璐璐风格，线条较柔和、明暗更平滑。适合动漫和风格化插画。",
        "filter_cel_heavy": "重墨赛璐璐",
        "filter_cel_heavy_hint": "更强的黑色墨线与更扁平的明暗，呈现更浓的漫画/Borderlands 风格。照片可能偏硬。",
        "preprocess_filter": "预处理滤镜",
        "preprocess_filter_hint": "选择 GPU 生成器运行前如何简化图像。可在图像预览页对比；预估层数越低通常形状越少。",
        "generate_source_original": "原图",
        "generate_source_filtered": "滤镜后",
        "generate_result_plain": "无滤镜",
        "generate_result_filtered": "使用 {filter}",
        "json_tag_bilateral": "[双边]",
        "json_tag_posterize": "[色调分离]",
        "json_tag_clahe": "[CLAHE]",
        "json_tag_smooth": "[模糊]",
        "json_tag_cel_soft": "[柔和赛璐璐]",
        "json_tag_cel_heavy": "[重墨赛璐璐]",
        "luma_before": "原图",
        "luma_after": "亮度分带后",
        "luma_before_hint": "选择图片后在此预览原图。",
        "luma_after_hint": "亮度分带结果将显示在此。",
        "luma_output_folder": "输出目录：{path}",
        "luma_processing": "正在处理：{path}",
        "luma_saved": "已保存亮度分带图片：{path}",
        "luma_failed": "亮度分带失败：{error}",
        "tools_tab": "工具",
        "tools_tab_hint": "实验性创意工具（Forza Painter 1.6.X），与 JSON 生成流程分离。每个工具独立面板，后续可扩展，不影响生成或文字贴膜工作流。",
        "tools_panel_color_picker": "取色器",
        "tools_panel_bg_remove": "去背景",
        "tools_panel_fh6": "FH6 诊断",
        "tools_color_picker_hint": "从任意图片文件取色。点击画布锁定颜色；Shift+滚轮调整采样大小。Forza H/S/B 与 Bang 转换器一致。",
        "tools_color_browse": "浏览图片",
        "tools_color_no_image": "浏览一张图片以开始取色。",
        "tools_color_file_filter": "图片文件",
        "tools_bg_remove_hint": "多种去背景方式：在线工具适合快速导出；桌面软件适合精细贴膜准备。",
        "tools_bg_online_title": "在线（快速导出）",
        "tools_bg_desktop_title": "桌面（更多控制）",
        "tools_bg_iloveimg_title": "iloveimg — 去背景",
        "tools_bg_iloveimg_desc": "免费浏览器流程：上传、去背景、下载 PNG。适合快速处理贴花与标志。",
        "tools_bg_pixlr_title": "Pixlr — 去背景",
        "tools_bg_pixlr_desc": "浏览器编辑器，支持去背景与微调，适合抠图后轻量修图。",
        "tools_bg_gimp_title": "GIMP",
        "tools_bg_gimp_desc": "免费桌面编辑器。用按颜色选择/模糊选择与图层蒙版处理复杂图像。",
        "tools_bg_mspaint_title": "Microsoft 画图（Windows 11）",
        "tools_bg_mspaint_desc": "内置“删除背景”（图像菜单），适合简单主体、截图与扁平图。",
        "tools_bg_inkscape_title": "Inkscape",
        "tools_bg_inkscape_desc": "矢量友好：位图描摹、编辑路径，导出干净 PNG/SVG 作贴膜参考。",
        "tools_badge_online": "在线",
        "tools_badge_desktop": "桌面",
        "tools_open_link": "在浏览器中打开",
        "tools_open_website": "打开网站",
        "tools_open_guide": "打开说明",
        "tools_open_paint": "打开画图",
        "tools_fh6_hint": "内存诊断与 FH6 会话工具。需要 Forza Horizon 6 正在运行且会话有效。",
        "tutorial_tab": "教程",
        "acknowledgements_tab": "致谢",
        "colors_values": "颜色数值",
        "colors_pixel_size": "采样大小（像素）",
        "colors_click_hint": "点击图片取色。",
        "colors_hex": "Hex",
        "colors_rgb": "RGB",
        "colors_hsl": "HSL",
        "colors_hsb": "HSB",
        "colors_forza": "Forza H / S / B",
        "colors_copy_hex": "复制 Hex",
        "colors_copy_forza": "复制 Forza",
        "colors_open_bang": "打开 Bang 转换器",
        "colors_copied": "已复制到剪贴板。",
        "colors_saved": "已保存颜色 {hex}",
        "colors_saved_history": "已保存的颜色（点击可恢复）",
        "monitor_tab": "资源监控",
        "monitor_why_title": "为什么有这个？",
        "images": "图片",
        "add_images": "添加图片",
        "remove_image": "移除选中图片",
        "quality": "品质配置",
        "import_preset": "导入预设",
        "open_preset_folder": "打开预设目录",
        "custom_settings": "使用自定义参数",
        "custom_layers": "输出层数",
        "custom_resolution": "最大分辨率",
        "custom_random": "随机样本",
        "custom_mutated": "变异样本",
        "custom_save_at": "保存节点",
        "preprocess_mode": "预处理模式",
        "luma_prep": "亮度分带（Luma Prep）— 平涂区域更清晰，可能柔化细节",
        "luma_prep_hint": "适合 Logo、贴花和平涂色块。渐变、头发、皮肤和精细角色建议关闭。",
        "generate_compare_source": "源图预处理",
        "generate_compare_result": "生成结果对比",
        "generate_without_luma": "未启用 Luma Prep",
        "generate_with_luma": "启用 Luma Prep",
        "generate_layers_count": "{count} 层",
        "generate_no_checkpoint": "尚无 checkpoint",
        "luma_status_none": "选择图片后可查看是否使用 Luma Prep，以及对应的 JSON checkpoint。",
        "luma_status_next_on": "下次生成：已启用 Luma Prep（使用亮度分带源图）。",
        "luma_status_next_off": "下次生成：未启用 Luma Prep（使用原图）。",
        "luma_status_file_ready": "亮度分带文件：已就绪（{name}）。",
        "luma_status_file_missing": "亮度分带文件：尚未生成（启用 Luma Prep 或首次以 Luma Prep 生成后会出现）。",
        "luma_status_checkpoints": "Checkpoint — 普通：{plain} · Luma：{luma}。",
        "luma_status_last_run_on": "该图片最近一次生成使用了 Luma Prep。",
        "luma_status_last_run_off": "该图片最近一次生成未使用 Luma Prep。",
        "luma_status_last_run_unknown": "尚未记录该图片的完成生成记录。",
        "luma_column_next": " ← 下次",
        "luma_column_last": "（上次）",
        "luma_image_tag_ready": "已有 luma 文件",
        "luma_image_tag_missing": "无 luma 文件",
        "json_tag_luma": "[Luma]",
        "json_tag_plain": "[普通]",
        "generate_log_pipeline_luma": "正在使用 Luma Prep 生成（输入：{path}）",
        "generate_log_pipeline_plain": "正在不使用 Luma Prep 生成（原图）",
        "generate_log_output_luma": "已生成 JSON（Luma Prep）：{path}",
        "generate_log_output_plain": "已生成 JSON（未用 Luma Prep）：{path}",
        "generate_select_image": "选择图片以对比预处理与生成结果。",
        "save_custom_preset": "保存为预设",
        "custom_panel_title": "自定义参数",
        "custom_panel_hint": "上方预设会自动填入这些参数；勾选使用自定义参数后可直接修改。",
        "generate_step_image": "第 1 步 - 选择图片",
        "generate_step_image_hint": "添加 PNG/JPG/BMP 图片。生成的 JSON 会保存在原图片旁边。",
        "generate_step_image_credit": "若展示的图片或艺术作品非本人创作，请尽可能注明原作者。",
        "preview_image_added_to_generate": "已加入生成图片列表：{name}",
        "preview_image_already_on_generate": "已在生成图片列表中：{name}",
        "generate_step_quality": "第 2 步 - 选择品质",
        "generate_step_quality_hint": "快速配置耗时短；慢速配置会占用更多 GPU 时间，通常画面更干净。",
        "generate_step_run": "第 3 步 - 开始生成",
        "generate_step_run_hint": "点击一次后等待。进度会显示在日志里，生成的 JSON 会自动加入导入页面。",
        "scroll_hint": "添加图片、选择预设；需要时直接修改下方自定义参数。",
        "start_generate": "按当前配置生成",
        "stop_generate": "中断当前生成",
        "open_output": "打开输出目录",
        "preview": "预览",
        "preview_hint": "选择图片或 JSON 后会在这里预览。",
        "preview_unavailable": "当前环境无法显示预览。可安装可选预览依赖，也可以直接继续生成或导入。",
        "logs": "日志",
        "export_logs": "导出详细日志",
        "progress": "进度",
        "json_files": "Geometry JSON 文件",
        "add_json": "添加 JSON",
        "remove_json": "移除选中 JSON",
        "use_outputs": "使用已生成 JSON",
        "step_game": "第 1 步 - 游戏",
        "step_game_hint": "启动 FH6，进入 Vinyl Group Editor，载入未分组的球形模板，然后刷新进程列表。",
        "step_template": "第 2 步 - 模板",
        "step_template_hint": "填写游戏里当前模板显示的真实层数。",
        "step_json": "第 3 步 - JSON",
        "step_json_hint": "使用本软件生成的 JSON，或手动添加 geometry JSON。",
        "step_import": "第 4 步 - 导入",
        "step_import_hint": "只点一次导入。软件会安全定位 FH6 图层表，然后写入图案。",
        "advanced_options": "高级选项",
        "show_advanced": "显示高级",
        "hide_advanced": "隐藏高级",
        "import_preview": "已选 JSON 预览",
        "game_profile": "游戏 profile",
        "pid": "PID",
        "layer_count": "模板层数",
        "layer_count_required": "请填写模板层数。输入游戏中显示的精确层数。",
        "layer_import_info": "已选 JSON：— | 请在上方填写游戏中的模板层数",
        "easy_import": "简化导入",
        "easy_import_hint": "FH6 通常不需要手填地址。留空即可复用当前 session，或在导入前自动定位。",
        "manual_count": "层数地址",
        "manual_table": "图层表地址",
        "auto_locate": "自动定位 FH6",
        "import_json": "导入 JSON",
        "handmade_section": "手工 / 通用 JSON（FH6）",
        "handmade_section_hint": "用于包含真实 FH6 形状类型码的 JSON（不仅是生成的矩形/椭圆）。导出会读取当前打开的贴膜组；导入仅写入可安全保存的图层字段。导入后请在 FH6 中保存并重新加载贴膜组。",
        "export_typecode_json": "导出当前组为 JSON",
        "typecode_trim_after_import": "导入后将贴膜组层数裁剪为实际导入层数",
        "typecode_allow_unknown": "允许实验性形状码（高级）",
        "typecode_export_done": "已导出 {count} 层到 {path}",
        "typecode_export_failed": "导出失败：{error}",
        "typecode_import_mode": "对手工/通用 JSON 使用导入器：{name}",
        "typecode_import_done": "手工导入完成：{name}",
        "typecode_trim_done": "已将贴膜组层数裁剪为 {count}",
        "typecode_trim_failed": "裁剪失败：{error}",
        "typecode_missing_group": "无法解析 FH6 组地址，无法导出/裁剪。请重新自动定位。",
        "diagnose": "诊断",
        "save_snapshot": "保存层数快照",
        "compare_snapshot": "对比快照",
        "snapshot_count": "快照层数",
        "current_count": "当前层数",
        "inspect_table": "精查 table",
        "table_address": "候选 table",
        "admin_note": "导入需要管理员权限。如果日志出现 OpenProcess 失败，请用管理员身份启动本程序。",
        "no_game": "未检测到支持的游戏进程",
        "ready": "就绪",
        "running": "运行中",
        "done": "完成",
        "failed": "失败",
        "stopped": "已中断",
        "no_generation_running": "当前没有正在生成的任务。",
        "stopping_generation": "正在中断当前生成...",
        "generation_stopped": "生成已中断。",
        "generator_recycled_layers": "生成器在 {max_layer}/{total} 后回收了被完全遮挡的旧图层，正在继续。这是正常回收，不是重新开始。",
        "existing_checkpoints_found": "发现 {image} 已有 checkpoint JSON：{count} 个，已把最合适的一个加入导入列表。",
        "checkpoint_available_after_failure": "虽然本次生成失败/中断，但已有 checkpoint 可用：{path}",
        "imported_presets": "已导入 {count} 个预设文件。",
        "saved_preset": "已保存预设：{path}",
        "no_image_selected": "没有选中图片。",
        "no_json_selected": "没有选中 JSON。",
        "cannot_resume_checkpoint": "已有 checkpoint 可以复用/导入，但当前 GPU 生成器还不支持真正从 checkpoint 继续生成。",
        "locating": "正在查找当前 FH6 模板...",
        "locating_wait": "这一步最长可能需要 5 分钟。请保持 FH6 停留在 Vinyl Group Editor，不要切换菜单，耐心等待。",
        "located": "已安全定位并验证 FH6 模板。",
        "importing": "正在导入 JSON 到 FH6...",
        "json_too_small": "当前 JSON 可绘制层数远少于模板可用容量，导入会很糊；请换用更高层数的 JSON。",
        "json_needs_more_template_layers": "FH 需要预留 4 个边界层，才能正常保存封面和贴到车上。模板层数建议至少为 JSON 可绘制层数 + 4。",
        "safe_stop": "未找到安全 FH6 模板，已在写入前停止。",
        "update_available_title": "发现新版本",
        "update_available_message": "检测到新版本。\n\n当前版本：v{current}\n最新版本：v{latest}",
        "update_open_page": "打开更新页面",
        "update_later": "稍后再说",
        "update_check_failed_title": "更新检查失败",
        "update_check_failed_message": "无法检查更新。你可以继续使用当前版本。\n\n{error}",
        "update_current": "当前已经是最新版本。",
        "changelog": "更新内容",
        "runtime_folder": "运行/缓存目录",
        "open_runtime_folder": "打开运行缓存目录",
        "runtime_location": "运行缓存文件会保存在软件旁边：{runtime}。FH6 定位缓存：{probe}。",
        "resource_monitor_title": "资源监控",
        "resource_cpu": "CPU",
        "resource_gpu": "GPU",
        "resource_temp_nominal": "温度读数正常。",
        "resource_unavailable": "不可用",
        "resource_heat_warning_banner": "/// 警告！检测到明显高温！ ///",
        "resource_heat_critical_banner": "/// 温度危险。请停止程序。 ///",
        "resource_heat_log_warning": "/// 警告！检测到明显高温！ ///（峰值 {temp}°C）",
        "resource_heat_log_critical": "/// 温度危险。请停止程序。 ///（峰值 {temp}°C）",
        "resource_temp_returned_normal": "资源监控：温度已恢复正常（峰值 {temp}°C）。",
        "log_no_run_folder_selected": "未选择生成运行文件夹。",
        "log_no_json_in_run": "在 {path} 中未找到 JSON",
        "log_selected_best_final": "已选择最佳 final：{name}",
        "log_no_quality_profile": "未选择品质配置。",
        "log_save_preset_failed": "保存预设失败：{error}",
        "log_clipboard_failed": "复制到剪贴板失败：{error}",
        "log_export_detailed_failed": "导出详细日志失败：{error}",
        "log_export_detailed_done": "详细日志已导出：{path}（{chars} 字符，上限 {limit}）。",
        "log_update_check_failed": "更新检查失败：{error}",
        "log_update_available": "发现新版本：v{latest}（当前 v{current}）",
        "dialog_choose_images": "选择图片",
        "dialog_import_preset": "导入生成器预设",
        "log_import_preset_failed": "导入预设 {path} 失败：{error}",
        "dialog_choose_geometry_json": "选择 geometry JSON",
        "log_added_generated_json": "已将 {count} 个生成的 JSON 文件添加到导入列表。",
        "log_process_stale": "所选游戏进程 pid {pid} 已不在运行；正在刷新进程列表。",
        "log_no_game_process": "未选择有效的支持游戏进程。请启动 FH6 后点击刷新。",
        "log_generation_already_running": "生成任务已在运行。请等待完成或使用「中断当前生成」。",
        "log_no_images_selected": "未选择图片。",
        "log_missing_generator": "缺少生成器：{path}",
        "log_pid_layer_required": "需要 PID 和模板层数。",
        "log_no_json_files_selected": "未选择 JSON 文件。",
        "log_pid_snapshot_required": "需要 PID 和快照层数。",
        "log_pid_snapshot_current_required": "需要 PID、快照层数和当前层数。",
        "log_pid_layer_table_required": "需要 PID、层数和 table 地址。",
        "update_no_changelog": "没有可用的更新说明章节。",
        "startup_failed": "应用启动失败。{details}\n\n{name}：{error}",
        "log_skipped_handmade_on_final": "已在 Final 导入页跳过 handmade/类型码 JSON：{name}",
        "log_skipped_non_handmade": "已跳过非 handmade JSON：{name}",
        "no_settings_profiles": "未找到设置配置文件。",
        "text_shape_rectangles": "矩形",
        "text_shape_squares": "正方形",
        "text_shape_ellipses": "椭圆",
        "text_shape_circles": "圆形",
        "text_shape_triangles": "三角形",
        "text_shape_mixed": "混合",
        "tutorial": """小白流程

1. 从 GitHub Releases 下载单文件 EXE，直接运行。普通用户不需要 Python、.venv 或 bat 文件。

2. 启动 Forza Horizon 6，进入 Create Vinyl Group / Vinyl Group Editor。

3. 载入或新建一个由大量 sphere 图层组成的模板。建议 500 层以上。导入前必须先 ungroup。

4. 在本软件的“生成 JSON”页添加 PNG/JPG/BMP 图片，选择品质配置，点击“开始生成”。

5. 打开“导入”页，添加生成的 JSON，或点击“使用已生成 JSON”。游戏 profile 保持 Forza Horizon 6。

6. 填写游戏里当前模板的真实层数。FH6 通常不需要手动填写内存地址。点击“导入 JSON”，软件会在需要时自动定位当前 FH6 图层表。

7. 如果日志提示 OpenProcess 或权限失败，请关闭软件，用管理员身份重新运行 EXE。如果重启过游戏、切换过菜单或重新加载模板，请用正确层数重新导入。

说明

- JSON 生成使用自带的 GPU/OpenCL 生成器，请保持显卡驱动正常。
- FH6 地址只对当前游戏进程和当前编辑器状态有效。
- 如果软件找不到安全模板，请确认编辑器仍然打开、模板已经 ungroup、层数填写完全正确。
""",
    },
    "ko": {
        "title": app_title(),
        "subtitle": "geometry JSON을 생성하고 Forza Horizon 비닐 그룹 편집기로 가져옵니다.",
        "header_kicker": "FORZA PAINTER 1.6.X",
        "header_audit": "실험판",
        "language": "언어",
        "process": "게임 프로세스",
        "refresh": "새로고침",
        "generate_tab": "JSON 생성",
        "import_final_tab": "Final JSON 가져오기",
        "import_final_tab_hint": "이 앱에서 생성한 최종 geometry JSON(사각형·회전 타원)을 가져옵니다. 생성 실행 폴더를 고르거나 JSON을 직접 추가한 뒤 그룹 해제된 FH6 템플릿에 가져옵니다.",
        "import_final_runs": "생성 실행",
        "import_final_refresh_runs": "실행 목록 새로고침",
        "import_final_run_files": "선택한 실행의 JSON",
        "import_final_use_best": "최적 safe final 사용(실행 내 최대 레이어)",
        "import_final_pick_best": "최적 final 선택",
        "import_final_import": "Final JSON을 FH6에 가져오기",
        "import_handmade_tab": "수작업 JSON 가져오기",
        "handmade_tab": "수작업 JSON",
        "handmade_tab_hint": "실제 FH6 도형 타입 코드가 있는 사용자 JSON을 가져옵니다(생성 사각형/타원 아님). 가져온 뒤 FH6에서 비닐 그룹을 저장하고 다시 불러오세요.",
        "export_game_tab": "게임 JSON보내기",
        "export_game_tab_hint": "FH6에서 열린 비닐 그룹을 수작업/타입코드 JSON으로보냅니다. 가져오기와 동일한 게임 연결 및 템플릿 레이어 수를 사용하세요.",
        "export_game_json": "열린 FH6 그룹을 JSON으로보내기",
        "export_open_folder": "보내기 폴더 열기",
        "handmade_choose_json": "수작업 JSON 선택",
        "handmade_import": "수작업 JSON을 FH6로 가져오기",
        "handmade_export": "열린 FH6 그룹을 JSON으로 보내기",
        "handmade_status_none": "수작업 JSON을 선택하면 지원되는 도형 수를 확인할 수 있습니다.",
        "handmade_status_counts": "도형: 전체 {total} · 지원 {supported} · 미지원 {unsupported}",
        "preview_tab": "이미지 미리보기",
        "preview_tab_hint": "생성 전에 필터와 예상 레이어를 비교하세요. 레이어 수는 추정치이며, 낮을수록 도형이 적을 수 있습니다. 카드를 클릭한 뒤 생성 탭에서 사용합니다.",
        "preview_choose_image": "이미지 선택",
        "preview_use_generate_image": "생성 탭 선택 이미지 사용",
        "preview_apply_generate": "생성 탭 열기",
        "preview_open_folder": "미리보기 캐시 열기",
        "preview_processing": "필터 미리보기 생성 중: {path}",
        "preview_failed": "필터 미리보기 실패: {error}",
        "preview_output_folder": "미리보기 캐시: {path}",
        "preview_estimate": "약 {count} 레이어 (추정)",
        "preview_estimate_unknown": "추정 불가",
        "preview_select_filter": "생성에 사용할 필터 카드를 클릭하세요.",
        "filter_none": "원본",
        "filter_none_hint": "전처리 없이 원본 이미지를 사용합니다. 사진, 부드러운 그라데이션, 머리카락·피부 등 추가 단순화를 원하지 않을 때 적합합니다.",
        "filter_luma": "루마 밴드",
        "filter_luma_hint": "에지를 고려한 루마 밴드로 비슷한 톤을 더 깔끔한 단계로 만듭니다. 로고, 데칼, 애니 평면·단색 영역에 적합합니다.",
        "filter_bilateral": "양방향 스무딩",
        "filter_bilateral_hint": "에지는 유지하면서 노이즈와 질감을 부드럽게 합니다. 사진, 인물, 피부, 머리카락에 적합합니다.",
        "filter_posterize": "포스터라이즈",
        "filter_posterize_hint": "이미지의 색 단계 수를 줄입니다. 스타일 아트, 포스터, 제한 팔레트 디자인에 적합합니다.",
        "filter_clahe": "CLAHE 대비",
        "filter_clahe_hint": "국부 대비를 높여 어둡거나 밋밋한 영역을 더 잘 보이게 합니다. 노출 부족·안개·저대비 원본에 적합합니다.",
        "filter_smooth": "약한 블러",
        "filter_smooth_hint": "가벼운 가우시안 블러로 미세 디테일과 JPEG 아티팩트를 완화합니다. 노이즈 많은 스크린샷·JPEG에 적합합니다.",
        "filter_cel_soft": "소프트 셀 셰이딩",
        "filter_cel_soft_hint": "윤곽선이 더 부드럽고 채움이 자연스러운 코믹/셀 스타일입니다. 애니·스타일 아트에 잘 맞습니다.",
        "filter_cel_heavy": "헤비 잉크 셀 셰이딩",
        "filter_cel_heavy_hint": "검은 잉크 라인과 평면 음영을 강하게 적용해 Borderlands 같은 강한 코믹 느낌을 냅니다.",
        "preprocess_filter": "전처리 필터",
        "preprocess_filter_hint": "GPU 생성기 실행 전 이미지를 어떻게 단순화할지 선택합니다. 이미지 미리보기에서 비교하세요. 추정 레이어가 낮을수록 도형이 적을 수 있습니다.",
        "generate_source_original": "원본",
        "generate_source_filtered": "필터 적용",
        "generate_result_plain": "필터 없음",
        "generate_result_filtered": "{filter} 사용",
        "json_tag_bilateral": "[양방향]",
        "json_tag_posterize": "[포스터]",
        "json_tag_clahe": "[CLAHE]",
        "json_tag_smooth": "[블러]",
        "json_tag_cel_soft": "[소프트 셀]",
        "json_tag_cel_heavy": "[헤비 잉크]",
        "luma_before": "원본",
        "luma_after": "루마 밴드 후",
        "luma_before_hint": "이미지를 선택하면 원본이 여기에 표시됩니다.",
        "luma_after_hint": "루마 밴드 결과가 여기에 표시됩니다.",
        "luma_output_folder": "출력 폴더: {path}",
        "luma_processing": "처리 중: {path}",
        "luma_saved": "루마 밴드 이미지 저장됨: {path}",
        "luma_failed": "루마 밴드 실패: {error}",
        "tools_tab": "도구",
        "tools_tab_hint": "실험용 크리에이티브 유틸리티(Forza Painter 1.6.X). JSON 생성과 분리됩니다. 각 도구는 독립 패널이며, 생성·텍스트 비닐 워크플로에는 영향을 주지 않습니다.",
        "tools_panel_color_picker": "색상 선택기",
        "tools_panel_bg_remove": "배경 제거",
        "tools_panel_fh6": "FH6 진단",
        "tools_color_picker_hint": "임의 이미지 파일에서 색을 샘플링합니다. 캔버스를 클릭해 색을 고정하고, Shift+휠로 샘플 크기를 조절합니다. Forza H/S/B는 Bang 변환기와 일치합니다.",
        "tools_color_browse": "이미지 찾기",
        "tools_color_no_image": "색을 샘플링할 이미지를 선택하세요.",
        "tools_color_file_filter": "이미지 파일",
        "tools_bg_remove_hint": "배경 제거 방법이 여러 가지입니다. 온라인 도구는 빠른보내기에, 데스크톱 앱은 비닐 준비에 더 세밀한 제어가 가능합니다.",
        "tools_bg_online_title": "온라인(빠른보내기)",
        "tools_bg_desktop_title": "데스크톱(세밀한 제어)",
        "tools_bg_iloveimg_title": "iloveimg — 배경 제거",
        "tools_bg_iloveimg_desc": "무료 브라우저 워크플로: 업로드, 배경 제거, PNG 다운로드. 데칼·로고에 적합합니다.",
        "tools_bg_pixlr_title": "Pixlr — 배경 제거",
        "tools_bg_pixlr_desc": "배경 제거와 간단한 보정이 가능한 브라우저 편집기. 컷아웃 후 가벼운 수정에 유용합니다.",
        "tools_bg_gimp_title": "GIMP",
        "tools_bg_gimp_desc": "무료 데스크톱 편집기. 색 선택/퍼지 선택과 레이어 마스크로 복잡한 아트를 정밀하게 처리합니다.",
        "tools_bg_mspaint_title": "Microsoft 그림판(Windows 11)",
        "tools_bg_mspaint_desc": "내장 배경 제거(이미지 메뉴). 단순 피사체·스크린샷·플랫 아트에 빠릅니다.",
        "tools_bg_inkscape_title": "Inkscape",
        "tools_bg_inkscape_desc": "벡터 친화: 비트맵 추적, 경로 편집, 깨끗한 PNG/SVG보내기로 비닐 참고용 제작.",
        "tools_badge_online": "온라인",
        "tools_badge_desktop": "데스크톱",
        "tools_open_link": "브라우저에서 열기",
        "tools_open_website": "웹사이트 열기",
        "tools_open_guide": "가이드 열기",
        "tools_open_paint": "그림판 열기",
        "tools_fh6_hint": "메모리 진단 및 FH6 세션 도구입니다. Forza Horizon 6이 실행 중이고 유효한 세션이 필요합니다.",
        "tutorial_tab": "튜토리얼",
        "acknowledgements_tab": "감사의 글",
        "colors_values": "색상 값",
        "colors_pixel_size": "샘플 크기(px)",
        "colors_click_hint": "이미지를 클릭해 색을 선택하세요.",
        "colors_hex": "Hex",
        "colors_rgb": "RGB",
        "colors_hsl": "HSL",
        "colors_hsb": "HSB",
        "colors_forza": "Forza H / S / B",
        "colors_copy_hex": "Hex 복사",
        "colors_copy_forza": "Forza 복사",
        "colors_open_bang": "Bang 변환기 열기",
        "colors_copied": "클립보드에 복사했습니다.",
        "colors_saved": "색상 저장됨 {hex}",
        "colors_saved_history": "저장된 색상 (클릭하여 불러오기)",
        "monitor_tab": "리소스 모니터",
        "monitor_why_title": "왜 있나요?",
        "images": "이미지",
        "add_images": "이미지 추가",
        "remove_image": "선택한 이미지 제거",
        "quality": "품질 프로필",
        "import_preset": "프리셋 가져오기",
        "open_preset_folder": "프리셋 폴더 열기",
        "custom_settings": "사용자 설정 사용",
        "custom_layers": "출력 레이어",
        "custom_resolution": "최대 해상도",
        "custom_random": "무작위 샘플",
        "custom_mutated": "변형 샘플",
        "custom_save_at": "체크포인트 저장",
        "preprocess_mode": "전처리 모드",
        "luma_prep": "루마 프렙 — 평면 영역은 더 깔끔, 미세 디테일은 약해질 수 있음",
        "luma_prep_hint": "로고·데칼·단색 영역에 적합. 부드러운 gradient, 머리카락, 피부, 캐릭터 디테일은 끄세요.",
        "generate_compare_source": "소스 전처리",
        "generate_compare_result": "생성 결과 비교",
        "generate_without_luma": "루마 프렙 없음",
        "generate_with_luma": "루마 프렙 사용",
        "generate_layers_count": "{count} 레이어",
        "generate_no_checkpoint": "checkpoint 없음",
        "luma_status_none": "이미지를 선택하면 루마 프렙 적용 여부와 JSON checkpoint를 확인할 수 있습니다.",
        "luma_status_next_on": "다음 생성: 루마 프렙 켜짐(루마 밴드 소스 사용).",
        "luma_status_next_off": "다음 생성: 루마 프렙 꺼짐(원본 이미지 사용).",
        "luma_status_file_ready": "루마 밴드 파일: 준비됨 ({name}).",
        "luma_status_file_missing": "루마 밴드 파일: 아직 없음(Luma Prep 켜고 생성하면 생성됩니다).",
        "luma_status_checkpoints": "Checkpoint — 일반: {plain} · Luma: {luma}.",
        "luma_status_last_run_on": "이 이미지의 마지막 완료 생성은 루마 프렙을 사용했습니다.",
        "luma_status_last_run_off": "이 이미지의 마지막 완료 생성은 루마 프렙을 사용하지 않았습니다.",
        "luma_status_last_run_unknown": "이 이미지에 대한 완료된 생성 기록이 없습니다.",
        "luma_column_next": " ← 다음",
        "luma_column_last": "(마지막)",
        "luma_image_tag_ready": "luma 파일 있음",
        "luma_image_tag_missing": "luma 파일 없음",
        "json_tag_luma": "[Luma]",
        "json_tag_plain": "[일반]",
        "generate_log_pipeline_luma": "루마 프렙으로 생성 중(입력: {path})",
        "generate_log_pipeline_plain": "루마 프렙 없이 생성 중(원본 이미지)",
        "generate_log_output_luma": "JSON 생성됨(루마 프렙): {path}",
        "generate_log_output_plain": "JSON 생성됨(루마 프렙 없음): {path}",
        "generate_select_image": "이미지를 선택하면 전처리와 결과를 비교할 수 있습니다.",
        "save_custom_preset": "프리셋으로 저장",
        "custom_panel_title": "사용자 설정",
        "custom_panel_hint": "선택한 프리셋 값이 자동으로 채워집니다. 생성 전에 값을 바꾸려면 사용자 설정을 켜세요.",
        "generate_step_image": "1단계 - 이미지 선택",
        "generate_step_image_hint": "PNG/JPG/BMP 이미지를 추가하세요. 생성된 JSON은 원본 이미지 옆에 저장됩니다.",
        "generate_step_image_credit": "본인이 만들지 않은 이미지나 아트를 사용하는 경우, 가능한 한 원작자를 표기해 주세요.",
        "preview_image_added_to_generate": "생성 이미지 목록에 추가됨: {name}",
        "preview_image_already_on_generate": "이미 생성 이미지 목록에 있음: {name}",
        "generate_step_quality": "2단계 - 품질 선택",
        "generate_step_quality_hint": "빠른 프로필은 시간이 적게 걸립니다. 느린 프로필은 GPU 시간을 더 쓰지만 보통 더 깔끔합니다.",
        "generate_step_run": "3단계 - 생성",
        "generate_step_run_hint": "한 번 클릭한 뒤 기다리세요. 진행 상황은 로그에 표시되고, 생성된 JSON은 가져오기 페이지에 자동으로 추가됩니다.",
        "scroll_hint": "이미지를 추가하고 프리셋을 선택한 뒤, 필요하면 사용자 설정을 조정하세요.",
        "start_generate": "현재 설정으로 생성",
        "stop_generate": "현재 생성 중지",
        "open_output": "출력 폴더 열기",
        "preview": "미리보기",
        "preview_hint": "이미지나 JSON을 선택하면 여기에 미리보기가 표시됩니다.",
        "preview_unavailable": "미리보기를 사용할 수 없습니다. 선택 미리보기 의존성을 설치하거나, 미리보기 없이 계속 진행하세요.",
        "logs": "로그",
        "export_logs": "자세한 로그 내보내기",
        "progress": "진행 상황",
        "json_files": "Geometry JSON 파일",
        "add_json": "JSON 추가",
        "remove_json": "선택한 JSON 제거",
        "use_outputs": "생성된 JSON 사용",
        "step_game": "1단계 - 게임",
        "step_game_hint": "FH6를 실행하고 비닐 그룹 편집기를 연 뒤, 그룹 해제된 구체 템플릿을 불러오고 프로세스 목록을 새로고침하세요.",
        "step_template": "2단계 - 템플릿",
        "step_template_hint": "현재 게임 안 템플릿에 표시된 정확한 레이어 수를 입력하세요.",
        "step_json": "3단계 - JSON",
        "step_json_hint": "이 앱에서 생성한 JSON을 사용하거나 geometry JSON을 직접 추가하세요.",
        "step_import": "4단계 - 가져오기",
        "step_import_hint": "가져오기를 한 번만 클릭하세요. 앱이 FH6 레이어 테이블을 안전하게 찾은 뒤 디자인을 씁니다.",
        "advanced_options": "고급 옵션",
        "show_advanced": "고급 옵션 표시",
        "hide_advanced": "고급 옵션 숨기기",
        "import_preview": "선택한 JSON 미리보기",
        "game_profile": "게임 프로필",
        "pid": "PID",
        "layer_count": "템플릿 레이어 수",
        "layer_count_required": "템플릿 레이어 수를 입력하세요. 게임에 표시된 정확한 레이어 수를 입력하십시오.",
        "easy_import": "간편 가져오기",
        "easy_import_hint": "FH6에서는 주소를 비워두세요. 앱이 현재 세션을 재사용하거나 가져오기 전에 자동으로 찾습니다.",
        "manual_count": "레이어 수 주소",
        "manual_table": "레이어 테이블 주소",
        "auto_locate": "FH6 자동 찾기",
        "import_json": "JSON 가져오기",
        "handmade_section": "수작업 / 범용 JSON (FH6)",
        "handmade_section_hint": "실제 FH6 도형 타입 코드가 있는 JSON용(생성된 사각형/타원만이 아님).보내기는 열린 비닐 그룹을 읽고, 가져오기는 저장 안전 필드만 씁니다. 가져온 뒤 FH6에서 저장 후 다시 불러오세요.",
        "export_typecode_json": "열린 그룹을 JSON으로 보내기",
        "typecode_trim_after_import": "가져온 뒤 비닐 그룹 레이어 수를 실제 가져온 수로 자르기",
        "typecode_allow_unknown": "실험적 도형 코드 허용(고급)",
        "typecode_export_done": "{count}개 레이어를 {path}에보냈습니다",
        "typecode_export_failed": "보내기 실패: {error}",
        "typecode_import_mode": "수작업/범용 가져오기 사용: {name}",
        "typecode_import_done": "수작업 가져오기 완료: {name}",
        "typecode_trim_done": "비닐 그룹 레이어 수를 {count}(으)로 잘랐습니다",
        "typecode_trim_failed": "자르기 실패: {error}",
        "typecode_missing_group": "자르기/보내기용 FH6 그룹 주소를 찾지 못했습니다. 자동 위치 찾기를 다시 실행하세요.",
        "diagnose": "진단",
        "save_snapshot": "레이어 수 스냅샷 저장",
        "compare_snapshot": "스냅샷 비교",
        "snapshot_count": "스냅샷 레이어 수",
        "current_count": "현재 레이어 수",
        "inspect_table": "테이블 검사",
        "table_address": "후보 테이블",
        "admin_note": "가져오기는 관리자 권한이 필요합니다. OpenProcess 실패가 보이면 이 앱을 관리자 권한으로 실행하세요.",
        "no_game": "지원되는 게임 프로세스를 찾지 못했습니다",
        "ready": "준비됨",
        "running": "실행 중",
        "done": "완료",
        "failed": "실패",
        "stopped": "중지됨",
        "no_generation_running": "현재 실행 중인 생성 작업이 없습니다.",
        "stopping_generation": "현재 생성을 중지하는 중...",
        "generation_stopped": "생성이 중지되었습니다.",
        "generator_recycled_layers": "생성기가 {max_layer}/{total} 이후 완전히 가려진 이전 레이어를 재활용했습니다. 정상 동작이며 처음부터 다시 시작한 것이 아닙니다.",
        "existing_checkpoints_found": "{image}의 기존 checkpoint JSON {count}개를 찾았습니다. 가장 적합한 파일을 가져오기 목록에 추가했습니다.",
        "checkpoint_available_after_failure": "이번 생성이 실패/중지되었지만 저장된 checkpoint를 사용할 수 있습니다: {path}",
        "imported_presets": "{count}개 프리셋 파일을 가져왔습니다.",
        "saved_preset": "프리셋을 저장했습니다: {path}",
        "no_image_selected": "선택한 이미지가 없습니다.",
        "no_json_selected": "선택한 JSON이 없습니다.",
        "cannot_resume_checkpoint": "기존 checkpoint는 재사용/가져오기할 수 있지만 현재 GPU 생성기는 진정한 checkpoint 이어하기를 아직 지원하지 않습니다.",
        "locating": "현재 FH6 템플릿을 찾는 중...",
        "locating_wait": "최대 5분 정도 걸릴 수 있습니다. FH6를 Vinyl Group Editor에 그대로 두고 메뉴를 전환하지 말고 기다려 주세요.",
        "located": "FH6 템플릿을 찾고 검증했습니다.",
        "importing": "JSON을 FH6로 가져오는 중...",
        "json_too_small": "선택한 JSON의 그릴 수 있는 레이어 수가 템플릿 사용 가능 용량보다 훨씬 적습니다. 가져오면 흐릿해 보이므로 더 높은 레이어 JSON을 선택하세요.",
        "json_needs_more_template_layers": "FH는 커버 저장과 적용 범위를 올바르게 처리하려면 경계 레이어 4개가 필요합니다. JSON의 그릴 수 있는 레이어 수 + 4 이상인 템플릿을 사용하세요.",
        "safe_stop": "안전한 FH6 템플릿을 찾지 못해 쓰기 전에 중지했습니다.",
        "update_available_title": "새 버전 사용 가능",
        "update_available_message": "새 버전이 있습니다.\n\n현재: v{current}\n최신: v{latest}",
        "update_open_page": "업데이트 페이지 열기",
        "update_later": "나중에",
        "update_check_failed_title": "업데이트 확인 실패",
        "update_check_failed_message": "업데이트를 확인하지 못했습니다. 현재 버전을 계속 사용할 수 있습니다.\n\n{error}",
        "update_current": "현재 최신 버전입니다.",
        "changelog": "변경 내역",
        "runtime_folder": "런타임/캐시 폴더",
        "open_runtime_folder": "런타임 폴더 열기",
        "runtime_location": "런타임/캐시 파일은 앱 옆에 저장됩니다: {runtime}. FH6 probe cache: {probe}.",
        "resource_monitor_title": "리소스 모니터",
        "resource_cpu": "CPU",
        "resource_gpu": "GPU",
        "resource_temp_nominal": "온도 측정값 정상.",
        "resource_unavailable": "사용 불가",
        "resource_heat_warning_banner": "/// 경고! 심각한 고온이 감지되었습니다! ///",
        "resource_heat_critical_banner": "/// 온도 위험. 프로그램을 중지하세요. ///",
        "resource_heat_log_warning": "/// 경고! 심각한 고온이 감지되었습니다! /// (최고 {temp}°C)",
        "resource_heat_log_critical": "/// 온도 위험. 프로그램을 중지하세요. /// (최고 {temp}°C)",
        "tutorial": """초보자용 작업 순서

1. GitHub Releases에서 단일 EXE를 다운로드해 바로 실행하세요. 일반 사용자는 Python, .venv, bat 파일이 필요 없습니다.

2. Forza Horizon 6를 실행하고 Create Vinyl Group / Vinyl Group Editor로 들어갑니다.

3. 많은 단순 sphere 레이어로 만든 템플릿을 불러오거나 새로 만드세요. 500개 이상의 레이어를 권장합니다. 가져오기 전에는 반드시 템플릿을 ungroup해야 합니다.

4. 이 앱의 JSON 생성 페이지에서 PNG/JPG/BMP 이미지를 추가하고 품질 프로필을 선택한 뒤 생성을 시작하세요.

5. 가져오기 페이지를 여세요. 생성된 JSON을 추가하거나 생성된 JSON 사용을 클릭하세요. 게임 프로필은 Forza Horizon 6로 둡니다.

6. 현재 게임에 불러온 템플릿의 실제 레이어 수를 입력하세요. FH6에서는 보통 메모리 주소를 직접 입력할 필요가 없습니다. JSON 가져오기를 클릭하면 필요할 때 앱이 현재 FH6 레이어 테이블을 자동으로 찾습니다.

7. OpenProcess 또는 권한 오류가 보이면 앱을 닫고 EXE를 관리자 권한으로 다시 실행하세요. 게임을 다시 시작했거나 메뉴를 바꿨다면 정확한 레이어 수로 다시 가져오세요.

참고

- JSON 생성은 포함된 GPU/OpenCL 생성기를 사용하므로 그래픽 드라이버를 최신 상태로 유지하세요.
- 현재 FH6 주소는 현재 게임 프로세스와 현재 편집기 상태에서만 유효합니다.
- 앱이 안전한 템플릿을 찾지 못하면 편집기가 열려 있는지, 템플릿이 ungroup 상태인지, 레이어 수가 정확한지 확인하세요.
""",
    },
    "zh-tw": {
        "title": app_title(),
        "subtitle": "產生 geometry JSON 並匯入 Forza Horizon 貼紙編輯器。",
        "language": "語言",
        "layer_count": "模板圖層數",
        "layer_count_required": "請填寫模板圖層數。輸入遊戲中顯示的精確圖層數。",
        "step_template": "第 2 步 - 模板",
        "step_template_hint": "填寫遊戲裡目前模板顯示的真實圖層數。",
        "import_json": "匯入 JSON",
        "ready": "就緒",
        "running": "執行中",
        "done": "完成",
        "failed": "失敗",
        "stopped": "已停止",
        "locating": "正在安全定位 FH6 圖層表…請保持 Vinyl Group Editor 開啟，勿切換選單。",
        "located": "已定位目前 FH6 圖層表。",
    },
}

TEXT = apply_text_patches(TEXT, app_title_text=app_title())
TEXT = merge_japanese_text(TEXT, app_title_text=app_title())
TEXT = merge_korean_patch(TEXT)


def ensure_dirs():
    PROBE_DIR.mkdir(parents=True, exist_ok=True)


def tr(lang, key):
    return tr_text(TEXT, lang, key)


def version_key(value):
    parts = []
    for part in re.findall(r"\d+", str(value)):
        parts.append(int(part))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def parse_version_source(source):
    match = re.search(r'__version__\s*=\s*"([^"]+)"', source or "")
    if not match:
        raise ValueError("remote version file did not contain __version__")
    return match.group(1).strip()


def is_windows_admin():
    if os.name != "nt":
        return True
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def ensure_elevated_or_exit():
    if os.name != "nt" or is_windows_admin():
        return
    if os.environ.get("FORZA_PAINTER_NO_ELEVATE") == "1":
        return
    params = subprocess.list2cmdline(sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 0)
    raise SystemExit(0)


def fetch_text_url(url, timeout=UPDATE_CHECK_TIMEOUT_SECONDS, accept="text/plain,*/*"):
    validate_fetch_url(url)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": f"{APP_DISPLAY_NAME}/{__version__}",
            "Accept": accept,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(256 * 1024)
    return data.decode("utf-8", errors="replace")


def fetch_latest_release_version(timeout=UPDATE_CHECK_TIMEOUT_SECONDS):
    validate_fetch_url(GITHUB_RELEASES_API)
    request = urllib.request.Request(
        GITHUB_RELEASES_API,
        headers={
            "User-Agent": f"{APP_DISPLAY_NAME}/{__version__}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read(256 * 1024).decode("utf-8", errors="replace"))
    tag = str(payload.get("tag_name", "")).strip()
    if tag.lower().startswith("v"):
        tag = tag[1:]
    if not tag:
        raise ValueError("GitHub release response did not include tag_name")
    return tag


def extract_changelog_section(changelog, version):
    text = (changelog or "").strip()
    if not text:
        return ""
    heading = re.compile(rf"^(#{{1,6}})\s+v?{re.escape(str(version))}\b.*$", re.I | re.M)
    match = heading.search(text)
    if not match:
        return text[:6000]
    next_heading = re.compile(rf"^{re.escape(match.group(1))}\s+\S+", re.M)
    next_match = next_heading.search(text, match.end())
    end = next_match.start() if next_match else len(text)
    return text[match.start():end].strip()[:6000]


def helper_command(helper_name):
    if getattr(sys, "frozen", False):
        return [sys.executable, "--helper", helper_name]
    return [sys.executable, APP_DIR / f"{helper_name}.py"]


def run_embedded_helper(helper_name, args):
    if helper_name == "fh6_probe":
        import fh6_probe

        previous_argv = sys.argv
        try:
            sys.argv = ["fh6_probe.py", *args]
            return fh6_probe.main()
        finally:
            sys.argv = previous_argv
    if helper_name == "main":
        import main as importer_main

        return importer_main.main(["main.py", *args])
    if helper_name == "fh6_import_typecode_json":
        import fh6_import_typecode_json

        previous_argv = sys.argv
        try:
            sys.argv = ["fh6_import_typecode_json.py", *args]
            fh6_import_typecode_json.main()
            return 0
        finally:
            sys.argv = previous_argv
    if helper_name == "fh6_export_typecode_json":
        import fh6_export_typecode_json

        previous_argv = sys.argv
        try:
            sys.argv = ["fh6_export_typecode_json.py", *args]
            fh6_export_typecode_json.main()
            return 0
        finally:
            sys.argv = previous_argv
    if helper_name == "fh6_trim_group_count":
        import fh6_trim_group_count

        previous_argv = sys.argv
        try:
            sys.argv = ["fh6_trim_group_count.py", *args]
            fh6_trim_group_count.main()
            return 0
        finally:
            sys.argv = previous_argv
    raise SystemExit(f"Unknown helper: {helper_name}")


def game_processes():
    names = {name.lower(): key for key, profile in PROFILES.items() for name in profile.process_names}
    found = []
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            name = proc.info.get("name") or ""
            key = names.get(name.lower())
            if key:
                found.append({
                    "pid": proc.info["pid"],
                    "name": name,
                    "profile": key,
                    "label": f"{name} pid {proc.info['pid']}",
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def parse_hex_or_empty(value):
    value = str(value or "").strip()
    return value or None


def load_session_location():
    if not SESSION_PATH.exists():
        return None
    try:
        return json.loads(SESSION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def clear_session_location():
    try:
        SESSION_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def session_pid_is_live(session, game):
    try:
        pid = int(session.get("pid", -1))
        proc = psutil.Process(pid)
        profile = PROFILES.get(game)
        return bool(profile and proc.name().lower() in [name.lower() for name in profile.process_names])
    except (psutil.Error, TypeError, ValueError):
        return False


def session_matches_current_import(session, game, pid, layer_count):
    if not session:
        return False
    ok, _reason = validate_fh6_session(session)
    if not ok:
        return False
    if str(session.get("layer_count", "")) != str(layer_count):
        return False
    if not session_pid_is_live(session, game):
        return False
    try:
        session_pid = int(session.get("pid", -1))
        return not pid or int(pid) == session_pid
    except (TypeError, ValueError):
        return False


def preview_size_tuple(max_size=None):
    if max_size is None:
        return PREVIEW_MAX, PREVIEW_MAX
    if isinstance(max_size, (tuple, list)):
        if len(max_size) >= 2:
            width, height = max_size[0], max_size[1]
        elif len(max_size) == 1:
            width = height = max_size[0]
        else:
            width = height = PREVIEW_MAX
    else:
        width = height = max_size
    try:
        width = int(width)
        height = int(height)
    except (TypeError, ValueError):
        width = height = PREVIEW_MAX
    return max(1, width), max(1, height)


def preview_scale(width, height, max_size=None):
    max_w, max_h = preview_size_tuple(max_size)
    if width <= 0 or height <= 0:
        return 1.0
    return min(max_w / width, max_h / height, 1.0)


def resize_keep_aspect(image, max_size=None):
    loaded = load_cv2()
    if not loaded:
        return image
    cv2, _np = loaded
    height, width = image.shape[:2]
    scale = preview_scale(width, height, max_size)
    if scale < 1.0:
        resized_w = max(1, int(round(width * scale)))
        resized_h = max(1, int(round(height * scale)))
        image = cv2.resize(image, (resized_w, resized_h), interpolation=cv2.INTER_AREA)
    return image


def image_to_photo(image, max_size=None):
    loaded = load_cv2()
    if not loaded:
        return None
    cv2, _np = loaded
    image = resize_keep_aspect(image, max_size)
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        return None
    return encoded.tobytes()


def pil_to_photo(image, max_size=None):
    loaded = load_pillow()
    if not loaded:
        return None
    Image, _ImageDraw = loaded
    image = image.convert("RGB")
    image.thumbnail(preview_size_tuple(max_size), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def render_source_image(path, max_size=None):
    loaded = load_cv2()
    if loaded:
        cv2, _np = loaded
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None:
            return image_to_photo(image, max_size)
    loaded = load_pillow()
    if not loaded:
        return None
    Image, _ImageDraw = loaded
    try:
        with Image.open(path) as image:
            return pil_to_photo(image, max_size)
    except Exception:
        return None


def render_geometry_json(path, max_size=None):
    if is_typecode_geometry_json(path):
        typecode_preview = _render_typecode_geometry_json_pillow(path, max_size)
        if typecode_preview:
            return typecode_preview
    pillow_preview = render_geometry_json_pillow(path, max_size)
    if pillow_preview:
        return pillow_preview
    loaded = load_cv2()
    if not loaded:
        return None
    cv2, np = loaded
    try:
        data = load_normalized_geometry(path)
        shapes = data["shapes"]
        image_w, image_h = [int(v) for v in shapes[0]["data"][2:]]
        bg_r, bg_g, bg_b, bg_a = [int(v) for v in shapes[0]["color"]]
        scale = preview_scale(image_w, image_h, max_size)
        preview_w = max(1, int(round(image_w * scale)))
        preview_h = max(1, int(round(image_h * scale)))
        preview = np.zeros((preview_h, preview_w, 3), np.uint8)
        if bg_a > 0:
            preview[:, :] = (bg_b, bg_g, bg_r)
        else:
            preview[:, :] = (38, 38, 38)
            tile = max(8, int(round(32 * scale)))
            for y in range(0, preview_h, tile):
                for x in range(0, preview_w, tile):
                    if ((x // tile) + (y // tile)) % 2 == 0:
                        preview[y:y + tile, x:x + tile] = (58, 58, 58)
        for shape in shapes[1:]:
            color = [int(v) for v in shape.get("color", [])]
            if len(color) == 4 and color[3] <= 0:
                continue
            r, g, b, _a = color
            shape_type = int(shape.get("type", 0))
            if shape_type == ROTATED_ELLIPSE:
                x, y, w, h, rot_deg = shape["data"]
                center = (int(round(float(x) * scale)), int(round(float(y) * scale)))
                axes = (max(1, int(round(float(h) * scale))), max(1, int(round(float(w) * scale))))
                preview = cv2.ellipse(preview, center, axes, -90 + float(rot_deg), 0.0, 360.0, (b, g, r), thickness=-1)
            elif shape_type == RECTANGLE:
                x, y, w, h = shape["data"]
                x = float(x)
                y = float(y)
                w = float(w)
                h = float(h)
                x0 = int(round((x - w / 2) * scale))
                y0 = int(round((y - h / 2) * scale))
                x1 = int(round((x + w / 2) * scale))
                y1 = int(round((y + h / 2) * scale))
                preview = cv2.rectangle(preview, (x0, y0), (x1, y1), (b, g, r), thickness=-1)
        return image_to_photo(preview, max_size)
    except Exception:
        return None


def render_geometry_json_pillow(path, max_size=None):
    if is_typecode_geometry_json(path):
        return _render_typecode_geometry_json_pillow(path, max_size)
    loaded = load_pillow()
    if not loaded:
        return None
    Image, ImageDraw = loaded
    try:
        data = load_normalized_geometry(path)
        shapes = data["shapes"]
        image_w, image_h = [int(v) for v in shapes[0]["data"][2:]]
        bg_r, bg_g, bg_b, bg_a = [int(v) for v in shapes[0]["color"]]
        scale = preview_scale(image_w, image_h, max_size)
        preview_w = max(1, int(round(image_w * scale)))
        preview_h = max(1, int(round(image_h * scale)))
        if bg_a > 0:
            preview = Image.new("RGB", (preview_w, preview_h), (bg_r, bg_g, bg_b))
        else:
            preview = Image.new("RGB", (preview_w, preview_h), (38, 38, 38))
            draw_bg = ImageDraw.Draw(preview)
            tile = max(8, int(round(32 * scale)))
            for y in range(0, preview_h, tile):
                for x in range(0, preview_w, tile):
                    if ((x // tile) + (y // tile)) % 2 == 0:
                        draw_bg.rectangle((x, y, min(preview_w, x + tile), min(preview_h, y + tile)), fill=(58, 58, 58))
        draw = ImageDraw.Draw(preview)
        for shape in shapes[1:]:
            color = [int(v) for v in shape.get("color", [])]
            if len(color) == 4 and color[3] <= 0:
                continue
            r, g, b, _a = color
            shape_type = int(shape.get("type", 0))
            if shape_type == RECTANGLE:
                x, y, w, h = [float(v) for v in shape["data"]]
                x0 = int(round((x - w / 2) * scale))
                y0 = int(round((y - h / 2) * scale))
                x1 = int(round((x + w / 2) * scale))
                y1 = int(round((y + h / 2) * scale))
                draw.rectangle((x0, y0, x1, y1), fill=(r, g, b))
            elif shape_type == ROTATED_ELLIPSE:
                x, y, w, h, rot_deg = [float(v) for v in shape["data"]]
                draw_preview_ellipse_pillow(preview, x, y, w, h, rot_deg, (r, g, b), scale)
        return pil_to_photo(preview)
    except Exception:
        return None


def draw_preview_ellipse_pillow(image, x, y, w, h, rot_deg, color, scale):
    # Match the historical OpenCV preview path used before the one-file EXE:
    # cv2.ellipse(..., axes=(h, w), angle=-90+rot).
    width, height = image.size
    cx = float(x) * scale
    cy = float(y) * scale
    rx = max(float(h) * scale, 1.0)
    ry = max(float(w) * scale, 1.0)
    theta = (-90.0 + float(rot_deg)) * (math.pi / 180.0)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    inv_rx2 = 1.0 / (rx * rx)
    inv_ry2 = 1.0 / (ry * ry)
    extent_x = math.sqrt(rx * rx * cos_t * cos_t + ry * ry * sin_t * sin_t)
    extent_y = math.sqrt(rx * rx * sin_t * sin_t + ry * ry * cos_t * cos_t)
    x_min = max(0, int(math.floor(cx - extent_x - 1)))
    x_max = min(width - 1, int(math.ceil(cx + extent_x + 1)))
    y_min = max(0, int(math.floor(cy - extent_y - 1)))
    y_max = min(height - 1, int(math.ceil(cy + extent_y + 1)))
    if x_min > x_max or y_min > y_max:
        return
    pixels = image.load()
    r, g, b = color
    for yy in range(y_min, y_max + 1):
        dy = (float(yy) + 0.5) - cy
        for xx in range(x_min, x_max + 1):
            dx = (float(xx) + 0.5) - cx
            xr = dx * cos_t + dy * sin_t
            yr = -dx * sin_t + dy * cos_t
            if xr * xr * inv_rx2 + yr * yr * inv_ry2 <= 1.0:
                pixels[xx, yy] = (r, g, b)


def _rotated_rect_points(x, y, w, h, rot_deg, scale):
    cx = float(x) * scale
    cy = float(y) * scale
    hw = max(1.0, float(w) * scale / 2.0)
    hh = max(1.0, float(h) * scale / 2.0)
    theta = float(rot_deg) * (math.pi / 180.0)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
    points = []
    for dx, dy in corners:
        px = cx + dx * cos_t - dy * sin_t
        py = cy + dx * sin_t + dy * cos_t
        points.append((int(round(px)), int(round(py))))
    return points


def _render_typecode_geometry_json_pillow(path, max_size=None):
    loaded = load_pillow()
    if not loaded:
        return None
    Image, ImageDraw = loaded
    try:
        shapes, skipped = load_typecode_shapes(path, allow_unknown_low_byte=True)
        if not shapes:
            return None
        xs = [float(item["x"]) for item in shapes]
        ys = [float(item["y"]) for item in shapes]
        sxs = [max(1.0, float(item["sx"])) for item in shapes]
        sys_ = [max(1.0, float(item["sy"])) for item in shapes]
        min_x = min(x - sx / 2.0 for x, sx in zip(xs, sxs))
        max_x = max(x + sx / 2.0 for x, sx in zip(xs, sxs))
        min_y = min(y - sy / 2.0 for y, sy in zip(ys, sys_))
        max_y = max(y + sy / 2.0 for y, sy in zip(ys, sys_))
        pad = 18.0
        width = max(1, int(round((max_x - min_x) + pad * 2.0)))
        height = max(1, int(round((max_y - min_y) + pad * 2.0)))
        max_w, max_h = preview_size_tuple(max_size)
        scale = min(max_w / max(1.0, width), max_h / max(1.0, height), 1.0)
        preview_w = max(1, int(round(width * scale)))
        preview_h = max(1, int(round(height * scale)))
        preview = Image.new("RGB", (preview_w, preview_h), (38, 38, 38))
        draw_bg = ImageDraw.Draw(preview)
        tile = max(8, int(round(24 * scale)))
        for y in range(0, preview_h, tile):
            for x in range(0, preview_w, tile):
                if ((x // tile) + (y // tile)) % 2 == 0:
                    draw_bg.rectangle((x, y, min(preview_w, x + tile), min(preview_h, y + tile)), fill=(58, 58, 58))
        draw = ImageDraw.Draw(preview)
        for item in shapes:
            code = int(item.get("type_code", 0))
            x = (float(item["x"]) - min_x + pad) * scale
            y = (float(item["y"]) - min_y + pad) * scale
            sx = max(1.0, float(item["sx"])) * scale
            sy = max(1.0, float(item["sy"])) * scale
            rot = float(item.get("rotation", 0.0))
            color = tuple(int(v) for v in item.get("color", (255, 255, 255, 255))[:3])
            if code in (1048678, 1048712):
                draw_preview_ellipse_pillow(preview, x, y, sx / max(scale, 1e-6), sy / max(scale, 1e-6), rot, color, scale)
            elif code == 1048677:
                side = min(sx, sy)
                points = _rotated_rect_points(x / max(scale, 1e-6), y / max(scale, 1e-6), side / max(scale, 1e-6), side / max(scale, 1e-6), rot, scale)
                draw.polygon(points, fill=color)
            elif code == 1048679:
                pts = [(0.0, -sy / 2.0), (sx / 2.0, sy / 2.0), (-sx / 2.0, sy / 2.0)]
                theta = rot * (math.pi / 180.0)
                cos_t = math.cos(theta)
                sin_t = math.sin(theta)
                tri = []
                for dx, dy in pts:
                    px = x + dx * cos_t - dy * sin_t
                    py = y + dx * sin_t + dy * cos_t
                    tri.append((int(round(px)), int(round(py))))
                draw.polygon(tri, fill=color)
            elif code == 1048688:
                # Circle border: draw filled then cut center with background.
                bbox = (int(round(x - sx / 2.0)), int(round(y - sy / 2.0)), int(round(x + sx / 2.0)), int(round(y + sy / 2.0)))
                draw.ellipse(bbox, fill=color)
                inner_scale = 0.72
                inner = (
                    int(round(x - (sx * inner_scale) / 2.0)),
                    int(round(y - (sy * inner_scale) / 2.0)),
                    int(round(x + (sx * inner_scale) / 2.0)),
                    int(round(y + (sy * inner_scale) / 2.0)),
                )
                draw.ellipse(inner, fill=(38, 38, 38))
            else:
                points = _rotated_rect_points(x / max(scale, 1e-6), y / max(scale, 1e-6), sx / max(scale, 1e-6), sy / max(scale, 1e-6), rot, scale)
                draw.polygon(points, fill=color)
        if skipped:
            # Light badge in corner when some shapes are unsupported by importer.
            badge = f"unsupported: {len(skipped)}"
            draw.rectangle((6, 6, 6 + 8 * len(badge), 24), fill=(20, 20, 20))
            draw.text((10, 9), badge, fill=(220, 120, 120))
        return pil_to_photo(preview)
    except Exception:
        return None


class App:
    def __init__(self, initial_images):
        ensure_dirs()
        self.root = Tk()
        self.root.title(app_title())
        self.root.geometry("1420x900")
        self.root.minsize(1180, 780)
        self.root.configure(bg=COLOR_BG)
        self.lang = resolve_initial_language_code(ROOT)
        self.queue = queue.Queue()
        self.shutdown_event = threading.Event()
        self.active_processes = set()
        self.process_lock = threading.Lock()
        self.generation_lock = threading.Lock()
        self.generation_running = False
        self.current_generator_proc = None
        self.eta_intervals = deque(maxlen=24)
        self.eta_last_layer = None
        self.eta_last_time = None
        self.eta_smoothed_seconds_per_layer = None
        self.eta_display_remaining = None
        self.eta_max_layer_seen = None
        self.eta_recycle_notice_active = False
        self.closed = False
        self.settings = load_settings()
        self.images = [Path(path) for path in initial_images if Path(path).exists()]
        self._last_generation_preprocess: dict[str, str] = {}
        self._preview_filter_cards: dict[str, dict] = {}
        self._preview_filter_payload: dict[str, dict] = {}
        self._preview_source_path: Path | None = None
        self._preview_render_jobs: dict[str, str | None] = {}
        self._preview_compute_running = False
        self._preprocess_mode_labels: dict[str, str] = {}
        self.json_files = []
        self.outputs = []
        self.processes = []
        self.photo = None
        self.use_custom_settings = StringVar(value="0")
        self.custom_stop_at = StringVar()
        self.custom_max_resolution = StringVar()
        self.custom_random_samples = StringVar()
        self.custom_mutated_samples = StringVar()
        self.custom_save_at = StringVar()
        self.custom_preprocess_mode = StringVar(value="none")
        self.preprocess_mode = StringVar(value=PREPROCESS_NONE)
        self.custom_preprocess_mode.trace_add("write", self._sync_preprocess_from_custom)
        self.translated = []
        self.detailed_log_lock = threading.Lock()
        self.detailed_log_lines = deque()
        self.detailed_log_chars = 0
        self.current_preview_request = None
        self.preview_resize_job = None
        self.update_state = {"status": "checking"}
        self.update_dialog = None
        self.update_check_started = False
        self.status = StringVar(value=tr(self.lang, "ready"))
        self.progress_text = StringVar(value="")
        self.selected_profile = StringVar()
        self.selected_game = StringVar(value="fh6")
        self.selected_pid = StringVar()
        self.layer_count = StringVar()
        self.layer_count_info = StringVar(value=tr(self.lang, "layer_import_info"))
        self.snapshot_count = StringVar()
        self.current_count = StringVar()
        self.count_address = StringVar()
        self.table_address = StringVar()
        self.typecode_trim_after_import = StringVar(value="1")
        self.typecode_allow_unknown = StringVar(value="0")
        self.use_best_safe_final = StringVar(value="1")
        self.inspect_table_value = StringVar()
        self.text_vinyl = TextVinylWorkspace(self)
        self.tools_workspace = ToolsWorkspace(self)
        self.runtime_folder = StringVar(value=str(ROOT))
        self.advanced_visible = False
        self.theme_id = StringVar(value=load_saved_theme_id(ROOT))
        self.palette = resolve_palette(self.theme_id.get())
        _install_color_globals(self.palette)
        self._layout_panes = {}
        self._ui_layout = load_ui_layout(ROOT)
        self._layout_save_job = None
        self._layout_restore_jobs: list[str] = []
        self._generate_compare_jobs: dict[str, str] = {}
        self._resource_monitor_settings = load_resource_monitor_settings(ROOT)
        self._resource_monitor_backend = None
        self._resource_heat_state = "normal"
        self._resource_monitor_snapshot = None
        self._header_telemetry: HeaderTelemetryPanel | None = None
        self._build()
        self._apply_ui_fonts()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_processes()
        if self.settings:
            self.selected_profile.set(self.settings[min(2, len(self.settings) - 1)]["label"])
            self._update_setting_description()
        for image_path in list(self.images):
            self._load_existing_checkpoints_for_image(image_path)
        self._render_lists()
        self.log_line(tr(self.lang, "runtime_location").format(runtime=ROOT / "runtime", probe=PROBE_DIR.parent))
        self._poll_queue()
        self._start_resource_monitor()
        self.root.after(1000, self.start_update_check)

    def _ui_font(self, size: int = 10, *, bold: bool = False) -> tuple:
        name = ui_font_name(self.lang)
        return (name, size, "bold") if bold else (name, size)

    def _apply_ui_fonts(self) -> None:
        global UI_INPUT_FONT
        UI_INPUT_FONT = self._ui_font(10)
        self._configure_styles()
        log = getattr(self, "log", None)
        if log is not None:
            try:
                log.config(font=UI_LOG_FONT)
            except Exception:
                pass

    def _configure_styles(self):
        style = ttk.Style(self.root)
        ui_font = ui_font_name(getattr(self, "lang", "en"))
        try:
            style.theme_use("clam")
        except Exception:
            pass
        # ttk style calls occasionally differ across bundled Tcl/Tk builds in one-file EXEs.
        # Keep startup resilient: if a style element is unsupported, skip that rule.
        try:
            style.configure(".", background=COLOR_BG, foreground=COLOR_TEXT, fieldbackground=COLOR_INPUT)
            style.configure("TFrame", background=COLOR_BG)
            style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
            style.configure("Primary.TNotebook", background=COLOR_BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
            style.configure(
                "Primary.TNotebook.Tab",
                padding=(22, 10),
                font=(ui_font, 10, "bold"),
                background=COLOR_PANEL_ALT,
                foreground=COLOR_TEXT,
                borderwidth=0,
            )
            style.map(
                "Primary.TNotebook.Tab",
                background=[("selected", COLOR_ACCENT_DARK), ("!selected", COLOR_PANEL_ALT)],
                foreground=[("selected", COLOR_SELECT_FG), ("!selected", COLOR_MUTED)],
            )
            style.configure(
                "Script.TNotebook",
                background=COLOR_BG,
                borderwidth=0,
                tabmargins=(0, 0, 0, 0),
            )
            style.configure(
                "Script.TNotebook.Tab",
                padding=(14, 8),
                font=(ui_font, 9, "bold"),
                background=COLOR_PANEL_ALT,
                foreground=COLOR_TEXT,
                borderwidth=0,
            )
            style.map(
                "Script.TNotebook.Tab",
                background=[("selected", COLOR_ACCENT_DARK), ("!selected", COLOR_PANEL_ALT)],
                foreground=[("selected", COLOR_SELECT_FG), ("!selected", COLOR_MUTED)],
            )
            style.configure(
                "TLabelframe",
                background=COLOR_PANEL,
                foreground=COLOR_TEXT,
                bordercolor=COLOR_BORDER,
                lightcolor=COLOR_FRAME_LIGHT,
                darkcolor=COLOR_FRAME_DARK,
                relief="solid",
            )
            style.configure(
                "TLabelframe.Label",
                background=COLOR_PANEL,
                foreground=COLOR_TEXT,
                font=(ui_font, 10, "bold"),
            )
            style.configure(
                "TCombobox",
                fieldbackground=COLOR_INPUT,
                background=COLOR_PANEL_ALT,
                foreground=COLOR_TEXT,
                arrowcolor=COLOR_TEXT,
                bordercolor=COLOR_BORDER,
                lightcolor=COLOR_BORDER,
                darkcolor=COLOR_BORDER,
            )
            style.map(
                "TCombobox",
                fieldbackground=[("readonly", COLOR_INPUT)],
                foreground=[("readonly", COLOR_TEXT)],
                selectbackground=[("readonly", COLOR_ACCENT_DARK)],
                selectforeground=[("readonly", COLOR_SELECT_FG)],
            )
            style.configure(
                "TScrollbar",
                background=COLOR_PANEL_ALT,
                troughcolor=COLOR_BG,
                bordercolor=COLOR_BORDER,
                arrowcolor=COLOR_TEXT,
            )
            style.configure("TPanedwindow", background=COLOR_BORDER)
        except Exception:
            pass

        try:
            style.configure("Sash", sashthickness=5, gripcount=0, background=COLOR_SASH)
            style.map("Sash", background=[("active", COLOR_ACCENT)])
        except Exception:
            pass

    def _register_pane(self, paned, layout_key: str, orient: str) -> None:
        self._layout_panes[layout_key] = (paned, orient)
        paned.bind("<ButtonRelease-1>", lambda _event: self._schedule_layout_save(), add="+")
        paned.bind("<B1-Motion>", lambda _event: self._schedule_layout_save(), add="+")

    def _widget_alive(self, widget) -> bool:
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except (TclError, Exception):
            return False

    def _cancel_layout_jobs(self) -> None:
        if self._layout_save_job:
            try:
                self.root.after_cancel(self._layout_save_job)
            except Exception:
                pass
            self._layout_save_job = None
        for job in self._layout_restore_jobs:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self._layout_restore_jobs.clear()

    def _schedule_layout_save(self):
        if self._layout_save_job:
            try:
                self.root.after_cancel(self._layout_save_job)
            except Exception:
                pass
        self._layout_save_job = self.root.after(400, self._persist_pane_layout)

    def _persist_pane_layout(self):
        self._layout_save_job = None
        ratios = dict(self._ui_layout)
        for key, (paned, orient) in list(self._layout_panes.items()):
            measured = pane_ratio(paned, orient)
            if measured is not None:
                ratios[key] = measured
        self._ui_layout = ratios
        save_ui_layout(ROOT, ratios)

    def _restore_pane_layout(self, layout_key: str | None = None) -> None:
        keys = [layout_key] if layout_key else list(self._layout_panes.keys())
        for key in keys:
            entry = self._layout_panes.get(key)
            if not entry:
                continue
            paned, orient = entry
            try:
                if not paned.winfo_exists():
                    continue
            except Exception:
                continue
            ratio = self._ui_layout.get(key, DEFAULT_PANE_RATIOS.get(key, 0.7))
            apply_pane_ratio(paned, orient, ratio)

    def _restore_all_pane_layouts(self) -> None:
        for key in list(self._layout_panes.keys()):
            self._restore_pane_layout(key)

    def _restore_ready_pane_layouts(self) -> None:
        """Restore pane ratios only when widgets exist and are large enough to measure."""
        for key, (paned, orient) in list(self._layout_panes.items()):
            try:
                if not paned.winfo_exists():
                    continue
            except Exception:
                continue
            paned.update_idletasks()
            total = paned.winfo_height() if orient == "vertical" else paned.winfo_width()
            if total < 80:
                continue
            self._restore_pane_layout(key)

    def _restore_shell_layouts(self) -> None:
        self._restore_pane_layout("main_vertical")

    def _schedule_layout_restore(self, *, include_tabs: bool = True) -> None:
        self._cancel_layout_jobs()

        def _run_shell() -> None:
            if self.closed:
                return
            self._restore_shell_layouts()
            if include_tabs:
                self._restore_ready_pane_layouts()

        for delay in (80, 200, 500):
            self._layout_restore_jobs.append(self.root.after(delay, _run_shell))

    def _create_paned(self, parent, orient: str, layout_key: str, **pack_kwargs) -> ttk.PanedWindow:
        paned = ttk.PanedWindow(parent, orient=orient)
        pack_kwargs.setdefault("fill", BOTH)
        pack_kwargs.setdefault("expand", True)
        paned.pack(**pack_kwargs)
        self._register_pane(paned, layout_key, orient)
        return paned

    def _register_process(self, proc):
        with self.process_lock:
            self.active_processes.add(proc)

    def _popen_registered(self, cmd, **kwargs):
        # Hold process_lock across Popen + registration so on_close cannot miss
        # a child process that starts while the window is closing.
        with self.process_lock:
            if self.shutdown_event.is_set() or self.closed:
                return None
            proc = subprocess.Popen(cmd, **kwargs)
            self.active_processes.add(proc)
            return proc

    def _unregister_process(self, proc):
        with self.process_lock:
            self.active_processes.discard(proc)

    def _terminate_process(self, proc):
        if proc.poll() is not None:
            return
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=5,
                )
            else:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def _terminate_active_processes(self):
        with self.process_lock:
            processes = list(self.active_processes)
        for proc in processes:
            self._terminate_process(proc)

    def on_close(self):
        self.closed = True
        self.shutdown_event.set()
        self._terminate_active_processes()
        self.root.destroy()

    def _parent_bg(self, parent):
        try:
            return parent.cget("bg")
        except Exception:
            return COLOR_PANEL

    def _theme_fg(self, role: str) -> str:
        roles = {
            "text": COLOR_TEXT,
            "muted": COLOR_MUTED,
            "hint": COLOR_HINT,
            "info": COLOR_INFO,
            "success": COLOR_SUCCESS,
            "error": COLOR_ERROR,
        }
        return roles.get(role, COLOR_TEXT)

    def _label(self, parent, key, theme_role: str = "text", **kwargs):
        kwargs.setdefault("bg", self._parent_bg(parent))
        if "fg" not in kwargs:
            kwargs.setdefault("fg", self._theme_fg(theme_role))
        widget = Label(parent, text=tr(self.lang, key), **kwargs)
        widget._theme_role = theme_role
        self.translated.append((widget, key, "text"))
        return widget

    def _button(self, parent, key, command, **kwargs):
        kwargs.setdefault("bg", COLOR_BUTTON)
        kwargs.setdefault("fg", COLOR_TEXT)
        kwargs.setdefault("disabledforeground", COLOR_MUTED)
        kwargs.setdefault("activebackground", COLOR_BUTTON_ACTIVE)
        kwargs.setdefault("activeforeground", COLOR_BUTTON_ACTIVE_FG)
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("highlightthickness", 1)
        kwargs.setdefault("highlightbackground", COLOR_BORDER)
        kwargs.setdefault("highlightcolor", COLOR_ACCENT)
        kwargs.setdefault("padx", 8)
        kwargs.setdefault("pady", 3)
        widget = Button(parent, text=tr(self.lang, key), command=command, **kwargs)
        self.translated.append((widget, key, "text"))
        return widget

    def _bind_wraplength(self, label, container, padding=24, minimum=160):
        def _on_configure(event=None):
            if not self._widget_alive(label) or not self._widget_alive(container):
                return
            try:
                width = event.width if event is not None else container.winfo_width()
                if width > padding + minimum:
                    label.configure(wraplength=max(minimum, width - padding))
            except TclError:
                pass

        container.bind("<Configure>", _on_configure, add="+")

    def _make_vertical_scroll(self, parent):
        scroll_area = Frame(parent)
        canvas = Canvas(scroll_area, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_area, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill="y")
        inner = Frame(canvas)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _update_scroll_region(_event=None):
            if not self._widget_alive(canvas):
                return
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except TclError:
                pass

        def _match_canvas_width(event):
            if not self._widget_alive(canvas):
                return
            try:
                canvas.itemconfigure(window, width=event.width)
            except TclError:
                pass

        def _mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(_event=None):
            canvas.bind_all("<MouseWheel>", _mousewheel)

        def _unbind_mousewheel(_event=None):
            canvas.unbind_all("<MouseWheel>")

        inner.bind("<Configure>", _update_scroll_region)
        canvas.bind("<Configure>", _match_canvas_width)
        scroll_area.bind("<Enter>", _bind_mousewheel)
        scroll_area.bind("<Leave>", _unbind_mousewheel)
        return scroll_area, inner

    def _bind_text_mousewheel(self, widget):
        def _mousewheel(event):
            widget.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind(_event=None):
            widget.bind_all("<MouseWheel>", _mousewheel)

        def _unbind(_event=None):
            widget.unbind_all("<MouseWheel>")

        widget.bind("<Enter>", _bind)
        widget.bind("<Leave>", _unbind)

    def _label_fg_for_widget(self, widget) -> str:
        role = getattr(widget, "_theme_role", None)
        if role:
            return self._theme_fg(role)
        return COLOR_TEXT

    def _apply_theme_recursive(self, widget):
        try:
            if isinstance(widget, Frame):
                if getattr(widget, "_chrome_bg_locked", False):
                    widget.configure(bg=COLOR_BG)
                elif widget.master is self.root:
                    widget.configure(bg=COLOR_BG)
                else:
                    widget.configure(bg=COLOR_PANEL)
            elif isinstance(widget, Label):
                if widget in (
                    getattr(self, "generate_source_before_preview", None),
                    getattr(self, "generate_source_after_preview", None),
                    getattr(self, "generate_result_without_preview", None),
                    getattr(self, "generate_result_with_preview", None),
                    getattr(self, "import_preview_label", None),
                ):
                    widget.configure(bg=COLOR_PREVIEW_BG, fg=COLOR_PREVIEW_FG)
                elif widget is getattr(self, "update_indicator", None):
                    widget.configure(bg=COLOR_PANEL)
                else:
                    widget.configure(bg=self._parent_bg(widget.master), fg=self._label_fg_for_widget(widget))
            elif isinstance(widget, Button):
                widget.configure(
                    bg=COLOR_BUTTON,
                    fg=COLOR_TEXT,
                    disabledforeground=COLOR_MUTED,
                    activebackground=COLOR_BUTTON_ACTIVE,
                    activeforeground=COLOR_BUTTON_ACTIVE_FG,
                    relief="flat",
                    bd=0,
                    highlightbackground=COLOR_BORDER,
                    highlightcolor=COLOR_ACCENT,
                )
            elif isinstance(widget, Checkbutton):
                widget.configure(
                    bg=self._parent_bg(widget.master),
                    fg=COLOR_TEXT,
                    disabledforeground=COLOR_MUTED,
                    activebackground=self._parent_bg(widget.master),
                    activeforeground=COLOR_TEXT,
                    selectcolor=COLOR_INPUT,
                    relief="flat",
                    highlightbackground=COLOR_BORDER,
                    highlightcolor=COLOR_ACCENT,
                )
            elif isinstance(widget, Entry):
                widget.configure(
                    bg=COLOR_INPUT,
                    fg=COLOR_TEXT,
                    insertbackground=COLOR_TEXT,
                    disabledbackground=COLOR_PANEL_ALT,
                    disabledforeground=COLOR_MUTED,
                    readonlybackground=COLOR_INPUT,
                    relief="flat",
                    highlightthickness=1,
                    highlightbackground=COLOR_BORDER,
                    highlightcolor=COLOR_ACCENT,
                    font=UI_INPUT_FONT,
                )
            elif isinstance(widget, Listbox):
                widget.configure(
                    bg=COLOR_INPUT,
                    fg=COLOR_TEXT,
                    selectbackground=COLOR_ACCENT_DARK,
                    selectforeground=COLOR_SELECT_FG,
                    highlightthickness=1,
                    highlightbackground=COLOR_BORDER,
                    relief="flat",
                    font=UI_INPUT_FONT,
                )
            elif isinstance(widget, Text):
                log_font = UI_LOG_FONT if widget in (getattr(self, "log", None),) else UI_INPUT_FONT
                widget.configure(
                    bg=COLOR_INPUT,
                    fg=COLOR_TEXT,
                    insertbackground=COLOR_TEXT,
                    selectbackground=COLOR_ACCENT_DARK,
                    selectforeground=COLOR_SELECT_FG,
                    highlightthickness=1,
                    highlightbackground=COLOR_BORDER,
                    relief="flat",
                    font=log_font,
                )
            elif isinstance(widget, DonutGauge):
                fill = COLOR_SUCCESS if getattr(widget, "_donut_role", None) == "cpu" else COLOR_ACCENT
                widget.set_scheme(
                    track_color=COLOR_BORDER,
                    fill_color=fill,
                    bg_color=COLOR_BG if widget.master is self.root else self._parent_bg(widget.master),
                    text_color=COLOR_TEXT,
                    muted_color=COLOR_MUTED,
                )
            elif isinstance(widget, Canvas):
                chrome_bg = getattr(widget, "_chrome_bg", None)
                widget.configure(bg=chrome_bg or COLOR_PANEL, highlightthickness=0)
        except (TclError, Exception):
            pass
        for child in widget.winfo_children():
            self._apply_theme_recursive(child)

    def _build(self):
        self._configure_styles()
        header = Frame(self.root, bg=COLOR_BG)
        header.pack(fill=X, padx=16, pady=(14, 8))
        title_box = Frame(header, bg=COLOR_BG)
        title_box._chrome_bg_locked = True
        title_box.pack(side=LEFT, anchor="nw")
        kicker = self._label(title_box, "header_kicker", anchor="w", font=("Segoe UI", 9, "bold"), fg=COLOR_INFO)
        kicker.pack(fill=X)
        self._label(title_box, "title", font=("Segoe UI", 21, "bold"), anchor="w").pack(fill=X, pady=(2, 0))
        audit_label = Label(
            title_box,
            text=tr(self.lang, "header_audit").upper(),
            anchor="w",
            fg=COLOR_MUTED,
            bg=COLOR_BG,
            font=("Segoe UI", 9),
        )
        audit_label.pack(fill=X, pady=(1, 2))
        audit_label._theme_role = "muted"
        self.translated.append((audit_label, "header_audit", "text_upper"))
        self._label(title_box, "subtitle", anchor="w", theme_role="muted", font=("Segoe UI", 10)).pack(fill=X)

        if self._resource_monitor_settings.enabled:
            self._header_telemetry = HeaderTelemetryPanel(self, header)

        right = Frame(header, bg=COLOR_BG)
        right._chrome_bg_locked = True
        right.pack(side=RIGHT)
        self.update_indicator = Label(
            right,
            text="",
            bg=COLOR_PANEL,
            fg=COLOR_WARN,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            padx=4,
            pady=1,
        )
        self.update_indicator.bind("<Button-1>", self.show_update_status)
        self._label(right, "theme_label").pack(anchor="e")
        self.theme_combo = ttk.Combobox(right, state="readonly", width=22)
        self._sync_theme_combo()
        self.theme_combo.pack(anchor="e", pady=(0, 8))
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme)
        self._label(right, "language").pack(anchor="e")
        self.lang_combo = ttk.Combobox(right, values=list(LANGUAGES.keys()), state="readonly", width=16)
        self.lang_combo.set(language_display_name(self.lang))
        self.lang_combo.pack(anchor="e")
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_language)

        self._header_rule_canvas = header_rule(self.root, height=2, bg=COLOR_BG, line=COLOR_BORDER)

        process_card = Frame(self.root, bg=COLOR_PANEL, highlightbackground=COLOR_BORDER, highlightthickness=1)
        process_card.pack(fill=X, padx=16, pady=(0, 10))
        inner_bar = Frame(process_card, bg=COLOR_PANEL)
        inner_bar.pack(fill=X, padx=12, pady=10)
        self._label(inner_bar, "process").pack(side=LEFT)
        self.process_combo = ttk.Combobox(inner_bar, textvariable=self.selected_pid, state="readonly", width=44)
        self.process_combo.pack(side=LEFT, padx=8)
        self._button(inner_bar, "refresh", self.refresh_processes).pack(side=LEFT)
        status_label = Label(inner_bar, textvariable=self.status, anchor="e", bg=COLOR_PANEL, fg=COLOR_MUTED)
        status_label._theme_role = "muted"
        status_label.pack(side=RIGHT)

        self.main_pane = self._create_paned(
            self.root,
            orient=VERTICAL,
            layout_key="main_vertical",
            padx=14,
            pady=(0, 4),
        )

        self.workspace = Frame(self.main_pane)
        self.log_pane = Frame(self.main_pane)
        self.main_pane.add(self.workspace, weight=4)
        self.main_pane.add(self.log_pane, weight=1)

        self.workspace.rowconfigure(0, weight=1)
        self.workspace.columnconfigure(0, weight=1)
        self.workspace_body = Frame(self.workspace)
        self.workspace_body.grid(row=0, column=0, sticky="nsew")

        self._init_workspace_tabs()
        self._build_log()
        self.text_vinyl.refresh_mandarin_char_list()
        self.text_vinyl.refresh_fonts()
        self._apply_theme()
        self._bind_workspace_tab_events()
        self._schedule_layout_restore()

    def _init_workspace_tabs(self) -> None:
        self._workspace_bound_main = False
        self.main_tabs = ttk.Notebook(self.workspace_body, style="Primary.TNotebook")
        self.main_tabs.pack(fill=BOTH, expand=True, pady=(0, 4))

        self.generate_tab = Frame(self.main_tabs)
        self.import_final_tab = Frame(self.main_tabs)
        self.handmade_tab = Frame(self.main_tabs)
        self.export_game_tab = Frame(self.main_tabs)
        self.preview_tab_frame = Frame(self.main_tabs)
        self.text_tab = Frame(self.main_tabs)
        self.tools_tab = Frame(self.main_tabs)
        self.tutorial_tab = Frame(self.main_tabs)
        self.acknowledgements_tab = Frame(self.main_tabs)

        self._build_image_preview_tab()
        self._build_generate_tab()
        self._build_import_final_tab()
        self._build_handmade_tab()
        self._build_export_game_tab()
        self._build_text_tab()
        self._build_tools_tab()
        self._build_tutorial_tab()
        self._build_acknowledgements_tab()

        for tab, key in self._workspace_tab_specs():
            self.main_tabs.add(tab, text=tr(self.lang, key))
        self.tabs = self.main_tabs

        self._ensure_tab_strip()
        self._bind_workspace_tab_events()
        try:
            self.main_tabs.select(0)
        except Exception:
            pass
        self.workspace_body.update_idletasks()

    def _workspace_tab_specs(self):
        return (
            (self.generate_tab, "generate_tab"),
            (self.import_final_tab, "import_final_tab"),
            (self.handmade_tab, "import_handmade_tab"),
            (self.export_game_tab, "export_game_tab"),
            (self.preview_tab_frame, "preview_tab"),
            (self.text_tab, "text_tab"),
            (self.tools_tab, "tools_tab"),
            (self.tutorial_tab, "tutorial_tab"),
            (self.acknowledgements_tab, "acknowledgements_tab"),
        )

    def _ensure_tab_strip(self) -> None:
        if not hasattr(self, "_tab_strip_canvas") or not self._tab_strip_canvas.winfo_exists():
            self._tab_strip_canvas = Canvas(self.workspace, height=18, bg=COLOR_BG, highlightthickness=0, bd=0)
            setattr(self._tab_strip_canvas, "_chrome_bg", COLOR_BG)
            self._tab_strip_canvas.bind("<Configure>", lambda _e: self._paint_tab_strip())
        self._tab_strip_canvas.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        self._paint_tab_strip()

    def _paint_tab_strip(self, _event=None) -> None:
        if not hasattr(self, "_tab_strip_canvas"):
            return
        c = self._tab_strip_canvas
        c.delete("dots")
        tabs = getattr(self, "main_tabs", None)
        if tabs is None:
            return
        try:
            sel = int(tabs.index(tabs.select()))
        except Exception:
            sel = 0
        n = len(self._workspace_tab_specs())
        w = max(1, c.winfo_width())
        dot_r = 4
        gap = 11
        total = n * (dot_r * 2) + (n - 1) * gap
        x_start = max(dot_r + 6, (w - total) // 2 + dot_r)
        cy = 10
        for i in range(n):
            xc = x_start + i * (dot_r * 2 + gap)
            if i == sel:
                c.create_oval(
                    xc - dot_r,
                    cy - dot_r,
                    xc + dot_r,
                    cy + dot_r,
                    fill=COLOR_ACCENT,
                    outline=COLOR_SUCCESS,
                    width=1,
                    tags="dots",
                )
            else:
                c.create_oval(
                    xc - dot_r + 1,
                    cy - dot_r + 1,
                    xc + dot_r - 1,
                    cy + dot_r - 1,
                    fill="",
                    outline=COLOR_BORDER,
                    width=1,
                    tags="dots",
                )

    def _bind_workspace_tab_events(self):
        if getattr(self, "_workspace_bound_main", False) or self.main_tabs is None:
            return
        self.main_tabs.bind("<<NotebookTabChanged>>", self._on_main_tab_changed)
        self._workspace_bound_main = True

    def _is_text_tab_active(self) -> bool:
        try:
            return self.main_tabs.select() == str(self.text_tab)
        except Exception:
            return False

    def _is_tools_tab_active(self) -> bool:
        try:
            return self.main_tabs.select() == str(self.tools_tab)
        except Exception:
            return False

    def _on_main_tab_changed(self, _event=None):
        self._paint_tab_strip()
        self._schedule_preview_refresh()
        if self._is_import_final_tab_active():
            self.refresh_generated_runs()
        if self._is_text_tab_active():
            self.text_vinyl.on_tab_activated()
        if self._is_tools_tab_active():
            self.tools_workspace.on_tab_activated()
        self.root.after(50, self._restore_ready_pane_layouts)

    def _theme_label_key(self, theme_id: str) -> str:
        return f"theme_{normalize_theme_id(theme_id)}"

    def _theme_display_name(self, theme_id: str) -> str:
        return tr(self.lang, self._theme_label_key(theme_id))

    def _theme_id_from_display(self, display: str) -> str:
        needle = (display or "").strip()
        for theme_id in THEME_IDS:
            if self._theme_display_name(theme_id) == needle:
                return theme_id
        return normalize_theme_id(self.theme_id.get())

    def _sync_theme_combo(self) -> None:
        if not hasattr(self, "theme_combo"):
            return
        names = [self._theme_display_name(theme_id) for theme_id in THEME_IDS]
        self.theme_combo["values"] = names
        current = self._theme_display_name(self.theme_id.get())
        if current in names:
            self.theme_combo.set(current)

    def _refresh_header_chrome(self) -> None:
        rule = getattr(self, "_header_rule_canvas", None)
        if rule is not None:
            rule._chrome_bg = COLOR_BG  # type: ignore[attr-defined]
            rule._chrome_line = COLOR_BORDER  # type: ignore[attr-defined]
            try:
                rule.configure(bg=COLOR_BG)
                rule.event_generate("<Configure>")
            except Exception:
                pass

    def _apply_theme(self, theme_id: str | None = None) -> None:
        tid = normalize_theme_id(theme_id or self.theme_id.get())
        self.theme_id.set(tid)
        self.palette = resolve_palette(tid)
        _install_color_globals(self.palette)
        save_theme_id(ROOT, tid)
        self.root.configure(bg=COLOR_BG)
        self._configure_styles()
        self._apply_theme_recursive(self.root)
        if self._header_telemetry is not None:
            self._header_telemetry.apply_theme_recursive(self._apply_theme_recursive)
        self._refresh_header_chrome()
        self._paint_tab_strip()
        self._sync_theme_combo()
        self.text_vinyl.update_theme_hints()

    def _on_theme(self, _event=None) -> None:
        self._apply_theme(self._theme_id_from_display(self.theme_combo.get()))

    def _build_generate_tab(self):
        paned = self._create_paned(self.generate_tab, orient=HORIZONTAL, layout_key="generate_horizontal", padx=10, pady=10)
        left_outer = Frame(paned)
        right = Frame(paned)
        paned.add(left_outer, weight=3)
        paned.add(right, weight=2)

        scroll_hint = self._label(left_outer, "scroll_hint", anchor="w", justify=LEFT, theme_role="hint")
        scroll_hint.pack(fill=X, padx=0, pady=(0, 6))
        self._bind_wraplength(scroll_hint, left_outer)
        scroll_area, left = self._make_vertical_scroll(left_outer)
        scroll_area.pack(fill=BOTH, expand=True, pady=(0, 8))

        step1 = ttk.LabelFrame(left, text=tr(self.lang, "generate_step_image"))
        self.translated.append((step1, "generate_step_image", "text"))
        step1.pack(fill=X, pady=(0, 6))
        step1_hint = self._label(step1, "generate_step_image_hint", anchor="w", justify=LEFT, theme_role="hint")
        step1_hint.pack(fill=X, padx=10, pady=(8, 2))
        self._bind_wraplength(step1_hint, step1)
        self.translated.append((step1_hint, "generate_step_image_hint", "text"))
        step1_credit = self._label(step1, "generate_step_image_credit", anchor="w", justify=LEFT, theme_role="hint")
        step1_credit.pack(fill=X, padx=10, pady=(0, 6))
        self._bind_wraplength(step1_credit, step1)
        self.translated.append((step1_credit, "generate_step_image_credit", "text"))
        row = Frame(step1)
        row.pack(fill=X, padx=10, pady=(6, 2))
        self._label(row, "images").pack(side=LEFT)
        self._button(row, "add_images", self.add_images).pack(side=RIGHT)
        self._button(row, "remove_image", self.remove_selected_image).pack(side=RIGHT, padx=8)
        self.image_list = Listbox(step1, height=3)
        self.image_list.pack(fill=X, padx=10, pady=(2, 4))
        self.image_list.bind("<<ListboxSelect>>", self._preview_selected_image)
        self.generate_luma_status = Label(step1, text="", anchor="w", justify=LEFT, fg=COLOR_MUTED, bg=COLOR_PANEL, wraplength=360)
        self.generate_luma_status._theme_role = "hint"
        self.generate_luma_status.pack(fill=X, padx=10, pady=(0, 8))
        self._bind_wraplength(self.generate_luma_status, step1)

        step2 = ttk.LabelFrame(left, text=tr(self.lang, "generate_step_quality"))
        self.translated.append((step2, "generate_step_quality", "text"))
        step2.pack(fill=X, pady=(0, 6))
        profile_row = Frame(step2)
        profile_row.pack(fill=X, padx=10, pady=(8, 4))
        self._label(profile_row, "quality").pack(side=LEFT)
        self.profile_combo = ttk.Combobox(
            profile_row,
            values=[item["label"] for item in self.settings],
            textvariable=self.selected_profile,
            state="readonly",
            width=32,
        )
        self.profile_combo.pack(side=LEFT, fill=X, expand=True, padx=(8, 0))
        self.profile_combo.bind("<<ComboboxSelected>>", self._update_setting_description)
        preset_actions = Frame(step2)
        preset_actions.pack(fill=X, padx=10, pady=(0, 6))
        self._button(preset_actions, "import_preset", self.import_preset).pack(side=LEFT)
        self._button(preset_actions, "open_preset_folder", self.open_preset_folder).pack(side=LEFT, padx=8)
        self.setting_description = Label(step2, text="", anchor="w", justify=LEFT, fg=COLOR_MUTED, bg=COLOR_PANEL)
        self.setting_description._theme_role = "muted"
        self.setting_description._theme_role = "muted"
        self.setting_description.pack(fill=X, padx=10, pady=(0, 4))
        self._bind_wraplength(self.setting_description, step2)

        filter_row = Frame(step2)
        filter_row.pack(fill=X, padx=10, pady=(0, 4))
        self._label(filter_row, "preprocess_filter").pack(side=LEFT)
        self.preprocess_mode_combo = ttk.Combobox(filter_row, state="readonly", width=28)
        self.preprocess_mode_combo.pack(side=LEFT, fill=X, expand=True, padx=(8, 0))
        self.preprocess_mode_combo.bind("<<ComboboxSelected>>", self._on_preprocess_mode_combo)
        self.preprocess_filter_active_hint = self._label(
            step2, "filter_none_hint", anchor="w", justify=LEFT, theme_role="hint"
        )
        self.preprocess_filter_active_hint.pack(fill=X, padx=10, pady=(0, 4))
        self._bind_wraplength(self.preprocess_filter_active_hint, step2)
        filter_hint = self._label(step2, "preprocess_filter_hint", anchor="w", justify=LEFT, theme_role="hint")
        filter_hint.pack(fill=X, padx=10, pady=(0, 8))
        self._bind_wraplength(filter_hint, step2)

        custom_section = ttk.LabelFrame(left, text=tr(self.lang, "custom_panel_title"))
        self.translated.append((custom_section, "custom_panel_title", "text"))
        custom_section.pack(fill=X, pady=(0, 6))
        custom_hint = self._label(custom_section, "custom_panel_hint", anchor="w", justify=LEFT, theme_role="info")
        custom_hint.pack(fill=X, padx=10, pady=(6, 2))
        self._bind_wraplength(custom_hint, custom_section)
        custom_toggle = Checkbutton(
            custom_section,
            text=tr(self.lang, "custom_settings"),
            variable=self.use_custom_settings,
            onvalue="1",
            offvalue="0",
            command=self._sync_custom_state,
        )
        custom_toggle.pack(anchor="w", padx=10, pady=(0, 2))
        self.translated.append((custom_toggle, "custom_settings", "text"))
        custom_grid = Frame(custom_section)
        custom_grid.pack(fill=X, padx=10, pady=(0, 6))
        self.custom_fields = []
        custom_specs = [
            ("custom_layers", self.custom_stop_at),
            ("custom_resolution", self.custom_max_resolution),
            ("custom_random", self.custom_random_samples),
            ("custom_mutated", self.custom_mutated_samples),
            ("custom_save_at", self.custom_save_at),
        ]
        for row_index, (key, variable) in enumerate(custom_specs):
            label = self._label(custom_grid, key, anchor="w")
            label.grid(row=row_index, column=0, sticky="w", pady=1, padx=(0, 8))
            entry = Entry(custom_grid, textvariable=variable, width=18)
            entry.grid(row=row_index, column=1, sticky="ew", pady=1)
            self.custom_fields.append(entry)
        custom_grid.columnconfigure(1, weight=1)
        preprocess_widget = self._field(
            custom_grid,
            "preprocess_mode",
            self.custom_preprocess_mode,
            row=len(custom_specs),
            values=list(PREPROCESS_MODE_IDS),
            readonly=True,
        )
        self.custom_fields.append(preprocess_widget)
        custom_actions = Frame(custom_section)
        custom_actions.pack(fill=X, padx=10, pady=(0, 8))
        self._button(custom_actions, "save_custom_preset", self.save_custom_preset).pack(side=LEFT)
        self._sync_custom_state()
        self.root.after_idle(self._refresh_preprocess_mode_combo)

        step3 = ttk.LabelFrame(left_outer, text=tr(self.lang, "generate_step_run"))
        self.translated.append((step3, "generate_step_run", "text"))
        step3.pack(fill=X)
        run_hint = self._label(step3, "generate_step_run_hint", anchor="w", justify=LEFT)
        run_hint.pack(fill=X, padx=10, pady=(8, 4))
        self._bind_wraplength(run_hint, step3)
        actions = Frame(step3)
        actions.pack(fill=X, padx=10, pady=(4, 12))
        self.generate_button = self._button(actions, "start_generate", self.start_generate, font=("Segoe UI", 12, "bold"), height=2)
        self.generate_button.pack(side=LEFT, fill=X, expand=True)
        self.stop_generate_button = self._button(actions, "stop_generate", self.stop_generate, height=2, state="disabled")
        self.stop_generate_button.pack(side=LEFT, padx=8)
        self._button(actions, "open_output", self.open_output_folder, height=2).pack(side=LEFT)

        compare_scroll, compare_body = self._make_vertical_scroll(right)
        compare_scroll.pack(fill=BOTH, expand=True)
        compare_hint = self._label(compare_body, "generate_select_image", anchor="w", justify=LEFT, theme_role="hint")
        compare_hint.pack(fill=X, pady=(0, 6))
        self._bind_wraplength(compare_hint, compare_body)
        self.generate_compare_hint = compare_hint

        source_box = ttk.LabelFrame(compare_body, text=tr(self.lang, "generate_compare_source"))
        self.translated.append((source_box, "generate_compare_source", "text"))
        source_box.pack(fill=X, pady=(0, 8))
        source_row = Frame(source_box)
        source_row.pack(fill=X, padx=8, pady=8)
        source_row.columnconfigure(0, weight=1)
        source_row.columnconfigure(1, weight=1)
        source_row.rowconfigure(1, weight=0, minsize=GENERATE_COMPARE_SOURCE_MIN)

        self._label(source_row, "luma_before", anchor="w", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 4))
        self._label(source_row, "luma_after", anchor="w", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky="w", padx=(4, 0))
        self.generate_source_before_preview = Label(
            source_row,
            text=tr(self.lang, "luma_before_hint"),
            bg=COLOR_PREVIEW_BG,
            fg=COLOR_PREVIEW_FG,
        )
        self.generate_source_before_preview.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.generate_source_before_preview.bind("<Configure>", lambda _e: self._schedule_generate_compare_refresh("source_before"))
        self.generate_source_after_preview = Label(
            source_row,
            text=tr(self.lang, "luma_after_hint"),
            bg=COLOR_PREVIEW_BG,
            fg=COLOR_PREVIEW_FG,
        )
        self.generate_source_after_preview.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))
        self.generate_source_after_preview.bind("<Configure>", lambda _e: self._schedule_generate_compare_refresh("source_after"))

        result_box = ttk.LabelFrame(compare_body, text=tr(self.lang, "generate_compare_result"))
        self.translated.append((result_box, "generate_compare_result", "text"))
        result_box.pack(fill=X, pady=(0, 8))
        result_row = Frame(result_box)
        result_row.pack(fill=X, padx=8, pady=8)
        result_row.columnconfigure(0, weight=1)
        result_row.columnconfigure(1, weight=1)
        result_row.rowconfigure(1, weight=0, minsize=GENERATE_COMPARE_RESULT_MIN)

        self.generate_result_without_header = self._label(
            result_row, "generate_result_plain", anchor="w", font=("Segoe UI", 10, "bold")
        )
        self.generate_result_without_header.grid(row=0, column=0, sticky="w", padx=(0, 4))
        self.generate_result_with_header = self._label(
            result_row, "generate_result_filtered", anchor="w", font=("Segoe UI", 10, "bold")
        )
        self.generate_result_with_header.grid(row=0, column=1, sticky="w", padx=(4, 0))
        self.generate_layers_without_label = self._label(result_row, "generate_no_checkpoint", anchor="w", theme_role="muted")
        self.generate_layers_without_label.grid(row=2, column=0, sticky="w", padx=(0, 4), pady=(4, 0))
        self.generate_layers_with_label = self._label(result_row, "generate_no_checkpoint", anchor="w", theme_role="muted")
        self.generate_layers_with_label.grid(row=2, column=1, sticky="w", padx=(4, 0), pady=(4, 0))
        self.generate_result_without_preview = Label(
            result_row,
            text=tr(self.lang, "generate_no_checkpoint"),
            bg=COLOR_PREVIEW_BG,
            fg=COLOR_PREVIEW_FG,
        )
        self.generate_result_without_preview.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=(4, 0))
        self.generate_result_without_preview.bind("<Configure>", lambda _e: self._schedule_generate_compare_refresh("result_without"))
        self.generate_result_with_preview = Label(
            result_row,
            text=tr(self.lang, "generate_no_checkpoint"),
            bg=COLOR_PREVIEW_BG,
            fg=COLOR_PREVIEW_FG,
        )
        self.generate_result_with_preview.grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=(4, 0))
        self.generate_result_with_preview.bind("<Configure>", lambda _e: self._schedule_generate_compare_refresh("result_with"))

        self._generate_compare_image = None
        self._generate_compare_jobs = {}

    def _is_import_final_tab_active(self) -> bool:
        try:
            return self.main_tabs.select() == str(self.import_final_tab)
        except Exception:
            return False

    def _active_generation_result_label(self):
        if not hasattr(self, "generate_result_without_preview"):
            return None
        if self._selected_preprocess_mode() != PREPROCESS_NONE:
            return self.generate_result_with_preview
        return self.generate_result_without_preview

    def _selected_preprocess_mode(self) -> str:
        return normalize_preprocess_mode(self.preprocess_mode.get())

    def _filter_label(self, mode_id: str | None = None) -> str:
        mode_id = normalize_preprocess_mode(mode_id if mode_id is not None else self._selected_preprocess_mode())
        spec = filter_spec(mode_id)
        return tr(self.lang, spec.label_key) if spec else mode_id

    def _filter_hint_text(self, mode_id: str | None = None) -> str:
        mode_id = normalize_preprocess_mode(mode_id if mode_id is not None else self._selected_preprocess_mode())
        spec = filter_spec(mode_id)
        return tr(self.lang, spec.hint_key) if spec else ""

    def _update_preprocess_filter_active_hint(self, mode_id: str | None = None):
        if not hasattr(self, "preprocess_filter_active_hint"):
            return
        self.preprocess_filter_active_hint.config(text=self._filter_hint_text(mode_id))

    def _refresh_preprocess_mode_combo(self):
        if not hasattr(self, "preprocess_mode_combo"):
            return
        current = self._selected_preprocess_mode()
        labels: list[str] = []
        mapping: dict[str, str] = {}
        for spec in PREPROCESS_FILTERS:
            label = tr(self.lang, spec.label_key)
            labels.append(label)
            mapping[label] = spec.mode_id
        self._preprocess_mode_labels = mapping
        self.preprocess_mode_combo["values"] = labels
        pick = next((label for label, mode in mapping.items() if mode == current), labels[0] if labels else "")
        self.preprocess_mode_combo.set(pick)

    def _set_preprocess_mode(self, mode_id: str, *, refresh_ui: bool = True):
        mode_id = normalize_preprocess_mode(mode_id)
        self.preprocess_mode.set(mode_id)
        if self.use_custom_settings.get() == "1":
            self.custom_preprocess_mode.set(mode_id)
        if not refresh_ui:
            self._update_preprocess_filter_active_hint(mode_id)
            return
        self._refresh_preprocess_mode_combo()
        self._update_preprocess_filter_active_hint(mode_id)
        self._refresh_generate_compare()
        self._update_luma_status_label()
        self._update_compare_column_headers()
        if self._preview_filter_cards:
            self._highlight_preview_filter_cards()

    def _on_preprocess_mode_combo(self, _event=None):
        mode_id = self._preprocess_mode_labels.get(self.preprocess_mode_combo.get(), PREPROCESS_NONE)
        self._set_preprocess_mode(mode_id, refresh_ui=True)

    def _image_list_display(self, image_path: Path) -> str:
        mode = self._selected_preprocess_mode()
        if mode != PREPROCESS_NONE and preprocessed_image_exists(image_path, mode):
            tag = tr(self.lang, "luma_image_tag_ready")
        elif mode != PREPROCESS_NONE:
            tag = tr(self.lang, "luma_image_tag_missing")
        else:
            tag = self._filter_label(PREPROCESS_NONE)
        return f"{image_path.name}  ·  {tag}"

    def _json_preprocess_tag_key(self, json_path: Path) -> str:
        path_mode = preprocess_mode_for_path(json_path)
        if path_mode:
            spec = filter_spec(path_mode)
            if spec:
                return spec.json_tag_key
        for image_path in self.images:
            for spec in PREPROCESS_FILTERS:
                if spec.mode_id == PREPROCESS_NONE:
                    continue
                if json_from_preprocess_pipeline(json_path, image_path, preprocess_mode=spec.mode_id):
                    return spec.json_tag_key
        return "json_tag_plain"

    def _json_list_display(self, json_path: Path) -> str:
        return f"{tr(self.lang, self._json_preprocess_tag_key(json_path))}  {json_path.name}"

    def _checkpoint_summary(self, jsons) -> str:
        if not jsons:
            return tr(self.lang, "generate_no_checkpoint")
        return tr(self.lang, "generate_layers_count").format(count=geometry_shape_count(jsons[0]))

    def _preview_estimate_for_image(self, image_path: Path | None, mode_id: str) -> int | None:
        if image_path is None or not self._preview_filter_payload:
            return None
        if str(getattr(self, "_preview_source_path", "")) != str(image_path.resolve()):
            return None
        entry = self._preview_filter_payload.get(normalize_preprocess_mode(mode_id))
        return int(entry["estimate"]) if entry and entry.get("estimate") else None

    def _result_layer_label(self, image_path: Path, mode_id: str, json_path) -> str:
        if json_path:
            return tr(self.lang, "generate_layers_count").format(count=geometry_shape_count(json_path))
        estimate = self._preview_estimate_for_image(image_path, mode_id)
        if estimate:
            return tr(self.lang, "preview_estimate").format(count=estimate)
        return tr(self.lang, "generate_no_checkpoint")

    def _update_luma_status_label(self):
        if not hasattr(self, "generate_luma_status"):
            return
        image_path = self._selected_generate_image()
        if image_path is None:
            self.generate_luma_status.config(text=tr(self.lang, "luma_status_none"))
            return
        mode = self._selected_preprocess_mode()
        lines = [
            tr(self.lang, "luma_status_next_off")
            if mode == PREPROCESS_NONE
            else tr(self.lang, "luma_status_next_on").format(filter=self._filter_label(mode))
        ]
        if mode != PREPROCESS_NONE:
            if preprocessed_image_exists(image_path, mode):
                lines.append(
                    tr(self.lang, "luma_status_file_ready").format(
                        name=preprocessed_image_path(image_path, mode).name
                    )
                )
            else:
                lines.append(tr(self.lang, "luma_status_file_missing"))
        plain = checkpoints_for_image(image_path, preprocess_mode=PREPROCESS_NONE)
        filtered = checkpoints_for_image(image_path, preprocess_mode=mode) if mode != PREPROCESS_NONE else []
        lines.append(
            tr(self.lang, "luma_status_checkpoints").format(
                plain=self._checkpoint_summary(plain),
                filtered=self._checkpoint_summary(filtered),
            )
        )
        last = self._last_generation_preprocess.get(str(image_path.resolve()))
        if last and last != PREPROCESS_NONE:
            lines.append(tr(self.lang, "luma_status_last_run_on").format(filter=self._filter_label(last)))
        elif last == PREPROCESS_NONE:
            lines.append(tr(self.lang, "luma_status_last_run_off"))
        else:
            lines.append(tr(self.lang, "luma_status_last_run_unknown"))
        self.generate_luma_status.config(text="\n".join(lines))

    def _update_compare_column_headers(self):
        if not hasattr(self, "generate_result_without_header"):
            return
        mode = self._selected_preprocess_mode()
        uses_filter = mode != PREPROCESS_NONE
        image_path = self._selected_generate_image()
        last = self._last_generation_preprocess.get(str(image_path.resolve())) if image_path else None

        self.generate_result_with_header.config(
            text=tr(self.lang, "generate_result_filtered").format(filter=self._filter_label(mode))
            if uses_filter
            else tr(self.lang, "generate_result_plain"),
        )
        self.generate_result_without_header.config(text=tr(self.lang, "generate_result_plain"))

        columns = (
            (self.generate_result_without_header, self.generate_result_without_preview, False),
            (self.generate_result_with_header, self.generate_result_with_preview, True),
        )
        for header, preview, is_filtered_column in columns:
            is_next = uses_filter == is_filtered_column
            is_last = last is not None and (last != PREPROCESS_NONE) == is_filtered_column
            if is_next:
                header.config(fg=COLOR_ACCENT)
                preview.config(highlightbackground=COLOR_ACCENT, highlightthickness=3)
            elif is_last:
                header.config(fg=COLOR_WARN)
                preview.config(highlightbackground=COLOR_WARN, highlightthickness=2)
            else:
                header.config(fg=COLOR_MUTED)
                preview.config(highlightthickness=0)

    def _selected_generate_image(self):
        selection = self.image_list.curselection() if hasattr(self, "image_list") else ()
        if selection:
            return Path(self.images[selection[0]])
        if self.images:
            return Path(self.images[0])
        return None

    def _label_preview_bounds(self, label, *, min_height: int = 0):
        try:
            self.root.update_idletasks()
            width = label.winfo_width()
            height = label.winfo_height()
        except Exception:
            width = height = 0
        if width <= 32:
            width = PREVIEW_MAX
        else:
            width = max(1, width - 12)
        if height <= 32:
            height = min_height if min_height > 0 else PREVIEW_MAX
        else:
            height = max(min_height, height - 12) if min_height > 0 else max(1, height - 12)
        return width, height

    def _render_label_image_preview(self, label, path, hint_key, *, min_height: int = 0):
        if path is None or not Path(path).exists():
            label.config(image="", text=tr(self.lang, hint_key))
            label.image = None
            return
        data = render_source_image(path, self._label_preview_bounds(label, min_height=min_height))
        if not data:
            label.config(image="", text=tr(self.lang, "preview_unavailable"))
            label.image = None
            return
        image = PhotoImage(data=data)
        label.config(image=image, text="", bg=COLOR_PREVIEW_BG)
        label.image = image

    def _render_label_json_preview(self, label, path, hint_key, *, min_height: int = 0):
        if path is None or not Path(path).exists():
            label.config(image="", text=tr(self.lang, hint_key))
            label.image = None
            return
        data = render_geometry_json(path, self._label_preview_bounds(label, min_height=min_height))
        if not data:
            label.config(image="", text=tr(self.lang, "preview_unavailable"))
            label.image = None
            return
        image = PhotoImage(data=data)
        label.config(image=image, text="", bg=COLOR_PREVIEW_BG)
        label.image = image

    def _refresh_generate_compare(self, which=None):
        if not hasattr(self, "generate_source_before_preview"):
            return
        image_path = self._selected_generate_image()
        self._generate_compare_image = image_path
        if image_path is None:
            if which in (None, "source_before"):
                self.generate_source_before_preview.config(image="", text=tr(self.lang, "luma_before_hint"))
                self.generate_source_before_preview.image = None
            if which in (None, "source_after"):
                self.generate_source_after_preview.config(image="", text=tr(self.lang, "luma_after_hint"))
                self.generate_source_after_preview.image = None
            if which in (None, "result_without"):
                self.generate_result_without_preview.config(image="", text=tr(self.lang, "generate_no_checkpoint"))
                self.generate_result_without_preview.image = None
                self.generate_layers_without_label.config(text=tr(self.lang, "generate_no_checkpoint"))
            if which in (None, "result_with"):
                self.generate_result_with_preview.config(image="", text=tr(self.lang, "generate_no_checkpoint"))
                self.generate_result_with_preview.image = None
                self.generate_layers_with_label.config(text=tr(self.lang, "generate_no_checkpoint"))
            self._update_luma_status_label()
            self._update_compare_column_headers()
            return

        if which in (None, "source_before"):
            self._render_label_image_preview(
                self.generate_source_before_preview,
                image_path,
                "luma_before_hint",
                min_height=GENERATE_COMPARE_SOURCE_MIN,
            )
        mode = self._selected_preprocess_mode()
        if which in (None, "source_after"):
            after_path = None
            if mode != PREPROCESS_NONE:
                if preprocessed_image_exists(image_path, mode):
                    after_path = preprocessed_image_path(image_path, mode)
                else:
                    cached = self._preview_filter_payload.get(mode)
                    if cached and Path(cached.get("path", "")).exists():
                        after_path = Path(cached["path"])
                    elif load_cv2():
                        try:
                            from preprocess.filters import preprocess_image_file

                            after_path = preprocess_image_file(image_path, mode)
                        except Exception:
                            after_path = None
            self._render_label_image_preview(
                self.generate_source_after_preview,
                after_path,
                "luma_after_hint",
                min_height=GENERATE_COMPARE_SOURCE_MIN,
            )

        without_jsons = checkpoints_for_image(image_path, preprocess_mode=PREPROCESS_NONE)
        with_jsons = checkpoints_for_image(image_path, preprocess_mode=mode) if mode != PREPROCESS_NONE else []
        without_json = without_jsons[0] if without_jsons else None
        with_json = with_jsons[0] if with_jsons else None

        if which in (None, "result_without"):
            if without_json:
                self._render_label_json_preview(
                    self.generate_result_without_preview,
                    without_json,
                    "generate_no_checkpoint",
                    min_height=GENERATE_COMPARE_RESULT_MIN,
                )
            else:
                self.generate_result_without_preview.config(image="", text=tr(self.lang, "generate_no_checkpoint"))
                self.generate_result_without_preview.image = None
            self.generate_layers_without_label.config(
                text=self._result_layer_label(image_path, PREPROCESS_NONE, without_json)
            )
        if which in (None, "result_with"):
            if with_json:
                self._render_label_json_preview(
                    self.generate_result_with_preview,
                    with_json,
                    "generate_no_checkpoint",
                    min_height=GENERATE_COMPARE_RESULT_MIN,
                )
            else:
                self.generate_result_with_preview.config(image="", text=tr(self.lang, "generate_no_checkpoint"))
                self.generate_result_with_preview.image = None
            self.generate_layers_with_label.config(
                text=self._result_layer_label(image_path, mode, with_json)
            )
        self._update_luma_status_label()
        self._update_compare_column_headers()

    def _schedule_generate_compare_refresh(self, which=None):
        if not hasattr(self, "_generate_compare_jobs"):
            return
        job_key = which or "all"
        job = self._generate_compare_jobs.get(job_key)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self._generate_compare_jobs[job_key] = self.root.after(
            180,
            lambda w=which: self._run_generate_compare_refresh(w),
        )

    def _run_generate_compare_refresh(self, which):
        self._generate_compare_jobs.pop(which or "all", None)
        if self.closed:
            return
        self._refresh_generate_compare(which)

    def _build_text_tab(self):
        self.text_vinyl.build(self.text_tab)

    def _build_fh6_import_connection(self, parent) -> Frame:
        container = Frame(parent)

        step1 = ttk.LabelFrame(container, text=tr(self.lang, "step_game"))
        self.translated.append((step1, "step_game", "text"))
        step1.pack(fill=X, pady=(0, 10))
        step1_hint = self._label(step1, "step_game_hint", anchor="w", justify=LEFT)
        step1_hint.pack(fill=X, padx=10, pady=(8, 4))
        self._bind_wraplength(step1_hint, step1)
        game_row = Frame(step1)
        game_row.pack(fill=X, padx=10, pady=(0, 10))
        self._label(game_row, "game_profile").pack(side=LEFT)
        ttk.Combobox(
            game_row,
            values=list(PROFILES.keys()),
            textvariable=self.selected_game,
            state="readonly",
            width=8,
        ).pack(side=LEFT, padx=8)
        self._label(game_row, "pid").pack(side=LEFT)
        Entry(game_row, textvariable=self.selected_pid, width=30).pack(side=LEFT, padx=8)
        self._button(game_row, "refresh", self.refresh_processes).pack(side=LEFT)

        step2 = ttk.LabelFrame(container, text=tr(self.lang, "step_template"))
        self.translated.append((step2, "step_template", "text"))
        step2.pack(fill=X, pady=(0, 10))
        step2_hint = self._label(step2, "step_template_hint", anchor="w", justify=LEFT)
        step2_hint.pack(fill=X, padx=10, pady=(8, 4))
        self._bind_wraplength(step2_hint, step2)
        template_row = Frame(step2)
        template_row.pack(fill=X, padx=10, pady=(0, 10))
        self._label(template_row, "layer_count").pack(side=LEFT)
        entry = Entry(template_row, textvariable=self.layer_count, width=18, font=("Segoe UI", 13))
        entry.pack(side=LEFT, padx=8)
        if not hasattr(self, "layer_count_entry"):
            self.layer_count_entry = entry
            self.layer_count.trace_add("write", self._on_layer_count_changed)
        layer_info = Label(
            step2,
            textvariable=self.layer_count_info,
            anchor="w",
            justify=LEFT,
            bg=COLOR_PANEL,
            fg=COLOR_MUTED,
        )
        layer_info._theme_role = "muted"
        layer_info.pack(fill=X, padx=10, pady=(0, 10))
        if not hasattr(self, "_layer_info_label_bound"):
            self.translated.append((layer_info, "layer_import_info", "text"))
            self._layer_info_label_bound = True
        self._bind_wraplength(layer_info, step2)
        return container

    def _build_import_final_tab(self):
        paned = self._create_paned(
            self.import_final_tab, orient=HORIZONTAL, layout_key="import_horizontal", padx=10, pady=10
        )
        left_outer = Frame(paned)
        right = Frame(paned)
        paned.add(left_outer, weight=3)
        paned.add(right, weight=2)

        scroll_area, left = self._make_vertical_scroll(left_outer)
        scroll_area.pack(fill=BOTH, expand=True, padx=0, pady=10)

        tab_hint = self._label(left, "import_final_tab_hint", anchor="w", justify=LEFT, theme_role="hint")
        tab_hint.pack(fill=X, pady=(0, 10))
        self._bind_wraplength(tab_hint, left)

        self._build_fh6_import_connection(left).pack(fill=X)

        runs_box = ttk.LabelFrame(left, text=tr(self.lang, "import_final_runs"))
        self.translated.append((runs_box, "import_final_runs", "text"))
        runs_box.pack(fill=X, pady=(0, 10))
        runs_row = Frame(runs_box)
        runs_row.pack(fill=X, padx=10, pady=(8, 4))
        self._button(runs_row, "import_final_refresh_runs", self.refresh_generated_runs).pack(side=LEFT)
        self._button(runs_row, "import_final_pick_best", self.pick_best_safe_final_json).pack(side=RIGHT)
        runs_body = Frame(runs_box)
        runs_body.pack(fill=X, padx=10, pady=(0, 6))
        self.generated_runs_list = Listbox(runs_body, height=5)
        self.generated_runs_list.pack(fill=X, expand=True)
        self.generated_runs_list.bind("<<ListboxSelect>>", self._on_generated_run_select)
        self._generated_run_paths: list[Path] = []

        files_box = ttk.LabelFrame(left, text=tr(self.lang, "import_final_run_files"))
        self.translated.append((files_box, "import_final_run_files", "text"))
        files_box.pack(fill=X, pady=(0, 10))
        files_row = Frame(files_box)
        files_row.pack(fill=X, padx=10, pady=(8, 4))
        self._label(files_row, "json_files").pack(side=LEFT)
        self._button(files_row, "add_json", self.add_json).pack(side=RIGHT)
        self._button(files_row, "remove_json", self.remove_selected_json).pack(side=RIGHT, padx=(8, 0))
        self._button(files_row, "use_outputs", self.use_generated_outputs).pack(side=RIGHT, padx=8)
        json_body = Frame(files_box)
        json_body.pack(fill=X, padx=10, pady=(0, 6))
        json_scrollbar = ttk.Scrollbar(json_body, orient="vertical")
        json_scrollbar.pack(side=RIGHT, fill="y")
        self.json_list = Listbox(json_body, height=7, yscrollcommand=json_scrollbar.set)
        self.json_list.pack(side=LEFT, fill=X, expand=True)
        json_scrollbar.config(command=self.json_list.yview)
        self.json_list.bind("<<ListboxSelect>>", self._preview_selected_json)
        best_toggle = Checkbutton(
            files_box,
            text=tr(self.lang, "import_final_use_best"),
            variable=self.use_best_safe_final,
            onvalue="1",
            offvalue="0",
        )
        best_toggle.pack(anchor="w", padx=10, pady=(0, 10))
        self.translated.append((best_toggle, "import_final_use_best", "text"))
        self._final_run_json_paths: list[Path] = []

        step4 = ttk.LabelFrame(right, text=tr(self.lang, "step_import"))
        self.translated.append((step4, "step_import", "text"))
        step4.pack(fill=X, pady=(0, 10))
        import_hint = self._label(step4, "step_import_hint", anchor="w", justify=LEFT)
        import_hint.pack(fill=X, padx=10, pady=(8, 4))
        self._bind_wraplength(import_hint, step4)
        easy_hint = self._label(step4, "easy_import_hint", anchor="w", justify=LEFT, theme_role="muted")
        easy_hint.pack(fill=X, padx=10, pady=4)
        self._bind_wraplength(easy_hint, step4)
        admin_note = self._label(step4, "admin_note", anchor="w", justify=LEFT, theme_role="hint")
        admin_note.pack(fill=X, padx=10, pady=4)
        self._bind_wraplength(admin_note, step4)
        actions = Frame(step4)
        actions.pack(fill=X, padx=10, pady=12)
        self._button(
            actions,
            "import_final_import",
            self.start_import_final,
            font=("Segoe UI", 13, "bold"),
            height=2,
        ).pack(side=LEFT, fill=X, expand=True)
        self.advanced_button = self._button(actions, "show_advanced", self.toggle_advanced)
        self.advanced_button.pack(side=LEFT, padx=(8, 0))

        self.advanced_frame = ttk.LabelFrame(right, text=tr(self.lang, "advanced_options"))
        self.translated.append((self.advanced_frame, "advanced_options", "text"))
        self._field(self.advanced_frame, "manual_count", self.count_address, row=0)
        self._field(self.advanced_frame, "manual_table", self.table_address, row=1)
        self._button(self.advanced_frame, "auto_locate", self.start_auto_locate).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(8, 4)
        )

        self._label(right, "import_preview", anchor="w", font=("Segoe UI", 12, "bold")).pack(fill=X, pady=(8, 0))
        self.import_preview_label = Label(
            right,
            text=tr(self.lang, "preview_hint"),
            bg=COLOR_PREVIEW_BG,
            fg=COLOR_PREVIEW_FG,
            width=56,
            height=20,
        )
        self.import_preview_label.pack(fill=BOTH, expand=True, pady=6)
        self.import_preview_label.bind("<Configure>", self._schedule_preview_refresh)
        self.refresh_generated_runs()

    def _build_export_game_tab(self):
        paned = self._create_paned(
            self.export_game_tab, orient=HORIZONTAL, layout_key="export_game_horizontal", padx=10, pady=10
        )
        left = Frame(paned)
        right = Frame(paned)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        scroll_area, body = self._make_vertical_scroll(left)
        scroll_area.pack(fill=BOTH, expand=True, padx=0, pady=10)

        hint = self._label(body, "export_game_tab_hint", anchor="w", justify=LEFT, theme_role="hint")
        hint.pack(fill=X, pady=(0, 10))
        self._bind_wraplength(hint, body)

        self._build_fh6_import_connection(body).pack(fill=X)

        export_box = ttk.LabelFrame(body, text=tr(self.lang, "export_game_tab"))
        self.translated.append((export_box, "export_game_tab", "text"))
        export_box.pack(fill=X, pady=(0, 10))
        export_actions = Frame(export_box)
        export_actions.pack(fill=X, padx=10, pady=12)
        self._button(
            export_actions,
            "export_game_json",
            self.start_export_typecode_json,
            font=("Segoe UI", 13, "bold"),
            height=2,
        ).pack(side=LEFT, fill=X, expand=True)
        self._button(export_actions, "export_open_folder", self.open_typecode_export_folder).pack(side=LEFT, padx=(8, 0))

        admin_note = self._label(right, "admin_note", anchor="w", justify=LEFT, theme_role="hint")
        admin_note.pack(fill=X, padx=10, pady=8)
        self._bind_wraplength(admin_note, right)
        typecode_hint = self._label(right, "handmade_section_hint", anchor="w", justify=LEFT, theme_role="hint")
        typecode_hint.pack(fill=X, padx=10, pady=4)
        self._bind_wraplength(typecode_hint, right)

    def _build_handmade_tab(self):
        paned = self._create_paned(self.handmade_tab, orient=HORIZONTAL, layout_key="import_horizontal", padx=10, pady=10)
        left = Frame(paned)
        right = Frame(paned)
        paned.add(left, weight=3)
        paned.add(right, weight=2)

        scroll_area, body = self._make_vertical_scroll(left)
        scroll_area.pack(fill=BOTH, expand=True, padx=0, pady=10)

        hint = self._label(body, "handmade_tab_hint", anchor="w", justify=LEFT, theme_role="hint")
        hint.pack(fill=X, pady=(0, 10))
        self._bind_wraplength(hint, body)

        self._build_fh6_import_connection(body).pack(fill=X)

        actions = ttk.LabelFrame(body, text=tr(self.lang, "import_handmade_tab"))
        self.translated.append((actions, "import_handmade_tab", "text"))
        actions.pack(fill=X, pady=(0, 10))
        row = Frame(actions)
        row.pack(fill=X, padx=10, pady=(10, 8))
        self._button(row, "handmade_choose_json", self.add_handmade_json).pack(side=LEFT)
        self._button(row, "handmade_import", self.start_import_handmade).pack(side=RIGHT)

        trim_toggle = Checkbutton(
            actions,
            text=tr(self.lang, "typecode_trim_after_import"),
            variable=self.typecode_trim_after_import,
            onvalue="1",
            offvalue="0",
        )
        trim_toggle.pack(anchor="w", padx=10, pady=(0, 2))
        self.translated.append((trim_toggle, "typecode_trim_after_import", "text"))
        unknown_toggle = Checkbutton(
            actions,
            text=tr(self.lang, "typecode_allow_unknown"),
            variable=self.typecode_allow_unknown,
            onvalue="1",
            offvalue="0",
        )
        unknown_toggle.pack(anchor="w", padx=10, pady=(0, 10))
        self.translated.append((unknown_toggle, "typecode_allow_unknown", "text"))

        files_box = ttk.LabelFrame(body, text=tr(self.lang, "step_json"))
        self.translated.append((files_box, "step_json", "text"))
        files_box.pack(fill=X, pady=(0, 10))
        files_hint = self._label(files_box, "step_json_hint", anchor="w", justify=LEFT, theme_role="hint")
        files_hint.pack(fill=X, padx=10, pady=(8, 4))
        self._bind_wraplength(files_hint, files_box)

        list_row = Frame(files_box)
        list_row.pack(fill=X, padx=10, pady=(0, 8))
        self.handmade_json_list = Listbox(list_row, height=7)
        self.handmade_json_list.pack(side=LEFT, fill=X, expand=True)
        self.handmade_json_list.bind("<<ListboxSelect>>", self._preview_selected_handmade_json)
        self._button(list_row, "remove_json", self.remove_selected_handmade_json).pack(side=RIGHT, padx=(8, 0))
        self.handmade_status_label = self._label(files_box, "handmade_status_none", anchor="w", justify=LEFT, theme_role="muted")
        self.handmade_status_label.pack(fill=X, padx=10, pady=(0, 10))
        self._bind_wraplength(self.handmade_status_label, files_box)

        self._label(right, "import_preview", anchor="w", font=("Segoe UI", 12, "bold")).pack(fill=X, pady=(0, 8))
        self.handmade_preview_label = Label(
            right,
            text=tr(self.lang, "preview_hint"),
            bg=COLOR_PREVIEW_BG,
            fg=COLOR_PREVIEW_FG,
            width=56,
            height=20,
        )
        self.handmade_preview_label.pack(fill=BOTH, expand=True)
        self.handmade_preview_label.bind("<Configure>", lambda _e: self._schedule_handmade_preview_refresh())
        self._handmade_preview_job = None

        self.handmade_json_files: list[Path] = []
        self._update_handmade_status()

    def refresh_generated_runs(self):
        if not hasattr(self, "generated_runs_list"):
            return
        self._generated_run_paths = discover_generated_run_folders(ROOT)
        self.generated_runs_list.delete(0, END)
        for path in self._generated_run_paths:
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            except OSError:
                mtime = "?"
            self.generated_runs_list.insert(END, f"{path.name}  ({mtime})")
        if self._generated_run_paths:
            self.generated_runs_list.selection_set(0)
            self._on_generated_run_select()

    def _on_generated_run_select(self, _event=None):
        if not hasattr(self, "generated_runs_list"):
            return
        selection = list(self.generated_runs_list.curselection())
        if not selection:
            return
        try:
            run_folder = self._generated_run_paths[selection[0]]
        except IndexError:
            return
        self._final_run_json_paths = json_candidates_for_run_folder(run_folder)
        if not hasattr(self, "json_list"):
            return
        self.json_list.delete(0, END)
        self.json_files.clear()
        for path in self._final_run_json_paths:
            try:
                layers = geometry_shape_count(path)
            except OSError:
                layers = "?"
            label = f"{path.name}  ({layers} layers)"
            self.json_list.insert(END, label)
            self.json_files.append(path)
        if self.use_best_safe_final.get() == "1":
            self.pick_best_safe_final_json(select_only=True)
        elif self.json_files:
            self.json_list.selection_set(len(self.json_files) - 1)
            self.show_json_preview(self.json_files[-1])
            self._update_import_layer_info(self.json_files[-1])

    def pick_best_safe_final_json(self, select_only: bool = False):
        selection = list(self.generated_runs_list.curselection()) if hasattr(self, "generated_runs_list") else []
        run_folder = None
        if selection:
            try:
                run_folder = self._generated_run_paths[selection[0]]
            except (IndexError, AttributeError):
                run_folder = None
        if run_folder is None and getattr(self, "_generated_run_paths", None):
            run_folder = self._generated_run_paths[0]
        if run_folder is None:
            self.log_line(tr(self.lang, "log_no_run_folder_selected"))
            return
        best = best_safe_final_json(run_folder)
        if best is None:
            self.log_line(tr(self.lang, "log_no_json_in_run").format(path=run_folder))
            return
        if best not in self.json_files:
            self.json_files.append(best)
            self._render_lists()
        try:
            index = self.json_files.index(best)
        except ValueError:
            return
        if hasattr(self, "json_list"):
            self.json_list.selection_clear(0, END)
            self.json_list.selection_set(index)
            self.json_list.see(index)
        self.show_json_preview(best)
        self._update_import_layer_info(best)
        if not select_only:
            self.log_line(tr(self.lang, "log_selected_best_final").format(name=best.name))

    def open_typecode_export_folder(self):
        TYPECODE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(TYPECODE_EXPORT_DIR)

    def start_import_final(self):
        if not self.json_files:
            self.log_line(tr(self.lang, "no_json_selected"))
            return
        layer_count = self.layer_count.get().strip()
        if not layer_count:
            self.log_line(tr(self.lang, "layer_count_required"))
            if hasattr(self, "layer_count_entry"):
                self.layer_count_entry.config(highlightbackground=COLOR_WARN, highlightthickness=1)
            return
        if hasattr(self, "layer_count_entry"):
            self.layer_count_entry.config(highlightbackground=COLOR_BORDER, highlightthickness=0)
        pid = self.ensure_live_game_pid()
        if not pid:
            return
        self.status.set(tr(self.lang, "running"))
        threading.Thread(target=self._import_final_worker, args=(pid,), daemon=True).start()

    def _import_final_worker(self, pid):
        game = self.selected_game.get() or "fh6"
        layer_count = self.layer_count.get().strip()
        try:
            locations = self._resolve_import_locations(pid, game, layer_count)
        except ValueError as exc:
            self.queue.put(("log", str(exc)))
            self.queue.put(("status", tr(self.lang, "failed")))
            return
        except RuntimeError:
            self.queue.put(("status", tr(self.lang, "failed")))
            return
        pid = locations["pid"]
        count_address = locations.get("count_address")
        table_address = locations.get("table_address")
        import_env = locations.get("import_env", {})
        for path in list(self.json_files):
            path = Path(path)
            if is_typecode_geometry_json(path):
                self.queue.put(
                    ("log", tr(self.lang, "log_skipped_handmade_on_final").format(name=path.name))
                )
                continue
            if game == "fh6" and layer_count:
                self._check_json_layer_fit(path, layer_count)
            cmd = [*helper_command("main"), "--game", game, "--no-preview", "--pid", str(pid)]
            if count_address:
                cmd.extend(["--layer-count-address", f"0x{int(count_address):x}"])
            if table_address:
                cmd.extend(["--layer-table-address", f"0x{int(table_address):x}"])
            if game == "fh6" and layer_count:
                cmd.extend(["--layer-count-value", str(layer_count)])
            cmd.append(str(path.resolve()))
            code = self.run_subprocess(cmd, extra_env=import_env)
            if code != 0:
                self.queue.put(("status", tr(self.lang, "failed")))
                return
        self.queue.put(("status", tr(self.lang, "done")))

    def add_handmade_json(self):
        files = filedialog.askopenfilenames(
            title=tr(self.lang, "handmade_choose_json"),
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not files:
            return
        for item in files:
            path = Path(item)
            if path.exists() and path not in self.handmade_json_files:
                self.handmade_json_files.append(path)
        self._render_handmade_list()
        if files:
            self._set_handmade_preview(Path(files[0]))

    def remove_selected_handmade_json(self):
        if not hasattr(self, "handmade_json_list"):
            return
        selection = list(self.handmade_json_list.curselection())
        if not selection:
            self.log_line(tr(self.lang, "no_json_selected"))
            return
        for index in sorted(selection, reverse=True):
            try:
                del self.handmade_json_files[index]
            except IndexError:
                pass
        self._render_handmade_list()
        self.handmade_preview_label.config(image="", text=tr(self.lang, "preview_hint"))
        self.handmade_preview_label.image = None

    def _render_handmade_list(self):
        if not hasattr(self, "handmade_json_list"):
            return
        self.handmade_json_list.delete(0, END)
        for path in self.handmade_json_files:
            self.handmade_json_list.insert(END, str(path))
        self._update_handmade_status()

    def _preview_selected_handmade_json(self, _event=None):
        if not hasattr(self, "handmade_json_list"):
            return
        selection = self.handmade_json_list.curselection()
        if selection:
            self._set_handmade_preview(self.handmade_json_files[selection[0]])

    def _schedule_handmade_preview_refresh(self):
        if not hasattr(self, "handmade_preview_label") or self.closed:
            return
        if self._handmade_preview_job is not None:
            try:
                self.root.after_cancel(self._handmade_preview_job)
            except Exception:
                pass
        self._handmade_preview_job = self.root.after(180, lambda: self._refresh_handmade_preview())

    def _refresh_handmade_preview(self):
        self._handmade_preview_job = None
        path = getattr(self, "_handmade_preview_path", None)
        if path:
            self._set_handmade_preview(path)

    def _set_handmade_preview(self, path: Path):
        self._handmade_preview_path = Path(path)
        if not path or not Path(path).exists():
            self.handmade_preview_label.config(image="", text=tr(self.lang, "preview_hint"))
            self.handmade_preview_label.image = None
            return
        data = render_geometry_json(path, self._preview_bounds(self.handmade_preview_label))
        if not data:
            self.handmade_preview_label.config(image="", text=tr(self.lang, "preview_unavailable"))
            self.handmade_preview_label.image = None
            return
        image = PhotoImage(data=data)
        self.handmade_preview_label.config(image=image, text="", bg=COLOR_PREVIEW_BG)
        self.handmade_preview_label.image = image
        self._update_handmade_status(path)

    def _update_handmade_status(self, path: Path | None = None):
        if not hasattr(self, "handmade_status_label"):
            return
        if path is None:
            path = getattr(self, "_handmade_preview_path", None)
        if not path or not Path(path).exists():
            self.handmade_status_label.config(text=tr(self.lang, "handmade_status_none"))
            return
        try:
            summary = typecode_shape_summary(path, allow_unknown_low_byte=False)
        except Exception:
            self.handmade_status_label.config(text=tr(self.lang, "handmade_status_none"))
            return
        self.handmade_status_label.config(
            text=tr(self.lang, "handmade_status_counts").format(
                total=summary.get("total", 0),
                supported=summary.get("supported", 0),
                unsupported=summary.get("unsupported", 0),
            )
        )

    def start_import_handmade(self):
        if not getattr(self, "handmade_json_files", None):
            self.log_line(tr(self.lang, "no_json_selected"))
            return
        layer_count = self.layer_count.get().strip()
        if not layer_count:
            self.log_line(tr(self.lang, "layer_count_required"))
            return
        pid = self.ensure_live_game_pid()
        if not pid:
            return
        self.status.set(tr(self.lang, "running"))
        threading.Thread(target=self._import_handmade_worker, args=(pid,), daemon=True).start()

    def _import_handmade_worker(self, pid):
        game = self.selected_game.get() or "fh6"
        layer_count = self.layer_count.get().strip()
        try:
            locations = self._resolve_import_locations(pid, game, layer_count)
        except Exception as exc:
            self.queue.put(("log", str(exc)))
            self.queue.put(("status", tr(self.lang, "failed")))
            return
        for path in list(self.handmade_json_files):
            path = Path(path)
            if not is_typecode_geometry_json(path):
                self.queue.put(("log", tr(self.lang, "log_skipped_non_handmade").format(name=path.name)))
                continue
            code = self._import_typecode_json_file(path, locations, layer_count)
            if code != 0:
                self.queue.put(("status", tr(self.lang, "failed")))
                return
        self.queue.put(("status", tr(self.lang, "done")))

    def _build_image_preview_tab(self):
        body = Frame(self.preview_tab_frame)
        body.pack(fill=BOTH, expand=True, padx=10, pady=10)

        controls = ttk.LabelFrame(body, text=tr(self.lang, "preview_tab"))
        self.translated.append((controls, "preview_tab", "text"))
        controls.pack(fill=X, pady=(0, 10))

        hint = self._label(controls, "preview_tab_hint", anchor="w", justify=LEFT, theme_role="hint")
        hint.pack(fill=X, padx=10, pady=(8, 6))
        self._bind_wraplength(hint, controls)

        actions = Frame(controls)
        actions.pack(fill=X, padx=10, pady=(0, 8))
        self._button(actions, "preview_choose_image", self.choose_preview_image).pack(side=LEFT)
        self._button(actions, "preview_use_generate_image", self.use_generate_image_for_preview).pack(side=LEFT, padx=8)
        self._button(actions, "preview_apply_generate", self.apply_preview_filter_to_generate).pack(side=LEFT)
        self._button(actions, "preview_open_folder", self.open_preview_folder).pack(side=RIGHT)

        self.preview_status_label = Label(
            controls,
            text=tr(self.lang, "preview_output_folder").format(path=PREVIEW_EXPORT_ROOT),
            anchor="w",
            justify=LEFT,
            bg=COLOR_PANEL,
            fg=COLOR_MUTED,
        )
        self.preview_status_label._theme_role = "muted"
        self.preview_status_label.pack(fill=X, padx=10, pady=(0, 6))
        self._bind_wraplength(self.preview_status_label, controls)

        select_hint = self._label(controls, "preview_select_filter", anchor="w", theme_role="hint")
        select_hint.pack(fill=X, padx=10, pady=(0, 10))
        self._bind_wraplength(select_hint, controls)

        scroll_area, grid_host = self._make_vertical_scroll(body)
        scroll_area.pack(fill=BOTH, expand=True)
        self.preview_filter_grid = Frame(grid_host)
        self.preview_filter_grid.pack(fill=BOTH, expand=True)
        preview_row_count = (len(PREPROCESS_FILTERS) + 1) // 2
        for row_index in range(preview_row_count):
            self.preview_filter_grid.rowconfigure(row_index, weight=1, minsize=340)
        for column in range(2):
            self.preview_filter_grid.columnconfigure(column, weight=1)

        for index, spec in enumerate(PREPROCESS_FILTERS):
            row, column = divmod(index, 2)
            card = Frame(
                self.preview_filter_grid,
                bg=COLOR_PANEL_ALT,
                highlightthickness=1,
                highlightbackground=COLOR_BORDER,
                cursor="hand2",
            )
            card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)
            card.columnconfigure(0, weight=1)
            card.rowconfigure(3, weight=1, minsize=260)

            title = Label(
                card,
                text=tr(self.lang, spec.label_key),
                anchor="w",
                bg=COLOR_PANEL_ALT,
                fg=COLOR_TEXT,
                font=("Segoe UI", 10, "bold"),
                cursor="hand2",
            )
            title.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
            estimate = Label(card, text="", anchor="w", bg=COLOR_PANEL_ALT, fg=COLOR_MUTED, cursor="hand2")
            estimate.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 2))
            card_hint = Label(
                card,
                text=tr(self.lang, spec.hint_key),
                anchor="w",
                justify=LEFT,
                wraplength=280,
                bg=COLOR_PANEL_ALT,
                fg=COLOR_MUTED,
                font=("Segoe UI", 9),
                cursor="hand2",
            )
            card_hint.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
            preview = Label(
                card,
                text=tr(self.lang, "luma_before_hint"),
                bg=COLOR_PREVIEW_BG,
                fg=COLOR_PREVIEW_FG,
                cursor="hand2",
            )
            preview.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
            preview.bind("<Configure>", lambda _e, mid=spec.mode_id: self._schedule_preview_filter_render(mid))

            def _select(_e=None, mode_id=spec.mode_id):
                self._set_preprocess_mode(mode_id, refresh_ui=True)

            for widget in (card, title, estimate, card_hint, preview):
                widget.bind("<Button-1>", _select)
            self._preview_filter_cards[spec.mode_id] = {
                "card": card,
                "title": title,
                "estimate": estimate,
                "hint": card_hint,
                "preview": preview,
                "spec": spec,
            }

        self._highlight_preview_filter_cards()

    def _preview_card_bounds(self, label):
        try:
            width = label.winfo_width()
            height = label.winfo_height()
        except Exception:
            width = height = 0
        if width <= 40 or height <= 40:
            return 360, 260
        return max(1, width - 12), max(1, height - 12)

    def _schedule_preview_filter_render(self, mode_id: str):
        job = self._preview_render_jobs.get(mode_id)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self._preview_render_jobs[mode_id] = self.root.after(
            180, lambda mid=mode_id: self._render_preview_filter_card(mid)
        )

    def _render_preview_filter_card(self, mode_id: str):
        self._preview_render_jobs[mode_id] = None
        if self.closed:
            return
        widgets = self._preview_filter_cards.get(mode_id)
        if not widgets:
            return
        label = widgets["preview"]
        estimate_label = widgets["estimate"]
        entry = self._preview_filter_payload.get(mode_id)
        if entry and entry.get("estimate"):
            estimate_label.config(text=tr(self.lang, "preview_estimate").format(count=int(entry["estimate"])))
        else:
            estimate_label.config(text=tr(self.lang, "preview_estimate_unknown"))
        path = entry.get("path") if entry else None
        if not path or not Path(path).exists():
            label.config(image="", text=tr(self.lang, "luma_before_hint"))
            label.image = None
            return
        data = render_source_image(path, self._preview_card_bounds(label))
        if not data:
            label.config(image="", text=tr(self.lang, "preview_unavailable"))
            label.image = None
            return
        image = PhotoImage(data=data)
        label.config(image=image, text="", bg=COLOR_PREVIEW_BG)
        label.image = image

    def _highlight_preview_filter_cards(self):
        if not self._preview_filter_cards:
            return
        selected = self._selected_preprocess_mode()
        for mode_id, widgets in self._preview_filter_cards.items():
            card = widgets["card"]
            if mode_id == selected:
                card.config(highlightbackground=COLOR_ACCENT, highlightthickness=3)
            else:
                card.config(highlightbackground=COLOR_BORDER, highlightthickness=1)

    def _start_preview_filter_compute(self, source: Path):
        if not load_cv2():
            messagebox.showerror(APP_DISPLAY_NAME, tr(self.lang, "preview_unavailable"))
            return
        if self._preview_compute_running:
            return
        source = Path(source)
        self._preview_source_path = source.resolve()
        self._preview_filter_payload = {}
        self._preview_compute_running = True
        self.preview_status_label.config(text=tr(self.lang, "preview_processing").format(path=source.name))
        for widgets in self._preview_filter_cards.values():
            widgets["estimate"].config(text=tr(self.lang, "preview_estimate_unknown"))
            widgets["preview"].config(image="", text=tr(self.lang, "luma_before_hint"))
            widgets["preview"].image = None
        threading.Thread(target=self._preview_filter_worker, args=(source,), daemon=True).start()

    def _preview_filter_worker(self, source: Path):
        try:
            payload = build_preview_payload(source)
            self.queue.put(("preview_filters_ready", (str(source.resolve()), payload)))
        except Exception as exc:
            self.queue.put(("preview_filters_failed", (str(source), str(exc))))

    def _apply_preview_filters_ready(self, source_key: str, payload: dict):
        self._preview_compute_running = False
        if str(getattr(self, "_preview_source_path", "")) != source_key:
            return
        self._preview_filter_payload = payload
        self.preview_status_label.config(
            text=tr(self.lang, "preview_output_folder").format(path=PREVIEW_EXPORT_ROOT)
        )
        for mode_id in self._preview_filter_cards:
            self._render_preview_filter_card(mode_id)
        self._highlight_preview_filter_cards()
        self._refresh_generate_compare()

    def choose_preview_image(self):
        path = filedialog.askopenfilename(
            title=tr(self.lang, "preview_choose_image"),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")],
        )
        if path:
            self._start_preview_filter_compute(Path(path))

    def _ensure_generate_images(self, paths: list[Path]) -> list[Path]:
        added_paths: list[Path] = []
        for item in paths:
            path = Path(item)
            if not path.exists() or path in self.images:
                continue
            self.images.append(path)
            added_paths.append(path)
            self._load_existing_checkpoints_for_image(path)
        if added_paths:
            self._render_lists()
            select_path = added_paths[0]
            try:
                index = self.images.index(select_path)
                self.image_list.selection_clear(0, END)
                self.image_list.selection_set(index)
                self.image_list.see(index)
            except (ValueError, TclError):
                pass
            self.show_source_preview(select_path)
        return added_paths

    def use_generate_image_for_preview(self):
        image_path = self._selected_generate_image()
        if image_path is None:
            messagebox.showinfo(APP_DISPLAY_NAME, tr(self.lang, "luma_status_none"))
            return
        image_path = Path(image_path)
        added = self._ensure_generate_images([image_path])
        if added:
            self.log_line(tr(self.lang, "preview_image_added_to_generate").format(name=image_path.name))
        elif image_path in self.images:
            try:
                index = self.images.index(image_path)
                self.image_list.selection_clear(0, END)
                self.image_list.selection_set(index)
                self.image_list.see(index)
            except (ValueError, TclError):
                pass
            self.show_source_preview(image_path)
            self.log_line(tr(self.lang, "preview_image_already_on_generate").format(name=image_path.name))
        self._start_preview_filter_compute(image_path)

    def apply_preview_filter_to_generate(self):
        try:
            self.main_tabs.select(self.generate_tab)
        except Exception:
            pass

    def open_preview_folder(self):
        PREVIEW_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
        os.startfile(PREVIEW_EXPORT_ROOT)

    def _copy_to_clipboard(self, text: str):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update_idletasks()
            self.log_line(tr(self.lang, "colors_copied"))
        except Exception as exc:
            self.log_line(tr(self.lang, "log_clipboard_failed").format(error=exc))

    def _build_tools_tab(self):
        self.tools_workspace.build(self.tools_tab)

    def _start_resource_monitor(self):
        if not self._resource_monitor_settings.enabled:
            return
        self._resource_monitor_backend = ResourceMonitorBackend()
        threading.Thread(target=self._resource_monitor_worker, daemon=True).start()

    def _resource_monitor_worker(self):
        settings = self._resource_monitor_settings
        backend = self._resource_monitor_backend
        if backend is None:
            return
        while not self.shutdown_event.is_set():
            snapshot = backend.poll()
            init_error = backend.consume_init_error_for_log()
            if init_error:
                self.queue.put(("log", f"Resource monitor: {init_error}"))
            self.queue.put(("resource_monitor", snapshot))
            if self.shutdown_event.wait(settings.poll_seconds):
                break

    def _peak_temperature(self, snapshot: ResourceSnapshot) -> float | None:
        temps = [snapshot.cpu_temp_c, snapshot.gpu_temp_c]
        measured = [temp for temp in temps if temp is not None]
        return max(measured) if measured else None

    def _handle_resource_heat_state(self, snapshot: ResourceSnapshot) -> None:
        heat_state = evaluate_heat_state(snapshot)
        previous = self._resource_heat_state
        self._resource_heat_state = heat_state

        panel = self._header_telemetry
        if panel is None:
            return

        if heat_state == "critical":
            banner = tr(self.lang, "resource_heat_critical_banner")
        elif heat_state == "warning":
            banner = tr(self.lang, "resource_heat_warning_banner")
        else:
            banner = ""
        panel.set_heat_state(heat_state, banner_text=banner)

        if heat_state == previous:
            return

        peak = self._peak_temperature(snapshot)
        peak_text = f"{peak:.0f}" if peak is not None else "?"
        if heat_state == "warning" and previous == "normal":
            self.log_line(tr(self.lang, "resource_heat_log_warning").format(temp=peak_text))
        elif heat_state == "critical" and previous in ("normal", "warning"):
            self.log_line(tr(self.lang, "resource_heat_log_critical").format(temp=peak_text))
        elif heat_state == "normal" and previous in ("warning", "critical"):
            self.log_line(tr(self.lang, "resource_temp_returned_normal").format(temp=peak_text))

    def _apply_resource_snapshot(self, snapshot: ResourceSnapshot):
        self._resource_monitor_snapshot = snapshot
        panel = self._header_telemetry
        if panel is None:
            return
        panel.apply_snapshot(snapshot)
        self._handle_resource_heat_state(snapshot)

    def _build_tutorial_tab(self):
        frame = Frame(self.tutorial_tab)
        frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        tutorial_scroll = ttk.Scrollbar(frame, orient="vertical")
        tutorial_scroll.pack(side=RIGHT, fill="y")
        self.tutorial_text = Text(frame, wrap="word", yscrollcommand=tutorial_scroll.set)
        self.tutorial_text.pack(side=LEFT, fill=BOTH, expand=True)
        tutorial_scroll.config(command=self.tutorial_text.yview)
        self._bind_text_mousewheel(self.tutorial_text)
        self._update_tutorial()

    def _build_acknowledgements_tab(self):
        frame = Frame(self.acknowledgements_tab)
        frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        acknowledgements_scroll = ttk.Scrollbar(frame, orient="vertical")
        acknowledgements_scroll.pack(side=RIGHT, fill="y")
        self.acknowledgements_text = Text(frame, wrap="word", yscrollcommand=acknowledgements_scroll.set)
        self.acknowledgements_text.pack(side=LEFT, fill=BOTH, expand=True)
        acknowledgements_scroll.config(command=self.acknowledgements_text.yview)
        self._bind_text_mousewheel(self.acknowledgements_text)
        self._update_acknowledgements()

    def _build_log(self):
        row = Frame(self.log_pane)
        row.pack(fill=X, padx=0, pady=(6, 2))
        self._label(row, "logs", anchor="w").pack(side=LEFT)
        self._button(row, "export_logs", self.export_detailed_log).pack(side=RIGHT)
        self._label(row, "progress", anchor="e").pack(side=LEFT, padx=(18, 4))
        progress_label = Label(row, textvariable=self.progress_text, anchor="w", bg=COLOR_BG, fg=COLOR_INFO)
        progress_label._theme_role = "info"
        progress_label.pack(side=LEFT, fill=X, expand=True)
        resize_hint = self._label(self.log_pane, "layout_resize_hint", anchor="w", theme_role="muted")
        resize_hint.pack(fill=X, padx=0, pady=(0, 4))
        log_frame = Frame(self.log_pane)
        log_frame.pack(fill=BOTH, expand=True, padx=0, pady=(0, 8))
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical")
        log_scroll.pack(side=RIGHT, fill="y")
        self.log = Text(log_frame, height=9, yscrollcommand=log_scroll.set)
        self.log.pack(side=LEFT, fill=BOTH, expand=True)
        log_scroll.config(command=self.log.yview)
        self._bind_text_mousewheel(self.log)

    def _field(self, parent, key, variable, row, values=None, readonly=False):
        self._label(parent, key, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=5)
        if values:
            widget = ttk.Combobox(parent, values=values, textvariable=variable, state="readonly" if readonly else "normal")
        else:
            widget = Entry(parent, textvariable=variable)
        widget.grid(row=row, column=1, sticky="ew", pady=5)
        parent.columnconfigure(1, weight=1)
        return widget

    def _on_language(self, _event=None):
        self.lang = LANGUAGES.get(self.lang_combo.get(), "en")
        save_language_code(ROOT, self.lang)
        self._sync_theme_combo()
        self._apply_ui_fonts()
        for widget, key, option in self.translated:
            try:
                if option == "text_upper":
                    widget.config(text=tr(self.lang, key).upper())
                else:
                    widget.config(**{option: tr(self.lang, key)})
            except Exception:
                pass
        for tab, key in self._workspace_tab_specs():
            self.main_tabs.tab(tab, text=tr(self.lang, key))
        if hasattr(self, "tools_workspace"):
            self.tools_workspace.on_language_changed()
        if hasattr(self, "generate_compare_hint"):
            self.generate_compare_hint.config(text=tr(self.lang, "generate_select_image"))
        if hasattr(self, "preview_status_label"):
            if self._preview_compute_running and self._preview_source_path:
                self.preview_status_label.config(
                    text=tr(self.lang, "preview_processing").format(path=Path(self._preview_source_path).name)
                )
            else:
                self.preview_status_label.config(
                    text=tr(self.lang, "preview_output_folder").format(path=PREVIEW_EXPORT_ROOT)
                )
        if self._preview_filter_cards:
            for mode_id, widgets in self._preview_filter_cards.items():
                widgets["title"].config(text=self._filter_label(mode_id))
                spec = widgets.get("spec")
                if spec and widgets.get("hint"):
                    widgets["hint"].config(text=tr(self.lang, spec.hint_key))
            self._refresh_preprocess_mode_combo()
            self._update_preprocess_filter_active_hint()
            self._highlight_preview_filter_cards()
            for mode_id in self._preview_filter_cards:
                self._render_preview_filter_card(mode_id)
        self.text_vinyl.on_language_changed()
        if self.photo is None and hasattr(self, "import_preview_label"):
            self.import_preview_label.config(text=tr(self.lang, "preview_hint"))
        if hasattr(self, "generate_source_before_preview"):
            self._refresh_generate_compare()
        if hasattr(self, "advanced_button"):
            self.advanced_button.config(text=tr(self.lang, "hide_advanced" if self.advanced_visible else "show_advanced"))
        if hasattr(self, "setting_description"):
            self._update_setting_description()
        self._update_tutorial()
        self._update_acknowledgements()
        self.text_vinyl.update_theme_hints()
        if self._resource_monitor_snapshot is not None:
            self._apply_resource_snapshot(self._resource_monitor_snapshot)
        self.status.set(tr(self.lang, "ready"))

    def _update_tutorial(self):
        self.tutorial_text.config(state="normal")
        self.tutorial_text.delete("1.0", END)
        self.tutorial_text.insert(END, tr(self.lang, "tutorial"))
        self.tutorial_text.config(state="disabled")

    def _update_acknowledgements(self):
        self.acknowledgements_text.config(state="normal")
        self.acknowledgements_text.delete("1.0", END)
        self.acknowledgements_text.insert(END, get_acknowledgements(self.lang))
        self.acknowledgements_text.config(state="disabled")

    def _update_setting_description(self, _event=None):
        if not self._widget_alive(getattr(self, "setting_description", None)):
            return
        item = self._selected_setting()
        try:
            self.setting_description.config(text=item["description"] if item else tr(self.lang, "no_settings_profiles"))
        except TclError:
            return
        if item and self.use_custom_settings.get() != "1":
            values = item.get("values", {})
            self.custom_stop_at.set(values.get("stopAt", "3000"))
            self.custom_max_resolution.set(values.get("maxResolution", "1200"))
            self.custom_random_samples.set(values.get("randomSamples", "3000"))
            self.custom_mutated_samples.set(values.get("mutatedSamples", "1000"))
            self.custom_save_at.set(values.get("saveAt", values.get("stopAt", "3000")))
            self.custom_preprocess_mode.set(values.get("preprocessMode", "none"))
            self._set_preprocess_mode(
                normalize_preprocess_mode(values.get("preprocessMode", "none")),
                refresh_ui=True,
            )

    def _sync_preprocess_from_custom(self, *_args):
        if self.use_custom_settings.get() != "1":
            return
        self.preprocess_mode.set(normalize_preprocess_mode(self.custom_preprocess_mode.get()))
        self._refresh_preprocess_mode_combo()
        if self._preview_filter_cards:
            self._highlight_preview_filter_cards()

    def _sync_custom_state(self):
        state = "normal" if self.use_custom_settings.get() == "1" else "disabled"
        for entry in getattr(self, "custom_fields", []):
            entry.config(state=state)
        if state == "disabled":
            self._update_setting_description()

    def _effective_setting(self):
        setting = self._selected_setting()
        if not setting:
            return None
        overlay = {}
        if self.use_custom_settings.get() == "1":
            overlay.update(self._custom_values())
        mode = self._selected_preprocess_mode()
        if mode != PREPROCESS_NONE:
            overlay["preprocessMode"] = mode
        if overlay:
            return write_custom_settings(setting, overlay)
        return setting

    def _custom_values(self):
        custom = {
            "stopAt": self.custom_stop_at.get(),
            "maxResolution": self.custom_max_resolution.get(),
            "randomSamples": self.custom_random_samples.get(),
            "mutatedSamples": self.custom_mutated_samples.get(),
            "saveAt": self.custom_save_at.get(),
            "preprocessMode": self.custom_preprocess_mode.get(),
        }
        if not custom["saveAt"] and custom["stopAt"]:
            custom["saveAt"] = custom["stopAt"]
        return custom

    def save_custom_preset(self):
        setting = self._selected_setting()
        if not setting:
            self.log_line(tr(self.lang, "log_no_quality_profile"))
            return
        USER_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = filedialog.asksaveasfilename(
            title=tr(self.lang, "save_custom_preset"),
            initialdir=str(USER_SETTINGS_DIR),
            initialfile=f"user-preset-{timestamp}.ini",
            defaultextension=".ini",
            filetypes=[("INI settings", "*.ini"), ("All files", "*.*")],
        )
        if not output:
            return
        try:
            saved_path = write_user_settings_preset(setting, self._custom_values(), output)
        except OSError as exc:
            self.log_line(tr(self.lang, "log_save_preset_failed").format(error=exc))
            return
        self._reload_settings(preferred_path=saved_path)
        self.log_line(tr(self.lang, "saved_preset").format(path=saved_path))

    def toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced_frame.pack(fill=X, pady=(0, 10))
        else:
            self.advanced_frame.pack_forget()
        self.advanced_button.config(text=tr(self.lang, "hide_advanced" if self.advanced_visible else "show_advanced"))

    def _selected_setting(self):
        label = self.selected_profile.get()
        for item in self.settings:
            if item["label"] == label:
                return item
        return self.settings[0] if self.settings else None

    def _reload_settings(self, preferred_path=None):
        previous = preferred_path
        if previous is None:
            current = self._selected_setting()
            previous = current.get("path") if current else None
        try:
            previous_resolved = Path(previous).resolve() if previous else None
        except OSError:
            previous_resolved = None
        self.settings = load_settings()
        values = [item["label"] for item in self.settings]
        if hasattr(self, "profile_combo"):
            self.profile_combo["values"] = values
        selected = None
        if previous_resolved:
            for item in self.settings:
                try:
                    if item["path"].resolve() == previous_resolved:
                        selected = item["label"]
                        break
                except OSError:
                    pass
        if selected is None and values:
            selected = values[min(2, len(values) - 1)]
        self.selected_profile.set(selected or "")
        self._update_setting_description()

    def _render_lists(self):
        self._render_image_list()
        self._render_json_list()

    def _render_image_list(self) -> None:
        if not hasattr(self, "image_list"):
            return
        self.image_list.delete(0, END)
        for path in self.images:
            self.image_list.insert(END, self._image_list_display(path))
        self._refresh_generate_compare()

    def _render_json_list(self) -> None:
        if not hasattr(self, "json_list"):
            return
        self.json_list.delete(0, END)
        for path in self.json_files:
            self.json_list.insert(END, self._json_list_display(path))
        self._update_import_layer_info()

    def _add_json_paths(self, paths):
        added = 0
        for output in best_geometry_jsons(paths):
            output = Path(output)
            if output not in self.outputs:
                self.outputs.append(output)
            if output not in self.json_files:
                self.json_files.append(output)
                added += 1
        return added

    def _load_existing_checkpoints_for_image(self, image_path, log_to_queue=False):
        existing = best_geometry_jsons(generated_jsons(image_path))
        if not existing:
            return 0
        added = self._add_json_paths(existing[:1])
        if added:
            message = tr(self.lang, "existing_checkpoints_found").format(image=Path(image_path).name, count=len(existing))
            if log_to_queue:
                self.queue.put(("log", message))
            else:
                self.log_line(message)
        return added

    def _queue_generated_outputs(self, source_image, before, *, generator_input=None, preprocess_mode=None):
        generator_input = Path(generator_input or source_image)
        after = generated_jsons(generator_input)
        new_outputs = best_geometry_jsons([path for path in after if path.resolve() not in before])
        if not new_outputs and after:
            new_outputs = best_geometry_jsons(after[:1])
        for output in new_outputs:
            if output not in self.outputs:
                self.outputs.append(output)
            if output not in self.json_files:
                self.json_files.append(output)
            mode = normalize_preprocess_mode(preprocess_mode) if preprocess_mode else PREPROCESS_NONE
            if mode == PREPROCESS_NONE:
                path_mode = preprocess_mode_for_path(output)
                if path_mode:
                    mode = path_mode
            if mode == PREPROCESS_NONE:
                self.queue.put(("log", tr(self.lang, "generate_log_output_plain").format(path=output.name)))
            else:
                self.queue.put(
                    (
                        "log",
                        tr(self.lang, "generate_log_output_filter").format(
                            filter=self._filter_label(mode), path=output.name
                        ),
                    )
                )
        return new_outputs

    def log_line(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._record_detail(f"UI: {message}")
        if not hasattr(self, "log"):
            return
        self.log.insert(END, f"[{timestamp}] {message}\n")
        self.log.see(END)

    def _record_detail(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        text = str(message).rstrip()
        entry = f"[{timestamp}] {text}"
        with self.detailed_log_lock:
            self.detailed_log_lines.append(entry)
            self.detailed_log_chars += len(entry) + 1
            while self.detailed_log_chars > DETAILED_LOG_MEMORY_LIMIT and self.detailed_log_lines:
                removed = self.detailed_log_lines.popleft()
                self.detailed_log_chars -= len(removed) + 1

    def _format_command(self, cmd):
        return subprocess.list2cmdline([str(item) for item in cmd])

    def _diagnostic_log_header(self):
        try:
            profile = self._selected_setting()
            profile_name = profile["label"] if profile else ""
            profile_path = str(profile["path"]) if profile else ""
        except Exception:
            profile_name = ""
            profile_path = ""
        selected_pid = self.selected_pid_value()
        generator_exists = GENERATOR_EXE.exists()
        lines = [
            f"{APP_DISPLAY_NAME} detailed log",
            f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
            f"App version: {__version__}",
            f"Python: {sys.version.replace(os.linesep, ' ')}",
            f"Platform: {platform.platform()}",
            f"Root: {ROOT}",
            f"Generator: {GENERATOR_EXE} exists={generator_exists}",
            f"Selected game: {self.selected_game.get()}",
            f"Selected PID: {selected_pid}",
            f"Selected process label: {self.selected_pid.get()}",
            f"Template layer count: {self.layer_count.get()}",
            f"Manual count address: {self.count_address.get()}",
            f"Manual table address: {self.table_address.get()}",
            f"Quality profile: {profile_name}",
            f"Quality profile path: {profile_path}",
            f"Custom settings enabled: {self.use_custom_settings.get()}",
            f"Images: {len(self.images)}",
            *[f"  image: {path}" for path in self.images],
            f"JSON files: {len(self.json_files)}",
            *[f"  json: {path}" for path in self.json_files],
            f"Generated outputs: {len(self.outputs)}",
            *[f"  output: {path}" for path in self.outputs],
        ]
        if SESSION_PATH.exists():
            try:
                session_text = SESSION_PATH.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                session_text = f"<failed to read session: {exc}>"
            lines.extend(["Current FH6 session file:", session_text[:4000]])
        return "\n".join(lines).rstrip() + "\n"

    def _build_detailed_log_text(self):
        header = self._diagnostic_log_header()
        try:
            visible_log = self.log.get("1.0", END).strip()
        except Exception:
            visible_log = ""
        with self.detailed_log_lock:
            detail_log = "\n".join(self.detailed_log_lines).strip()
        body = "\n\n".join(
            section
            for section in (
                "=== Detailed Event Log ===\n" + (detail_log or "<empty>"),
                "=== Visible UI Log ===\n" + (visible_log or "<empty>"),
            )
            if section
        )
        marker = f"\n\n--- Log truncated to last {DETAILED_LOG_OUTPUT_LIMIT} characters ---\n"
        prefix = header + "\n"
        budget = DETAILED_LOG_OUTPUT_LIMIT - len(prefix)
        if budget <= len(marker):
            result = (prefix + body)[-DETAILED_LOG_OUTPUT_LIMIT:]
            return result if len(result) <= DETAILED_LOG_OUTPUT_LIMIT else result[-DETAILED_LOG_OUTPUT_LIMIT:]
        if len(body) > budget:
            body = marker + body[-(budget - len(marker)):]
        result = (prefix + body).rstrip()
        if len(result) >= DETAILED_LOG_OUTPUT_LIMIT:
            result = result[:DETAILED_LOG_OUTPUT_LIMIT - 1]
        return result + "\n"

    def export_detailed_log(self):
        initial = f"forza-painter-fh6-log-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        output = filedialog.asksaveasfilename(
            title=tr(self.lang, "export_logs"),
            defaultextension=".txt",
            initialfile=initial,
            filetypes=[("Text log", "*.txt"), ("All files", "*.*")],
        )
        if not output:
            return
        text = redact_sensitive_log_text(self._build_detailed_log_text())
        try:
            Path(output).write_text(text, encoding="utf-8")
        except OSError as exc:
            self.log_line(tr(self.lang, "log_export_detailed_failed").format(error=exc))
            return
        self.log_line(
            tr(self.lang, "log_export_detailed_done").format(
                path=output, chars=len(text), limit=DETAILED_LOG_OUTPUT_LIMIT
            )
        )

    def start_update_check(self):
        if self.closed or self.update_check_started:
            return
        if not updates_enabled():
            self.update_state = {"status": "disabled"}
            return
        self.update_check_started = True
        threading.Thread(target=self._update_check_worker, daemon=True).start()

    def _update_check_worker(self):
        try:
            latest_version = fetch_latest_release_version()
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            self.queue.put(("update_failed", str(exc)))
            return

        changelog = ""
        try:
            changelog = fetch_text_url(UPDATE_CHANGELOG_URL)
        except (OSError, urllib.error.URLError, ValueError) as exc:
            self._record_detail(f"Update changelog fetch failed: {exc}")

        payload = {
            "current": __version__,
            "latest": latest_version,
            "changelog": extract_changelog_section(changelog, latest_version),
        }
        if version_key(latest_version) > version_key(__version__):
            self.queue.put(("update_available", payload))
        else:
            self.queue.put(("update_current", payload))

    def _set_update_indicator(self, text="", color=COLOR_WARN):
        indicator = getattr(self, "update_indicator", None)
        if indicator is None:
            return
        indicator.config(text=text, fg=color)
        if text:
            if not indicator.winfo_ismapped():
                indicator.pack(anchor="e", pady=(0, 6))
        elif indicator.winfo_ismapped():
            indicator.pack_forget()

    def _handle_update_failed(self, error):
        self.update_state = {"status": "failed", "error": error}
        self._set_update_indicator("!", COLOR_WARN)
        self.log_line(tr(self.lang, "log_update_check_failed").format(error=error))

    def _handle_update_current(self, payload):
        self.update_state = {"status": "current", **payload}
        self._set_update_indicator("")
        self._record_detail(f"Update check OK: latest={payload.get('latest')}")

    def _handle_update_available(self, payload):
        self.update_state = {"status": "available", **payload}
        self._set_update_indicator("!", COLOR_ACCENT)
        self.log_line(
            tr(self.lang, "log_update_available").format(latest=payload.get("latest"), current=__version__)
        )
        self.show_update_dialog(payload)

    def show_update_status(self, _event=None):
        status = self.update_state.get("status")
        if status == "failed":
            messagebox.showwarning(
                tr(self.lang, "update_check_failed_title"),
                tr(self.lang, "update_check_failed_message").format(error=self.update_state.get("error", "")),
                parent=self.root,
            )
        elif status == "available":
            self.show_update_dialog(self.update_state)

    def show_update_dialog(self, payload=None):
        payload = payload or self.update_state
        if self.update_dialog is not None and self.update_dialog.winfo_exists():
            self.update_dialog.lift()
            self.update_dialog.focus_force()
            return

        latest = payload.get("latest", "")
        changelog = payload.get("changelog") or tr(self.lang, "update_no_changelog")
        dialog = Toplevel(self.root)
        self.update_dialog = dialog
        dialog.title(tr(self.lang, "update_available_title"))
        dialog.configure(bg=COLOR_BG)
        dialog.resizable(True, True)

        body = Frame(dialog, bg=COLOR_BG)
        body.pack(fill=BOTH, expand=True, padx=16, pady=14)
        Label(
            body,
            text=tr(self.lang, "update_available_message").format(current=__version__, latest=latest),
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            justify=LEFT,
            anchor="w",
            font=("Segoe UI", 11, "bold"),
        ).pack(fill=X, pady=(0, 10))
        Label(
            body,
            text=tr(self.lang, "changelog"),
            bg=COLOR_BG,
            fg=COLOR_MUTED,
            anchor="w",
        ).pack(fill=X)

        text_frame = Frame(body, bg=COLOR_BG)
        text_frame.pack(fill=BOTH, expand=True, pady=(4, 12))
        changelog_text = Text(text_frame, width=80, height=18, wrap="word")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=changelog_text.yview)
        changelog_text.configure(
            yscrollcommand=scrollbar.set,
            bg=COLOR_INPUT,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            selectbackground=COLOR_ACCENT_DARK,
            selectforeground=COLOR_SELECT_FG,
            highlightthickness=1,
            highlightbackground=COLOR_BORDER,
            relief="flat",
        )
        changelog_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill="y")
        changelog_text.insert(END, changelog)
        changelog_text.config(state="disabled")

        actions = Frame(body, bg=COLOR_BG)
        actions.pack(fill=X)

        def close_update_dialog():
            self.update_dialog = None
            dialog.destroy()

        def open_update_page():
            webbrowser.open(UPDATE_RELEASE_URL)
            close_update_dialog()

        Button(
            actions,
            text=tr(self.lang, "update_later"),
            command=close_update_dialog,
            bg=COLOR_BUTTON,
            fg=COLOR_TEXT,
            activebackground=COLOR_BUTTON_ACTIVE,
            activeforeground=COLOR_TEXT,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
        ).pack(side=RIGHT)
        Button(
            actions,
            text=tr(self.lang, "update_open_page"),
            command=open_update_page,
            bg=COLOR_ACCENT_DARK,
            fg=COLOR_SELECT_FG,
            activebackground=COLOR_ACCENT,
            activeforeground=COLOR_SELECT_FG,
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
        ).pack(side=RIGHT, padx=(0, 8))

        dialog.protocol("WM_DELETE_WINDOW", close_update_dialog)

    def _reset_generation_eta(self):
        self.eta_intervals.clear()
        self.eta_last_layer = None
        self.eta_last_time = None
        self.eta_smoothed_seconds_per_layer = None
        self.eta_display_remaining = None
        self.eta_max_layer_seen = None
        self.eta_recycle_notice_active = False

    def _format_remaining_time(self, seconds):
        seconds = max(0, int(round(seconds)))
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        suffix = eta_suffix(self.lang)
        if hours:
            return f"{hours}h {minutes:02d}m {suffix}"
        if minutes:
            return f"{minutes}m {seconds:02d}s {suffix}"
        return f"{seconds}s {suffix}"

    def _progress_with_eta(self, friendly):
        match = re.match(r"Generated layer\s+(\d+)/(\d+)", friendly)
        if not match:
            return friendly
        current = int(match.group(1))
        total = int(match.group(2))
        now = time.time()
        if self.eta_max_layer_seen is not None and current <= self.eta_max_layer_seen:
            if current < self.eta_max_layer_seen and not self.eta_recycle_notice_active:
                self.eta_recycle_notice_active = True
                return tr(self.lang, "generator_recycled_layers").format(max_layer=self.eta_max_layer_seen, total=total)
            return None
        self.eta_max_layer_seen = current
        self.eta_recycle_notice_active = False
        if self.eta_last_layer is None:
            self.eta_last_layer = current
            self.eta_last_time = now
            return friendly
        layer_delta = current - self.eta_last_layer
        elapsed_seconds = now - self.eta_last_time
        self.eta_last_layer = current
        self.eta_last_time = now
        if layer_delta <= 0:
            return friendly
        if elapsed_seconds >= 0.05:
            self.eta_intervals.append(elapsed_seconds / layer_delta)
        remaining_layers = max(0, total - current)
        if remaining_layers == 0:
            self.eta_display_remaining = 0
            eta_time = datetime.fromtimestamp(now).strftime("%H:%M:%S")
            return f"{friendly} | ETA {eta_time} ({self._format_remaining_time(0)})"
        if not self.eta_intervals:
            return friendly
        intervals = sorted(self.eta_intervals)
        seconds_per_layer = intervals[len(intervals) // 2]
        if self.eta_smoothed_seconds_per_layer is None:
            self.eta_smoothed_seconds_per_layer = seconds_per_layer
        else:
            self.eta_smoothed_seconds_per_layer = (
                self.eta_smoothed_seconds_per_layer * 0.75
                + seconds_per_layer * 0.25
            )
        remaining_seconds = self.eta_smoothed_seconds_per_layer * remaining_layers
        if self.eta_display_remaining is None:
            self.eta_display_remaining = remaining_seconds
        else:
            expected_remaining = max(0, self.eta_display_remaining - elapsed_seconds)
            self.eta_display_remaining = expected_remaining * 0.8 + remaining_seconds * 0.2
        remaining_seconds = self.eta_display_remaining
        eta_time = datetime.fromtimestamp(now + remaining_seconds).strftime("%H:%M:%S")
        return f"{friendly} | ETA {eta_time} ({self._format_remaining_time(remaining_seconds)})"

    def friendly_generator_line(self, line):
        text = (line or "").strip()
        if not text:
            return None
        progress = re.match(r"\[(\d+)/(\d+)\]\s+(.*)", text)
        if progress:
            current, total, detail = progress.groups()
            if "Added rotated ellipse" in detail:
                return f"Generated layer {current}/{total}"
            if "Saved geometry checkpoint" in detail:
                return f"Saved JSON checkpoint {current}/{total}"
            if "Saved preview snapshot" in detail:
                return f"Updated preview {current}/{total}"
            if "Step completed" in detail:
                return None
            return None
        if text.startswith("Loaded image:"):
            return text
        if text.startswith("Settings:"):
            return text
        if text.startswith("OpenCL: Selected device"):
            return text
        if text.startswith("Scoring mode:"):
            return text
        if text in ("FINISHED",):
            return text
        if "error" in text.lower() or "failed" in text.lower() or "panic" in text.lower():
            return text
        return None

    def queue_generator_message(self, friendly, last_message):
        if not friendly or friendly == last_message:
            return last_message
        if friendly.startswith("Generated layer "):
            message = self._progress_with_eta(friendly)
            if not message:
                return last_message
            self.queue.put(("progress", message))
            self.queue.put(("log", message))
            return friendly
        if friendly == "FINISHED":
            self.queue.put(("progress", friendly))
        self.queue.put(("log", friendly))
        return friendly

    def _int_setting(self, setting, key, default=0):
        try:
            return int(str(setting.get("values", {}).get(key, default)).strip())
        except (TypeError, ValueError):
            return default

    def _log_generation_load_warning(self, setting):
        stop_at = self._int_setting(setting, "stopAt")
        random_samples = self._int_setting(setting, "randomSamples")
        mutated_samples = self._int_setting(setting, "mutatedSamples")
        max_resolution = self._int_setting(setting, "maxResolution")
        if random_samples >= 200000 or mutated_samples >= 8000 or max_resolution >= 2000:
            self.queue.put((
                "log",
                "High quality generation selected: "
                f"layers={stop_at}, randomSamples={random_samples}, "
                f"mutatedSamples={mutated_samples}, maxResolution={max_resolution}. "
                "The first layer can take a long time before progress appears.",
            ))

    def _generator_exit_message(self, returncode):
        if returncode in (3221225477, -1073741819):
            return (
                "GPU generator crashed with Windows access violation 0xC0000005. "
                "This is usually an OpenCL/GPU driver or generator runtime crash, not an import error. "
                "Try a lower preset, a lower Max Resolution / Random Samples, update the GPU driver, "
                "or convert the source image to a normal PNG/JPG path and retry."
            )
        if returncode == 3221226505:
            return (
                "GPU generator crashed with Windows stack buffer overrun 0xC0000409. "
                "Try updating the GPU driver, lowering the preset, or converting the image to PNG/JPG."
            )
        return f"Generator exited with code {returncode}."

    def add_images(self):
        files = filedialog.askopenfilenames(
            title=tr(self.lang, "dialog_choose_images"),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
        )
        added_paths = []
        for item in files:
            path = Path(item)
            if path.exists() and path not in self.images:
                self.images.append(path)
                added_paths.append(path)
                self._load_existing_checkpoints_for_image(path)
        self._render_lists()
        if files:
            self.show_source_preview(Path(files[0]))
        if added_paths:
            existing_added = sum(1 for path in added_paths if generated_jsons(path))
            if existing_added:
                self.log_line(tr(self.lang, "cannot_resume_checkpoint"))

    def remove_selected_image(self):
        selection = list(self.image_list.curselection())
        if not selection:
            self.log_line(tr(self.lang, "no_image_selected"))
            return
        for index in sorted(selection, reverse=True):
            try:
                del self.images[index]
            except IndexError:
                pass
        self._render_lists()
        self._refresh_generate_compare()

    def _unique_preset_destination(self, source_path):
        USER_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        stem = source_path.stem
        suffix = source_path.suffix or ".ini"
        candidate = USER_SETTINGS_DIR / f"{stem}{suffix}"
        index = 2
        while candidate.exists():
            candidate = USER_SETTINGS_DIR / f"{stem} ({index}){suffix}"
            index += 1
        return candidate

    def import_preset(self):
        files = filedialog.askopenfilenames(
            title=tr(self.lang, "dialog_import_preset"),
            filetypes=[("INI settings", "*.ini"), ("All files", "*.*")],
        )
        imported = []
        for item in files:
            source = Path(item)
            if not source.exists():
                continue
            destination = self._unique_preset_destination(source)
            try:
                shutil.copy2(source, destination)
                imported.append(destination)
            except OSError as exc:
                self.log_line(tr(self.lang, "log_import_preset_failed").format(path=source, error=exc))
        if imported:
            self._reload_settings(preferred_path=imported[-1])
            self.log_line(tr(self.lang, "imported_presets").format(count=len(imported)))

    def open_preset_folder(self):
        USER_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(USER_SETTINGS_DIR)

    def add_json(self):
        files = filedialog.askopenfilenames(
            title=tr(self.lang, "dialog_choose_geometry_json"),
            filetypes=[("Geometry JSON", "*.json"), ("All files", "*.*")],
        )
        for item in files:
            path = Path(item)
            if path.exists() and path not in self.json_files:
                self.json_files.append(path)
        self._render_lists()
        if files:
            self.show_json_preview(Path(files[0]))

    def remove_selected_json(self):
        selection = list(self.json_list.curselection())
        if not selection:
            self.log_line(tr(self.lang, "no_json_selected"))
            return
        for index in sorted(selection, reverse=True):
            try:
                del self.json_files[index]
            except IndexError:
                pass
        self._render_lists()
        if hasattr(self, "import_preview_label"):
            self.import_preview_label.config(image="", text=tr(self.lang, "preview_hint"))
            self.import_preview_label.image = None

    def use_generated_outputs(self):
        for path in self.outputs:
            if path.exists() and path not in self.json_files:
                self.json_files.append(path)
        self._render_lists()
        self.log_line(tr(self.lang, "log_added_generated_json").format(count=len(self.outputs)))

    def _preview_selected_image(self, _event=None):
        selection = self.image_list.curselection()
        if selection:
            self.show_source_preview(self.images[selection[0]])
        self._refresh_generate_compare()

    def _preview_selected_json(self, _event=None):
        selection = self.json_list.curselection()
        if selection:
            path = self.json_files[selection[0]]
            self.show_json_preview(path)
            self._update_import_layer_info(path)

    def _on_layer_count_changed(self, *_args):
        self._update_import_layer_info()

    def _update_import_layer_info(self, json_path=None):
        from generator_backend import geometry_shape_count

        if json_path is None:
            selection = self.json_list.curselection()
            if selection:
                json_path = self.json_files[selection[0]]
            elif self.json_files:
                json_path = self.json_files[-1]
        if not json_path:
            self.layer_count_info.set(tr(self.lang, "layer_import_info"))
            return
        try:
            json_layers = geometry_shape_count(json_path)
            name = Path(json_path).name
            template_text = self.layer_count.get().strip()
            if not template_text:
                self.layer_count_info.set(
                    f"Selected {name}: {json_layers} drawable layers. Enter your in-game template layer count."
                )
                return
            template_layers = int(template_text)
            usable = max(0, template_layers - 4)
            message = f"Selected {name}: {json_layers} drawable layers | Template: {template_layers} (usable ~{usable})"
            if json_layers > usable:
                message += " — template too small (+4 boundary layers required)"
            elif json_layers < max(1, int(usable * 0.75)):
                message += " — JSON may look sparse on this template"
            else:
                message += " — fit looks OK"
            self.layer_count_info.set(message)
        except (OSError, ValueError, TypeError) as exc:
            self.layer_count_info.set(f"Selected {Path(json_path).name}: unable to read layer count ({exc})")

    def _active_preview_label(self):
        if self._is_import_final_tab_active() and hasattr(self, "import_preview_label"):
            return self.import_preview_label
        return self._active_generation_result_label()

    def _set_import_preview(self, data):
        if not hasattr(self, "import_preview_label"):
            return
        if not data:
            self.import_preview_label.config(image="", text=tr(self.lang, "preview_unavailable"), bg=COLOR_PREVIEW_BG, fg=COLOR_PREVIEW_FG)
            self.import_preview_label.image = None
            return
        image = PhotoImage(data=data)
        self.import_preview_label.config(image=image, text="", bg=COLOR_PREVIEW_BG)
        self.import_preview_label.image = image

    def _preview_bounds(self, label=None):
        label = label or self._active_preview_label()
        if label is None:
            return PREVIEW_MAX, PREVIEW_MAX
        try:
            self.root.update_idletasks()
            width = label.winfo_width()
            height = label.winfo_height()
        except Exception:
            width = height = 0
        if width <= 32 or height <= 32:
            return PREVIEW_MAX, PREVIEW_MAX
        return max(1, width - 16), max(1, height - 16)

    def _schedule_preview_refresh(self, _event=None):
        if not self.current_preview_request or self.closed:
            return
        if self.preview_resize_job is not None:
            try:
                self.root.after_cancel(self.preview_resize_job)
            except Exception:
                pass
        self.preview_resize_job = self.root.after(180, self._refresh_current_preview)

    def _refresh_current_preview(self):
        self.preview_resize_job = None
        if self.closed:
            return
        request = self.current_preview_request
        if not request:
            return
        kind, path = request
        path = Path(path)
        if not path.exists():
            return
        if kind == "json":
            data = render_geometry_json(path, self._preview_bounds())
        else:
            data = render_source_image(path, self._preview_bounds())
        self.show_preview(data)

    def show_json_preview(self, path):
        path = Path(path)
        self.current_preview_request = ("json", path)
        data = render_geometry_json(path, self._preview_bounds(self.import_preview_label))
        self._set_import_preview(data)

    def show_preview(self, data):
        if not data:
            self.current_preview_request = None
            message = tr(self.lang, "preview_unavailable")
            if self._is_import_final_tab_active():
                self._set_import_preview(None)
                if hasattr(self, "import_preview_label"):
                    self.import_preview_label.config(text=message)
            label = self._active_generation_result_label()
            if label is not None:
                label.config(image="", text=message, bg=COLOR_PREVIEW_BG, fg=COLOR_PREVIEW_FG)
                label.image = None
            return
        self.photo = data
        if self._is_import_final_tab_active():
            self._set_import_preview(data)
            return
        label = self._active_generation_result_label()
        if label is None:
            return
        image = PhotoImage(data=data)
        label.config(image=image, text="", bg=COLOR_PREVIEW_BG)
        label.image = image

    def show_source_preview(self, path):
        path = Path(path)
        self.current_preview_request = ("source", path)
        self._refresh_generate_compare()

    def show_preview_file(self, path, remember=True):
        path = Path(path)
        if remember:
            self.current_preview_request = ("file", path)
        if path.suffix.lower() == ".json":
            data = render_geometry_json(path, self._preview_bounds())
            if data:
                if hasattr(self, "generate_result_without_preview"):
                    uses_filter = self._selected_preprocess_mode() != PREPROCESS_NONE
                    label = self.generate_result_with_preview if uses_filter else self.generate_result_without_preview
                    self._render_label_json_preview(label, path, "generate_no_checkpoint")
                    self._refresh_generate_compare("result_with" if uses_filter else "result_without")
                else:
                    self.show_preview(data)
                return
        if hasattr(self, "generate_result_without_preview"):
            label = self._active_generation_result_label()
            self._render_label_image_preview(label, path, "generate_no_checkpoint")
            return
        data = render_source_image(path, self._preview_bounds())
        if data:
            self.show_preview(data)
            return
        try:
            image = PhotoImage(file=str(path))
        except Exception:
            self.show_preview(None)
            return
        self.photo = image
        label = self._active_generation_result_label()
        if label is None:
            return
        label.config(image=image, text="", bg=COLOR_PREVIEW_BG)
        label.image = image

    def refresh_processes(self):
        self.processes = game_processes()
        values = [item["label"] for item in self.processes]
        if not values:
            values = [tr(self.lang, "no_game")]
        self.process_combo["values"] = values
        if self.processes:
            self.selected_pid.set(values[0])
            self.selected_game.set(self.processes[0]["profile"])
        else:
            self.selected_pid.set("")

    def selected_pid_value(self):
        raw = self.selected_pid.get()
        match = re.search(r"pid\s+(\d+)", raw, re.I)
        if match:
            return int(match.group(1))
        try:
            return int(raw.strip())
        except ValueError:
            return None

    def _pid_matches_game(self, pid, game):
        profile = PROFILES.get(game)
        if not pid or not profile:
            return False
        try:
            process_name = psutil.Process(pid).name().lower()
        except psutil.Error:
            return False
        return process_name in [name.lower() for name in profile.process_names]

    def ensure_live_game_pid(self):
        game = self.selected_game.get() or "fh6"
        pid = self.selected_pid_value()
        if self._pid_matches_game(pid, game):
            return pid
        if pid:
            self.log_line(tr(self.lang, "log_process_stale").format(pid=pid))
        self.refresh_processes()
        game = self.selected_game.get() or game
        pid = self.selected_pid_value()
        if self._pid_matches_game(pid, game):
            return pid
        self.log_line(tr(self.lang, "log_no_game_process"))
        return None

    def stop_generate(self):
        with self.generation_lock:
            if not self.generation_running:
                self.log_line(tr(self.lang, "no_generation_running"))
                return
            proc = self.current_generator_proc
        self.log_line(tr(self.lang, "stopping_generation"))
        self.shutdown_event.set()
        if proc is not None:
            self._terminate_process(proc)
        self.status.set(tr(self.lang, "stopped"))

    def start_generate(self):
        with self.generation_lock:
            if self.generation_running:
                self.log_line(tr(self.lang, "log_generation_already_running"))
                return
            self.generation_running = True
        if not self.images:
            with self.generation_lock:
                self.generation_running = False
            self.log_line(tr(self.lang, "log_no_images_selected"))
            return
        setting = self._effective_setting()
        if not setting:
            with self.generation_lock:
                self.generation_running = False
            self.log_line(tr(self.lang, "log_no_quality_profile"))
            return
        if not GENERATOR_EXE.exists():
            with self.generation_lock:
                self.generation_running = False
            self.log_line(tr(self.lang, "log_missing_generator").format(path=GENERATOR_EXE))
            return
        self.shutdown_event.clear()
        self._reset_generation_eta()
        self.progress_text.set("")
        self.status.set(tr(self.lang, "running"))
        if hasattr(self, "generate_button"):
            self.generate_button.config(state="disabled")
        if hasattr(self, "stop_generate_button"):
            self.stop_generate_button.config(state="normal")
        threading.Thread(target=self._generate_worker, args=(setting,), daemon=True).start()

    def _generate_worker(self, setting):
        try:
            self.queue.put(("log", f"Selected profile: {setting['path'].name}"))
            self._log_generation_load_warning(setting)
            for image_path in list(self.images):
                if self.shutdown_event.is_set():
                    self.queue.put(("status", tr(self.lang, "stopped")))
                    return
                self._reset_generation_eta()
                preprocess_mode = setting_preprocess_mode(setting)
                input_image = preprocess_input_image(image_path, setting)
                if preprocess_mode != PREPROCESS_NONE:
                    self.queue.put(
                        (
                            "log",
                            tr(self.lang, "generate_log_pipeline_filter").format(
                                filter=self._filter_label(preprocess_mode),
                                path=Path(input_image).name,
                            ),
                        )
                    )
                else:
                    self.queue.put(("log", tr(self.lang, "generate_log_pipeline_plain")))
                if input_image != image_path:
                    self.queue.put(("log", f"Preprocessed image: {input_image}"))
                before = {path.resolve() for path in generated_jsons(input_image)}
                preview_path = generator_preview_path(input_image)
                if preview_path.exists():
                    try:
                        preview_path.unlink()
                    except OSError:
                        pass
                self.queue.put(("log", f"Generating: {image_path}"))
                self.queue.put(("preview_file", image_path))
                flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                cmd = build_generator_command(input_image, setting)
                self._record_detail(f"GENERATOR COMMAND: {self._format_command(cmd)}")
                self.queue.put(("log", f"Running GPU generator with {setting['path'].name}"))
                if self.shutdown_event.is_set():
                    self.queue.put(("status", tr(self.lang, "stopped")))
                    return
                proc = self._popen_registered(
                    cmd,
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=flags,
                    env=build_generator_env(),
                )
                if proc is None:
                    self.queue.put(("status", tr(self.lang, "stopped")))
                    return
                with self.generation_lock:
                    self.current_generator_proc = proc

                last_json = None
                last_preview_mtime = None
                last_generator_message = None
                next_preview_scan = 0.0
                next_json_scan = 0.0
                output_queue = queue.Queue()

                def _read_generator_output():
                    try:
                        for raw_line in proc.stdout:
                            self._record_detail(f"GENERATOR RAW: {raw_line.rstrip()}")
                            output_queue.put(raw_line)
                    finally:
                        output_queue.put(None)

                reader = threading.Thread(target=_read_generator_output, daemon=True)
                reader.start()

                def _drain_generator_output():
                    nonlocal last_generator_message
                    while True:
                        try:
                            raw_line = output_queue.get_nowait()
                        except queue.Empty:
                            break
                        if raw_line is None:
                            continue
                        friendly = self.friendly_generator_line(raw_line)
                        last_generator_message = self.queue_generator_message(friendly, last_generator_message)

                try:
                    while proc.poll() is None:
                        if self.shutdown_event.is_set():
                            self._terminate_process(proc)
                            outputs = self._queue_generated_outputs(
                                image_path, before, generator_input=input_image, preprocess_mode=preprocess_mode
                            )
                            self.queue.put(
                                ("generation_preprocess", (str(Path(image_path).resolve()), preprocess_mode))
                            )
                            for output in outputs:
                                self.queue.put(("log", tr(self.lang, "checkpoint_available_after_failure").format(path=output)))
                            if outputs:
                                self.queue.put(("render_lists", None))
                            self.queue.put(("status", tr(self.lang, "stopped")))
                            return
                        _drain_generator_output()
                        now = time.monotonic()
                        if now >= next_preview_scan:
                            next_preview_scan = now + GENERATOR_PREVIEW_SCAN_SECONDS
                            preview_files = generated_preview_files(input_image)
                            if preview_files:
                                newest_preview = preview_files[0]
                                preview_mtime = newest_preview.stat().st_mtime
                                if preview_mtime != last_preview_mtime:
                                    last_preview_mtime = preview_mtime
                                    self.queue.put(("preview_file", newest_preview))
                        if now >= next_json_scan:
                            next_json_scan = now + GENERATOR_JSON_SCAN_SECONDS
                            newest = generated_jsons(input_image)
                            if newest and newest[0] != last_json:
                                last_json = newest[0]
                        time.sleep(GENERATOR_POLL_SLEEP_SECONDS)
                    if self.shutdown_event.is_set():
                        return
                    reader.join(timeout=1)
                    _drain_generator_output()
                finally:
                    self._unregister_process(proc)
                    with self.generation_lock:
                        if self.current_generator_proc is proc:
                            self.current_generator_proc = None
                if proc.returncode != 0:
                    self._record_detail(f"GENERATOR EXIT: {proc.returncode}")
                    outputs = self._queue_generated_outputs(
                        image_path, before, generator_input=input_image, preprocess_mode=preprocess_mode
                    )
                    self.queue.put(
                        ("generation_preprocess", (str(Path(image_path).resolve()), preprocess_mode))
                    )
                    for output in outputs:
                        self.queue.put(("log", tr(self.lang, "checkpoint_available_after_failure").format(path=output)))
                    if outputs:
                        self.queue.put(("render_lists", None))
                    self.queue.put(("log", self._generator_exit_message(proc.returncode)))
                    self.queue.put(("status", tr(self.lang, "failed")))
                    return
                self._record_detail("GENERATOR EXIT: 0")
                new_outputs = self._queue_generated_outputs(
                    image_path, before, generator_input=input_image, preprocess_mode=preprocess_mode
                )
                self.queue.put(
                    ("generation_preprocess", (str(Path(image_path).resolve()), preprocess_mode))
                )
                if not new_outputs:
                    self.queue.put(("log", "Generator finished but no JSON output was found."))
                    self.queue.put(("status", tr(self.lang, "failed")))
                    return
                for output in new_outputs:
                    preview_files = generated_preview_files(input_image)
                    if preview_files:
                        self.queue.put(("preview_file", preview_files[0]))
                    else:
                        self.queue.put(("preview_json", output))
            self.queue.put(("render_lists", None))
            self.queue.put(("status", tr(self.lang, "done")))
        except Exception as exc:
            self.queue.put(("log", f"Generator failed: {exc}"))
            self.queue.put(("status", tr(self.lang, "failed")))
        finally:
            self.queue.put(("generation_done", None))

    def open_output_folder(self):
        folder = None
        if self.outputs:
            folder = self.outputs[-1].parent
        elif self.images:
            folder = self.images[-1].parent
        if folder and folder.exists():
            os.startfile(folder)

    def open_runtime_folder(self):
        ROOT.mkdir(parents=True, exist_ok=True)
        os.startfile(ROOT)

    def run_subprocess(self, cmd, timeout=None, extra_env=None):
        self._record_detail(f"HELPER COMMAND: {self._format_command(cmd)}")
        self.queue.put(("log", self._friendly_command_name(cmd)))
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        env = os.environ.copy()
        env.update({"FORZA_PAINTER_NO_ELEVATE": "1", "FORZA_PAINTER_NO_PAUSE": "1"})
        if extra_env:
            env.update(extra_env)
        if self.shutdown_event.is_set():
            self._record_detail("HELPER EXIT: 130 before start")
            return 130
        proc = self._popen_registered(
            [str(x) for x in cmd],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags,
            env=env,
        )
        if proc is None:
            self._record_detail("HELPER EXIT: 130 no process")
            return 130
        started = time.time()
        try:
            while True:
                if self.shutdown_event.is_set():
                    self._terminate_process(proc)
                    self._record_detail("HELPER EXIT: 130 stopped")
                    return 130
                line = proc.stdout.readline()
                if line:
                    self._record_detail(f"HELPER RAW: {line.rstrip()}")
                    friendly = self._friendly_subprocess_line(line.rstrip())
                    if friendly:
                        self.queue.put(("log", friendly))
                if proc.poll() is not None:
                    break
                if timeout and time.time() - started > timeout:
                    self._terminate_process(proc)
                    self._record_detail(f"HELPER EXIT: 124 timeout after {timeout} seconds")
                    self.queue.put(("log", f"Timed out after {timeout} seconds."))
                    return 124
                time.sleep(0.05)
            if self.shutdown_event.is_set():
                self._record_detail("HELPER EXIT: 130 stopped after process exit")
                return 130
            for line in proc.stdout.read().splitlines():
                self._record_detail(f"HELPER RAW: {line.rstrip()}")
                friendly = self._friendly_subprocess_line(line.rstrip())
                if friendly:
                    self.queue.put(("log", friendly))
            self._record_detail(f"HELPER EXIT: {proc.returncode}")
            return proc.returncode
        finally:
            self._unregister_process(proc)

    def _friendly_command_name(self, cmd):
        joined = " ".join(str(x) for x in cmd)
        if "fh6_probe.py" in joined and "--auto-locate" in joined:
            return tr(self.lang, "locating")
        if "main.py" in joined:
            return tr(self.lang, "importing")
        return "Starting helper..."

    def _check_json_layer_fit(self, json_path, layer_count):
        try:
            from generator_backend import geometry_shape_count
            json_layers = geometry_shape_count(json_path)
            template_layers = int(layer_count)
        except Exception:
            return
        usable_layers = max(0, template_layers - 4)
        if json_layers and template_layers and json_layers > usable_layers:
            self.queue.put(("log", f"{tr(self.lang, 'json_needs_more_template_layers')} JSON={json_layers}, template={template_layers}, usable={usable_layers}"))
        if json_layers and usable_layers and json_layers < usable_layers * 0.75:
            self.queue.put(("log", f"{tr(self.lang, 'json_too_small')} JSON={json_layers}, usable={usable_layers}"))

    def _friendly_subprocess_line(self, line):
        if not line:
            return None
        raw = line.strip()
        lower = raw.lower()
        noisy_parts = (
            "base:",
            "candidate score=",
            "layout candidate",
            "table[",
            "ptr=0x",
            "count=0x",
            "tablefield=",
            "wrote fh6 session location",
            "fh6 layout-count scan checked",
            "process: forzahorizon",
            "current values:",
            "loaded ",
            "descriptor @",
            "info found:",
            "vtp found:",
        )
        if any(part in lower for part in noisy_parts):
            return None
        if "fast fh6 layer group candidates:" in lower:
            return tr(self.lang, "located")
        if "no safe fh6 layer group" in lower:
            return tr(self.lang, "safe_stop")
        if "auto-locating fh6 layer count/table" in lower:
            return tr(self.lang, "locating")
        if "cliverylayer table found" in lower:
            return tr(self.lang, "located")
        if "forza horizon 6 detected" in lower:
            return raw
        if raw.startswith("Writing layer") or raw == "DONE!" or raw.startswith("The ideal background color"):
            return raw
        if "access is denied" in lower or "winerror 5" in lower or "permissionerror" in lower:
            return (
                "Windows denied access to the FH6 process. "
                "The app should already request administrator rights on startup."
            )
        if "openprocess" in lower or "error" in lower or "failed" in lower or "traceback" in lower:
            return raw
        if raw.startswith("<class 'SystemExit'>") or raw.startswith("SystemExit: 0"):
            return None
        return raw

    def start_auto_locate(self):
        pid = self.ensure_live_game_pid()
        layer_count = self.layer_count.get().strip()
        if not pid or not layer_count:
            self.log_line(tr(self.lang, "log_pid_layer_required"))
            return
        self.status.set(tr(self.lang, "running"))
        threading.Thread(target=self._auto_locate_worker, args=(pid, layer_count), daemon=True).start()

    def _auto_locate_worker(self, pid, layer_count):
        clear_session_location()
        cmd = [
            *helper_command("fh6_probe"),
            "--game",
            self.selected_game.get() or "fh6",
            "--pid",
            str(pid),
            "--layer-count",
            str(layer_count),
            "--auto-locate",
            "--write-session",
            SESSION_PATH,
            "--limit-mb",
            str(MEMORY_SNAPSHOT_LIMIT_MB),
            "--max-matches",
            "500000",
            "--inspect-radius",
            "0x800",
            "--max-seconds",
            str(FH6_AUTO_LOCATE_MAX_SECONDS),
        ]
        self.queue.put(("log", tr(self.lang, "locating_wait")))
        code = self.run_subprocess(cmd, timeout=FH6_AUTO_LOCATE_TIMEOUT_SECONDS)
        located = False
        if code == 0 and SESSION_PATH.exists():
            session = load_session_location()
            if session_matches_current_import(session, self.selected_game.get() or "fh6", pid, layer_count):
                self.queue.put(("log", tr(self.lang, "located")))
                located = True
        self.queue.put(("status", tr(self.lang, "done") if located else tr(self.lang, "failed")))
        return located

    def _typecode_allow_unknown_shapes(self) -> bool:
        return self.typecode_allow_unknown.get() == "1"

    def _typecode_trim_enabled(self) -> bool:
        return self.typecode_trim_after_import.get() == "1"

    def _resolve_import_locations(self, pid, game: str, layer_count: str):
        user_manual = bool(parse_hex_or_empty(self.count_address.get()) or parse_hex_or_empty(self.table_address.get()))
        count_address = None
        table_address = None
        group_address = None
        import_env = {}
        if user_manual:
            try:
                count_value = parse_hex_or_empty(self.count_address.get())
                table_value = parse_hex_or_empty(self.table_address.get())
                if count_value:
                    count_address = parse_safe_hex_address(count_value)
                if table_value:
                    table_address = parse_safe_hex_address(table_value)
            except ValueError as exc:
                raise ValueError(f"Invalid advanced memory address: {exc}") from exc
            import_env["FORZA_PAINTER_ALLOW_MANUAL_ADDRESSES"] = "1"
        if not count_address and not table_address and game == "fh6":
            session = load_session_location()
            if session_matches_current_import(session, game, pid, layer_count):
                pid = int(session["pid"])
                count_address = int(session["count_address"])
                table_address = int(session["table_address"])
                group_address = session.get("group_address")
                if group_address is not None:
                    group_address = int(group_address)
                import_env["FORZA_PAINTER_TRUSTED_LOCATOR"] = "1"
                self.queue.put(("log", tr(self.lang, "located")))
            elif pid and layer_count:
                self.queue.put(("log", tr(self.lang, "locating")))
                located = self._auto_locate_worker(pid, layer_count)
                session = load_session_location()
                if located and session_matches_current_import(session, game, pid, layer_count):
                    pid = int(session["pid"])
                    count_address = int(session["count_address"])
                    table_address = int(session["table_address"])
                    group_address = session.get("group_address")
                    if group_address is not None:
                        group_address = int(group_address)
                    import_env["FORZA_PAINTER_TRUSTED_LOCATOR"] = "1"
                else:
                    raise RuntimeError("FH6 layer table could not be located.")
        if count_address and "FORZA_PAINTER_TRUSTED_LOCATOR" not in import_env and "FORZA_PAINTER_ALLOW_MANUAL_ADDRESSES" not in import_env:
            import_env["FORZA_PAINTER_TRUSTED_LOCATOR"] = "1"
        if group_address is None and count_address:
            profile = PROFILES.get(game)
            if profile:
                group_address = int(count_address) - profile.livery_count_offset
        return {
            "pid": int(pid),
            "count_address": count_address,
            "table_address": table_address,
            "group_address": group_address,
            "import_env": import_env,
        }

    def _import_typecode_json_file(self, path: Path, locations: dict, layer_count: str) -> int:
        table_address = locations.get("table_address")
        if not table_address:
            raise RuntimeError("Layer table address is required for handmade import.")
        TYPECODE_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem).strip("._") or "import"
        backup = TYPECODE_IMPORT_DIR / f"{safe}-{stamp}.backup.json"
        report = TYPECODE_IMPORT_DIR / f"{safe}-{stamp}.report.json"
        allow_unknown = self._typecode_allow_unknown_shapes()
        shape_count = typecode_shape_count(path, allow_unknown_low_byte=allow_unknown)
        cmd = [
            *helper_command("fh6_import_typecode_json"),
            "--pid",
            str(locations["pid"]),
            "--table",
            f"0x{int(table_address):x}",
            "--json",
            str(path.resolve()),
            "--backup",
            str(backup),
            "--report",
            str(report),
            "--write",
            "--compact-supported-layers",
            "--clear-unused",
            "--template-count",
            str(layer_count),
        ]
        if allow_unknown:
            cmd.append("--allow-unknown-low-byte")
        code = self.run_subprocess(cmd, extra_env=locations.get("import_env", {}))
        if code != 0:
            return code
        if self._typecode_trim_enabled() and shape_count > 0:
            code = self._trim_typecode_group_count(locations, shape_count)
        return code

    def _trim_typecode_group_count(self, locations: dict, new_count: int) -> int:
        group_address = locations.get("group_address")
        table_address = locations.get("table_address")
        if not group_address:
            self.queue.put(("log", tr(self.lang, "typecode_missing_group")))
            return 1
        TYPECODE_IMPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = TYPECODE_IMPORT_DIR / f"trim-{stamp}.backup.json"
        cmd = [
            *helper_command("fh6_trim_group_count"),
            "--pid",
            str(locations["pid"]),
            "--group",
            f"0x{int(group_address):x}",
            "--new-count",
            str(int(new_count)),
            "--backup",
            str(backup),
            "--trim-vector-end",
            "--write",
        ]
        if table_address:
            cmd.extend(["--table", f"0x{int(table_address):x}"])
        code = self.run_subprocess(cmd, extra_env=locations.get("import_env", {}))
        if code == 0:
            self.queue.put(("log", tr(self.lang, "typecode_trim_done").format(count=new_count)))
        else:
            self.queue.put(("log", tr(self.lang, "typecode_trim_failed").format(error=f"exit {code}")))
        return code

    def start_export_typecode_json(self):
        layer_count = self.layer_count.get().strip()
        if not layer_count:
            self.log_line(tr(self.lang, "layer_count_required"))
            return
        pid = self.ensure_live_game_pid()
        if not pid:
            return
        self.status.set(tr(self.lang, "running"))
        threading.Thread(target=self._export_typecode_worker, args=(pid, layer_count), daemon=True).start()

    def _export_typecode_worker(self, pid, layer_count: str):
        game = self.selected_game.get() or "fh6"
        try:
            locations = self._resolve_import_locations(pid, game, layer_count)
        except (ValueError, RuntimeError) as exc:
            self.queue.put(("log", str(exc)))
            self.queue.put(("status", tr(self.lang, "failed")))
            return
        table_address = locations.get("table_address")
        group_address = locations.get("group_address")
        if not table_address:
            self.queue.put(("log", tr(self.lang, "typecode_missing_group")))
            self.queue.put(("status", tr(self.lang, "failed")))
            return
        TYPECODE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = TYPECODE_EXPORT_DIR / f"fh6-export-{stamp}.json"
        report = output.with_suffix(".report.json")
        cmd = [
            *helper_command("fh6_export_typecode_json"),
            "--pid",
            str(locations["pid"]),
            "--table",
            f"0x{int(table_address):x}",
            "--count",
            str(layer_count),
            "--out",
            str(output),
            "--report",
            str(report),
            "--skip-transparent",
        ]
        if group_address:
            cmd.extend(["--group", f"0x{int(group_address):x}"])
        code = self.run_subprocess(cmd, extra_env=locations.get("import_env", {}))
        if code != 0:
            self.queue.put(("status", tr(self.lang, "failed")))
            return
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
            count = len(payload.get("shapes", []))
        except (OSError, json.JSONDecodeError):
            count = 0
        self.queue.put(("log", tr(self.lang, "typecode_export_done").format(count=count, path=output)))
        if hasattr(self, "handmade_json_files") and output not in self.handmade_json_files:
            self.handmade_json_files.append(output)
            self.queue.put(("render_handmade_lists", None))
        self.queue.put(("status", tr(self.lang, "done")))

    def start_import(self):
        if not self.json_files:
            self.log_line(tr(self.lang, "log_no_json_files_selected"))
            return
        layer_count = self.layer_count.get().strip()
        if not layer_count:
            self.log_line(tr(self.lang, "layer_count_required"))
            if hasattr(self, "layer_count_entry"):
                self.layer_count_entry.config(highlightbackground=COLOR_WARN, highlightthickness=1)
            return
        if hasattr(self, "layer_count_entry"):
            self.layer_count_entry.config(highlightbackground=COLOR_BORDER, highlightthickness=0)
        pid = self.ensure_live_game_pid()
        if not pid:
            return
        self.status.set(tr(self.lang, "running"))
        threading.Thread(target=self._import_worker, args=(pid,), daemon=True).start()

    def _import_worker(self, pid):
        game = self.selected_game.get() or "fh6"
        layer_count = self.layer_count.get().strip()
        try:
            locations = self._resolve_import_locations(pid, game, layer_count)
        except ValueError as exc:
            self.queue.put(("log", str(exc)))
            self.queue.put(("status", tr(self.lang, "failed")))
            return
        except RuntimeError:
            self.queue.put(("status", tr(self.lang, "failed")))
            return
        pid = locations["pid"]
        count_address = locations.get("count_address")
        table_address = locations.get("table_address")
        import_env = locations.get("import_env", {})
        for path in list(self.json_files):
            path = Path(path)
            if game == "fh6" and layer_count:
                self._check_json_layer_fit(path, layer_count)
            if is_typecode_geometry_json(path):
                self.queue.put(("log", tr(self.lang, "typecode_import_mode").format(name=path.name)))
                code = self._import_typecode_json_file(path, locations, layer_count)
                if code != 0:
                    self.queue.put(("status", tr(self.lang, "failed")))
                    return
                self.queue.put(("log", tr(self.lang, "typecode_import_done").format(name=path.name)))
                continue
            cmd = [*helper_command("main"), "--game", game, "--no-preview", "--pid", str(pid)]
            if count_address:
                cmd.extend(["--layer-count-address", f"0x{int(count_address):x}"])
            if table_address:
                cmd.extend(["--layer-table-address", f"0x{int(table_address):x}"])
            if game == "fh6" and layer_count:
                cmd.extend(["--layer-count-value", str(layer_count)])
            cmd.append(str(path.resolve()))
            code = self.run_subprocess(cmd, extra_env=import_env)
            if code != 0:
                self.queue.put(("status", tr(self.lang, "failed")))
                return
        self.queue.put(("status", tr(self.lang, "done")))

    def start_diagnose(self):
        pid = self.ensure_live_game_pid()
        cmd = [*helper_command("main"), "--game", self.selected_game.get() or "fh6", "--diagnose"]
        if pid:
            cmd.extend(["--pid", str(pid)])
        self.status.set(tr(self.lang, "running"))
        threading.Thread(target=lambda: self._run_command_worker(cmd, 120), daemon=True).start()

    def start_save_snapshot(self):
        pid = self.ensure_live_game_pid()
        count = self.snapshot_count.get().strip() or self.layer_count.get().strip()
        if not pid or not count:
            self.log_line(tr(self.lang, "log_pid_snapshot_required"))
            return
        output_path = PROBE_DIR / f"memory-count-{count}.jsonl"
        cmd = [
            *helper_command("fh6_probe"),
            "--game",
            self.selected_game.get() or "fh6",
            "--pid",
            str(pid),
            "--layer-count",
            str(count),
            "--save-memory-snapshot",
            output_path,
            "--limit-mb",
            str(MEMORY_SNAPSHOT_LIMIT_MB),
        ]
        self.status.set(tr(self.lang, "running"))
        threading.Thread(target=lambda: self._run_command_worker(cmd, 360), daemon=True).start()

    def start_compare_snapshot(self):
        pid = self.ensure_live_game_pid()
        previous = self.snapshot_count.get().strip()
        current = self.current_count.get().strip() or self.layer_count.get().strip()
        if not pid or not previous or not current:
            self.log_line(tr(self.lang, "log_pid_snapshot_current_required"))
            return
        snapshot_path = PROBE_DIR / f"memory-count-{previous}.jsonl"
        candidates_path = PROBE_DIR / f"memory-count-{previous}-to-{current}-candidates.json"
        intersect_path = PROBE_DIR / f"memory-count-{int(previous) - 1}-to-{previous}-candidates.json"
        cmd = [
            *helper_command("fh6_probe"),
            "--game",
            self.selected_game.get() or "fh6",
            "--pid",
            str(pid),
            "--layer-count",
            str(current),
            "--compare-memory-snapshot",
            snapshot_path,
            "--write-candidates",
            candidates_path,
            "--max-matches",
            "50000",
        ]
        if intersect_path.exists():
            cmd.extend(["--intersect-candidates", intersect_path])
        self.status.set(tr(self.lang, "running"))
        threading.Thread(target=lambda: self._run_command_worker(cmd, 360), daemon=True).start()

    def start_inspect_table(self):
        pid = self.ensure_live_game_pid()
        table = self.inspect_table_value.get().strip()
        count = self.layer_count.get().strip()
        if not pid or not table or not count:
            self.log_line(tr(self.lang, "log_pid_layer_table_required"))
            return
        cmd = [
            *helper_command("fh6_probe"),
            "--game",
            self.selected_game.get() or "fh6",
            "--pid",
            str(pid),
            "--layer-count",
            str(count),
            "--inspect-table",
            table,
            "--inspect-layers",
            "12",
        ]
        self.status.set(tr(self.lang, "running"))
        threading.Thread(target=lambda: self._run_command_worker(cmd, 60), daemon=True).start()

    def _run_command_worker(self, cmd, timeout):
        code = self.run_subprocess(cmd, timeout=timeout)
        self.queue.put(("status", tr(self.lang, "done") if code == 0 else tr(self.lang, "failed")))

    def _poll_queue(self):
        if self.closed:
            return
        while True:
            try:
                kind, payload = self.queue.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self.log_line(payload)
            elif kind == "progress":
                self.progress_text.set(payload)
            elif kind == "status":
                self.status.set(payload)
            elif kind == "generation_done":
                stopped = self.shutdown_event.is_set()
                with self.generation_lock:
                    self.generation_running = False
                    self.current_generator_proc = None
                if hasattr(self, "generate_button"):
                    self.generate_button.config(state="normal")
                if hasattr(self, "stop_generate_button"):
                    self.stop_generate_button.config(state="disabled")
                if stopped and not self.closed:
                    self.progress_text.set(tr(self.lang, "generation_stopped"))
                    self.status.set(tr(self.lang, "stopped"))
                    self.log_line(tr(self.lang, "generation_stopped"))
            elif kind == "preview":
                self.show_preview(payload)
            elif kind == "preview_json":
                self.show_preview_file(payload)
                self._refresh_generate_compare()
            elif kind == "preview_file":
                self.show_preview_file(payload)
            elif kind == "render_lists":
                self._render_lists()
            elif kind == "render_handmade_lists":
                self._render_handmade_list()
            elif kind == "preview_filters_ready":
                source_key, filter_payload = payload
                self._apply_preview_filters_ready(source_key, filter_payload)
            elif kind == "preview_filters_failed":
                _source_key, error = payload
                self._preview_compute_running = False
                self.preview_status_label.config(text=tr(self.lang, "preview_failed").format(error=error))
                self.log_line(tr(self.lang, "preview_failed").format(error=error))
            elif kind == "generation_preprocess":
                image_key, preprocess_mode = payload
                self._last_generation_preprocess[image_key] = normalize_preprocess_mode(preprocess_mode)
                self._update_luma_status_label()
                self._update_compare_column_headers()
            elif kind == "text_json_done":
                shape_mode = None
                if len(payload) >= 3:
                    payload, output, shape_mode = payload[0], payload[1], payload[2]
                else:
                    payload, output = payload[0], payload[1]
                self.text_vinyl.finish_json(payload, output, shape_mode=shape_mode)
            elif kind == "text_fonts_ready":
                self.text_vinyl.apply_fonts_by_script(payload)
            elif kind == "update_failed":
                self._handle_update_failed(payload)
            elif kind == "update_current":
                self._handle_update_current(payload)
            elif kind == "update_available":
                self._handle_update_available(payload)
            elif kind == "resource_monitor":
                self._apply_resource_snapshot(payload)
        if not self.closed:
            self.root.after(100, self._poll_queue)

    def run(self):
        self.root.mainloop()


def main():
    # Best-effort crash reporting for windowed one-file EXEs (no console output).
    fault_path = None
    try:
        for candidate in _startup_crash_report_paths():
            try:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                fault_path = candidate
                break
            except Exception:
                continue
        if fault_path is not None:
            try:
                faulthandler.enable(open(fault_path, "a", encoding="utf-8", errors="replace"))
            except Exception:
                pass

        if len(sys.argv) >= 3 and sys.argv[1] == "--helper":
            run_embedded_helper(sys.argv[2], sys.argv[3:])
            return
        ensure_elevated_or_exit()
        parser = argparse.ArgumentParser(description=f"Standalone {APP_DISPLAY_NAME} desktop app.")
        parser.add_argument("--version", action="version", version=app_version_string())
        parser.add_argument("images", nargs="*", help="Optional image files to preload.")
        args = parser.parse_args()
        App(args.images).run()
    except SystemExit:
        raise
    except BaseException as exc:
        written = _write_startup_crash_report(exc)
        try:
            # Show something user-visible when possible (even in --windowed mode).
            path_text = f"\n\nCrash report: {written}" if written else ""
            messagebox.showerror(
                APP_DISPLAY_NAME,
                tr("en", "startup_failed").format(
                    details=path_text,
                    name=type(exc).__name__,
                    error=exc,
                ),
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
