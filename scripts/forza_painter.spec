# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Forza Painter FH6.

Matrix builds set MATRIX_VARIANT_FILE to a JSON snippet from scripts/build_matrix/variants.json.
Release builds use safe defaults: onefile, no UPX, no strip, minimal hidden imports.
"""

import json
import os
from pathlib import Path

# Analysis, PYZ, EXE, COLLECT are injected by PyInstaller when executing this spec.
ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / "src"
VARIANT_FILE = os.environ.get("MATRIX_VARIANT_FILE", "")

DEFAULT_VARIANT = {
    "id": "release",
    "onefile": True,
    "noupx": True,
    "noupx_cli": True,
    "debug": False,
    "strip": False,
    "console": False,
    "embed_bin": True,
    "embed_lhm": False,
    "collect_pythonnet": False,
}

if VARIANT_FILE and Path(VARIANT_FILE).is_file():
    VARIANT = json.loads(Path(VARIANT_FILE).read_text(encoding="utf-8"))
else:
    VARIANT = DEFAULT_VARIANT

block_cipher = None

# --- Data files (avoid embedding large unsigned EXEs when matrix variant says so) ---
datas = [
    (str(ROOT / "config"), "config"),
    (str(ROOT / "assets"), "assets"),
    (str(ROOT / "docs"), "docs"),
    (str(SRC / "_build_profile.json"), "."),
]

if VARIANT.get("embed_bin", True):
    datas.append((str(ROOT / "bin"), "bin"))

if VARIANT.get("embed_lhm", True):
    lhm = ROOT / "bin" / "librehardwaremonitor"
    if lhm.is_dir():
        datas.append((str(lhm), "librehardwaremonitor"))

# --- Hidden imports: only what the app actually imports ---
hiddenimports = [
    "win32timezone",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "psutil",
    "pywintypes",
    "pythoncom",
]

if VARIANT.get("collect_pythonnet", False):
    hiddenimports.extend(["clr"])

# Optional preview stack (large); excluded from matrix/release to reduce packer surface
excludes = [
    "matplotlib",
    "scipy",
    "pandas",
    "notebook",
    "IPython",
    "pytest",
    "tkinter.test",
    "test",
    "tests",
]

a = Analysis(
    [str(SRC / "app.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe_name = "forza-painter-fh6"
console = bool(VARIANT.get("console", False))
debug = bool(VARIANT.get("debug", False))
strip = bool(VARIANT.get("strip", False))
upx = not bool(VARIANT.get("noupx", True))

_onefile = bool(VARIANT.get("onefile", True))

if _onefile:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=exe_name,
        debug=debug,
        bootloader_ignore_signals=False,
        strip=strip,
        upx=upx,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=console,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        onefile=True,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=exe_name,
        debug=debug,
        bootloader_ignore_signals=False,
        strip=strip,
        upx=upx,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=console,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=strip,
        upx=upx,
        upx_exclude=[],
        name=exe_name,
    )
