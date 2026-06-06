@echo off
REM ============================================================
REM  Đóng gói ứng dụng thành 1 file .exe chạy trên Windows
REM  Yêu cầu: đã cài Python 3.9+ và Tesseract-OCR
REM ============================================================
echo [1/3] Cai dat thu vien...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

echo [2/3] Dong goi bang PyInstaller...
python -m PyInstaller --noconfirm pdf2excel.spec

echo [3/3] Xong!
echo File chay nam tai:  dist\BCTC_PDF_to_Excel.exe
pause
