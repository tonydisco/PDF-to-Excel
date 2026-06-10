# Build ban Windows (.exe/.msi): dong goi sidecar (PyInstaller) + tauri build.
# Neu co tessbundle\ (chay bundle_tesseract.ps1) -> NHUNG ca Tesseract.
# Yeu cau: .venv (deps + pyinstaller), Node/pnpm, Rust (MSVC), VS C++ Build Tools.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$root = Split-Path -Parent $here

$py = $env:PYTHON
if (-not $py) { $py = Join-Path $root ".venv\Scripts\python.exe" }
# $py co the la duong dan file HOAC ten lenh tren PATH (CI dat PYTHON=python).
if (-not (Test-Path $py)) {
  $cmd = Get-Command $py -ErrorAction SilentlyContinue
  if ($cmd) { $py = $cmd.Source } else { throw "Khong thay Python: $py (set PYTHON=... hoac tao .venv)" }
}

Write-Host "==> [1/3] Dong goi sidecar"
& $py -m pip show pyinstaller *> $null
if ($LASTEXITCODE -ne 0) { & $py -m pip install pyinstaller }

$piArgs = @("--noconfirm", "--onefile", "--name", "bctc-sidecar", "--collect-all", "fitz", "--paths", "..")

if (Test-Path "tessbundle\tesseract\tesseract.exe") {
  Write-Host "==> Nhung Tesseract (tessbundle) -> app self-contained"
  $piArgs += @("--add-data", "tessbundle\tesseract;tesseract", "--add-data", "tessbundle\tessdata;tessdata")
} else {
  Write-Host "==> (dev) khong co tessbundle -> dung Tesseract he thong; chi nhung vie"
  $piArgs += @("--add-data", "..\tessdata\vie.traineddata;tessdata")
}

foreach ($p in @("anthropic", "google.genai", "keyring", "certifi")) {
  & $py -c "import $p" *> $null
  if ($LASTEXITCODE -eq 0) { $piArgs += @("--collect-all", $p) }
}
& $py -c "import keyring" *> $null
if ($LASTEXITCODE -eq 0) { $piArgs += @("--copy-metadata", "keyring") }

$piArgs += @("--distpath", "..\dist_sidecar", "--workpath", "..\build_sidecar", "--specpath", "..\build_sidecar", "..\sidecar.py")
& $py -m PyInstaller @piArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

New-Item -ItemType Directory -Force -Path "src-tauri\binaries" | Out-Null
Copy-Item "..\dist_sidecar\bctc-sidecar.exe" "src-tauri\binaries\bctc-sidecar-x86_64-pc-windows-msvc.exe" -Force

Write-Host "==> [2/3] pnpm install"
& pnpm install --no-frozen-lockfile
if ($LASTEXITCODE -ne 0) { throw "pnpm install failed" }

Write-Host "==> [3/3] tauri build"
& pnpm tauri build
if ($LASTEXITCODE -ne 0) { throw "tauri build failed" }

Write-Host "==> XONG: src-tauri\target\release\bundle\"
