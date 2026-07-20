# -*- coding: utf-8 -*-
"""
Chỉ số chất lượng bóc tách.

Tầng 1 (cần đáp án): đúng / sót / lệch / thừa.
Tầng 2 (không cần đáp án): độ phủ khung + tỷ lệ đạt kiểm tra cân đối.

Tầng 2 tồn tại vì chỉ có 14 PDF là có đáp án, quá mỏng để phủ các nhóm file
trước 2015, file ngân hàng, file mojibake. Độ phủ là proxy trực tiếp cho "sót
data"; cân đối là proxy cho "lệch data".
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from bctc import templates as T      # noqa: E402
from bctc import engine              # noqa: E402


def canon(code):
    """
    Dạng chính tắc để so khớp mã số.

    Báo cáo in mã là '1', khung template ghi '01' -> phải quy về một dạng.
    Giữ nguyên hậu tố chữ ('411a').
    """
    s = str(code).strip()
    m = re.match(r"^0*(\d+)([abc]?)$", s)
    if not m:
        return s
    return m.group(1) + m.group(2)


def _codes(stmt_key):
    """Tập mã số của khung, dạng chính tắc."""
    if stmt_key == "LCTT":
        tpl_codes = (T.codes_of(T.LUU_CHUYEN_TIEN_TE_GT)
                     | T.codes_of(T.LUU_CHUYEN_TIEN_TE_TT))
    else:
        tpl_codes = T.codes_of(T.STATEMENTS[stmt_key][1])
    return {canon(c) for c in tpl_codes}


def _norm_map(d):
    return {canon(k): v for k, v in (d or {}).items()}


def compare(expected, actual):
    """
    So từng ô. Ô đáp án rỗng hoặc bằng 0 được coi là "không có số liệu" và
    chỉ dùng để phát hiện 'thừa'.
    """
    exp, act = _norm_map(expected), _norm_map(actual)
    out = {"dung": 0, "sot": 0, "lech": 0, "thua": 0}
    for code in set(exp) | set(act):
        e = exp.get(code, (None, None))
        a = act.get(code, (None, None))
        for i in (0, 1):
            g, o = e[i], a[i]
            has_g = g is not None and g != 0
            has_o = o is not None and o != 0
            if has_g and o == g:
                out["dung"] += 1
            elif has_g and not has_o:
                out["sot"] += 1
            elif has_g:
                out["lech"] += 1
            elif has_o:
                out["thua"] += 1
    return out


def coverage(values, stmt_key):
    """Tỷ lệ mã trong khung có ít nhất một giá trị khác None."""
    codes = _codes(stmt_key)
    if not codes:
        return 0.0
    got = {c for c, v in _norm_map(values).items()
           if c in codes and v and any(x is not None for x in v)}
    return len(got) / float(len(codes))


def balance_score(cdkt):
    """(số phép kiểm tra đạt, tổng số phép chạy được) trên Bảng cân đối."""
    checks = engine._check_balance(cdkt or {})
    return sum(1 for _, ok, _ in checks if ok), len(checks)
