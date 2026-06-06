# -*- coding: utf-8 -*-
"""
Chạy dòng lệnh:

    python cli.py file1.pdf file2.pdf -o ./Excel_output
    python cli.py *.pdf --hq            # chất lượng cao (DPI 300)
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bctc import engine


def main():
    ap = argparse.ArgumentParser(description="BCTC PDF (scan) -> Excel theo Thông tư 200")
    ap.add_argument("pdfs", nargs="+", help="Đường dẫn các file PDF (tối đa 10)")
    ap.add_argument("-o", "--out", default="Excel_output", help="Thư mục lưu Excel")
    ap.add_argument("--hq", action="store_true", help="Chất lượng cao (DPI 300, chậm hơn)")
    ap.add_argument("--lang", default="vie", help="Mã ngôn ngữ Tesseract (mặc định: vie)")
    args = ap.parse_args()

    pdfs = [p for p in args.pdfs if p.lower().endswith(".pdf")]
    if not pdfs:
        print("Không có file PDF hợp lệ."); sys.exit(1)

    dpis = (180, 220, 290) if args.hq else (180, 235)
    results = engine.convert_many(
        pdfs, args.out, lang=args.lang, dpis=dpis,
        log=lambda m: print(m, flush=True),
        progress=lambda d, t: print(f"   [{d}/{t}]", flush=True),
    )

    print("\n===== TỔNG KẾT =====")
    for r in results:
        if not r.get("out_path"):
            print(f"  ✖ {r['name']}: {r.get('error','lỗi')}"); continue
        bad = [d for d, ok, _ in (r.get("checks") or []) if not ok]
        conflicts = r.get("conflicts") or []
        flag = "✓" if not bad and not r.get("warnings") and not conflicts else "⚠"
        print(f"  {flag} {r['name']} -> {os.path.basename(r['out_path'])}")
        for w in (r.get("warnings") or []):
            print(f"       - {w}")
        for d in bad:
            print(f"       - lệch cân đối: {d}")
        if conflicts:
            print(f"       - {len(conflicts)} ô nên soát lại (hai lần đọc lệch)")


if __name__ == "__main__":
    main()
