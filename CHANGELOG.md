# Changelog

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
