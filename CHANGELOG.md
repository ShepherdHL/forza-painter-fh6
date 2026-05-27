# Changelog

## Unreleased

### Core / upstream merge

- Merged upstream v1.6.5–v1.6.6 core fixes while keeping fork features (text vinyl, colors tab, resource monitor, security policy).
- Added `utils.py` with shared helpers, typed exceptions, and lazy OpenCV/Pillow loaders.
- Fixed `luma_band` preprocessing to use BGR→LAB (OpenCV-native) and atomic file writes.
- Generator runs use a sanitized environment; polling intervals match upstream to reduce UI overhead.
- Preprocessed generation inputs are tracked via `input_image` so JSON/previews are discovered correctly.
- Import requires template layer count before starting; added Traditional Chinese (`zh-tw`) UI option.
- Bundled presets set `forceOpaqueShapes = false`; heaviest preset uses `previewEvery = 100`.
- Updated bundled GPU generator to upstream `v1.2-Canary-20260525`; frozen `Color`/`Shape` dataclasses and `ShapeType` enum.

### Generation & preprocess

- **Image Preview** tab: compare preprocess filters and estimated layer cost before generating.
- **Preprocess filter** dropdown on Generate: Original, Luma Bands, Bilateral, Posterize, CLAHE, Mild Blur, Soft Cel Shading, Heavy Ink Cel Shading.
- Source/result compare panels on Generate when a filter is active.
- `src/preprocess/` package (`filters.py`, `luma.py`, `complexity.py`, `common.py`).

### FH6 import / export (Kloudy-style workflow)

- Three dedicated tabs: **Import Final JSON**, **Import Handmade JSON**, **Export Game JSON**.
- **Import Final JSON**: generated geometry JSON, run-folder browser, best-safe-final selection, preview, import.
- **Import Handmade JSON**: FH6 type-code / handmade JSON with supported/unsupported shape counts and preview.
- **Export Game JSON**: export open vinyl group to type-code JSON (`runtime/typecode-export/`).
- New helpers: `fh6_import_typecode_json.py`, `fh6_export_typecode_json.py`, `fh6_trim_group_count.py`, `fh6_typecode_json.py`.
- Auto-route type-code vs geometry JSON; optional trim group layer count after handmade import.

### UI & other

