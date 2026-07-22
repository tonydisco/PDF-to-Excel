# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec dùng chung cho Windows (.exe) và macOS (.app).
Build:  pyinstaller pdf2excel.spec
"""
import os
import sys
from PyInstaller.utils.hooks import collect_submodules

datas = [
    ("assets", "assets"),          # icon + sprite
]

# Tesseract-OCR portable đi kèm app (nếu có thư mục 'tesseract/').
# CI Windows tạo thư mục này -> app chạy độc lập, không cần cài Tesseract.
# vie.traineddata đã nằm trong tesseract/tessdata/ nên KHÔNG đóng gói thêm
# thư mục tessdata/ ở gốc — trước đây bị gói hai lần.
if os.path.isdir("tesseract"):
    datas.append(("tesseract", "tesseract"))
else:
    # Chạy từ mã nguồn / build macOS: dùng tessdata cạnh mã nguồn.
    datas.append(("tessdata", "tessdata"))

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

# Splash: phản hồi thị giác ngay khi bấm mở, trong lúc Python + thư viện nạp.
# Chỉ hỗ trợ trên Windows/Linux (PyInstaller chưa hỗ trợ splash trên macOS).
_splash_img = os.path.join("assets", "icon_256.png")
splash = None
if sys.platform != "darwin" and os.path.exists(_splash_img):
    splash = Splash(
        _splash_img,
        binaries=a.binaries,
        datas=a.datas,
        text_pos=(10, 240),
        text_size=10,
        text_color="black",
    )

_exe_args = [pyz, a.scripts]
if splash is not None:
    _exe_args.append(splash)
_exe_args.append([])

exe = EXE(
    *_exe_args,
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
_coll_args = [exe]
if splash is not None:
    _coll_args.append(splash.binaries)
_coll_args += [a.binaries, a.datas]

coll = COLLECT(
    *_coll_args,
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
