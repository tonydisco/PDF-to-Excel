#!/usr/bin/env bash
# Đóng gói Python sidecar (lõi OCR bctc) thành 1 binary độc lập bằng PyInstaller,
# đặt vào desktop/src-tauri/binaries/ đúng tên <target-triple> cho Tauri externalBin.
# In ra dòng "TRIPLE=<triple>" để build_macos.sh đọc.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"          # desktop/
ROOT="$(cd "$HERE/.." && pwd)"                 # repo root
PY="${PYTHON:-$ROOT/.venv/bin/python}"

# PY có thể là ĐƯỜNG DẪN file hoặc TÊN LỆNH trên PATH (CI đặt PYTHON=python).
if [ ! -x "$PY" ]; then
  if command -v "$PY" >/dev/null 2>&1; then PY="$(command -v "$PY")"
  else echo "Không thấy Python tại '$PY' (set PYTHON=... hoặc tạo .venv)"; exit 1; fi
fi

echo "==> PyInstaller build sidecar ($("$PY" --version 2>&1))"
"$PY" -m pip show pyinstaller >/dev/null 2>&1 || "$PY" -m pip install pyinstaller
# Tính năng AI (tuỳ chọn): bundle SDK Claude/Gemini + keyring + chứng chỉ TLS.
# Để best-effort — nếu chưa cài, PyInstaller vẫn build (lõi OCR không phụ thuộc).
AI_FLAGS=()
for pkg in anthropic google.genai keyring certifi; do
  if "$PY" -c "import importlib,sys; importlib.import_module('${pkg}')" >/dev/null 2>&1; then
    AI_FLAGS+=(--collect-all "$pkg")
  fi
done
# keyring tìm backend qua entry-point metadata -> cần copy metadata khi đóng băng.
"$PY" -c "import keyring" >/dev/null 2>&1 && AI_FLAGS+=(--copy-metadata keyring)

# Tesseract: nếu có tessbundle/ (chạy bundle_tesseract.sh) -> NHÚNG cả engine
# (app không cần cài Tesseract). Nếu không -> chỉ nhúng vie, dùng Tesseract hệ thống.
TESS_FLAGS=()
if [ -d "$HERE/tessbundle/tesseract" ]; then
  echo "==> Nhúng Tesseract relocatable (tessbundle/) -> app self-contained"
  TESS_FLAGS+=(--add-data "$HERE/tessbundle/tesseract:tesseract")
  TESS_FLAGS+=(--add-data "$HERE/tessbundle/tessdata:tessdata")
else
  echo "==> (dev) không thấy tessbundle -> dùng Tesseract hệ thống; chỉ nhúng vie"
  TESS_FLAGS+=(--add-data "$ROOT/tessdata/vie.traineddata:tessdata")
fi

"$PY" -m PyInstaller --noconfirm --onefile --name bctc-sidecar \
  "${TESS_FLAGS[@]}" \
  --collect-all fitz "${AI_FLAGS[@]}" --paths "$ROOT" \
  --distpath "$ROOT/dist_sidecar" --workpath "$ROOT/build_sidecar" --specpath "$ROOT/build_sidecar" \
  "$ROOT/sidecar.py"

BIN="$ROOT/dist_sidecar/bctc-sidecar"
ARCH="$(file "$BIN" | grep -oE 'x86_64|arm64' | head -1)"
case "$ARCH" in
  arm64)  TRIPLE="aarch64-apple-darwin" ;;
  x86_64) TRIPLE="x86_64-apple-darwin" ;;
  *) echo "Không nhận diện arch của binary: $ARCH"; exit 1 ;;
esac

mkdir -p "$HERE/src-tauri/binaries"
cp "$BIN" "$HERE/src-tauri/binaries/bctc-sidecar-$TRIPLE"
chmod +x "$HERE/src-tauri/binaries/bctc-sidecar-$TRIPLE"
echo "==> OK: src-tauri/binaries/bctc-sidecar-$TRIPLE ($ARCH)"

# Để `tauri dev` qua được validate externalBin trên máy có HOST triple khác arch
# sidecar (vd Python x86_64 trên Apple Silicon): đặt thêm 1 bản theo host triple.
# Dev KHÔNG dùng binary này (lib.rs dev spawn .venv), chỉ cần file tồn tại.
HOST_TRIPLE="$(rustc -vV 2>/dev/null | sed -n 's/^host: //p')"
if [ -n "$HOST_TRIPLE" ] && [ "$HOST_TRIPLE" != "$TRIPLE" ]; then
  cp "$BIN" "$HERE/src-tauri/binaries/bctc-sidecar-$HOST_TRIPLE"
  chmod +x "$HERE/src-tauri/binaries/bctc-sidecar-$HOST_TRIPLE"
  echo "==> (dev) copy thêm cho host triple: bctc-sidecar-$HOST_TRIPLE"
fi
echo "TRIPLE=$TRIPLE"
