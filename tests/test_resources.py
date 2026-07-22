# -*- coding: utf-8 -*-
from tests.regression.resources import ResourceProbe


def test_probe_do_duoc_thoi_gian_va_cpu():
    with ResourceProbe() as p:
        total = 0
        for i in range(2_000_000):     # đủ nặng để CPU-giây > 0
            total += i
    assert p.wall > 0
    assert p.cpu > 0
    assert p.peak_rss_mb > 0


def test_probe_cpu_khong_vuot_qua_wall_nhan_so_luong_cpu():
    import os
    with ResourceProbe() as p:
        sum(range(500_000))
    assert p.cpu <= p.wall * max(1, os.cpu_count() or 1) + 1.0