- Resource monitor: CPU/GPU load, clock, and temperature bar with green/yellow/red temp colors (80°C / 90°C), persistent heat warnings, and log messages when thresholds are crossed.
- Text vinyl: selectable trace shape modes (rectangles, squares, ellipses, circles, triangles, mixed) with FH6 template guidance in the UI and `--shape-mode` CLI flag.
- Text vinyl: Korean (Hangul) coverage checks, improved glyph detection, [KR] fonts ranked first when Hangul is typed, and Malgun Gothic fallbacks on Windows.
- Text vinyl: script sub-tabs (Universal/Latin, Japanese, Korean, Chinese) with separate text and font selections per tab, plus a font search bar on each tab.
- UI locked to dark mode for consistent, readable text and inputs; appearance picker removed until a fuller UI overhaul. Dark palette contrast improved (inputs, labels, log font).
- Workspace split: Generate JSON and import tabs on the left; Text vinyl, Colors, Tools, and Tutorial on the right (resizable divider).
- Default single tab bar (less clutter); optional **Split workspace** in the header restores two-column tabs (applies immediately; saved in `ui_layout.json`).
- Colors tab: click saves the color to a swatch history; hover only previews on the swatch.
- Colors tab: sample pixels from Generate-tab images (prev/next cycle), with Hex/RGB/HSL/HSB and Forza H/S/B matching [Bang's Forza Color Converter](https://dxbang.github.io/forza-colors/).
- Appearance themes (System/Light/Sakura/Elite) deferred: only dark is active in the desktop app.
- Resizable panel dividers: drag to resize the log vs main workspace, Generate/Import previews, and Text vinyl reference section. Layout saved to `runtime/settings/ui_layout.json`.
- `requirements-preview.txt`: Pillow for filter and handmade JSON previews in dev/venv setups.

## v1.6.1 / 2026-05-24

- Updated the app version to `v1.6.1`; release packages now use `forza-painter-fh6-v1.6.1.exe`.
- Disabled `luma_band` preprocessing by default in bundled presets.
- Import no longer reuses stale FH6 session data from `webui-data`; it re-locates the current template before writing.
- JSON previews now use one stable renderer path to avoid ellipse preview distortion differences between packaged EXE environments.

## v1.6.0 / 2026-05-24

- Updated the app version to `v1.6.0`; release packages now use `forza-painter-fh6-v1.6.0.exe`.
- Updated the bundled GPU generator to upstream `canary-26052401`.
- Added upstream `errorGridSize` preset support.
- Integrated the upstream transparent-area overhang prevention algorithm adjustment.
- Significantly improved generation quality for the large ellipse at the bottom of transparent images.

## v1.5.4 / 2026-05-23

- Fixed preview scaling for high-resolution source images, generator preview PNG files, and JSON previews.
- Previews now adapt to the current preview panel size while preserving the original image aspect ratio, avoiding stretched or partially visible previews when using large max-resolution settings such as 3000.
- Fixed JSON preview rendering for type 16 rotated ellipses in the packaged EXE by making the Pillow fallback follow the historical OpenCV preview coordinate conversion.

## v1.5.3 / 2026-05-22

- Added user preset import for the one-file EXE; imported `.ini` presets are stored in the external `config/settings/` folder beside the app.
- Added remove buttons for the selected image and selected JSON entries.
- Improved checkpoint handling: existing checkpoint JSON files are detected and reusable checkpoints are added to the Import list after failed or stopped generation.
- Fixed JSON output discovery when source image filenames contain extra dots, such as `image.1png.png`.
- Improved generation progress logs when the GPU generator recycles fully covered layers, so the UI no longer looks like generation restarted from an earlier layer.
- Added a Pillow-based preview fallback and packaged it into the EXE so fresh one-file installs can preview images and JSON without OpenCV.

## v1.5.2 / 2026-05-22

- Added a PyInstaller-based one-file EXE so normal users no longer need to install Python, create `.venv`, or keep helper files beside the app.
- The GUI EXE now re-launches itself in hidden helper mode for import and FH6 memory probing.
- The Tools page and startup log now show where external runtime/cache files are stored.
- Fixed the batch bootstrap variable-expansion bug that could run `-m venv` instead of `python -m venv`.
- Added a repeatable `scripts/make_exe_release.ps1` build script for the one-file EXE package.

## v1.5.1 / 2026-05-22

- Fixed startup dependency installation when a project `.venv` exists but its Python does not have `pip`; the bootstrapper now runs `ensurepip --upgrade` before installing requirements.
- Improved startup-script diagnostics when required release files are missing, with a clear message to fully extract the release ZIP first.

## v1.5.0 / 2026-05-22

- Added a startup update check against the GitHub `main` branch version file.
- When update checking fails, the app shows a small `!` indicator in the top-right corner; clicking it shows the failure reason.
- When a newer version is available, the app displays this changelog section and lets the user open the update page.
- Switched the desktop UI to a dark theme for better contrast during long generation and import sessions.
- Updated the bundled GPU/OpenCL generator to upstream `canary-26052102`.
- Added the upstream work-group evaluation algorithm from PR #4, reducing GPU candidate-evaluation overhead and improving generation throughput on supported OpenCL devices.
- `start_app.bat` now bootstraps the project-local `.venv`: it installs missing dependencies and then launches the app.
- Dependency installation now uses `.venv` instead of installing packages into the global Python environment.

## v1.4.1 / 2026-05-21

- FH6 template auto-location now tries both the v1.3 small/medium-region address-order scan and the v1.4 large-region chunked scan before giving up.
- Added an RTTI vtable fallback locator for difficult FH6 sessions while keeping the existing safe table validation before writing.
- Raised the FH6 auto-location budget to 300 seconds, with a 360-second outer watchdog timeout.
- Added a user-facing wait message before FH6 auto-location starts, warning users to keep the Vinyl Group Editor open and avoid switching menus.

## v1.4.0 / 2026-05-21

- Added detailed log export with a 50000-character output limit.
- Detailed logs include helper/generator raw output, commands, exit codes, process/template state, and current session data.
- Improved FH6 template auto-location by scanning large writable private memory regions in 4 MB chunks.
- Increased the FH6 auto-location scan budget to 120 seconds and the outer watchdog timeout to 160 seconds.

## v1.3.0 / 2026-05-21

- Updated the bundled GPU/OpenCL generator to upstream `canary-26052101`.
- Added the upstream generator device-selection fix, prioritizing NVIDIA GPUs with the most VRAM.
- Generation logs now show the selected OpenCL device.
- Improved FH6 template auto-locate failure handling so stale session cache is not reported as a newly verified template.
