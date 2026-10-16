# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for HeadSwap Studio Desktop.

Build:  pyinstaller desktop/HeadSwapStudio.spec
Output: dist/HeadSwapStudio  (single-file executable, console enabled so
        `--cli` headless mode prints progress; the GUI runs normally too)
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))
MODEL = os.path.join(ROOT, "models", "face_detection_yunet_2023mar.onnx")

a = Analysis(
    [os.path.join(ROOT, "desktop", "faceswap_desktop.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[(MODEL, "models")] if os.path.exists(MODEL) else [],
    hiddenimports=["cv2", "numpy", "face_swap"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"] if os.environ.get("HEADSWAP_HEADLESS_BUILD") else [],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="HeadSwapStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
