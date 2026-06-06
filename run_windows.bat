@echo off
REM Chay ung dung truc tiep (khong can dong goi) tren Windows
cd /d "%~dp0"
echo Kiem tra & cai thu vien (lan dau co the hoi lau)...
python -m pip install -r requirements.txt >nul 2>&1
echo Dang mo ung dung...
python app.py
if errorlevel 1 pause
