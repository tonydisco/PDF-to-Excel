#!/usr/bin/env bash
# Đóng gói Python sidecar (lõi OCR bctc) thành 1 binary độc lập bằng PyInstaller,
# đặt vào desktop/src-tauri/binaries/ đúng tên <target-triple> cho Tauri externalBin.
# In ra dòng "TRIPLE=<triple>" để build_macos.sh đọc.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"          # desktop/
ROOT="$(cd "$HERE/.." && pwd)"                 # repo root
PY="${PYTHON:-$ROOT/.venv/bin/python}"

[ -x "$PY" ] || { echo "Không thấy Python venv tại $PY (set PYTHON=... hoặc tạo .venv)"; exit 1; }

echo "==> PyInstaller build sidecar ($("$PY" --version 2>&1))"
"$PY" -m pip show pyinstaller >/dev/null 2>&1 || "$PY" -m pip install pyinstaller
"$PY" -m PyInstaller --noconfirm --onefile --name bctc-sidecar \
  --add-data "$ROOT/tessdata/vie.traineddata:tessdata" \
  --collect-all fitz --paths "$ROOT" \
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
echo "TRIPLE=$TRIPLE"
