#!/bin/bash
# ============================================================
#  Đóng gói ứng dụng thành .app chạy trên macOS
#  Yêu cầu: Python 3.9+ và Tesseract (brew install tesseract tesseract-lang)
# ============================================================
set -e
echo "[1/4] Cài đặt thư viện..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller

echo "[2/4] Tạo icon..."
python3 assets/make_icon.py
iconutil -c icns assets/icon.iconset -o assets/icon.icns || true

echo "[3/4] Đóng gói bằng PyInstaller..."
python3 -m PyInstaller --noconfirm pdf2excel.spec

echo "[4/4] Xong!"
echo "Ứng dụng nằm tại:  dist/BCTC_PDF_to_Excel.app"
echo "Mở bằng:  open dist/BCTC_PDF_to_Excel.app"
