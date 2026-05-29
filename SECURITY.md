# Security policy

## Scope

forza-painter FH6 is a **local Windows desktop tool** that attaches to a running **Forza Horizon 6** process to read and write **vinyl / livery editor** data. It is not a remote service and does not ship background agents.

## What the application accesses

| Access | Purpose |
| --- | --- |
| `ForzaHorizon6.exe` (or shipping executable) process memory | Locate the vinyl layer table and read/write layer fields during import/export |
| Local image and JSON files | Generate geometry, previews, import/export backups |
| Optional HTTPS to GitHub | Update check only when enabled (`api.github.com`, `raw.githubusercontent.com`) |
| GPU via OpenCL | Image-to-geometry generation (no game memory) |

## What we do **not** modify

The importer is intentionally narrow. It does **not** target gameplay values such as:

- Player position, speed, or physics
- Credits, vouchers, inventory, or progression
- Race times, stats, or online rankings
- Anti-cheat or networking stacks

Geometry import writes only known **vinyl layer** fields (position, scale, rotation, color, shape id, mask) after the layer table passes validation.

## Safety limits (code-enforced)

Central limits live in `src/security_policy.py`, including:

- User-mode address range validation
- Template layer count bounds (100–3000)
- Maximum geometry JSON size and shape count
- Maximum memory read size per operation
- FH6 session JSON schema validation before reuse
- Manual memory addresses disabled unless explicitly allowed via environment flags set by the app

## Helper subprocesses

The GUI may launch **the same executable** in `--helper` mode (or sibling Python modules in development) to run import, export, or probe tasks. Helpers inherit `FORZA_PAINTER_NO_ELEVATE=1` so they do not chain UAC prompts; the parent process should already be elevated when performing memory writes.

Command lines are logged in the detailed log with **redacted** addresses and PIDs when redaction is enabled (default).

## Administrator rights

Administrator elevation is required for reliable `OpenProcess` access to FH6 on many systems. The GUI requests elevation **when you start a memory operation** (import, export, or diagnostics), not silently at every launch.

## Privacy

- No analytics or telemetry servers.
- No account credentials are collected.
- Optional update check fetches public GitHub release metadata only.

## Antivirus / Windows Defender false positives

This app uses process memory access, optional administrator elevation, PyInstaller one-file packaging, and a bundled unsigned GPU helper executable. Those behaviors overlap with cheat and malware heuristics even though the source is open and scoped to vinyl editing.

**LibreHardwareMonitor is not bundled.** Earlier builds that loaded it could trigger `VulnerableDriver:WinNT/Winring0`. There is no in-app hardware monitor; use external tools if needed. See [docs/HARDWARE_MONITORING.md](docs/HARDWARE_MONITORING.md).

See [docs/DEFENDER_AUDIT.md](docs/DEFENDER_AUDIT.md) for a traced behavior audit and [docs/DEFENDER_REPRO.md](docs/DEFENDER_REPRO.md) for a phased reproduction workflow. Enable `FORZA_PAINTER_DEFENDER_AUDIT=1` to log operations to `runtime/logs/defender-audit.log`.

## Reporting vulnerabilities

If you believe you found a security issue (for example, an unbounded memory write path or unexpected network exfiltration), open a private report via GitHub Security Advisories on this repository or contact the maintainer through the repository profile.

Please include: version, steps to reproduce, and whether the issue requires administrator rights or a malicious JSON file.

## Ban / account risk

Memory editing while the game is running may violate game terms or trigger anti-cheat heuristics. See [docs/SAFETY.md](docs/SAFETY.md) for user-facing risk guidance. That risk is separate from malware risk on your PC.
