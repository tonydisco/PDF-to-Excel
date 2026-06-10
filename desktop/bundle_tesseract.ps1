# Gói Tesseract (Windows) vào desktop\tessbundle\ để NHÚNG vào app
# -> bản đóng gói không cần người dùng cài Tesseract.
# Windows tìm DLL cạnh .exe -> chỉ cần copy tesseract.exe + *.dll phẳng.
# Yêu cầu: đã cài Tesseract (vd: choco install tesseract) hoặc set $env:TESSERACT_DIR.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
$out  = Join-Path $here "tessbundle"

$src = $env:TESSERACT_DIR
if (-not $src) {
  foreach ($p in @("C:\Program Files\Tesseract-OCR", "C:\Program Files (x86)\Tesseract-OCR")) {
    if (Test-Path (Join-Path $p "tesseract.exe")) { $src = $p; break }
  }
}
if (-not $src) { throw "Khong thay Tesseract-OCR. Cai (choco install tesseract) hoac set TESSERACT_DIR." }
Write-Host "==> Tesseract: $src"

if (Test-Path $out) { Remove-Item -Recurse -Force $out }
New-Item -ItemType Directory -Force -Path "$out\tesseract", "$out\tessdata" | Out-Null

Copy-Item (Join-Path $src "tesseract.exe") "$out\tesseract\"
Copy-Item (Join-Path $src "*.dll") "$out\tesseract\" -ErrorAction SilentlyContinue

# tessdata: vie (repo) + eng/osd (ban cai)
Copy-Item (Join-Path $root "tessdata\vie.traineddata") "$out\tessdata\"
foreach ($t in @("eng", "osd")) {
  $f = Join-Path $src "tessdata\$t.traineddata"
  if (Test-Path $f) { Copy-Item $f "$out\tessdata\" } else { Write-Host "   ! thieu $t.traineddata" }
}
$dll = (Get-ChildItem "$out\tesseract\*.dll" | Measure-Object).Count
Write-Host "==> tessbundle xong ($dll DLL)"
