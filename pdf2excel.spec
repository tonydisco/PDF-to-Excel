# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec dùng chung cho Windows (.exe) và macOS (.app).
Build:  pyinstaller pdf2excel.spec
"""
import os
import sys
from PyInstaller.utils.hooks import collect_submodules

datas = [
    ("tessdata", "tessdata"),      # đóng gói kèm gói tiếng Việt (vie.traineddata)
    ("assets", "assets"),          # icon + sprite
]

# icon theo nền tảng (nếu đã sinh bằng assets/make_icon.py)
_icns = os.path.join("assets", "icon.icns")
_ico = os.path.join("assets", "icon.ico")
ICON_FILE = _icns if (sys.platform == "darwin" and os.path.exists(_icns)) else (
    _ico if os.path.exists(_ico) else None)

hiddenimports = collect_submodules("fitz") + ["PIL._tkinter_finder"]

a = Analysis(
    ["app.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy.tests", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="BCTC_PDF_to_Excel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,                 # ứng dụng cửa sổ (không hiện terminal)
    disable_windowed_traceback=False,
    argv_emulation=True,           # macOS: nhận file kéo-thả vào icon
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
)

# macOS: gói thành .app
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="BCTC_PDF_to_Excel.app",
        icon=(_icns if os.path.exists(_icns) else None),
        bundle_identifier="vn.btg.bctc.pdf2excel",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleDisplayName": "BCTC PDF → Excel",
        },
    )
