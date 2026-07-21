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

# Tesseract-OCR portable đi kèm app (nếu có thư mục 'tesseract/').
# CI Windows sẽ tạo thư mục này -> .exe chạy độc lập, không cần cài Tesseract.
if os.path.isdir("tesseract"):
    datas.append(("tesseract", "tesseract"))

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
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,         # onedir: binaries/datas do COLLECT() gom
    name="BCTC_PDF_to_Excel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                     # UPX: tốn thời gian giải nén mỗi lần chạy
                                   # + là tác nhân kinh điển gây false-positive
                                   # antivirus trên Windows
    console=False,                 # ứng dụng cửa sổ (không hiện terminal)
    disable_windowed_traceback=False,
    argv_emulation=True,           # macOS: nhận file kéo-thả vào icon
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
)

# onedir: giải nén MỘT lần lúc cài đặt, các lần mở sau chạy thẳng.
# Chế độ onefile cũ giải nén lại toàn bộ payload ra %TEMP% mỗi lần khởi động,
# rồi bị Windows Defender quét lại từ đầu — trên máy Win10 ổ HDD mất 30-90
# giây MỖI LẦN MỞ.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BCTC_PDF_to_Excel",
)

# macOS: gói thành .app
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="BCTC_PDF_to_Excel.app",
        icon=(_icns if os.path.exists(_icns) else None),
        bundle_identifier="vn.btg.bctc.pdf2excel",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleDisplayName": "BCTC PDF → Excel",
        },
    )
