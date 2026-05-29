# Defender comparative build matrix

Evidence-based pipeline to find **which build artifact or runtime behavior** triggers Windows Defender.

## Quick start

```powershell
# Full pipeline (builds 11 variants — allow 30–90+ minutes)
.\scripts\run_defender_matrix_pipeline.ps1

# Administrator PowerShell recommended for Defender scans
```

Outputs under `dist/defender-matrix/`:

| File | Content |
| --- | --- |
| `build_manifest.json` | Built EXE paths |
| `analysis_results.json` | SHA256, size, PE imports, UPX heuristic |
| `smoke_results.json` | `--matrix-smoke` startup, `_MEI*` temp dirs |
| `defender_scan_results.json` | MpCmdRun per-variant detection |
| `MATRIX_REPORT.md` | Merged conclusions |

## Matrix variants (11)

Defined in `scripts/build_matrix/variants.json`:

| ID | Purpose |
| --- | --- |
| `onefile-baseline` | Default onefile (PyInstaller default UPX off) |
| `onedir` | No onefile unpack to `%TEMP%\_MEI*` |
| `onefile-no-upx-installed` | PATH stripped of UPX before build |
| `onefile-noupx-explicit` | `--noupx` + `upx=False` in spec |
| `onefile-no-embedded-binaries` | No `bin/` or LHM DLLs in bundle |
| `onefile-no-elevation` | Baked `disable_elevation` |
| `onefile-debug-console` | Console + debug bootloader |
| `onefile-stripped` | `strip=True` |
| `onefile-no-geometrize` | No geometrize EXE + generator disabled |
| `onefile-no-networking` | GitHub/update fetch disabled |
| `onefile-no-memory-scan` | Read/write/scan disabled |

## PyInstaller spec (production-safe defaults)

`scripts/forza_painter.spec`:

- **No UPX** (`upx=False` when `noupx` variant flag set)
- **No** `--collect-all pythonnet` unless LHM embedded
- **Excludes** matplotlib, scipy, pytest, etc.
- **Minimal** hidden imports
- **No** cv2/numpy in release spec (preview optional stack removed from EXE)

Release builds via `scripts/make_exe_release.ps1` use the same spec.

## Runtime profile gates

Baked `src/_build_profile.json` at build time (`src/build_profile.py`):

| Gate | Effect |
| --- | --- |
| `disable_elevation` | Blocks UAC relaunch |
| `disable_generator` | Blocks geometrize spawn |
| `disable_networking` | Blocks update/check HTTPS |
| `disable_memory_scan` | Blocks RPM/WPM / signature scan |

Override in dev without rebuild:

```bat
set FORZA_PAINTER_DISABLE_MEMORY_SCAN=1
```

## Single-variant commands

```powershell
.\scripts\build_defender_matrix.ps1 -VariantId onedir
.\scripts\defender_matrix\run_smoke_tests.ps1
.\scripts\defender_matrix\run_defender_scans.ps1   # Admin
.\scripts\defender_matrix\analyze_builds.py
.\scripts\defender_matrix\generate_report.py
```

## Interpreting “first clean build”

The report compares Defender scan results across variants:

- **baseline detected, `onedir` clean** → onefile unpack / packer heuristic.
- **baseline detected, `onefile-no-memory-scan` clean** → memory APIs (expected for this app class).
- **baseline detected, `onefile-no-geometrize` clean** → bundled unsigned child EXE.
- **All flagged** → likely cloud reputation on publisher cert absence; sign binaries.

## Limitations

- MpCmdRun results vary by signature version and cloud protection.
- `onefile-no-elevation` smoke does not test elevated import — use manual import test separately.
- Builds are **unsigned** until you apply your code-signing certificate.

See also [DEFENDER_AUDIT.md](DEFENDER_AUDIT.md) and [DEFENDER_REPRO.md](DEFENDER_REPRO.md).
