# Build consolidation (May 2026)

Three local copies were merged into this folder (`forza-painter-fh6`):

| Source | Role |
| --- | --- |
| `forza-painter-fh6-1.6.1_A2` | Upstream **v1.6.1** (preprocess/luma, generator updates) |
| `forza-painter-fh6_A1` | Security hardening, UX tweaks, **Text vinyl** |
| `forza-painter-fh6` | **Canonical** target (this tree) |

Archived copies live under `C:\Projects\Forza Painter\_archive\`.

## What was kept

- **Base:** v1.6.1 generator and app structure
- **Security:** `security_policy.py`, hardened `native.py`, `main.py`, `fh6_probe.py`, `geometry_json.py`
- **UX:** auto-elevate via `start_app.bat`, Tutorial tab on the far right, template layer import hint, FH6 Tools tab
- **Text vinyl:** `text_geometry.py`, `text_ocr.py`, `text_to_json.py`, Text vinyl tab, `docs/TEXT_VINYL.md`, optional `requirements-text-ocr.txt`

## Run

```bat
start_app.bat
```

Or from source: `.venv\Scripts\python.exe src\app.py` (admin recommended for FH6 import).
