# Forza Painter — brand assets

**Canonical mark:** `fp-monogram-master.png` — fused **FP** monogram (Forza-style interlock: F top bar spans P; P stem phases from F middle bar; orange + white brush tip only). Reads **FP**. **No purple.**

Rebuild everything from the master:

```powershell
cd logo
python build_logo_variants.py
```

## Files

| File | Purpose |
|------|---------|
| `fp-monogram-master.png` | **Source of truth** — edit, then rebuild |
| `fp-monogram.svg` | Simplified vector sketch |
| `forza-painter-icon-1024.png` | Square icon |
| `forza-painter-app-icon-1024.png` | Rounded app plate |
| `forza-painter-lockup-vertical.png` | FP mark + FORZA / PAINTER |
| `forza-painter-lockup-horizontal.png` | FP mark + wordmark |
| `forza-painter.ico` | Windows / PyInstaller |
| `png/icon-*.png` | Favicon sizes |

## Palette

| Color | Hex |
|-------|-----|
| Orange | `#FF6A00` |
| White | `#FFFFFF` |
| Black | `#000000` |
