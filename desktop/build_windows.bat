@echo off
REM Build ban Windows (.exe / .msi): dong goi sidecar Python (PyInstaller) + tauri build.
REM Yeu cau: .venv (deps + pyinstaller), Node/pnpm, Rust (rustup), Tesseract de DEV.
REM May NHAN ban cai van can cai Tesseract-OCR mot lan (goi tieng Viet da bundle).
setlocal
cd /d "%~dp0"

set PY=%PYTHON%
if "%PY%"=="" set PY=..\.venv\Scripts\python.exe
if not exist "%PY%" (
  echo Khong thay Python venv tai %PY%. Set PYTHON=... hoac tao .venv.
  exit /b 1
)

echo ==> [1/3] Dong goi sidecar
"%PY%" -m pip show pyinstaller >nul 2>&1 || "%PY%" -m pip install pyinstaller
"%PY%" -m PyInstaller --noconfirm --onefile --name bctc-sidecar ^
  --add-data "..\tessdata\vie.traineddata;tessdata" ^
  --collect-all fitz --paths ".." ^
  --distpath "..\dist_sidecar" --workpath "..\build_sidecar" --specpath "..\build_sidecar" ^
  "..\sidecar.py"
if errorlevel 1 exit /b 1

if not exist "src-tauri\binaries" mkdir "src-tauri\binaries"
copy /Y "..\dist_sidecar\bctc-sidecar.exe" "src-tauri\binaries\bctc-sidecar-x86_64-pc-windows-msvc.exe"

echo ==> [2/3] Chuan bi
call pnpm install

echo ==> [3/3] tauri build
call pnpm tauri build

echo.
echo ==> XONG. Ket qua o: src-tauri\target\release\bundle\
echo Luu y: may chay app can cai Tesseract-OCR (bo UB-Mannheim). Goi vie da bundle.
endlocal
