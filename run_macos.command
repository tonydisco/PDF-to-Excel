#!/bin/bash
# Chạy ứng dụng trên macOS — double-click để mở.
# Tự chọn Python có Tk (giao diện) hoạt động, cài thư viện, đảm bảo Tesseract.
cd "$(dirname "$0")"

echo "==> Tìm Python có giao diện (Tk) hoạt động..."
WORKS=""
for PY in /usr/bin/python3 python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  command -v "$PY" >/dev/null 2>&1 || [ -x "$PY" ] || continue
  if "$PY" -c "import tkinter; r=tkinter.Tk(); r.destroy()" >/dev/null 2>&1; then
    WORKS="$PY"; break
  fi
done

if [ -z "$WORKS" ]; then
  echo ""
  echo "!! Khong tim thay Python co Tk chay duoc tren may nay."
  echo "   Cach don gian nhat: tai & cai Python tai https://www.python.org/downloads/"
  echo "   (ban python.org da kem san Tk tuong thich), roi double-click lai file nay."
  echo ""
  read -p "Nhan Enter de dong..." _; exit 1
fi
echo "    Dung: $WORKS"

echo "==> Cài thư viện Python..."
"$WORKS" -m pip install -r requirements.txt >/dev/null 2>&1 \
 || "$WORKS" -m pip install --user -r requirements.txt >/dev/null 2>&1 \
 || "$WORKS" -m pip install --user --break-system-packages -r requirements.txt >/dev/null 2>&1

# Tesseract (OCR) — chỉ cần phần mã máy; gói tiếng Việt đã đính kèm trong tessdata/
if ! command -v tesseract >/dev/null 2>&1 \
   && [ ! -x /opt/homebrew/bin/tesseract ] && [ ! -x /usr/local/bin/tesseract ]; then
  echo "==> Cài Tesseract (OCR) qua Homebrew..."
  command -v brew >/dev/null 2>&1 && brew install tesseract
fi

echo "==> Đang mở ứng dụng..."
hash -r 2>/dev/null || true
"$WORKS" app.py
