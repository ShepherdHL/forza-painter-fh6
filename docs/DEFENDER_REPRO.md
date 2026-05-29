# Reproducible Defender / AV trigger isolation

Use this workflow to determine **which operation** caused a detection, not just that the app was flagged.

## Prerequisites

- Windows 10/11 with Microsoft Defender (or note third-party AV product).
- For memory tests: Forza Horizon 6 running in Vinyl Group Editor (as required by the app).
- Build or copy you are testing (dev: `start_app.bat`; release: one-file EXE).

## 1. Enable behavior audit log

```bat
set FORZA_PAINTER_DEFENDER_AUDIT=1
```

Launch the app. Confirm log exists:

`runtime/logs/defender-audit.log`

Each line includes UTC time, PID, frozen/elevated flags, category, and redacted details.

## 2. Clear Defender history (optional baseline)

1. Windows Security → Virus & threat protection → Protection history.
2. Note existing entries; filter by time after each test phase.

For Event Viewer power users:

```powershell
Get-WinEvent -LogName "Microsoft-Windows-Windows Defender/Operational" -MaxEvents 20 |
  Where-Object { $_.Id -in 1116,1117,5007 } |
  Format-Table TimeCreated, Id, Message -Wrap
```

## 3. Phased isolation matrix

Run phases **in order**. After each phase, check Protection history before continuing.

| Phase | Steps | Expected audit categories | Typical AV trigger |
| --- | --- | --- | --- |
| **A — Cold start (standard user)** | Launch app, wait 30s, close. No Import/Generate. | `STARTUP` only | PyInstaller unpack (one-file EXE) |
| **B — Cold start (admin)** | Right-click EXE → Run as administrator; idle 30s. | `STARTUP` | Unpack + elevated Python/EXE |
| **C — Generate JSON** | Add image, Generate (no game needed). | `PROCESS_SPAWN` (geometrize-go) | Unsigned child EXE, GPU |
| **D — Process enum** | Open Import tab; refresh PID list with game running. | `PROCESS_ENUM` | Low alone |
| **E — Elevation only** | Standard user → Import → accept consent → UAC restart. | `ELEVATION`, `STARTUP` | UAC + new elevated process |
| **F — Auto-locate** | After E, run Auto-locate. | `MEMORY_QUERY`, `MEMORY_READ`, `MEMORY_SCAN` | **High** — scan game memory |
| **G — Import** | Import geometry with consent. | `HELPER`, `MEMORY_WRITE`, `PROCESS_SPAWN` | **Critical** — write game memory |
| **H — Resource monitor** | Enable header telemetry / eco cooldown (if LHM present). | `DLL_LOAD` | pythonnet + LHM DLLs |

Record the **first phase** where Defender alerts. That phase maps to the fix priority in [DEFENDER_AUDIT.md](DEFENDER_AUDIT.md).

## 4. Automated helper script

From an elevated or standard PowerShell (project root):

```powershell
.\scripts\defender_repro.ps1 -Phase A
```

Phases: `A`, `B`, `C`, `D`, `E`, `F`, `G`, `H`, or `All` (manual steps still required for GUI actions).

The script:

- Sets `FORZA_PAINTER_DEFENDER_AUDIT=1`
- Prints audit log tail after you press Enter
- Optionally snapshots recent Defender operational events

## 5. PyInstaller vs dev Python

| Mode | Command | Isolation note |
| --- | --- | --- |
| Dev | `start_app.bat` | No one-file unpack; helpers are `.py` scripts |
| Release | `dist\forza-painter-fh6-v*.exe` | Tests packer/unpack heuristics |

If **only release** alerts on phase A, focus on signing and `--onedir` experiments.

## 6. Submitting a false positive

Include:

1. Signed EXE SHA-256 (if available).
2. Phase letter from section 3.
3. Last 50 lines of `defender-audit.log`.
4. Defender threat name (e.g. `Behavior:Win32/Hive.ZY`).
5. Whether game was running and whether user elevated voluntarily.

Microsoft: [Submit a file for malware analysis](https://www.microsoft.com/en-us/wdsi/filesubmission) → **Software developer** → **False positive**.

## 7. Environment flags reference

| Variable | Effect on repro |
| --- | --- |
| `FORZA_PAINTER_DEFENDER_AUDIT=1` | Write `defender-audit.log` |
| `FORZA_PAINTER_NO_ELEVATE=1` | Skip UAC relaunch (helpers set this automatically) |
| `FORZA_PAINTER_CHECK_UPDATES=1` | Adds `NETWORK` events on manual update check |

See [ENVIRONMENT.md](ENVIRONMENT.md) for full list.
