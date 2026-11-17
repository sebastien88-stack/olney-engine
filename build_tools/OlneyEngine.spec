# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller definition for the self-contained Windows edition of Olney."""

from PyInstaller.utils.hooks import collect_submodules
import os


PROJECT_ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(PROJECT_ROOT, "assets", "olney_icon.ico"), "assets"),
    (os.path.join(PROJECT_ROOT, "data.json"), "."),
    (os.path.join(PROJECT_ROOT, "places.json"), "."),
    (os.path.join(PROJECT_ROOT, "interpretation"), "interpretation"),
    (os.path.join(PROJECT_ROOT, "tzdata"), "tzdata"),
    (os.path.join(PROJECT_ROOT, "README.md"), "."),
    (os.path.join(PROJECT_ROOT, "LICENSE"), "."),
    (os.path.join(PROJECT_ROOT, "LICENSING.md"), "."),
    (os.path.join(PROJECT_ROOT, "README.fr.md"), "."),
    (os.path.join(PROJECT_ROOT, "BACKEND_LECTURE.md"), "."),
    (os.path.join(PROJECT_ROOT, "THIRD_PARTY_NOTICES.md"), "."),
    (os.path.join(PROJECT_ROOT, "THIRD_PARTY_LICENSES"), "THIRD_PARTY_LICENSES"),
]


a = Analysis(
    [os.path.join(PROJECT_ROOT, "app.py")],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("tzdata"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Olney Engine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=os.path.join(PROJECT_ROOT, "build_tools", "windows_version_info.txt"),
    icon=os.path.join(PROJECT_ROOT, "assets", "olney_icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Olney Engine",
)
