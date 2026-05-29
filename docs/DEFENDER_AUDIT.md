# Windows Defender / antivirus false-positive audit

**Audit date:** 2026-05-29  
**Scope:** Source tree, build scripts, bundled binaries, runtime behavior (traced from code — not speculative).

This application is a **game-memory editor** for Forza Horizon vinyl data. Several behaviors are **legitimate for its purpose** but overlap with signatures used for cheats and malware. Defender may flag the app even when it is not malicious.

---

## Executive summary

| Risk tier | Finding | Likely Defender reaction |
| --- | --- | --- |
| **Critical** | `OpenProcess` + `ReadProcessMemory` / `WriteProcessMemory` on `ForzaHorizon6*.exe` while elevated | **HackTool**, **Behavior:Win32/GameCheats**, memory tampering |
| **High** | PyInstaller `--onefile` EXE (self-extract to `%TEMP%`, child processes) | **PUA:Win32/PyInstaller**, generic “untrusted packer” |
| **High** | Same signed/unsigned EXE re-launched with `--helper` + `runas` elevation | Parent/child + UAC + cross-process access |
| **Medium** | Bundled unsigned `bin/forza-painter-geometrize-go.exe` (~7.5 MB) spawned during Generate | Unknown binary, GPU/OpenCL workload |
| **Medium** | Large memory scans (`scan_block` up to 32 MB × 3 regions; `fh6_probe` `VirtualQueryEx` walks) | Cheat-engine-style scanning |
| **Low** | `pythonnet` + `clr.AddReference` to LibreHardwareMonitor DLLs | Dynamic assembly load |
| **Low** | `taskkill /F /T` on child processes | Process termination pattern |
| **Low** | HKLM font registry read (`text_fonts.py`) | Benign; rarely the primary trigger |
| **None observed** | Startup persistence, miners, remote C2, keyboard hooks, DLL injection into third parties | Not present in codebase |

**Most likely user report:** warnings after **running as Administrator** and using **Import**, **Auto-locate**, or **Diagnostics** — not from idle UI theming.

**Fixed in this audit:** CLI `src/main.py` no longer auto-elevates at startup (it previously contradicted GUI “import-only elevation”). Resource monitor no longer **requires** admin before attempting LHM init.

---

## 1. Behavior checklist (traced)

### 1.1 Process memory (primary trigger)

| API / pattern | Files | When it runs |
| --- | --- | --- |
| `OpenProcess`, `ReadProcessMemory`, `WriteProcessMemory` | `src/native.py`, `src/fh6_import_typecode_json.py`, `src/fh6_export_typecode_json.py`, `src/fh6_trim_group_count.py`, `src/fh6_probe.py` | Import, export, probe, CLI `main.py` |
| `CreateToolhelp32Snapshot` / `Module32FirstW` | `src/native.py` | Resolve game module base |
| `VirtualQueryEx` + region iteration | `src/fh6_probe.py` | Auto-locate, diagnostics, snapshots |
| Signature `scan_block` (up to **32 MB** read per region) | `src/native.py`, `src/main.py`, `src/game_profiles.py` | Livery signature search: 3× `(offset, 0x02000000)` per profile |

`game_profiles.COMMON_SCAN_REGIONS` totals **96 MB** of reads per full signature pass on the game process.

### 1.2 Elevation (amplifies severity)

| Mechanism | Files | Notes |
| --- | --- | --- |
| `ShellExecuteW(..., "runas", ...)` | `src/trust_workflow.py` | User-consented restart for memory work |
| `IsUserAnAdmin` | `trust_workflow`, `resource_monitor`, UI privilege label | Display only |
| ~~Auto-elevate at `main.py` CLI entry~~ | ~~`src/main.py`~~ | **Removed** — was a major mismatch with documented behavior |

GUI path: `prepare_memory_work()` in `src/trust_workflow.py` → consent dialog → optional UAC → `request_admin_restart()`.

### 1.3 Subprocess / process spawn

| Child | Launcher | Purpose |
| --- | --- | --- |
| Same EXE `--helper <name>` | `app.helper_command`, `run_subprocess` | Import, export, probe (frozen build) |
| `python.exe` + `fh6_*.py` | Dev mode `helper_command` | Same helpers without one-file unpack |
| `bin/forza-painter-geometrize-go.exe` | `generator_backend.build_generator_command` | GPU JSON generation |
| `taskkill /PID … /F /T` | `app._terminate_process` | Stop generator/helpers on exit |

Helpers set `FORZA_PAINTER_NO_ELEVATE=1` to avoid UAC chains (`app.run_subprocess`).

### 1.4 Packaging / binaries

| Artifact | Build | AV notes |
| --- | --- | --- |
| `dist/forza-painter-fh6-v*.exe` | `scripts/make_exe_release.ps1` — PyInstaller `--onefile --windowed` | Extracts embedded payload to temp; high false-positive rate unsigned |
| `bin/forza-painter-geometrize-go.exe` | Prebuilt, committed | **NotSigned** (Authenticode verified 2026-05-29); no version resource |
| `bin/librehardwaremonitor/*.dll` | `scripts/fetch_librehardwaremonitor.ps1` from GitHub releases | Downloaded at build/dev setup; bundled in EXE via `--add-data` |

No Electron/Tauri. No self-modifying Python bytecode at runtime.

### 1.5 Network

| Endpoint | Gate | File |
| --- | --- | --- |
| `api.github.com` | `FORZA_PAINTER_CHECK_UPDATES` | `security_policy.py`, `app.fetch_latest_release_version` |
| `raw.githubusercontent.com` | Same + changelog fetch | `app.fetch_text_url` |

No auto-updater binary download — metadata only.

### 1.6 Registry / persistence / hooks

