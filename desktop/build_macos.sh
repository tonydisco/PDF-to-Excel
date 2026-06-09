#!/usr/bin/env bash
# Build bản macOS (.app + .dmg): đóng gói sidecar Python rồi tauri build,
# target khớp arch của sidecar (xử lý cả máy có Python x86_64 trên Apple Silicon).
#
# Yêu cầu: .venv (deps + pyinstaller), Node/pnpm, Rust (rustup), Tesseract để DEV;
# máy NHẬN bản .dmg vẫn cần cài Tesseract một lần (gói tiếng Việt đã bundle sẵn).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
export PATH="$HOME/.cargo/bin:$PATH"

echo "==> [1/3] Đóng gói sidecar"
TRIPLE="$(bash build_sidecar.sh | sed -n 's/^TRIPLE=//p' | tail -1)"
[ -n "$TRIPLE" ] || { echo "Không lấy được TRIPLE từ build_sidecar.sh"; exit 1; }
echo "==> Tauri target: $TRIPLE"

echo "==> [2/3] Chuẩn bị"
rustup target add "$TRIPLE" 2>/dev/null || true
pnpm install

echo "==> [3/3] tauri build"
pnpm tauri build --target "$TRIPLE"

echo ""
echo "==> XONG. Kết quả:"
ls -1 "src-tauri/target/$TRIPLE/release/bundle/dmg/"*.dmg 2>/dev/null || echo "  (chưa thấy .dmg)"
ls -1d "src-tauri/target/$TRIPLE/release/bundle/macos/"*.app 2>/dev/null || true
echo "Lưu ý: máy chạy app cần cài Tesseract (brew install tesseract). Gói vie đã bundle."
