# -*- coding: utf-8 -*-
"""
Chọn số luồng OCR chạy song song.

Mỗi luồng gọi một tiến trình tesseract riêng (OMP_THREAD_LIMIT=1), nên số
luồng chính là số nhân CPU bị chiếm dụng hoàn toàn. Đặt bằng số LUỒNG LOGIC
sẽ ghim sạch CPU: máy nóng, quạt kêu, giao diện giật.

Máy đích là Windows 10, 4 GB RAM, 2-4 nhân — luôn phải chừa headroom cho
luồng giao diện và hệ điều hành.
"""
import os

MODE_ECO = "eco"
MODE_BALANCED = "balanced"
MODE_MAX = "max"

MODES = (MODE_ECO, MODE_BALANCED, MODE_MAX)

MODE_LABELS = {
    MODE_ECO: "Tiết kiệm điện",
    MODE_BALANCED: "Cân bằng",
    MODE_MAX: "Tối đa",
}


def worker_count(mode=MODE_BALANCED, logical=None):
    """
    Số luồng OCR nên dùng.

    eco      : 1 luồng — máy yếu, hoặc chạy nền lâu mà không muốn nóng.
    balanced : ~nửa số luồng logic, chừa 1 — mặc định.
    max      : tất cả trừ 1 — chỉ khi người dùng chủ động chọn.
    """
    if logical is None:
        logical = os.cpu_count() or 2
    logical = max(1, int(logical))

    if mode == MODE_ECO:
        return 1
    if mode == MODE_MAX:
        return max(1, logical - 1)
    return max(1, logical // 2 - 1)
