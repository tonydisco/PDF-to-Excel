#!/usr/bin/env bash
# Tạo gói Tesseract RELOCATABLE (macOS) tại desktop/tessbundle/ để nhúng vào app
# -> bản đóng gói KHÔNG cần người dùng cài Tesseract.
#
# Cách làm: copy `tesseract` + dùng dylibbundler gom mọi .dylib phụ thuộc và sửa
# rpath về @executable_path/lib (đã kiểm chứng chạy độc lập). tessdata gồm vie
# (repo) + eng/osd (hệ thống).
#
# Yêu cầu máy build: brew install tesseract dylibbundler
# Layout ra:  tessbundle/tesseract/bin/{tesseract, lib/*.dylib}
#             tessbundle/tessdata/{vie,eng,osd}.traineddata
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"           # desktop/
ROOT="$(cd "$HERE/.." && pwd)"                  # repo root
OUT="$HERE/tessbundle"

TESS="$(command -v tesseract || true)"
[ -n "$TESS" ] || { echo "❌ Cần Tesseract: brew install tesseract"; exit 1; }
command -v dylibbundler >/dev/null || { echo "❌ Cần dylibbundler: brew install dylibbundler"; exit 1; }

echo "==> Tesseract: $TESS ($("$TESS" --version 2>&1 | head -1))"
rm -rf "$OUT"
mkdir -p "$OUT/tesseract/bin/lib" "$OUT/tessdata"

cp "$TESS" "$OUT/tesseract/bin/tesseract"
chmod +w "$OUT/tesseract/bin/tesseract"
echo "==> Gom dylib + sửa rpath (@executable_path/lib) + ad-hoc sign"
dylibbundler -of -b -x "$OUT/tesseract/bin/tesseract" -d "$OUT/tesseract/bin/lib" -p @executable_path/lib >/dev/null

# tessdata: vie (repo) + eng/osd (hệ thống). Dò trực tiếp (tránh find|head + pipefail).
cp "$ROOT/tessdata/vie.traineddata" "$OUT/tessdata/"
for t in eng osd; do
  for d in /opt/homebrew/share/tessdata /usr/local/share/tessdata /usr/share/tessdata "$(dirname "$TESS")/../share/tessdata"; do
    if [ -f "$d/$t.traineddata" ]; then cp "$d/$t.traineddata" "$OUT/tessdata/"; break; fi
  done
  [ -f "$OUT/tessdata/$t.traineddata" ] || echo "   ⚠ thiếu $t.traineddata (bỏ qua)"
done

echo "==> tessbundle xong ($(du -sh "$OUT" | cut -f1)) · $(ls "$OUT/tesseract/bin/lib" | wc -l | tr -d ' ') dylib"
