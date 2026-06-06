#!/bin/bash
# Chạy ứng dụng trực tiếp (không cần đóng gói) trên macOS — double-click để mở
cd "$(dirname "$0")"
echo "Kiểm tra & cài thư viện (lần đầu có thể hơi lâu)..."
python3 -m pip install -r requirements.txt >/dev/null 2>&1
echo "Đang mở ứng dụng..."
python3 app.py
