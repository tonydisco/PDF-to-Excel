# -*- coding: utf-8 -*-
"""
So sánh 2 báo cáo benchmark (Markdown từ score.py): trước vs sau một thay đổi.
In delta balance-pass + coverage theo TỪNG file, đánh dấu CẢI THIỆN / THỤT LÙI.

Dùng:
  ./.venv/bin/python bench/compare.py bench/results-baseline-full.md bench/results-after-totalfix.md
"""
import sys
import re


def parse(md):
    """Đọc bảng score.py -> {file: dict(cdkt,kq,lc,npass,nchk,conf)}."""
    rows = {}
    for line in open(md, encoding="utf-8"):
        if not line.startswith("| ") or "File |" in line or "---" in line:
            continue
        c = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(c) < 7:
            continue
        name = c[0]
        try:
            cdkt, kq, lc = int(c[1]), int(c[2]), int(c[3])
        except ValueError:
            rows[name] = None          # dòng LỖI
            continue
        m = re.match(r"(\d+)/(\d+)", c[4])
        npass, nchk = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
        found = sum(1 for v in (cdkt, kq, lc) if v > 0)
        rows[name] = dict(found=found, npass=npass, nchk=nchk, conf=int(c[5]))
    return rows


def bal_clean(r):
    return r and r["nchk"] > 0 and r["npass"] == r["nchk"]


def main():
    a, b = parse(sys.argv[1]), parse(sys.argv[2])
    keys = list(a)
    improved = regressed = 0
    print(f"{'file':40} | before  | after   | Δ")
    print("-" * 72)
    for k in keys:
        ra, rb = a.get(k), b.get(k)
        if not ra or not rb:
            continue
        sa = f"{ra['found']}/3 {ra['npass']}/{ra['nchk']}"
        sb = f"{rb['found']}/3 {rb['npass']}/{rb['nchk']}"
        # "tốt hơn" = coverage tăng, hoặc nhiều phép cân đối ĐẠT hơn, hoặc ít conflict hơn
        score_a = (ra["found"], ra["npass"], -ra["conf"])
        score_b = (rb["found"], rb["npass"], -rb["conf"])
        tag = ""
        if score_b > score_a:
            tag = "✅ tốt hơn"; improved += 1
        elif score_b < score_a:
            tag = "⚠️ thụt lùi"; regressed += 1
        if tag:
            print(f"{k[:40]:40} | {sa:7} | {sb:7} | {tag}  c{ra['conf']}->{rb['conf']}")
    print("-" * 72)
    cov_a = sum(a[k]["found"] for k in keys if a[k]) / sum(1 for k in keys if a[k])
    cov_b = sum(b[k]["found"] for k in keys if b[k]) / sum(1 for k in keys if b[k])
    clean_a = sum(1 for k in keys if bal_clean(a.get(k)))
    clean_b = sum(1 for k in keys if bal_clean(b.get(k)))
    conf_a = sum(a[k]["conf"] for k in keys if a[k])
    conf_b = sum(b[k]["conf"] for k in keys if b[k])
    print(f"Coverage TB : {cov_a:.2f} -> {cov_b:.2f}")
    print(f"Balance sạch: {clean_a} -> {clean_b} file")
    print(f"Conflicts   : {conf_a} -> {conf_b}")
    print(f"Files tốt hơn: {improved} · thụt lùi: {regressed}")


if __name__ == "__main__":
    main()