- **Registry:** read-only font list under `HKLM\...\Fonts` (`src/text_fonts.py`) for Text Vinyl fonts.
- **Persistence:** none (no Run keys, scheduled tasks, or services).
- **Hooks:** Tk `<MouseWheel>` bindings only (UI scroll) — not global input hooks.

### 1.7 PowerShell / shell

| Script | When |
| --- | --- |
| `scripts/fetch_librehardwaremonitor.ps1` | Dev install / `make_exe_release.ps1` only — **not** at app runtime |
| `start_app.bat`, `ensure_venv.bat` | Dev launcher; calls venv Python, optional fetch script |

### 1.8 Temp files

- PyInstaller one-file extraction directory under `%TEMP%\_MEI*` (runtime).
- `runtime/logs/`, `runtime/previews/`, crash reports (`forza-painter-startup-crash.txt`).
- Build script uses `%TEMP%` for LHM zip extract (`fetch_librehardwaremonitor.ps1`).

---

## 2. Dependency audit

From `requirements.txt` (runtime):

| Package | Version constraint | Risk notes |
| --- | --- | --- |
| `psutil` | >=5.9.0 | Process enumeration — normal for this app |
| `pywin32` | >=306 | Windows API bindings |
| `pillow` | >=10.4.0 | Image I/O |
| `pythonnet` | >=3.0.0 | CLR hosting for LHM; dynamic DLL load |

Optional `requirements-preview.txt`: `numpy`, `opencv-python` (preview only).

**Not found:** postinstall scripts in repo, npm hooks, crypto miners, telemetry SDKs, abandoned typosquat packages.

**Install-time network:** `pip install` + optional `Invoke-WebRequest` for LHM DLLs during `ensure_venv.bat` / release build — not during end-user EXE run.

---

## 3. Severity and recommended fixes

### Critical — memory + elevation combo

**What Defender sees:** Admin process opens game with VM read/write, scans memory, writes buffers.

**Mitigation (product):**
- Keep **import-only elevation** (GUI already does; CLI fixed).
- Submit **false-positive report** to Microsoft with signed build when available.
- Document in release notes: expect detections until code-signed.

**Mitigation (technical):** Already narrowed writes via `security_policy.py` validation; do not remove safety checks to “look less suspicious.”

### High — PyInstaller one-file

**Fix options:**
1. Ship **`--onedir`** build for fewer packer heuristics (larger zip).
2. **Authenticode-sign** the outer EXE and geometrize helper.
3. Add **version resource** / company name to PE (build script enhancement).

### High — self-spawn `--helper`

**Why:** Parent EXE → child EXE (same path) + pipes is a common malware pattern.

**Mitigations:**
- Frozen build already uses in-process `run_embedded_helper` when invoked with `--helper` (no second disk EXE in dev for helpers — dev uses separate `.py` files).
- Log helper launches (detailed log + `defender-audit.log` when enabled).

### Medium — unsigned geometrize-go.exe

**Fix:** Rebuild from [forza-painter-geometrize-gpu](https://github.com/zjl88858/forza-painter-geometrize-gpu), sign, embed checksum in release notes. Consider spawning only from a fixed path under `ROOT/bin`.

### Medium — memory scanning volume

**Fix:** Reduce scan regions after FH6 signatures stabilize; cache session addresses (`fh6_session_location_v1`) to avoid re-scanning.

### Low — LHM / pythonnet

**Fix:** Default resource monitor off for first run; already falls back to psutil for CPU load without LHM.

---

## 4. Code signing readiness

Before release signing:

1. Build with `scripts/make_exe_release.ps1`.
2. Sign **both** `forza-painter-fh6.exe` and `bin/forza-painter-geometrize-go.exe`.
3. Timestamp with RFC3161 TSA.
4. Publish SHA-256 on GitHub Releases (already in `publish_release.ps1` checklist).
5. File [Microsoft security intelligence submission](https://www.microsoft.com/en-us/wdsi/filesubmission) with “false positive” + signed sample.

---

## 5. Debug logging (isolate live triggers)

Set:

```bat
set FORZA_PAINTER_DEFENDER_AUDIT=1
```

Log file: `runtime/logs/defender-audit.log` (next to EXE or project root).

Categories: `ELEVATION`, `PROCESS_SPAWN`, `MEMORY_READ`, `MEMORY_WRITE`, `MEMORY_SCAN`, `MEMORY_QUERY`, `DLL_LOAD`, `NETWORK`, `REGISTRY_READ`, `HELPER`, `STARTUP`.

Correlate timestamps with **Windows Security → Protection history** and **Event Viewer → Microsoft-Windows-Windows Defender/Operational** (event ID 1116/1117).

See [DEFENDER_REPRO.md](DEFENDER_REPRO.md) for step-by-step isolation.

---

## 6. What is *not* causing detections

- UI theme / hub navigation refactor alone (no new native behavior).
- i18n, preset renames, eco preset JSON settings.
- GitHub update check when disabled (default off).
- `webbrowser.open` for help URLs.

If warnings appear **immediately at launch** while elevated, suspect **PyInstaller unpack** or **LHM DLL load**, not import.

---

## Comparative build matrix

For hard evidence across 11 PyInstaller variants (onefile vs onedir, no UPX, no embedded binaries, etc.), run:

```powershell
.\scripts\run_defender_matrix_pipeline.ps1
```

See [DEFENDER_MATRIX.md](DEFENDER_MATRIX.md).

## Related docs

- [SECURITY.md](../SECURITY.md) — product security scope
- [SAFETY.md](SAFETY.md) — user-facing game/ban risk
- [ENVIRONMENT.md](ENVIRONMENT.md) — environment variables
- [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) — shipping steps
