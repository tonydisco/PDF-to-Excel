# -*- coding: utf-8 -*-
"""Canh các quyết định đóng gói không bị vô tình đảo ngược."""
import os
import re

SPEC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "pdf2excel.spec")


def _doc_spec():
    with open(SPEC, encoding="utf-8") as fh:
        return fh.read()


def test_dung_che_do_onedir():
    """Phải có COLLECT() — onefile giải nén lại toàn bộ payload MỖI lần mở."""
    src = _doc_spec()
    assert "COLLECT(" in src, "thiếu COLLECT() -> đang là onefile"


def test_exe_khong_om_binaries():
    """EXE() chỉ nhận a.scripts; binaries/datas do COLLECT() gom."""
    src = _doc_spec()
    m = re.search(r"exe\s*=\s*EXE\((.*?)\n\)", src, re.S)
    assert m, "không tìm thấy khối EXE("
    than = m.group(1)
    assert "a.binaries" not in than, "EXE() còn ôm a.binaries -> vẫn là onefile"
    assert "a.datas" not in than, "EXE() còn ôm a.datas -> vẫn là onefile"


def test_tat_upx():
    """UPX vừa tốn thời gian giải nén vừa kích hoạt false-positive antivirus."""
    src = _doc_spec()
    assert re.search(r"upx\s*=\s*False", src), "UPX chưa tắt"
    assert not re.search(r"upx\s*=\s*True", src), "còn chỗ đặt upx=True"
