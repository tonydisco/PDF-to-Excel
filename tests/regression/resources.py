# -*- coding: utf-8 -*-
"""
Đo tài nguyên một đoạn xử lý: thời gian thực, CPU-giây, RSS đỉnh.

CPU-giây là chỉ số quan trọng nhất cho mục tiêu "giảm nhiệt": nó đo tổng công
CPU đã bỏ ra, không phụ thuộc việc chạy song song bao nhiêu luồng. Giảm
CPU-giây = giảm nhiệt thật, còn giảm thời gian thực có thể chỉ là chạy nhiều
luồng hơn (thậm chí NÓNG hơn).
"""
import os
import time


def _peak_rss_mb():
    """RSS đỉnh của tiến trình, tính bằng MB. Trả 0.0 nếu không đo được."""
    try:
        import resource
        val = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux trả KB, macOS trả byte
        return val / (1024.0 * 1024.0) if val > 1 << 20 else val / 1024.0
    except ImportError:
        pass
    try:                                    # Windows
        import ctypes
        from ctypes import wintypes

        class _PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD),
                        ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]

        c = _PMC()
        c.cb = ctypes.sizeof(c)
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return c.PeakWorkingSetSize / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def _cpu_seconds():
    """CPU-giây của tiến trình VÀ các tiến trình con (tesseract chạy ở con)."""
    t = time.process_time()
    try:
        import resource
        ch = resource.getrusage(resource.RUSAGE_CHILDREN)
        t += ch.ru_utime + ch.ru_stime
    except ImportError:
        pass
    return t


class ResourceProbe(object):
    """Context manager đo tài nguyên. Dùng: with ResourceProbe() as p: ..."""

    def __init__(self):
        self.wall = 0.0
        self.cpu = 0.0
        self.peak_rss_mb = 0.0

    def __enter__(self):
        self._t0 = time.time()
        self._c0 = _cpu_seconds()
        return self

    def __exit__(self, *exc):
        self.wall = time.time() - self._t0
        self.cpu = _cpu_seconds() - self._c0
        self.peak_rss_mb = _peak_rss_mb()
        return False
