# Environment variables

Optional flags for support, testing, and advanced workflows. Normal users do not need these.

| Variable | Default | Purpose |
| --- | --- | --- |
| `FORZA_PAINTER_NO_ELEVATE` | unset | Skip UAC re-launch (set automatically for helper subprocesses). |
| `FORZA_PAINTER_NO_PAUSE` | unset | Skip “Press Enter” pause in CLI `main.py` after exit. |
| `FORZA_PAINTER_TRUSTED_LOCATOR` | unset | Allow import using addresses from a validated auto-locate session (set by the GUI). |
| `FORZA_PAINTER_ALLOW_MANUAL_ADDRESSES` | unset | Allow manual layer count/table addresses from the Advanced panel. |
| `FORZA_PAINTER_CHECK_UPDATES` | off | Set to `1` / `true` / `yes` to enable GitHub update checks. |
| `FORZA_PAINTER_REDACT_LOGS` | `1` (on) | Redact PIDs and `0x…` addresses in redacted log output. Set `0` to disable. |
| `FORZA_PAINTER_GAME` | auto | Force game profile key (`fh6`, `fh5`) for CLI import. |
| `FORZA_PAINTER_DEFENDER_AUDIT` | off | Append structured behavior lines to `runtime/logs/defender-audit.log` for AV false-positive isolation. See [DEFENDER_REPRO.md](DEFENDER_REPRO.md). |

## Consent flag file

After you accept the in-app memory consent dialog, the app may create:

`runtime/settings/memory_work_consent.flag`

Delete this file to see the consent dialog again.
