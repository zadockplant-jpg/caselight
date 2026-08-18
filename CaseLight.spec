# -*- mode: python ; coding: utf-8 -*-
import sys

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("liquidctl.driver")
if sys.platform == "win32":
    hiddenimports += collect_submodules("soundcard")

analysis = Analysis(
    ["caselight_launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[("assets", "assets"), ("scripts", "scripts"), ("udev", "udev")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="CaseLight",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon="assets/caselight.ico" if sys.platform == "win32" else None,
)
