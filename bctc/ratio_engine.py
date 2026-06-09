# -*- coding: utf-8 -*-
"""
Tính CHỈ SỐ TÀI CHÍNH tất định trên máy từ số liệu đã bóc (Thông tư 200).
Triết lý: máy tính số (tất định, kiểm toán được); LLM chỉ DIỄN GIẢI sau.

Đầu vào: results = {stmt_key: {code: (cur, prior)}}  (CDKT/KQHDKD/LCTT)
Đầu ra : dict {groups[], altman, flags[]} cho UI + để gửi LLM (chỉ tỉ số).
"""


def _g(results, stmt, code, idx=0):
    """Lấy giá trị (idx 0=năm nay/cuối năm, 1=năm trước/đầu năm) hoặc None."""
    v = results.get(stmt, {}).get(code)
    if not v:
        return None
    return v[idx]


def _div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def _ratio(label, value, unit, formula, ok=None, warn=None, higher_better=True):
    """Gắn tone theo ngưỡng. ok/warn là ngưỡng; higher_better quyết định chiều."""
    tone = "neutral"
    if value is not None and ok is not None and warn is not None:
        if higher_better:
            tone = "ok" if value >= ok else ("warn" if value < warn else "neutral")
        else:
            tone = "ok" if value <= ok else ("warn" if value > warn else "neutral")
    return {"label": label, "value": value, "unit": unit, "formula": formula, "tone": tone}


def compute(results):
    R = results
    # --- nguồn ---
    ts_nh = _g(R, "CDKT", "100")          # tài sản ngắn hạn
    tien = _g(R, "CDKT", "110")           # tiền & tương đương
    htk = _g(R, "CDKT", "140")            # hàng tồn kho
    tong_ts = _g(R, "CDKT", "270")
    no_pt = _g(R, "CDKT", "300")          # nợ phải trả
    no_nh = _g(R, "CDKT", "310")          # nợ ngắn hạn
    von_csh = _g(R, "CDKT", "400")
    ln_chua_pp = _g(R, "CDKT", "421")     # LNST chưa phân phối (cho Altman X2)

    dt_thuan = _g(R, "KQHDKD", "10") or _g(R, "KQHDKD", "01")
    ln_gop = _g(R, "KQHDKD", "20")
    ln_tt = _g(R, "KQHDKD", "50")         # LN trước thuế
    lai_vay = _g(R, "KQHDKD", "23")       # chi phí lãi vay
    lnst = _g(R, "KQHDKD", "60")

    cfo = _g(R, "LCTT", "20")             # LC tiền thuần từ HĐKD

    # năm trước cho tăng trưởng
    dt_truoc = _g(R, "KQHDKD", "10", 1) or _g(R, "KQHDKD", "01", 1)
    lnst_truoc = _g(R, "KQHDKD", "60", 1)

    def pct(x):
        return None if x is None else round(x * 100, 1)

    groups = [
        {"key": "thanh_khoan", "label": "Thanh khoản", "items": [
            _ratio("Thanh toán hiện hành", _round(_div(ts_nh, no_nh)), "x", "TSNH(100) / Nợ NH(310)", ok=1.5, warn=1.0),
            _ratio("Thanh toán nhanh", _round(_div((ts_nh - htk) if (ts_nh is not None and htk is not None) else None, no_nh)), "x", "(TSNH−HTK) / Nợ NH", ok=1.0, warn=0.7),
            _ratio("Thanh toán tiền mặt", _round(_div(tien, no_nh)), "x", "Tiền(110) / Nợ NH(310)", ok=0.5, warn=0.1),
        ]},
        {"key": "don_bay", "label": "Đòn bẩy & khả năng thanh toán", "items": [
            _ratio("Nợ / Vốn chủ", _round(_div(no_pt, von_csh)), "x", "Nợ PT(300) / VCSH(400)", ok=1.0, warn=2.0, higher_better=False),
            _ratio("Nợ / Tổng tài sản", pct(_div(no_pt, tong_ts)), "%", "Nợ PT(300) / Tổng TS(270)", ok=50, warn=70, higher_better=False),
            _ratio("Tự chủ tài chính", pct(_div(von_csh, tong_ts)), "%", "VCSH(400) / Tổng TS(270)", ok=50, warn=30),
        ]},
        {"key": "sinh_loi", "label": "Sinh lời", "items": [
            _ratio("ROA", pct(_div(lnst, tong_ts)), "%", "LNST(60) / Tổng TS(270)", ok=5, warn=0),
            _ratio("ROE", pct(_div(lnst, von_csh)), "%", "LNST(60) / VCSH(400)", ok=10, warn=0),
            _ratio("Biên LN gộp", pct(_div(ln_gop, dt_thuan)), "%", "LN gộp(20) / DT thuần(10)", ok=20, warn=5),
            _ratio("Biên LN sau thuế", pct(_div(lnst, dt_thuan)), "%", "LNST(60) / DT thuần(10)", ok=8, warn=0),
        ]},
        {"key": "hoat_dong_dong_tien", "label": "Hiệu quả & dòng tiền", "items": [
            _ratio("Vòng quay tổng tài sản", _round(_div(dt_thuan, tong_ts)), "x", "DT thuần(10) / Tổng TS(270)", ok=1.0, warn=0.3),
            _ratio("Dòng tiền HĐKD / Nợ NH", _round(_div(cfo, no_nh)), "x", "CFO(LC 20) / Nợ NH(310)", ok=0.4, warn=0.0),
            _ratio("Tăng trưởng doanh thu", pct(_div((dt_thuan - dt_truoc) if (dt_thuan is not None and dt_truoc) else None, dt_truoc)), "%", "Δ DT thuần so năm trước", ok=0, warn=-0.0001),
            _ratio("Tăng trưởng LNST", pct(_div((lnst - lnst_truoc) if (lnst is not None and lnst_truoc) else None, lnst_truoc)), "%", "Δ LNST so năm trước", ok=0, warn=-0.0001),
        ]},
    ]

    # --- Altman Z'' (DN phi sản xuất / thị trường mới nổi) ---
    altman = None
    if None not in (ts_nh, no_nh, tong_ts, von_csh, no_pt) and tong_ts:
        x1 = (ts_nh - no_nh) / tong_ts
        x2 = (ln_chua_pp / tong_ts) if ln_chua_pp is not None else 0.0
        ebit = (ln_tt + (lai_vay or 0)) if ln_tt is not None else None
        x3 = (ebit / tong_ts) if ebit is not None else 0.0
        x4 = no_pt and (von_csh / no_pt) or 0.0
        z = 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4
        zone = "an_toan" if z > 2.6 else ("nguy_hiem" if z < 1.1 else "canh_bao")
        zlabel = {"an_toan": "An toàn", "canh_bao": "Cảnh báo", "nguy_hiem": "Nguy hiểm"}[zone]
        altman = {"value": round(z, 2), "zone": zone, "label": zlabel}

    # --- cờ cảnh báo gộp (để LLM/UI nhấn) ---
    flags = []
    for grp in groups:
        for it in grp["items"]:
            if it["tone"] == "warn" and it["value"] is not None:
                flags.append(it["label"])
    if altman and altman["zone"] != "an_toan":
        flags.append(f"Altman Z'' = {altman['value']} ({altman['label']})")

    return {"groups": groups, "altman": altman, "flags": flags}


def _round(x, n=2):
    return None if x is None else round(x, n)
