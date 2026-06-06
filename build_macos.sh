#!/bin/bash
# ============================================================
#  Đóng gói ứng dụng thành .app chạy trên macOS
#  Yêu cầu: Python 3.9+ và Tesseract (brew install tesseract tesseract-lang)
# ============================================================
set -e
echo "[1/3] Cài đặt thư viện..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller

echo "[2/3] Đóng gói bằng PyInstaller..."
python3 -m PyInstaller --noconfirm pdf2excel.spec

echo "[3/3] Xong!"
echo "Ứng dụng nằm tại:  dist/BCTC_PDF_to_Excel.app"
echo "Mở bằng:  open dist/BCTC_PDF_to_Excel.app"
